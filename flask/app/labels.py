from app.db import get_db
from flask import current_app, g


def get_label_titles_dict():
    if 'label_titles_dict' not in g:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        sql = '''SELECT `labels`.`label`, `labels`.`counter` AS `label_counter`,
                `labels_articles`.`title`, `labels_articles`.`counter` AS `label_title_counter`,
                `articles`.`counter` AS `article_counter` 
                FROM `labels` LEFT JOIN `labels_articles` ON `labels`.`id` = `labels_articles`.`label_id`
                                LEFT JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`'''

        cursor.execute(sql)
        label_titles_dict = {}
        for row in cursor:
            if row['label'] not in label_titles_dict:
                label_titles_dict[row['label']] = {
                    'counter': row['label_counter'],
                    'titles': [{
                        'title': row['title'],
                        'label_title_counter': row['label_title_counter'],
                        'article_counter': row['article_counter'],
                        'decision': None
                    }]
                }
            else:
                label_titles_dict[row['label']]['titles'].append({
                    'title': row['title'],
                    'label_title_counter': row['label_title_counter'],
                    'article_counter': row['article_counter'],
                    'decision': None
                })
        cursor.close()

        g.label_titles_dict = label_titles_dict

    return g.label_titles_dict


def get_labels_exact(lines):
    label_titles_dict = get_label_titles_dict()

    labels = []
    for ngrams in range(1, current_app.config['MAX_NGRAMS'] + 1):
        for line_nr, line in enumerate(lines):
            for label_nr, label in enumerate(line):
                if label_nr + ngrams > len(line):  # cannot construct ngram of length "ngrams" starting from "label"
                    break
                label = ' '.join(line[label_nr:label_nr + ngrams])  # construct the label
                if label in label_titles_dict:
                    labels.append({
                        'line': line_nr,
                        'start': label_nr,
                        'ngrams': ngrams,
                        'counter': label_titles_dict[label]['counter'],
                        'titles': label_titles_dict[label]['titles']
                    })

    return labels
