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

    sql = '''CREATE TEMPORARY TABLE `current_articles` (
                `id` INT UNSIGNED NOT NULL
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin'''
    cursor.execute(sql)

    sql_insert_to_current_articles = 'INSERT INTO `current_articles` VALUES (%s)'
    for article_id in article_ids:
        data = (article_id, )
        cursor.execute(sql_insert_to_current_articles, data)

    sql = '''SELECT `current_articles`.`id`, `lines`.`article_id`
            FROM `current_articles`
            JOIN `wikipedia_decisions` ON `current_articles`.`id` = `wikipedia_decisions`.`destination_article_id`
            JOIN `lines` ON `wikipedia_decisions`.`source_line_id` = `lines`.`id`'''
    cursor.execute(sql)

    backlinks = defaultdict(set)
    for row in cursor:
        id = row['id']
        article_id = row['article_id']
        backlinks[id].add(article_id)

    cursor.close()
    return backlinks


def rate_by_topic_proximity(labels):
    rate_by_commonness(labels)
    context_terms = get_context_terms(labels)
    context_terms_backlinks = backlinks([label['disambiguation']['article_id'] for label in context_terms])
    pass
