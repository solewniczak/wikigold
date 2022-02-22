import pickle

import redis
import click
from flask import current_app, g
from flask.cli import with_appcontext
from tqdm import tqdm

from .db import get_db
from .helper import get_lines, ngrams


def get_redis(db_name=None):
    db_mappings = {
        'labels': 1,
        'backlinks': 2,
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
    article_backlinks = r.get(article_id)
    if article_backlinks is not None:
        article_backlinks = pickle.loads(article_backlinks)
    else:
        article_backlinks = set()
    return article_backlinks


def add_backlinks_to_cache(article_id, article_backlinks):
    r = get_redis('backlinks')
    r.set(article_id, pickle.dumps(article_backlinks))


def get_cached_label(label_name):
    r = get_redis('labels')
    label = r.get(label_name)
    if label is not None:
        label = pickle.loads(label)
    return label


def add_label_to_cache(label_name, label):
    r = get_redis('labels')
    r.set(label_name, pickle.dumps(label))


@click.command('cache-labels')
@click.argument('dump_id', type=int)
@click.option('-p', '--page-size', type=int, default=500000)
@click.option('-s', '--start-page', type=int, default=0)
@with_appcontext
def cache_labels_command(dump_id, page_size, start_page):
    db = get_db()

    cursor = db.cursor(dictionary=True)
    sql = 'SELECT COUNT(*) AS `articles_with_redirects_count` FROM `articles` WHERE `dump_id`=%s'
    cursor.execute(sql, (dump_id,))
    articles_with_redirects_count = cursor.fetchone()['articles_with_redirects_count']
    print(f'articles with redirects count: {articles_with_redirects_count}')

    sql = '''SELECT `id`, `counter`, `redirect_to_id` FROM `articles` WHERE `articles`.`dump_id`=%s'''
    data = (dump_id,)
    cursor.execute(sql, data)
    articles = {}
    redirects = {}
    with tqdm(total=articles_with_redirects_count) as pbar:
        for row in cursor:
            articles[row['id']] = row['counter']
            if row['redirect_to_id'] is not None:
                redirects[row['id']] = row['redirect_to_id']
            pbar.update(1)

    with tqdm(total=len(redirects)) as pbar:
        for redirect_id, destination_id in redirects.items():
            while destination_id in redirects:
                destination_id = redirects[destination_id]
            articles[destination_id] += articles[redirect_id] # update counters
            redirects[redirect_id] = destination_id
            pbar.update(1)

    sql = '''SELECT COUNT(*) AS `labels_articles_count` FROM `labels_articles` 
                JOIN `labels` ON `labels_articles`.`label_id`=`labels`.`id` WHERE `dump_id`=%s'''
    cursor.execute(sql, (dump_id,))
    labels_articles_count = cursor.fetchone()['labels_articles_count']
    print(f'labels articles count: {labels_articles_count}')

    sql = '''SELECT MIN(`labels_articles`.`id`) AS `first_id` FROM `labels_articles`
                JOIN `labels` ON `labels_articles`.`label_id` = `labels`.`id` WHERE `labels`.`dump_id`=%s'''
    cursor.execute(sql, (dump_id,))
    first_id = cursor.fetchone()['first_id']

    print(f'first id: {first_id}')
    steps = -(-labels_articles_count//page_size) - start_page
    with tqdm(total=steps) as pbar:
        for i in range(start_page*page_size, labels_articles_count, page_size):
            start_id = first_id + i
            end_id = min(start_id+page_size-1, labels_articles_count)

            pbar.set_description(f'processing ids from {start_id} to {end_id}')

            sql = f'''SELECT `labels`.`label`, `labels`.`counter` AS `label_counter`, `labels_articles`.`article_id`,
                            `labels_articles`.`counter` AS `label_article_counter`
                        FROM `labels_articles` JOIN `labels` ON `labels`.`id` = `labels_articles`.`label_id`
                        WHERE `labels_articles`.`article_id` IS NOT NULL AND `labels_articles`.`id` BETWEEN %s AND %s'''
            data = (start_id, end_id)
            cursor.execute(sql, data)

            labels = {}
            for row in cursor:
                label_name = row['label']
                label_counter = row['label_counter']

                if label_name in labels:
                    label = labels[label_name]
                else:
                    label = get_cached_label(label_name)
                    if label is None:
                        label = {'label_counter': label_counter,
                                 'articles': {}}
                    labels[label_name] = label

                label_articles = label['articles']
                article_id = row['article_id']
                if article_id in redirects:
                    article_id = redirects[article_id]
                article_counter = articles[article_id]

                if article_id in label_articles:  # update counters
                    label_articles[article_id]['label_article_counter'] += row['label_article_counter']
                else:
                    label_articles[article_id] = {'article_counter': article_counter,
                                                  'label_article_counter': row['label_article_counter']}

            for label_name, label_data in labels.items():
                add_label_to_cache(label_name, label_data)

            pbar.update(1)
        cursor.close()


def get_wikipedia_decisions_labels_set(article_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = '''SELECT `label` FROM `wikipedia_decisions` WHERE `source_article_id`=%s'''
    data = (article_id,)
    cursor.execute(sql, data)

    labels = set()
    for row in cursor:
        labels.add(row['label'])
    cursor.close()

    return labels


@click.command('cache-labels-counters')
@click.argument('dump_id', type=int)
@with_appcontext
def cache_labels_counters_command(dump_id):
    db = get_db()
    r = get_redis('labels')

    labels_counters = {}
    nb_labels = r.dbsize()
    with tqdm(total=nb_labels) as pbar:
        for label_name in r.scan_iter("*"):
            label_name = label_name.decode('utf-8')
            labels_counters[label_name] = {'appeared_in': 0, 'as_link_in': 0}
            pbar.update(1)

    cursor = db.cursor(dictionary=True)
    sql = 'SELECT `id` FROM `articles` WHERE `dump_id`=%s AND `redirect_to_title` IS NULL'
    cursor.execute(sql, (dump_id, ))
    articles_ids = [row['id'] for row in cursor]
    cursor.close()

    with tqdm(total=len(articles_ids)) as pbar:
        for article_id in articles_ids:
            try:
                lines = get_lines(article_id)  # raises ValueError
                wikipedia_labels_set = get_wikipedia_decisions_labels_set(article_id)
                article_ngrams = {ngram['name'] for ngram in ngrams(lines)}
                for label in article_ngrams:
                    if label in labels_counters:
                        labels_counters[label]['appeared_in'] += 1
                        if label in wikipedia_labels_set:
                            labels_counters[label]['as_link_in'] += 1
            except ValueError:
                print(f'cannot tokenize article: {article_id}. skipping')
            pbar.update(1)

    with tqdm(total=nb_labels) as pbar:
        for label_name, label_counters in labels_counters.items():
            label = get_cached_label(label_name)
            label.update(label_counters)
            add_label_to_cache(label_name, label)
            pbar.update(1)


@click.command('cache-backlinks')
@click.argument('dump_id', type=int)
@click.option('-p', '--page-size', type=int, default=500000)
@click.option('-s', '--start-page', type=int, default=0)
@with_appcontext
def cache_backlinks_command(dump_id, page_size, start_page):
    db = get_db()

    cursor = db.cursor(dictionary=True)
    sql = 'SELECT COUNT(*) AS `wikipedia_decisions_count` FROM `wikipedia_decisions` WHERE `dump_id`=%s'
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
                  f'WHERE `destination_article_id` IS NOT NULL AND `id` BETWEEN %s AND %s'
            data = (start_id, end_id)
            cursor.execute(sql, data)

            backlinks = {}
            for row in cursor:
                destination_article_id = row['destination_article_id']
                source_article_id = row['source_article_id']

                if destination_article_id in backlinks:
                    backlinks[destination_article_id].add(source_article_id)
                else:
                    article_backlinks = get_cached_backlinks(destination_article_id)
                    article_backlinks.add(source_article_id)
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
    app.cli.add_command(cache_labels_counters_command)
    app.cli.add_command(cache_backlinks_command)
    app.cli.add_command(flush_db_command)
    app.cli.add_command(flush_all_command)

