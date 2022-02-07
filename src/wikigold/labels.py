import time

from .cache import get_redis, get_cached_label_id
from .db import get_db
from flask import current_app, g
from nltk.corpus import stopwords


def get_label_titles_dict(dump_id, candidate_labels, min_label_count=1, min_label_articles_count=1):
    db = get_db()

    cursor = db.cursor(dictionary=True)

    start_time = time.time_ns()

    candidate_labels_unique = set(map(lambda candidate_label: candidate_label['name'], candidate_labels))
    candidate_labels_ids = []
    for label_name in candidate_labels_unique:
        id = get_cached_label_id(label_name)
        if id is not None:
            candidate_labels_ids.append(str(id))
    candidate_labels_ids_str = ','.join(candidate_labels_ids)
    sql = f'''SELECT `labels`.`label`, `labels`.`counter` AS `label_counter`,
                    `labels_articles`.`article_id`, `labels_articles`.`title`, `labels_articles`.`counter` AS `label_title_counter`,
                    `articles`.`counter` AS `article_counter`, `articles`.`caption`, `articles`.`redirect_to_title`
                    FROM `labels` JOIN `labels_articles` ON `labels`.`id` = `labels_articles`.`label_id`
                                  JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`
                    WHERE `labels`.`id` IN ({candidate_labels_ids_str})
                                  AND `labels`.`counter` >= %s AND `labels_articles`.`counter` >= %s'''

    cursor.execute(sql, (min_label_count, min_label_articles_count))

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

    print('runtime: ', (time.time_ns() - start_time)/1000000000)

    return label_titles_dict


def get_labels_exact(lines, knowledge_base, skip_stop_words=False, min_label_count=1, min_label_articles_count=1):
    stops = set(stopwords.words('english'))

    candidate_labels = []
    for ngrams in range(1, current_app.config['MAX_NGRAMS'] + 1):
        for line_nr, line in enumerate(lines):
            line_content = line['content']
            line_tokens = line['tokens']
            for token_nr, token in enumerate(line_tokens):
                # cannot construct ngram of length "ngrams" starting from "token"
                if token_nr + ngrams > len(line_tokens):
                    break

                # continuous ngram model
                label_start = line_tokens[token_nr][0]  # begin of the first gram
                label_end = line_tokens[token_nr + ngrams - 1][1] # end of the last gram
                label = line_content[label_start:label_end]

                if skip_stop_words and label in stops:
                    continue

                candidate_labels.append({
                    'name': label,
                    'line': line_nr,
                    'start': token_nr,
                    'ngrams': ngrams,
                })

    label_titles_dict = get_label_titles_dict(knowledge_base, candidate_labels, min_label_count, min_label_articles_count)
    labels = []
    for candidate_label in candidate_labels:
        label_name = candidate_label['name']
        if label_name in label_titles_dict:
            candidate_label['counter'] = label_titles_dict[label_name]['counter']
            candidate_label['titles'] = label_titles_dict[label_name]['titles']
            labels.append(candidate_label)

    return labels
