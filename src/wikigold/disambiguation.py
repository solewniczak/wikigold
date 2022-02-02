from collections import defaultdict

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
            'article_id': most_common_article['article_id'],
            'rating': most_common_article['commonness'],
        }


def get_context_terms(labels, commonness_threshold=0.9):
    """Assumes that labels has commonness calculated already"""
    context_terms = [label for label in labels if label['disambiguation']['rating'] >= commonness_threshold]
    return context_terms


def backlinks(article_ids):
    db = get_db()

    cursor = db.cursor(dictionary=True)

    article_ids_str = ','.join(map(str, article_ids))

    sql = f'SELECT `destination_article_id`, `source_article_id` ' \
          f'FROM `wikipedia_decisions` WHERE `destination_article_id` IN ({article_ids_str})'
    cursor.execute(sql)

    backlinks = defaultdict(set)
    for row in cursor:
        destination_article_id = row['destination_article_id']
        source_article_id = row['source_article_id']
        backlinks[destination_article_id].add(source_article_id)

    cursor.close()
    return backlinks


def rate_by_topic_proximity(labels):
    rate_by_commonness(labels)
    context_terms = get_context_terms(labels)
    context_terms_backlinks = backlinks([label['disambiguation']['article_id'] for label in context_terms])
    pass
