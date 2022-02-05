import json
import pickle
from collections import Counter

import redis

import click
from flask import current_app, g
from flask.cli import with_appcontext
from tqdm import tqdm

from .db import get_db


def get_labels_cache():
    if 'redis' not in g:
        g.redis = redis.from_url(current_app.config['REDIS_URL'], db=1)

    return g.redis


def get_backlinks_cache():
    if 'redis_backlinks' not in g:
        g.redis_backlinks = redis.from_url(current_app.config['REDIS_URL'], db=2)

    return g.redis_backlinks


def get_cached_backlinks(article_id):
    backlinks = get_backlinks_cache().get(article_id)
    if backlinks is not None:
        backlinks = pickle.loads(backlinks)
    return backlinks


def cached_labels():
    r = get_labels_cache()
    return r.dbsize()


@click.command('cache-dump')
@click.argument('dump_id')
@with_appcontext
def cache_dump_command(dump_id):
    r = get_labels_cache()
    db = get_db()

    cursor = db.cursor(dictionary=True)

    sql = 'SELECT COUNT(*) AS "counter" FROM `labels`'
    cursor.execute(sql)
    counter = cursor.fetchone()['counter']

    sql = '''SELECT `id`, `label` FROM `labels` WHERE `labels`.`dump_id`=%s'''
    data = (dump_id,)
    cursor.execute(sql, data)
    with tqdm(total=counter) as pbar:
        for row in cursor:
            key = row['label']
            value = row['id']
            r.set(key, value)
            pbar.update(1)
    cursor.close()


# @click.command('cache-backlinks')
# @click.argument('dump_id', type=int)
# @with_appcontext
# def cache_backlinks_command(dump_id):
#     r = get_redis(dump_id + 1)
#     db = get_db()
#
#     cursor = db.cursor(dictionary=False)
#     sql = 'SELECT `destination_article_id`, `source_article_id`  FROM `wikipedia_decisions` WHERE `dump_id`=%s'
#     cursor.execute(sql, (dump_id,))
#     wikipedia_decisions = cursor.fetchall()
#
#     cursor.close()

    # with tqdm(total=len(articles_ids)) as pbar:
    #     for article_id in articles_ids:
    #         sql = f'SELECT `source_article_id`  FROM `wikipedia_decisions` WHERE `destination_article_id`=%s'
    #         data = (article_id, )
    #         cursor.execute(sql, data)
    #         backlinks = Counter()
    #         for row in cursor:
    #             source_article_id = row['source_article_id']
    #             backlinks[source_article_id] += 1
    #         r.set(article_id, json.dumps(backlinks))
    #         pbar.update(1)
    #
    # cursor.close()


# @click.command('cache-backlinks')
# @click.argument('dump_id', type=int)
# @with_appcontext
# def cache_backlinks_command(dump_id):
#     r = get_redis(dump_id+1)
#     db = get_db()
#
#     cursor = db.cursor(dictionary=True)
#     sql = 'SELECT `wikipedia_decisions_count` FROM `dumps` WHERE `id`=%s'
#     cursor.execute(sql, (dump_id, ))
#     wikipedia_decisions_count = cursor.fetchone()['wikipedia_decisions_count']
#
#     print(f'wikipedia decisions count: {wikipedia_decisions_count}')
#
#     sql = f'SELECT `destination_article_id`, `source_article_id`  FROM `wikipedia_decisions` WHERE `dump_id`=%s'
#     data = (dump_id, )
#     cursor.execute(sql, data)
#     backlinks = defaultdict(Counter)
#     with tqdm(total=wikipedia_decisions_count) as pbar:
#         for row in cursor:
#             destination_article_id = row['destination_article_id']
#             source_article_id = row['source_article_id']
#             backlinks[destination_article_id][source_article_id] += 1
#             pbar.update(1)
#     cursor.close()
#
#     with tqdm(total=len(backlinks)) as pbar:
#         for destination_article_id, article_backlinks in backlinks.items():
#             r.set(destination_article_id, json.dumps(article_backlinks))
#             pbar.update(1)


@click.command('cache-backlinks')
@click.argument('dump_id', type=int)
@click.option('-p', '--page-size', type=int, default=500000)
@click.option('-s', '--start-page', type=int, default=0)
@with_appcontext
def cache_backlinks_command(dump_id, page_size, start_page):
    r = get_backlinks_cache()
    keys = r.keys()
    dbsize = r.dbsize()

    with tqdm(total=dbsize) as pbar:
        for key in keys:
            value = r.get(key)
            if value:
                value = json.loads(value)
                value_counter = Counter({int(k): v for k,v in value.items()})
                pickled_value = pickle.dumps(value_counter)
                r.set(key, pickled_value)
                pbar.update(1)
            else:
                print(f"unknown value for key: {key}")


    return
    # db = get_db()
    #
    # cursor = db.cursor(dictionary=True)
    # sql = 'SELECT `wikipedia_decisions_count` FROM `dumps` WHERE `id`=%s'
    # cursor.execute(sql, (dump_id, ))
    # wikipedia_decisions_count = cursor.fetchone()['wikipedia_decisions_count']
    # print(f'wikipedia decisions count: {wikipedia_decisions_count}')
    #
    # sql = 'SELECT MIN(`id`) AS `first_id` FROM `wikipedia_decisions` WHERE `dump_id`=%s'
    # cursor.execute(sql, (dump_id,))
    # first_id = cursor.fetchone()['first_id']
    #
    # print(f'first id: {first_id}')
    # steps = -(-wikipedia_decisions_count//page_size) - start_page
    # with tqdm(total=steps) as pbar:
    #     for i in range(start_page*page_size, wikipedia_decisions_count, page_size):
    #         start_id = first_id + i
    #         end_id = min(start_id+page_size-1, wikipedia_decisions_count)
    #
    #         pbar.set_description(f'processing ids from {start_id} to {end_id}')
    #
    #         sql = f'SELECT `destination_article_id`, `source_article_id`  FROM `wikipedia_decisions`' \
    #               f'WHERE `id` BETWEEN %s AND %s'
    #         data = (start_id, end_id)
    #         cursor.execute(sql, data)
    #
    #         backlinks = {}
    #         for row in cursor:
    #             destination_article_id = str(row['destination_article_id'])
    #             source_article_id = str(row['source_article_id'])
    #
    #             if destination_article_id in backlinks:
    #                 backlinks[destination_article_id][source_article_id] += 1
    #             else:
    #                 article_backlinks = r.get(destination_article_id)
    #                 if article_backlinks is None:
    #                     article_backlinks = Counter()
    #                 else:
    #                     article_backlinks = Counter(json.loads(article_backlinks))
    #                 article_backlinks[source_article_id] += 1
    #                 backlinks[destination_article_id] = article_backlinks
    #
    #         for destination_article_id, article_backlinks in backlinks.items():
    #             r.set(destination_article_id, json.dumps(article_backlinks))
    #         pbar.update(1)
    #     cursor.close()


@click.command('flush-dump')
@click.argument('dump_id')
@with_appcontext
def flush_dump_command(dump_id):
    r = get_redis(dump_id)
    r.flushdb()


@click.command('flush-all')
@with_appcontext
def flush_all_command():
    r = get_redis()
    r.flushall()


def init_app(app):
    app.cli.add_command(cache_dump_command)
    app.cli.add_command(flush_dump_command)
    app.cli.add_command(flush_all_command)
    app.cli.add_command(cache_backlinks_command)
