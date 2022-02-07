import pickle
from collections import Counter, defaultdict

import redis

import click
from flask import current_app, g
from flask.cli import with_appcontext
from tqdm import tqdm

from .db import get_db


def get_redis(db_name=None):
    db_mappings = {
        'labels': 1,
        'backlinks': 2,
        'labels_titles': 3
    }

    if db_name is None:
        db = 0
    else:
        db = db_mappings[db_name]

    if 'redis' not in g:
        g.redis = {}

    if db not in g.redis:
        g.redis[db] = redis.from_url(current_app.config['REDIS_URL'], db=db)

    return g.redis[db]


def get_cached_backlinks(article_id):
    r = get_redis('backlinks')
    backlinks = r.get(article_id)
    if backlinks is not None:
        backlinks = pickle.loads(backlinks)
    return backlinks


def add_backlinks_to_cache(article_id, backlinks):
    r = get_redis('backlinks')
    r.set(article_id, pickle.dumps(backlinks))


def get_cached_label(label_name):
    """Returns tuple: label_id, label_counter"""
    r = get_redis('labels')
    label = r.get(label_name)
    if label is not None:
        label = pickle.loads(label)
    return label


def add_label_to_cache(label_name, label_id, label_counter):
    r = get_redis('labels')
    value = (label_id, label_counter)
    r.set(label_name, pickle.dumps(value))


# @click.command('cache-labels')
# @click.argument('dump_id')
# @with_appcontext
# def cache_labels_command(dump_id):
#     db = get_db()
#
#     cursor = db.cursor(dictionary=True)
#
#     sql = 'SELECT `labels_count` FROM `dumps` WHERE `id`=%s'
#     cursor.execute(sql, (dump_id,))
#     labels_count = cursor.fetchone()['labels_count']
#     print(f'labels count: {labels_count}')
#
#     sql = f'''SELECT `labels`.`label`, `labels`.`counter` AS `label_counter`,
#                     `labels_articles`.`article_id`, `labels_articles`.`title`, `labels_articles`.`counter` AS `label_title_counter`,
#                     `articles`.`counter` AS `article_counter`, `articles`.`caption`, `articles`.`redirect_to_title`
#                         FROM `labels` JOIN `labels_articles` ON `labels`.`id` = `labels_articles`.`label_id`
#                                       JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`'''
#     cursor.execute(sql)
#
#     labels = {}
#     with tqdm(total=labels_count) as pbar:
#         for row in cursor:
#             label = row['label']
#             if label not in labels:
#                 labels[label] = {
#                     'counter': row['label_counter'],
#                     'titles': []
#                 }
#             labels[label]['titles'].append({
#                 'article_id': row['article_id'],
#                 'title': row['title'],
#                 'label_title_counter': row['label_title_counter'],
#                 'article_counter': row['article_counter'],
#                 'redirect_to_title': row['redirect_to_title']
#             })
#             pbar.update(1)
#     cursor.close()


@click.command('cache-labels')
@click.argument('dump_id')
@with_appcontext
def cache_labels_command(dump_id):
    db = get_db()

    cursor = db.cursor(dictionary=True)

    sql = 'SELECT `labels_count` FROM `dumps` WHERE `id`=%s'
    cursor.execute(sql, (dump_id,))
    labels_count = cursor.fetchone()['labels_count']
    print(f'labels count: {labels_count}')

    sql = '''SELECT `id`, `label`, `counter` AS `label_counter` FROM `labels` WHERE `labels`.`dump_id`=%s'''
    data = (dump_id,)
    cursor.execute(sql, data)
    with tqdm(total=labels_count) as pbar:
        for row in cursor:
            add_label_to_cache(row['label'], row['id'], row['label_counter'])
            pbar.update(1)
    cursor.close()


@click.command('cache-backlinks')
@click.argument('dump_id', type=int)
@click.option('-p', '--page-size', type=int, default=500000)
@click.option('-s', '--start-page', type=int, default=0)
@with_appcontext
def cache_backlinks_command(dump_id, page_size, start_page):
    db = get_db()

    cursor = db.cursor(dictionary=True)
    sql = 'SELECT `wikipedia_decisions_count` FROM `dumps` WHERE `id`=%s'
    cursor.execute(sql, (dump_id, ))
    wikipedia_decisions_count = cursor.fetchone()['wikipedia_decisions_count']
    print(f'wikipedia decisions count: {wikipedia_decisions_count}')

    sql = 'SELECT MIN(`id`) AS `first_id` FROM `wikipedia_decisions` WHERE `dump_id`=%s'
    cursor.execute(sql, (dump_id,))
    first_id = cursor.fetchone()['first_id']

    print(f'first id: {first_id}')
    steps = -(-wikipedia_decisions_count//page_size) - start_page
    with tqdm(total=steps) as pbar:
        for i in range(start_page*page_size, wikipedia_decisions_count, page_size):
            start_id = first_id + i
            end_id = min(start_id+page_size-1, wikipedia_decisions_count)

            pbar.set_description(f'processing ids from {start_id} to {end_id}')

            sql = f'SELECT `destination_article_id`, `source_article_id`  FROM `wikipedia_decisions`' \
                  f'WHERE `id` BETWEEN %s AND %s'
            data = (start_id, end_id)
            cursor.execute(sql, data)

            backlinks = {}
            for row in cursor:
                destination_article_id = row['destination_article_id']
                source_article_id = row['source_article_id']

                if destination_article_id in backlinks:
                    backlinks[destination_article_id][source_article_id] += 1
                else:
                    article_backlinks = get_cached_backlinks(destination_article_id)
                    if article_backlinks is None:
                        article_backlinks = Counter()
                    article_backlinks[source_article_id] += 1
                    backlinks[destination_article_id] = article_backlinks

            for destination_article_id, article_backlinks in backlinks.items():
                add_backlinks_to_cache(destination_article_id, article_backlinks)
            pbar.update(1)
        cursor.close()


@click.command('flush-db')
@click.argument('db_name')
@with_appcontext
def flush_db_command(db_name):
    r = get_redis(db_name)
    r.flushdb()


@click.command('flush-all')
@with_appcontext
def flush_all_command():
    r = get_redis()
    r.flushall()


def init_app(app):
    app.cli.add_command(cache_labels_command)
    app.cli.add_command(flush_db_command)
    app.cli.add_command(flush_all_command)
    app.cli.add_command(cache_backlinks_command)
