import re

from app.db import get_db
from flask import current_app, g
from nltk.corpus import stopwords

from app.dbconfig import get_dbconfig


def get_label_titles_dict():
    if 'label_titles_dict' not in g:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        currentdump_id = get_dbconfig('currentdump')

        sql = '''SELECT `labels`.`label`, `labels`.`counter` AS `label_counter`,
                `labels_articles`.`article_id`, `labels_articles`.`title`, `labels_articles`.`counter` AS `label_title_counter`,
                `articles`.`counter` AS `article_counter`, `articles`.`caption`, `articles`.`redirect_to_title`
                FROM `labels`   JOIN `labels_articles` ON `labels`.`id` = `labels_articles`.`label_id`
                                JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`
                WHERE `labels`.`dump_id`=%s'''

        data = (currentdump_id, )
        cursor.execute(sql, data)
        label_titles_dict = {}
        for row in cursor:
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
            if row['label'] not in label_titles_dict:
                label_titles_dict[row['label']] = {
                    'counter': row['label_counter'],
                    'titles': [title]
                }
            else:
                label_titles_dict[row['label']]['titles'].append(title)
        cursor.close()

        g.label_titles_dict = label_titles_dict

    return g.label_titles_dict


def get_labels_exact(lines, algorithm_normalized_json):
    label_titles_dict = get_label_titles_dict()
    stops = set(stopwords.words('english'))

    labels = []
    for ngrams in range(1, current_app.config['MAX_NGRAMS'] + 1):
        for line_nr, line in enumerate(lines):
            for label_nr, label in enumerate(line):
                if label_nr + ngrams > len(line):  # cannot construct ngram of length "ngrams" starting from "label"
                    break
                label = ' '.join(line[label_nr:label_nr + ngrams])  # construct the label
                # remove punctation
                label = re.sub(r'[.,]', '', label)
                if algorithm_normalized_json['skipstopwords'] and label in stops:
                    continue
                if label in label_titles_dict:
                    labels.append({
                        'name': label,
                        'line': line_nr,
                        'start': label_nr,
                        'ngrams': ngrams,
                        'counter': label_titles_dict[label]['counter'],
                        'titles': label_titles_dict[label]['titles']
                    })

    return labels
