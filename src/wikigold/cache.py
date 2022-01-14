import json

import redis

import click
from flask import current_app, g
from flask.cli import with_appcontext
from tqdm import tqdm

from .db import get_db


def get_redis(dump_id=None):
    if 'redis' not in g:
        g.redis = redis.from_url(current_app.config['REDIS_URL'], db=dump_id)

    return g.redis


def cached_labels(dump_id):
    r = get_redis(dump_id)
    return r.dbsize()


@click.command('cache-dump')
@click.argument('dump_id')
@with_appcontext
def cache_dump_command(dump_id):
    r = get_redis(dump_id)
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
