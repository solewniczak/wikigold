import os.path
from bz2 import BZ2Decompressor

from tqdm import tqdm
import requests

import click
from flask import current_app, g
from flask.cli import with_appcontext

from app.db import get_db
from app.mediawikixml import MediaWikiXml
import MwParallelParser.parser
import MwParserFromHellLinks.parser


@click.command('import-dump')
@click.argument('lang')
@click.argument('dump_date')
@click.option('-e', '--early-stopping', type=int, default=-1, help='Stop dump parsing after -e articles. -1 means no '
                                                                   'early stopping.')
@click.option('-p', '--parser', type=click.Choice(['MwParallelParser', 'MwParserFromHellLinks'], case_sensitive=False),
              default='MwParserFromHellLinks')
@with_appcontext
def import_dump_command(lang, dump_date, early_stopping, parser):

    filename = f'{lang}wiki-{dump_date}-pages-meta-current.xml'

    homedir = os.path.expanduser("~/")
    if homedir == "~/":
        raise ValueError('could not find a default download directory')

    download_dir = os.path.join(homedir, 'wikigold_data')
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    filepath = os.path.join(download_dir, filename)

    if not os.path.exists(filepath):
        url = f'http://dumps.wikimedia.org/{lang}wiki/{dump_date}/{filename}.bz2'
        chunk_size = 1024
        with requests.get(url, stream=True) as request:
            total_size = int(request.headers['Content-Length'])

            with open(filepath, 'wb') as file:
                decompressor = BZ2Decompressor()
                for data in tqdm(iterable=request.iter_content(chunk_size=chunk_size), total=total_size / chunk_size, unit='KB'):
                    file.write(decompressor.decompress(data))

    db = get_db()
    cursor = db.cursor()

    if parser == 'MwParallelParser':
        parser = MwParallelParser.parser.Parser()
    elif parser == 'MwParserFromHellLinks':
        parser = MwParserFromHellLinks.parser.Parser()

    mediawikixml = MediaWikiXml(filepath, parser)

    sql_charter_maximum_length = '''SELECT character_maximum_length FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = %s'''
    cursor.execute(sql_charter_maximum_length, ('articles', 'title'))
    title_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('lines', 'content'))
    line_content_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('labels', 'label'))
    label_maximum_length = cursor.fetchone()[0]

    sql_add_dump = "INSERT INTO dumps (`lang`, `date`, `parser_name`, `parser_version`) VALUES (%s, %s, %s, %s)"
    data_dump = (lang, dump_date, parser.name, parser.version)
    cursor.execute(sql_add_dump, data_dump)
    dump_id = cursor.lastrowid


    sql_add_article = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
    sql_add_article_redirect = "INSERT INTO `articles` (`title`, `redirect_to_title`, `dump_id`) VALUES (%s, %s, %s)"
    dict_articles_ids = {}
    dict_articles_captions = {}
    dict_redirect_articles = {}
    sql_add_line = "INSERT INTO `lines` (`article_id`, `nr`, `content`) VALUES (%s, %s, %s)"
    for title, lines, redirect_to in mediawikixml.parse(early_stopping=early_stopping):
        if len(title) > title_maximum_length:
            print(f"title: '{title[:title_maximum_length]}...' exceeds maximum title length ({title_maximum_length}). skipping")
            continue

        if redirect_to is None:
            caption = lines[0]
            data_article = (title, caption, dump_id)
            cursor.execute(sql_add_article, data_article)
            article_id = cursor.lastrowid
            dict_articles_ids[title] = article_id
            dict_articles_captions[title] = caption
            for line_nr, content in enumerate(lines):
                if len(content) > line_content_maximum_length:
                    print(f"line: {title}({line_nr}): '{content[:50]}...' exceeds maximum line length ({line_content_maximum_length}). skipping")
                    continue
                data_line = (article_id, line_nr, content)
                cursor.execute(sql_add_line, data_line)
        else:
            data_article = (title, redirect_to, dump_id)
            cursor.execute(sql_add_article_redirect, data_article)
            article_id = cursor.lastrowid
            dict_articles_ids[title] = article_id
            dict_redirect_articles[article_id] = redirect_to

    # save labels
    sql_add_label = "INSERT INTO `labels` (`label`, `dump_id`, `counter`) VALUES (%s, %s, %s)"
    dict_labels_ids = {}
    for label, counter in mediawikixml.links_labels.items():
        if len(label) > label_maximum_length:
            print(
                f"label: {label[:label_maximum_length]}...' exceeds maximum label length ({label_maximum_length}). skipping")
            continue

        data_label = (label, dump_id, counter)
        cursor.execute(sql_add_label, data_label)
        label_id = cursor.lastrowid
        dict_labels_ids[label] = label_id

    # save labels_titles
    sql_add_label_article = "INSERT INTO `labels_articles` (`label_id`, `title`, `article_id`, `counter`) VALUES (%s, %s, %s, %s)"
    for label, titles in mediawikixml.link_titles.items():
        for title, counter in titles.items():
            article_id = None
            if title in dict_articles_ids:
                article_id = dict_articles_ids[title]
            data_label_article = (dict_labels_ids[label], title, article_id, counter)
            cursor.execute(sql_add_label_article, data_label_article)

    # update article counters
    sql_update_article_counter = "UPDATE `articles` SET `counter`=%s WHERE `title`=%s AND `dump_id`=%s"
    for title, counter in mediawikixml.links_titles_freq.items():
        data_article = (counter, title, dump_id)
        cursor.execute(sql_update_article_counter, data_article)

    # update redirect articles
    sql_update_article_redirect = "UPDATE `articles` SET `caption`=%s, `redirect_to_id`=%s WHERE `id`=%s"
    for article_id, redirect_to_title in dict_redirect_articles.items():
        if redirect_to_title in dict_articles_ids:
            caption = dict_articles_captions[redirect_to_title]
            redirect_to_id = dict_articles_ids[redirect_to_title]
            data_article = (caption, redirect_to_id, article_id)
            cursor.execute(sql_update_article_redirect, data_article)

    # save dump_id in config
    sql_select_currentdump = "SELECT `value` FROM `config` WHERE `key`='currentdump'"
    cursor.execute(sql_select_currentdump)
    currentdump = cursor.fetchone()
    if currentdump is None:
        sql_insert_currentdump = "INSERT INTO `config` (`key`, `value`, `type`) VALUES ('currentdump', %s, 'int')"
        data_config = (dump_id, )
        cursor.execute(sql_insert_currentdump, data_config)

    db.commit()
    cursor.close()


def init_app(app):
    app.cli.add_command(import_dump_command)