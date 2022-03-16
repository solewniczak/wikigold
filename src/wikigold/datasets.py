import glob
import json
import os.path
from collections import defaultdict, Counter
from datetime import datetime

import pandas as pd

import click
from flask.cli import with_appcontext

from .db import get_db


@click.command('load-dataset')
@click.argument('name')
@click.argument('path')
@with_appcontext
def load_dataset(name, path):
    if name not in globals():
        raise NameError('unknown loader')

    db = get_db()
    cursor = db.cursor()
    sql = "INSERT INTO dumps (`lang`, `name`, `timestamp`) VALUES (%s, %s, %s)"
    data = ('en', name, datetime.now().isoformat())
    cursor.execute(sql, data)
    dump_id = cursor.lastrowid

    for title, caption, metadata, lines in globals()[name](path):
        sql = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
        data = (title, caption, dump_id)
        cursor.execute(sql, data)
        article_id = cursor.lastrowid

        for key, value in metadata.items():
            sql = "INSERT INTO `articles_metadata` (`article_id`, `key`, `value`) VALUES (%s, %s, %s)"
            data = (article_id, key, value)
            cursor.execute(sql, data)

        for nr, line in enumerate(lines):
            sql = "INSERT INTO `lines` (`nr`, `content`, `article_id`) VALUES (%s, %s, %s)"
            data = (nr, line, article_id)
            cursor.execute(sql, data)

    sql = 'UPDATE `dumps` SET `articles_count`=(SELECT COUNT(*) FROM articles WHERE `dump_id`=%s) WHERE `id`=%s'
    cursor.execute(sql, (dump_id, dump_id))

    db.commit()


def clmentbisaillon(path):
    '''https://www.kaggle.com/clmentbisaillon/fake-and-real-news-dataset'''
    dfs = {
        'Fake': pd.read_csv(os.path.join(path, 'Fake.csv')),
        'True': pd.read_csv(os.path.join(path, 'True.csv'))
    }
    counter = Counter()
    for label, df in dfs.items():
        for index, row in df.iterrows():
            lines = row['text'].split('\n')
            lines = [line.strip() for line in lines if line.strip() != '']
            if len(lines) > 0:
                metadata = {
                    'index': index,
                    'label': label,
                    'seq': counter[label],
                    'subject': row['subject'],
                    'date': row['date']
                }
                counter[label] += 1
                yield row['title'], lines[0], metadata, lines


def horne2017(path):
    '''https://github.com/BenjaminDHorne/fakenewsdata1'''
    path = os.path.join(path, 'Public Data')
    sources = ['Buzzfeed Political News Dataset', 'Random Poltical News Dataset']
    labels = ['Fake', 'Real', 'Satire']
    counters = defaultdict(Counter)
    for source in sources:
        for label in labels:
            contents_path = os.path.join(path, source, label)
            titles_path = os.path.join(path, source, label + '_titles')
            if not os.path.exists(contents_path):
                continue
            for content_file in os.listdir(contents_path):
                content_path = os.path.join(contents_path, content_file)
                with open(content_path, encoding='windows-1252') as file:
                    content = file.read().splitlines()
                lines = [line for line in content if line != '']

                if len(lines) > 0:
                    title_path = os.path.join(titles_path, content_file)
                    with open(title_path, encoding='iso-8859-1') as file:
                        title = file.readline()
                    metadata = {
                        'source': source,
                        'label': label,
                        'seq': counters[source][label],
                    }
                    counters[source][label] += 1
                    yield title, lines[0], metadata, lines


def fakenewsnet(path):
    '''https://github.com/KaiDMML/FakeNewsNet'''
    sources = ['politifact', 'gossipcop']
    labels = ['fake', 'real']
    counters = defaultdict(Counter)
    for source in sources:
        for label in labels:
            contents_path = os.path.join(path, source, label)
            for content_dir in os.listdir(contents_path):
                content_path = os.path.join(contents_path, content_dir, 'news content.json')
                try:
                    with open(content_path) as f:
                        data = json.load(f)
                    lines = data['text'].split('\n')
                    lines = [line.strip() for line in lines if line.strip() != '']
                    if len(lines) > 0:
                        metadata = {
                            'id': content_dir,
                            'source': source,
                            'label': label,
                            'seq': counters[source][label],
                        }
                        counters[source][label] += 1
                        yield data['title'], lines[0], metadata, lines
                except (FileNotFoundError, json.decoder.JSONDecodeError):
                    pass

def init_app(app):
    app.cli.add_command(load_dataset)