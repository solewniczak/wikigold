import json

import redis

import click
from flask import current_app, g
from flask.cli import with_appcontext
from tqdm import tqdm

from src.wikigold.db import get_db


def get_redis(dump_id=None):
    if 'redis' not in g:
        g.redis = redis.from_url(current_app.config['REDIS_URL'], db=dump_id)

    return g.redis


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

    sql = '''SELECT `labels`.`label`, `labels`.`counter` AS `label_counter`,
            `labels_articles`.`article_id`, `labels_articles`.`title`, `labels_articles`.`counter` AS `label_title_counter`,
            `articles`.`counter` AS `article_counter`, `articles`.`caption`, `articles`.`redirect_to_title`
            FROM `labels`   JOIN `labels_articles` ON `labels`.`id` = `labels_articles`.`label_id`
                            JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`
            WHERE `labels`.`dump_id`=%s AND `labels`.`counter` >= 5'''

    data = (dump_id,)
    cursor.execute(sql, data)
    with tqdm(total=counter) as pbar:
        for row in cursor:
            title = {
                'article_id': row['article_id'],
                'title': row['title'],
                'label_title_counter': row['label_title_counter'],
                'article_counter': row['article_counter'],
                'caption': row['caption'],
                'redirect_to_title': row['redirect_to_title']
            }
            if title['caption'] is not None:
                title['caption'] = title['caption'].decode('utf-8')

            label = row['label']
            value = r.get(label)
            if value is None:
                value = {
                    'counter': row['label_counter'],
                    'titles': [title]
                }
            else:
                value = json.loads(value)
                value['titles'].append(title)
            r.set(label, json.dumps(value))
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
