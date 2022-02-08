from collections import defaultdict
from math import log2

from .cache import get_cached_backlinks, add_backlinks_to_cache
from .db import get_db


def add_commonness_to_titles(labels):
    for label in labels:
        article_counter_sum = sum([title['article_counter'] for title in label['titles']])
        for title in label['titles']:
            title['commonness'] = title['article_counter']/article_counter_sum


def rate_by_commonness(labels):
    add_commonness_to_titles(labels)
    for label in labels:
        most_common_article = max(label['titles'], key=lambda title: title['commonness'])
        label['disambiguation'] = {
            'candidate_article_id': most_common_article['article_id'],
            'rating': most_common_article['commonness'],
        }


def get_context_terms(labels, commonness_threshold=0.9):
    """Assumes that labels has commonness calculated already"""
    context_terms = [label for label in labels if label['disambiguation']['rating'] >= commonness_threshold]
    return context_terms


def backlinks(article_ids):
    no_cached = []
    backlinks = defaultdict(set)
    # loads backlinks from cache
    for article_id in article_ids:
        article_backlinks = get_cached_backlinks(article_id)
        if article_backlinks is None:
            no_cached.append(article_id)
        else:
            backlinks[article_id] = set(article_backlinks.keys())

    if len(no_cached) > 0:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        article_ids_str = ','.join(map(str, no_cached))
        sql = f'SELECT `destination_article_id`, `source_article_id` ' \
              f'FROM `wikipedia_decisions` WHERE `destination_article_id` IN ({article_ids_str})'
        cursor.execute(sql)

        for row in cursor:
            destination_article_id = row['destination_article_id']
            source_article_id = row['source_article_id']
            backlinks[destination_article_id].add(source_article_id)
        cursor.close()

        # add missing backlinks to cache
        for destination_article_id, article_backlinks in backlinks.items():
            add_backlinks_to_cache(destination_article_id, article_backlinks)

    return backlinks


def semantic_relatedness(article_a_backlinks, article_b_backlinks, articles_count):
    aN = len(article_a_backlinks)
    bN = len(article_b_backlinks)
    abN = len(article_a_backlinks & article_b_backlinks)
    N = articles_count

    if abN == 0 or aN == 0 and bN == 0 or N == 0:
        return 0

    sr = (log2(max(aN, bN)) - log2(abN))/(log2(N) - log2(min(aN,bN)))
    return sr


def avg_semantic_relatedness(backlinks, article_id, other_articles_ids, articles_count):
    sum_sr = 0.0
    for other_article_id in other_articles_ids:
        sum_sr += semantic_relatedness(backlinks[article_id], backlinks[other_article_id], articles_count)
    return sum_sr/(len(backlinks)-1)


def count_tokens_in_lines(lines):
    return sum([len(line['tokens']) for line in lines])


def apply_links_to_text_ratio(labels, lines, links_to_text_ratio=0.12):
    tokens_in_text = count_tokens_in_lines(lines)
    tokens_to_links = int(links_to_text_ratio * tokens_in_text)
    labels_sorted = sorted(labels, key=lambda label: label['disambiguation']['rating'])
    labels_overlap = defaultdict(list)  # store information about labels overlapping
    while tokens_to_links > 0 and len(labels_sorted) > 0:
        label = labels_sorted.pop()
        overlap = False
        for ngram_idx in range(label['start'], label['start'] + label['ngrams']):
            if len(labels_overlap[label['line'], ngram_idx]) > 0:
                overlap = True

        if not overlap:
            label['disambiguation']['article_id'] = label['disambiguation']['candidate_article_id']
            tokens_to_links -= label['ngrams']
            for ngram_idx in range(label['start'], label['start'] + label['ngrams']):
                labels_overlap[label['line'], ngram_idx].append(label)


def rate_by_topic_proximity(labels, dump_id, max_context_terms=20):
    unique_articles_ids = set()
    for label in labels:
        unique_articles_ids.update([title['article_id'] for title in label['titles']])
    articles_backlinks = backlinks(unique_articles_ids)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql_select_articles_count = 'SELECT `articles_count` FROM dumps WHERE id=%s'
    cursor.execute(sql_select_articles_count, (dump_id, ))
    articles_count = cursor.fetchone()['articles_count']

    rate_by_commonness(labels)
    context_terms = get_context_terms(labels)

    sr_for_context_terms = {}
    sum_sr_for_context_terms = 0.0
    unique_context_terms_articles_ids = set([label['disambiguation']['candidate_article_id'] for label in context_terms])
    for context_term_article_id in unique_context_terms_articles_ids:
        other_articles_ids = [article_id for article_id in unique_context_terms_articles_ids if article_id != context_term_article_id]
        sr_for_context_term = avg_semantic_relatedness(articles_backlinks, context_term_article_id, other_articles_ids, articles_count)
        sr_for_context_terms[context_term_article_id] = sr_for_context_term
        sum_sr_for_context_terms += sr_for_context_term

    avg_sr_for_context_terms = sum_sr_for_context_terms/len(context_terms)

    unique_context_terms_articles_ids = set()  # some context terms will be removed, so clean the set
    for label in context_terms:
        context_term_article_id = label['disambiguation']['candidate_article_id']
        context_term_sr = sr_for_context_terms[context_term_article_id]
        if context_term_sr >= avg_sr_for_context_terms:
            label['disambiguation']['context_term'] = True
            label['disambiguation']['rating'] = 1.0 # context terms always on top
            label['disambiguation']['semantic_relatedness'] = context_term_sr
            unique_context_terms_articles_ids.add(context_term_article_id)

    for label in labels:
        if 'context_term' not in label['disambiguation']:
            for title in label['titles']:
                article_id = title['article_id']
                sr_for_meaning = avg_semantic_relatedness(articles_backlinks, article_id,
                                                          unique_context_terms_articles_ids, articles_count)
                title['semantic_relatedness'] = sr_for_meaning
            article_with_max_sr = max(label['titles'], key=lambda title: title['semantic_relatedness'])
            label['disambiguation']['candidate_article_id'] = article_with_max_sr['article_id']
            label['disambiguation']['rating'] = article_with_max_sr['semantic_relatedness']


