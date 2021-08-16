from app.db import get_db
from flask import g


def get_labels_dict():
    if 'labels_dict' not in g:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        sql = "SELECT `label`, `counter` FROM `labels`"
        cursor.execute(sql)
        labels_dict = {}
        for row in cursor:
            labels_dict[row['label']] = row['counter']
        cursor.close()

        g.labels_dict = labels_dict

    return g.labels_dict


def get_labels_exact(lines, params):
    labels_dict = get_labels_dict()

    labels = []
    for ngrams in range(1, params['max_ngram']+1):
        for line_nr, line in enumerate(lines):
            for label_nr, label in enumerate(line):
                if label in labels_dict:
                    labels.append({
                        'line': line_nr,
                        'start': label_nr,
                        'ngrams': ngrams,
                        'dst': labels_dict[label]
                    })

    return labels
