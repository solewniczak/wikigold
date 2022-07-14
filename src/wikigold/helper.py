import json
from urllib.parse import urljoin

from flask import g, current_app, url_for
from nltk import TreebankWordTokenizer
from nltk.data import load

from .db import get_db


def absolute_url_for(endpoint, **values):
    if current_app.config['BASE_URL'] != '':
        relative_url = url_for(endpoint, **values)
        url = urljoin(current_app.config['BASE_URL'], relative_url)
    else:
        url = url_for(endpoint, **values, _external=True)
    return url


def word_tokenize_spans(text, language="english"):
    sent_tokenizer = load(f'tokenizers/punkt/{language}.pickle')
    word_tokenizer = TreebankWordTokenizer()

    sentence_spans = sent_tokenizer.span_tokenize(text)
    for (sentence_span_start, sentence_span_end) in sentence_spans:
        sentence = text[sentence_span_start:sentence_span_end]
        word_spans = word_tokenizer.span_tokenize(sentence)
        for (token_span_start, token_span_end) in word_spans:
            yield sentence_span_start + token_span_start, sentence_span_start + token_span_end


def get_lines(article_id, limit=None):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = "SELECT `id`, `content` FROM `lines` WHERE `article_id`=%s ORDER BY `nr`"
    if limit:
        sql += f" LIMIT {limit}"

    data = (article_id,)
    cursor.execute(sql, data)

    lines = []
    try:
        for row in cursor:
            line_text = row['content'].decode('utf-8')
            line_tokens = []
            for (token_span_start, token_span_end) in word_tokenize_spans(line_text):
                line_tokens.append((token_span_start, token_span_end))
            lines.append({'content': line_text, 'tokens': line_tokens})
    except ValueError:
        cursor.reset()
        raise
    finally:
        cursor.close()

    return lines


def ngrams(lines):
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
                label_end = line_tokens[token_nr + ngrams - 1][1]  # end of the last gram
                label = line_content[label_start:label_end]

                yield {
                    'name': label,
                    'line': line_nr,
                    'start': token_nr,
                    'ngrams': ngrams,
                }


def get_ground_truth_decisions(article_id, ground_truth_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = '''SELECT `lines`.`nr`, `ground_truth_decisions`.`start`, `ground_truth_decisions`.`length`,
                `ground_truth_decisions`.`label`, `ground_truth_decisions`.`label_id`,
                `ground_truth_decisions`.`destination_title`, `ground_truth_decisions`.`destination_article_id`,
                `articles`.`caption`
                FROM `ground_truth_decisions`
                JOIN `lines` ON `ground_truth_decisions`.`source_line_id` = `lines`.`id`
                LEFT JOIN `articles` ON `ground_truth_decisions`.`destination_article_id` = `articles`.`id`
                WHERE `lines`.`article_id`=%s AND `ground_truth_decisions`.`ground_truth_id`=%s'''
    data = (article_id, ground_truth_id)
    cursor.execute(sql, data)

    decisions = []
    for row in cursor:
        try:
            caption = row['caption'].decode('utf-8')
        except AttributeError:
            caption = None

        decision = {
            'line': row['nr'],
            'start': row['start'],
            'length': row['length'],
            'label': row['label'],
            'label_id': row['label_id'],
            'destination_title': row['destination_title'],
            'destination_article_id': row['destination_article_id'],
            'destination_caption': caption
        }
        decisions.append(decision)

    cursor.close()
    return decisions


def get_user_decisions(article_id, algorithm_normalized_json_key, user_id):
    db = get_db()
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
    """
    Method returns the string key that unambiguously identifies the algorithm and its parameters.

    Returns:
        string: The key of the algorithm.
        Dict: The parameters of algorithm with resolved default values.
    """

    # Default values
    algorithm_defaults = {
        'paragraphs_limit': '',  # must be string because can be empty
        'retrieval': '',
        'skip_stop_words': False,
        'rate_keywords_by': '',
        'links_to_text_ratio': 0.12,  # only apply if rate_keywords_by is not empty
        'min_label_count': 1,  # get only labels that are used n times in Wikipedia
        'min_label_articles_count': 1,  # get only senses that link to the specific label n times in wikipedia
        'disambiguation': '',  # disambiguation algorith
        'min_keyphraseness': 0.0,  # get only keywords with given a priori probability
        'min_sense_probability': 0.0,  # consider only senses with given a priori probability
        'min_label_sense_probability': 0.0,  # use per label sense probability rather than global sense probability
        'resolve_overlaps': '' # how to deal with overlapping keywords. By default keep them to the disambiguation phrase.
    }

    if type(algorithm) == str:
        algorithm_parsed = json.loads(algorithm)
    else:
        algorithm_parsed = algorithm

    # Parse parameters
    if 'skip_stop_words' in algorithm_parsed:
        algorithm_parsed['skip_stop_words'] = bool(int(algorithm_parsed['skip_stop_words']))
    if 'min_label_count' in algorithm_parsed:
        algorithm_parsed['min_label_count'] = int(algorithm_parsed['min_label_count'])
    if 'min_label_articles_count' in algorithm_parsed:
        algorithm_parsed['min_label_articles_count'] = int(algorithm_parsed['min_label_articles_count'])
    if 'links_to_text_ratio' in algorithm_parsed:
        algorithm_parsed['links_to_text_ratio'] = float(algorithm_parsed['links_to_text_ratio'])
    if 'min_keyphraseness' in algorithm_parsed:
        algorithm_parsed['min_keyphraseness'] = float(algorithm_parsed['min_keyphraseness'])
    if 'min_sense_probability' in algorithm_parsed:
        algorithm_parsed['min_sense_probability'] = float(algorithm_parsed['min_sense_probability'])
    if 'min_label_sense_probability' in algorithm_parsed:
        algorithm_parsed['min_label_sense_probability'] = float(algorithm_parsed['min_label_sense_probability'])

    # Apply default values
    for default_key, default_value in algorithm_defaults.items():
        if default_key not in algorithm_parsed:
            algorithm_parsed[default_key] = default_value

    # Algorithm key omits default values
    algorithm_key = {key: value for key, value in algorithm_parsed.items() if
                     algorithm_parsed[key] != algorithm_defaults[key]}

    return json.dumps(algorithm_key, sort_keys=True), algorithm_parsed


def wikification(lines, algorithm_normalized_json):
    from .retrieval import get_labels_exact, resolve_overlap_longest
    from .disambiguation import rate_by, rate_by_relatedness, resolve_overlap_best_match

    if algorithm_normalized_json['retrieval'] == 'exact':
        labels = get_labels_exact(lines, algorithm_normalized_json)
    else:
        raise Exception("unknown retrieval algorithm")

    if algorithm_normalized_json['resolve_overlaps'] == 'longest':
        labels = resolve_overlap_longest(labels)

    if algorithm_normalized_json['disambiguation'] == 'commonness':
        rate_by(labels, 'sense_probability')
    elif algorithm_normalized_json['disambiguation'] == 'la_commonness':
        rate_by(labels, 'label_sense_probability')
    elif algorithm_normalized_json['disambiguation'] == 'context_terms_relatedness':
        rate_by_relatedness(labels)

    # when there is no overlaps the function simpy assignes candidate_article_id to final "article_id" which is
    # algorithm decisions, in other case we select the candidates with the best 'rating' property.
    if algorithm_normalized_json['disambiguation'] != '':
        resolve_overlap_best_match(labels)

    for label in labels:
        if 'disambiguation' in label and 'article_id' in label['disambiguation']:
            label['decision'] = label['disambiguation']['article_id']

    return labels
