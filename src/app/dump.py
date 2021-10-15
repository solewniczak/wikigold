import bz2
import json
from datetime import datetime
import os.path
from bz2 import BZ2Decompressor
from functools import partial

from tqdm import tqdm
import requests

import click
from flask import current_app, g
from flask.cli import with_appcontext

from app.db import get_db
from app.mediawikixml import MediaWikiXml, iterate_xml_dump, normalize_title

import mwparserfromhelllinks
import mwparallelparser


@click.command('import-dump')
@click.argument('lang')
@click.argument('dump_date')
@click.option('-e', '--early-stopping', type=int, default=-1, help='Stop dump parsing after -e articles. -1 means no '
                                                                   'early stopping.')
@click.option('-p', '--parser', type=click.Choice(['MwParallelParser', 'MwParserFromHellLinks'], case_sensitive=False),
              default='MwParserFromHellLinks')
@click.option('-m', '--mirror', default='http://dumps.wikimedia.org')
@click.option('--download/--no-download', default=False)
@click.option('--decompress/--no-decompress', default=False)
@with_appcontext
def import_dump_command(lang, dump_date, early_stopping, parser, mirror, download, decompress):

    mirror = mirror.rstrip('/')

    filename = f'{lang}wiki-{dump_date}-pages-meta-current.xml'
    filename_bz2 = f'{lang}wiki-{dump_date}-pages-meta-current.xml.bz2'
    filename_metadata = f'{lang}wiki-{dump_date}-metadata.json'

    url = f'{mirror}/{lang}wiki/{dump_date}/{filename_bz2}'

    homedir = os.path.expanduser("~/")
    if homedir == "~/":
        raise ValueError('could not find a default download directory')

    download_dir = os.path.join(homedir, 'wikigold_data')
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    filepath = os.path.join(download_dir, filename)
    filepath_bz2 = os.path.join(download_dir, filename_bz2)
    filepath_metadata = os.path.join(download_dir, filename_metadata)

    chunk_size = 1024

    def download_xml_dump():
        if not os.path.exists(filepath_bz2):
            r = requests.get(url, stream=True)
            total_size = int(r.headers['Content-Length'])
            with open(filepath_bz2, 'wb') as file_bz2, tqdm(
                    desc='downloading: ' + filename_bz2,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=chunk_size,
            ) as bar:
                for data in r.iter_content(chunk_size=chunk_size):
                    size = file_bz2.write(data)
                    bar.update(size)
            r.close()

    def decompress_xml_dump():
        if not os.path.exists(filepath):
            total_size = os.path.getsize(filepath_bz2)
            with open(filepath_bz2, 'rb') as file_bz2, open(filepath, 'wb') as file, tqdm(
                    desc='unpacking: ' + filename_bz2,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
            ) as bar:
                decompressor = BZ2Decompressor()
                for data in iter(partial(file_bz2.read, chunk_size), b''):
                    size = len(data)
                    file.write(decompressor.decompress(data))
                    bar.update(size)

    def xml_dump_stream():
        if download and decompress:
            download_xml_dump()
            decompress_xml_dump()
            return open(filepath)
        elif download:
            download_xml_dump()
            return bz2.open(filepath_bz2)
        else:
            raise "downloading on fly not implemented"

    if not os.path.exists(filepath_metadata):
        with xml_dump_stream() as dump:
            print('collecting metadata ...', end=' ')
            titles_in_ns0 = set()
            for page in iterate_xml_dump(dump, tags=('ns', 'title')):
                ns = page['ns'].text.strip()
                title = page['title'].text
                if ns == '0':
                    title = normalize_title(title)
                    titles_in_ns0.add(title)

            metadata = {'titles_in_ns0': list(titles_in_ns0)}
            with open(filepath_metadata, 'w') as file:
                json.dump(metadata, file)
            print('done')
    else:
        print(f'loading metadata from: {filename_metadata}')
        with open(filepath_metadata, 'r') as file:
            metadata = json.load(file)
        metadata['titles_in_ns0'] = set(metadata['titles_in_ns0'])

    db = get_db()
    cursor = db.cursor()

    if parser == 'MwParallelParser':
        parser = mwparallelparser.Parser()
    elif parser == 'MwParserFromHellLinks':
        parser = mwparserfromhelllinks.Parser()

    dump = xml_dump_stream()
    mediawikixml = MediaWikiXml(dump, metadata, parser)

    sql_charter_maximum_length = '''SELECT character_maximum_length FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = %s'''
    cursor.execute(sql_charter_maximum_length, ('articles', 'title'))
    title_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('lines', 'content'))
    line_content_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('labels', 'label'))
    label_maximum_length = cursor.fetchone()[0]

    sql_add_dump = "INSERT INTO dumps (`lang`, `date`, `parser_name`, `parser_version`, `timestamp`) VALUES (%s, %s, %s, %s, %s)"
    data_dump = (lang, dump_date, parser.name, parser.version, datetime.now().isoformat())
    cursor.execute(sql_add_dump, data_dump)
    dump_id = cursor.lastrowid


    sql_add_article = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
    sql_add_article_redirect = "INSERT INTO `articles` (`title`, `redirect_to_title`, `dump_id`) VALUES (%s, %s, %s)"
    dict_articles_ids = {}
    dict_articles_captions = {}
    dict_redirect_articles = {}
    dict_lines_ids = {}
    sql_add_line = "INSERT INTO `lines` (`article_id`, `nr`, `content`) VALUES (%s, %s, %s)"
    for title, lines, redirect_to in mediawikixml.parse(early_stopping=early_stopping):
        if len(title) > title_maximum_length:
            print(f"title: '{title[:title_maximum_length]}...' exceeds maximum title length ({title_maximum_length}). skipping")
            continue

        if redirect_to is None:
            try:
                caption = lines[0]
            except IndexError:
                caption = None
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
                line_id = cursor.lastrowid
                dict_lines_ids[(title, line_nr)] = line_id
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
                f"save labels: label {label[:label_maximum_length]}...' exceeds maximum label length ({label_maximum_length}). skipping")
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

            try:
                data_label_article = (dict_labels_ids[label], title, article_id, counter)
                cursor.execute(sql_add_label_article, data_label_article)
            except KeyError:
                print(f'save label_titles: there is no label: {label} in database')

    sql_add_wikipedia_decision = '''INSERT INTO `wikipedia_decisions`
    (`source_line_id`, `start`, `length`, `destination_title`, `destination_article_id`) VALUES (%s, %s, %s, %s, %s)'''
    for link in mediawikixml.wikipedia_decisions:
        if (link['source'], link['line']) not in dict_lines_ids:
            print(f'there is not line for {link["source"]}:{link["line"]}')
            continue
        source_line_id = dict_lines_ids[(link['source'], link['line'])]
        destination_title = link['destination']
        if link['destination'] in dict_articles_ids:
            destination_article_id = dict_articles_ids[link['destination']]
        else:
            destination_article_id = None
            # print(f'cannot find destination article id for title: {destination_title}')
        if len(destination_title) > title_maximum_length:
            print(
                f"destination title: '{destination_title[:title_maximum_length]}...' exceeds maximum title length ({title_maximum_length}). skipping")
        else:
            data_wikipedia_decision = (source_line_id, link['start'], link['length'], destination_title, destination_article_id)
            cursor.execute(sql_add_wikipedia_decision, data_wikipedia_decision)


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
    dump.close()


def init_app(app):
    app.cli.add_command(import_dump_command)