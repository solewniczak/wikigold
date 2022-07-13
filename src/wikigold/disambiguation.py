from collections import defaultdict
from math import log2

from flask import current_app

from .cache import get_cached_backlinks
from .db import get_db


def resolve_overlap_best_match(labels):
    """Search for overlapping links and select only the one with the best rating from all overlaps.
    The algorithm process the labels starting from the top-rated candidate,
    so there is guarantee that in case of the overlap the best candidate will be selected.

    The function adds 'article_id' attribute to label['disambiguation'] data structure, based on
    label['disambiguation']['candidate_article_id'] and label['disambiguation']['rating'] attributes
    that should be there."""

    labels_sorted = sorted(labels, key=lambda label: label['disambiguation']['rating'], reverse=True)
    labels_overlap = defaultdict(list)  # store information about labels overlapping
    for label in labels_sorted:  # start from the best label
        overlap = False
        for ngram_idx in range(label['start'], label['start'] + label['ngrams']):
            if len(labels_overlap[label['line'], ngram_idx]) > 0:
                overlap = True

            if not overlap:
                label['disambiguation']['article_id'] = label['disambiguation']['candidate_article_id']
                for ngram_idx in range(label['start'], label['start'] + label['ngrams']):
                    labels_overlap[label['line'], ngram_idx].append(label)


def rate_by(labels, rating_key):
    for label in labels:
        best_matching_article = max(label['articles'], key=lambda article: article[rating_key])
        label['disambiguation'] = {
            'candidate_article_id': best_matching_article['article_id'],
            'rating': best_matching_article[rating_key],
        }


def lesk(labels):
    """Function implements Lesk disambiguation algorithm from (Michalcea and Csomani, 2007)  paper.
    The context of the disambiguating term is the current paragraph.
    The disambiguating word definition is caption (the first paragraph)."""
    pass # Not implemented yet.


def get_context_terms(labels, commonness_threshold=0.9):
    """Assumes that labels has commonness calculated already"""
    context_terms = [label for label in labels if label['disambiguation']['rating'] >= commonness_threshold]
    return context_terms


def backlinks(article_ids):
    backlinks = {}
    # loads backlinks from cache
    for article_id in article_ids:
        backlinks[article_id] = get_cached_backlinks(article_id)

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


def rate_by_topic_proximity(labels, max_context_terms=20):
    unique_articles_ids = set()
    for label in labels:
        unique_articles_ids.update([article['article_id'] for article in label['articles']])
    articles_backlinks = backlinks(unique_articles_ids)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql_select_articles_count = 'SELECT `articles_count` FROM dumps WHERE id=%s'
    cursor.execute(sql_select_articles_count, (current_app.config['KNOWLEDGE_BASE'], ))
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

    avg_sr_for_context_terms = sum_sr_for_context_terms/len(context_terms) # TODO: what if len(context_terms) == 0?

    for label in context_terms:
        context_term_article_id = label['disambiguation']['candidate_article_id']
        context_term_sr = sr_for_context_terms[context_term_article_id]
        if context_term_sr >= avg_sr_for_context_terms:
            label['disambiguation']['context_term_sr'] = context_term_sr

    context_terms = [label for label in context_terms if 'context_term_sr' in label['disambiguation']]
    context_terms.sort(key=lambda label: label['disambiguation']['context_term_sr'], reverse=True)
    context_terms = context_terms[:max_context_terms]  # filter out the worst context terms

    unique_context_terms_articles_ids = set([label['disambiguation']['candidate_article_id'] for label in context_terms
                                             if 'context_term' in label['disambiguation']]) # update context terms articles ids

    for label in context_terms:
        label['disambiguation']['rating'] = 1.0  # context terms always included

    for label in labels:
        if 'context_term' not in label['disambiguation']:
            for article in label['articles']:
                article_id = article['article_id']
                sr_for_meaning = avg_semantic_relatedness(articles_backlinks, article_id,
                                                          unique_context_terms_articles_ids, articles_count)
                article['semantic_relatedness'] = sr_for_meaning
            article_with_max_sr = max(label['articles'], key=lambda article: article['semantic_relatedness'])
            label['disambiguation']['candidate_article_id'] = article_with_max_sr['article_id']
            label['disambiguation']['rating'] = article_with_max_sr['semantic_relatedness']


