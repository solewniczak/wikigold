import json
import nltk

from flask import g

from app.db import get_db


def get_lines(article_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = "SELECT `id`, `content` FROM `lines` WHERE `article_id`=%s ORDER BY `nr`"
    data = (article_id,)
    cursor.execute(sql, data)

    lines = []
    for row in cursor:
        line_text = row['content'].decode('utf-8')
        line_tokens = nltk.word_tokenize(line_text)
        lines.append(line_tokens)

    cursor.close()

    return lines


def get_user_decisions(article_id, algorithm_normalized_json_key):
    db = get_db()
    user_id = g.user['id']

    cursor = db.cursor(dictionary=True)

    # check if EDL exists
    sql = '''SELECT `lines`.`nr` AS `source_line_nr`, `start`, `length`, `destination_article_id`
                FROM `decisions` JOIN `lines` ON `decisions`.`source_line_id` = `lines`.`id`
                JOIN `edls` ON `decisions`.`edl_id` = `edls`.`id`
                WHERE `edls`.`algorithm`=%s AND `edls`.`user_id`=%s AND `edls`.`article_id`=%s'''
    data = (algorithm_normalized_json_key, user_id, article_id)
    cursor.execute(sql, data)

    decisions_dict = {}
    for row in cursor:
        source_line_nr = row['source_line_nr']
        start = row['start']
        length = row['length']
        destination_article_id = row['destination_article_id']
        decisions_dict[source_line_nr, start, length] = destination_article_id

    cursor.close()

    return decisions_dict


def normalize_algorithm_json(algorithm):
    algorithm_parsed = json.loads(algorithm)

    if algorithm_parsed['algorithm'] == 'exact':
        if 'skipstopwords' not in algorithm_parsed:
            algorithm_parsed['skipstopwords'] = False
        else:
            algorithm_parsed['skipstopwords'] = bool(int(algorithm_parsed['skipstopwords']))

    return json.dumps(algorithm_parsed, sort_keys=True), algorithm_parsed