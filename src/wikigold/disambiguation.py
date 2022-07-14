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


def rate_by_relatedness(labels):
    lables_dict = get_labels_dict(labels)
    add_relatedness_to_labels_dict(lables_dict)
    for label in labels:
        label_name = label['name']
        if label_name in lables_dict:
            # apply relatedness to articles
            label['articles'] = lables_dict[label_name]['articles']
    rate_by(labels, 'relatedness')


def get_labels_dict(labels):
    """Remove position from labels and transform it to dictionary label_name:articles.
    This function assumes that each label in document has identical meaning which may not be true for all wikification
    algorithms."""
    import copy

    labels_dict = {}
    for label in labels:
        if label['name'] not in labels_dict:
            labels_dict[label['name']] = {
                'articles': copy.copy(label['articles']),
                'keyphraseness': label['keyphraseness']
            }

    return labels_dict


def add_relatedness_to_labels_dict(labels_dict):
    """@param label_articles_dict is the output of the get_label_titles_dict from the retrieval phrase.
    (Milne and Witten, 2008)"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql_select_articles_count = 'SELECT `articles_count` FROM dumps WHERE id=%s'
    cursor.execute(sql_select_articles_count, (current_app.config['KNOWLEDGE_BASE'],))
    articles_count = cursor.fetchone()['articles_count']

    # context terms
    context_terms = {label_name: label
                      for label_name, label in labels_dict.items()
                      if len(label['articles']) == 1}
    context_terms_articles_ids = [label['articles'][0]['article_id'] for label in context_terms.values()]
    context_terms_backlinks = backlinks(context_terms_articles_ids)

    if len(context_terms) == 0:
        raise Exception('cannot apply relatedness: no context terms available')

    for context_term_label_name, context_term_label in context_terms.items():
        context_term_article_id = context_term_label['articles'][0]['article_id']
        context_term_avg_relatedness = 0
        for ctx_to_ctx_label_name, ctx_to_ctx_label in context_terms.items():
            ctx_to_ctx_article_id = ctx_to_ctx_label['articles'][0]['article_id']
            if context_term_article_id != ctx_to_ctx_article_id:
                context_term_avg_relatedness += semantic_relatedness(context_terms_backlinks[context_term_article_id],
                                                                     context_terms_backlinks[ctx_to_ctx_article_id],
                                                                     articles_count)
        if len(context_terms) > 1:
            context_term_avg_relatedness /= len(context_terms)-1
        context_term_link_probability = context_term_label['keyphraseness']

        # update context terms statistics
        context_term_label['context_term_weight'] = (context_term_avg_relatedness+context_term_link_probability)/2

    for label_name, label in labels_dict.items():
        for article in label['articles']:
            article_id = article['article_id']
            article_backlinks = get_cached_backlinks(article_id)
            article['relatedness'] = 0.0
            for context_term_label_name, context_term_label in context_terms.items():
                context_term_article_id = context_term_label['articles'][0]['article_id']
                article['relatedness'] += context_term_label['context_term_weight'] *\
                                          semantic_relatedness(context_terms_backlinks[context_term_article_id],
                                                               article_backlinks, articles_count)

            article['relatedness'] /= len(context_terms)


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
