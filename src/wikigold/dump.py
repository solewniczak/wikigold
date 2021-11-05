import bz2
import json
import sys
from datetime import datetime
import os.path
from bz2 import BZ2Decompressor
from functools import partial

from tqdm import tqdm
import requests

import click
from flask import current_app, g
from flask.cli import with_appcontext

from .db import get_db
from .mediawikixml import MediaWikiXml, iterate_xml_dump, normalize_title

import mwparallelparser


@click.command('import-dump')
@click.argument('lang')
@click.argument('dump_date')
@click.option('-e', '--early-stopping', type=int, default=-1, help='Stop dump parsing after -e articles. -1 means no '
                                                                   'early stopping.')
@click.option('-m', '--mirror', default='http://dumps.wikimedia.org')
@click.option('--download/--no-download', default=False)
@click.option('--decompress/--no-decompress', default=False)
@with_appcontext
def import_dump_command(lang, dump_date, early_stopping, mirror, download, decompress):

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

    dump = xml_dump_stream()
    mediawikixml = MediaWikiXml(dump, metadata)

    sql_charter_maximum_length = '''SELECT character_maximum_length FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = %s'''
    cursor.execute(sql_charter_maximum_length, ('articles', 'title'))
    title_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('lines', 'content'))
    line_content_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('labels', 'label'))
    label_maximum_length = cursor.fetchone()[0]

    parser_name = mwparallelparser.__name__
    parser_version = mwparallelparser.__version__
    sql_add_dump = "INSERT INTO dumps (`lang`, `date`, `parser_name`, `parser_version`, `timestamp`) VALUES (%s, %s, %s, %s, %s)"
    data_dump = (lang, dump_date, parser_name, parser_version, datetime.now().isoformat())
    cursor.execute(sql_add_dump, data_dump)
    dump_id = cursor.lastrowid

    sql_add_article = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
    sql_add_article_redirect = "INSERT INTO `articles` (`title`, `redirect_to_title`, `dump_id`) VALUES (%s, %s, %s)"

    sql_add_line = "INSERT INTO `lines` (`article_id`, `nr`, `content`) VALUES (%s, %s, %s)"
    sql_add_wikipedia_decision = '''INSERT INTO `wikipedia_decisions`
    (`source_line_id`, `start`, `length`, `label`, `destination_title`, `dump_id`) VALUES (%s, %s, %s, %s, %s, %s)'''
    for title, lines, redirect_to, wikipedia_decisions in mediawikixml.parse(early_stopping=early_stopping):
        if len(title) > title_maximum_length:
            print(f"title '{title[:title_maximum_length]}...' exceeds maximum length ({title_maximum_length})")
            continue

        if redirect_to is None:
            try:
                caption = lines[0]
            except IndexError:
                caption = None
            data_article = (title, caption, dump_id)
            cursor.execute(sql_add_article, data_article)
            article_id = cursor.lastrowid

            for line_nr, content in enumerate(lines):
                if len(content) > line_content_maximum_length:
                    print(f"line {title}({line_nr}): '{content[:50]}...' exceeds maximum length ({line_content_maximum_length})")
                    continue
                data_line = (article_id, line_nr, content)
                cursor.execute(sql_add_line, data_line)
                line_id = cursor.lastrowid
                if line_nr in wikipedia_decisions:
                    for link in wikipedia_decisions[line_nr]:
                        label = link['label']
                        if len(label) > label_maximum_length:
                            print(f"label {label} in {title}({line_nr}): '{label[:label_maximum_length]}...' "
                                f"exceeds length ({label_maximum_length})")
                            continue
                        destination_title = link['destination']
                        if len(destination_title) > title_maximum_length:
                            print(f"destination title: '{destination_title[:title_maximum_length]}...' "
                                f"exceeds maximum length ({title_maximum_length})")
                        else:
                            data_wikipedia_decision = (line_id, link['start'], link['length'], link['label'],
                                                       link['destination'], dump_id)
                            cursor.execute(sql_add_wikipedia_decision, data_wikipedia_decision)

        else:
            data_article = (title, redirect_to, dump_id)
            cursor.execute(sql_add_article_redirect, data_article)

    # save labels
    sql_create_labels = '''INSERT INTO `labels` (`label`, `dump_id`, `counter`)
                            SELECT `label`, `dump_id`, COUNT(*) FROM `wikipedia_decisions` WHERE `dump_id`=%s GROUP BY `label`'''
    cursor.execute(sql_create_labels, (dump_id, ))

    # update wikipedia_decisions destination_id
    sql_update_wikipedia_decisions = '''
    UPDATE `wikipedia_decisions` INNER JOIN `articles` ON `wikipedia_decisions`.`destination_title`=`articles`.`title`
        SET `wikipedia_decisions`.`destination_article_id` = `articles`.`id`
        WHERE `wikipedia_decisions`.`dump_id`=%s AND `articles`.`dump_id`=%s'''
    cursor.execute(sql_update_wikipedia_decisions, (dump_id, dump_id))

    # update wikipedia_decisions label_id
    sql_update_wikipedia_decisions = '''
        UPDATE `wikipedia_decisions` INNER JOIN `labels` ON `wikipedia_decisions`.`label`=`labels`.`label`
            SET `wikipedia_decisions`.`label_id` = `labels`.`id`
            WHERE `wikipedia_decisions`.`dump_id`=%s AND `labels`.`dump_id`=%s'''
    cursor.execute(sql_update_wikipedia_decisions, (dump_id, dump_id))

    # update redirect articles
    sql_update_article_redirect = '''
    UPDATE `articles` `a1` INNER JOIN `articles` `a2` ON `a1`.`redirect_to_title`=`a2`.`title`
        SET `a1`.`caption`=`a2`.`caption`, `a1`.`redirect_to_id`=`a2`.`id`
        WHERE `a1`.`dump_id`=%s AND `a2`.`dump_id`=%s'''
    data_article_redirect = (dump_id, dump_id)
    cursor.execute(sql_update_article_redirect, data_article_redirect)

    # update article counters
    sql_update_article_counter = '''UPDATE `articles` INNER JOIN
                                        (SELECT `destination_title`, COUNT(*) AS `counter` FROM `wikipedia_decisions`
                                            WHERE `dump_id`=%s GROUP BY `destination_title`) `wd1`
                                        ON `articles`.`title`=`wd1`.`destination_title`
                                        SET `articles`.`counter`=`wd1`.`counter`
                                        WHERE `articles`.`dump_id`=%s'''
    cursor.execute(sql_update_article_counter, (dump_id, dump_id))

    # save labels_articles
    sql_create_labels_articles = '''INSERT INTO `labels_articles` (`label_id`, `title`, `article_id`, `counter`)
                            SELECT `wd`.`label_id`, `wd`.`destination_title`, `wd`.`destination_article_id`, COUNT(*)
                                FROM `wikipedia_decisions` `wd`
                                WHERE `wd`.`dump_id`=%s
                                GROUP BY `wd`.`label_id`, `wd`.`destination_title`, `wd`.`destination_article_id`'''
    cursor.execute(sql_create_labels_articles, (dump_id,))


    db.commit()
    cursor.close()
    dump.close()


def init_app(app):
    app.cli.add_command(import_dump_command)