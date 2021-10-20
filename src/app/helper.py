import json
import nltk

from flask import g
from nltk.tokenize.treebank import TreebankWordTokenizer
from nltk.tokenize.punkt import PunktSentenceTokenizer

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


def get_wikipedia_decisions(article_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = "SELECT `id`, `content` FROM `lines` WHERE `article_id`=%s ORDER BY `nr`"
    data = (article_id,)
    cursor.execute(sql, data)

    lines_spans = []
    for row in cursor:
        line_content = row['content'].decode('utf-8')
        sentences_spans = PunktSentenceTokenizer().span_tokenize(line_content)
        line_spans = [
            (sentence_span_start+token_span_start, sentence_span_start+token_span_end)
            for (sentence_span_start,sentence_span_end) in sentences_spans
            for (token_span_start, token_span_end)
            in TreebankWordTokenizer().span_tokenize(line_content[sentence_span_start:sentence_span_end])
        ]
        if len(line_spans) > 0:
            line_spans_starts, line_spans_ends = zip(*line_spans)
            lines_spans.append(({position: ngram for ngram, position in enumerate(line_spans_starts)},
                                    {position: ngram for ngram, position in enumerate(line_spans_ends)}))
        else:
            lines_spans.append(({}, {}))

    sql = '''SELECT `lines`.`nr`, `wikipedia_decisions`.`start`, `wikipedia_decisions`.`length`,
            `wikipedia_decisions`.`destination_title`, `wikipedia_decisions`.`destination_article_id`,
            `articles`.`caption`
            FROM `wikipedia_decisions`
            JOIN `lines` ON `wikipedia_decisions`.`source_line_id` = `lines`.`id`
            LEFT JOIN `articles` ON `wikipedia_decisions`.`destination_article_id` = `articles`.`id`
            WHERE `lines`.`article_id`=%s'''
    cursor.execute(sql, data)

    decisions = []
    for row in cursor:
        line_nr = row['nr']
        try:
            caption = row['caption'].decode('utf-8')
        except AttributeError:
            caption = None
        line_starts, line_ends = lines_spans[line_nr]
        try:
            start_ngram = line_starts[row['start']]
            end_ngram = line_ends[row['start']+row['length']]
            decision = {
                'line': row['nr'],
                'destination_title': row['destination_title'],
                'destination_article_id': row['destination_article_id'],
                'destination_caption': caption,
                'start': start_ngram,
                'ngrams': end_ngram-start_ngram+1
            }
            decisions.append(decision)
        except KeyError:
            pass

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

    if algorithm_parsed['algorithm'] == 'exact':
        if 'skipstopwords' not in algorithm_parsed:
            algorithm_parsed['skipstopwords'] = False
        else:
            algorithm_parsed['skipstopwords'] = bool(int(algorithm_parsed['skipstopwords']))

    return json.dumps(algorithm_parsed, sort_keys=True), algorithm_parsed