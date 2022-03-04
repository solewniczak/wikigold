from datetime import datetime

import pandas as pd

import click
from flask import current_app, g
from flask.cli import with_appcontext
from tqdm import tqdm

from .db import get_db


@click.command('load-dataset')
@click.argument('path')
@with_appcontext
def load_dataset(path):
    db = get_db()
    cursor = db.cursor()
    sql = "INSERT INTO dumps (`lang`, `name`, `timestamp`) VALUES (%s, %s, %s)"
    data = ('en', 'fake_or_real_news', datetime.now().isoformat())
    cursor.execute(sql, data)
    dump_id = cursor.lastrowid

    df = pd.read_csv(path)
    for index, row in df.iterrows():
        lines = row['text'].split('\n')
        lines = [line.strip() for line in lines if line.strip() != '']
        if len(lines) > 0:
            sql = "INSERT INTO `articles` (`title`, `caption`, `redirect_to_title`, `dump_id`) VALUES (%s, %s, %s, %s)"
            data = (index, row['title'], row['id'], dump_id)
            cursor.execute(sql, data)
            article_id = cursor.lastrowid

            for nr, line in enumerate(lines):
                sql = "INSERT INTO `lines` (`nr`, `content`, `article_id`) VALUES (%s, %s, %s)"
                data = (nr, line, article_id)
                cursor.execute(sql, data)

    sql = 'UPDATE `dumps` SET `articles_count`=(SELECT COUNT(*) FROM articles WHERE `dump_id`=%s) WHERE `id`=%s'
    cursor.execute(sql, (dump_id, dump_id))

    db.commit()


def init_app(app):
    app.cli.add_command(load_dataset)