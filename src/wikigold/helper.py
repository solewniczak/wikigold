import json

from flask import g
from nltk import TreebankWordTokenizer
from nltk.data import load

from .db import get_db


def word_tokenize_spans(text, language="english"):
    sent_tokenizer = load(f'tokenizers/punkt/{language}.pickle')
    word_tokenizer = TreebankWordTokenizer()

    sentence_spans = sent_tokenizer.span_tokenize(text)
    for (sentence_span_start, sentence_span_end) in sentence_spans:
        sentence = text[sentence_span_start:sentence_span_end]
        word_spans = word_tokenizer.span_tokenize(sentence)
        for (token_span_start, token_span_end) in word_spans:
            yield sentence_span_start+token_span_start, sentence_span_start+token_span_end


def get_lines(article_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = "SELECT `id`, `content` FROM `lines` WHERE `article_id`=%s ORDER BY `nr`"
    data = (article_id,)
    cursor.execute(sql, data)

    lines = []
    for row in cursor:
        line_text = row['content'].decode('utf-8')
        line_tokens = []
        for (token_span_start, token_span_end) in word_tokenize_spans(line_text):
            line_tokens.append((token_span_start, token_span_end))
        lines.append({'content': line_text, 'tokens': line_tokens})

    cursor.close()

    return lines


def get_wikipedia_decisions(article_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = '''SELECT `lines`.`nr`, `wikipedia_decisions`.`start`, `wikipedia_decisions`.`length`,
                `wikipedia_decisions`.`destination_title`, `wikipedia_decisions`.`destination_article_id`,
                `articles`.`caption`
                FROM `wikipedia_decisions`
                JOIN `lines` ON `wikipedia_decisions`.`source_line_id` = `lines`.`id`
                LEFT JOIN `articles` ON `wikipedia_decisions`.`destination_article_id` = `articles`.`id`
                WHERE `lines`.`article_id`=%s'''
    data = (article_id,)
    cursor.execute(sql, data)

    decisions = []
    for row in cursor:
        try:
            caption = row['caption'].decode('utf-8')
        except AttributeError:
            caption = None

        decision = {
            'line': row['nr'],
            'destination_title': row['destination_title'],
            'destination_article_id': row['destination_article_id'],
            'destination_caption': caption,
            'start': row['start'],
            'length': row['length']
        }
        decisions.append(decision)

    cursor.close()
    return decisions


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

    algorithm_parsed['knowledge_base'] = int(algorithm_parsed['knowledge_base'])

    if algorithm_parsed['retrieval'] == 'exact':
        if 'skipstopwords' not in algorithm_parsed:
            algorithm_parsed['skipstopwords'] = False
        else:
            algorithm_parsed['skipstopwords'] = bool(int(algorithm_parsed['skipstopwords']))

    return json.dumps(algorithm_parsed, sort_keys=True), algorithm_parsed