from nltk.tokenize.treebank import TreebankWordDetokenizer

from .cache import get_redis
from .db import get_db
from flask import current_app, g
from nltk.corpus import stopwords

from .helper import get_lines


def get_label_titles_dict(dump_id, candidate_labels):
    r = get_redis(dump_id)
    db = get_db()

    cursor = db.cursor(dictionary=True)

    sql = '''CREATE TEMPORARY TABLE `current_labels` (
            `id` INT UNSIGNED NOT NULL,
            `label` VARCHAR(255) NOT NULL
        ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin'''
    cursor.execute(sql)

    sql_insert_to_current_labels = 'INSERT INTO `current_labels` VALUES (%s, %s)'

    candidate_labels_unique = set(map(lambda candidate_label: candidate_label['name'], candidate_labels))
    for label_name in candidate_labels_unique:
        id = r.get(label_name)
        if id is not None:
            data = (id, label_name)
            cursor.execute(sql_insert_to_current_labels, data)

    sql = '''SELECT `current_labels`.`label`, `labels`.`counter` AS `label_counter`,
                    `labels_articles`.`article_id`, `labels_articles`.`title`, `labels_articles`.`counter` AS `label_title_counter`,
                    `articles`.`counter` AS `article_counter`, `articles`.`caption`, `articles`.`redirect_to_title`
                    FROM `current_labels` JOIN `labels` ON `current_labels`.`id` = `labels`.`id`
                                          JOIN `labels_articles` ON `current_labels`.`id` = `labels_articles`.`label_id`
                                          JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`'''

    cursor.execute(sql)

    label_titles_dict = {}
    for row in cursor:
        label_name = row['label']
        title = {
            'article_id': row['article_id'],
            'title': row['title'],
            'label_title_counter': row['label_title_counter'],
            'article_counter': row['article_counter'],
            'caption': row['caption'],
            'redirect_to_title': row['redirect_to_title']
        }
        if title['caption'] is not None:
            title['caption'] = title['caption'].decode('utf-8')
        if label_name not in label_titles_dict:
            label_titles_dict[label_name] = {
                'counter': row['label_counter'],
                'titles': [title]
            }
        else:
            label_titles_dict[label_name]['titles'].append(title)
    cursor.close()

    return label_titles_dict


def get_labels_exact(article_id, algorithm_normalized_json):
    lines = get_lines(article_id)

    dump_id = algorithm_normalized_json['knowledge_base']
    stops = set(stopwords.words('english'))

    candidate_labels = []
    for ngrams in range(1, current_app.config['MAX_NGRAMS'] + 1):
        for line_nr, line in enumerate(lines):
            for label_nr, label in enumerate(line):
                if label_nr + ngrams > len(line):  # cannot construct ngram of length "ngrams" starting from "label"
                    break

                label = TreebankWordDetokenizer().detokenize(line[label_nr:label_nr + ngrams])

                if algorithm_normalized_json['skipstopwords'] and label in stops:
                    continue

                candidate_labels.append({
                    'name': label,
                    'line': line_nr,
                    'start': label_nr,
                    'ngrams': ngrams,
                })

    label_titles_dict = get_label_titles_dict(dump_id, candidate_labels)
    labels = []
    for candidate_label in candidate_labels:
        label_name = candidate_label['name']
        if label_name in label_titles_dict:
            candidate_label['titles'] = label_titles_dict[label_name]['titles']
            labels.append(candidate_label)

    return labels
