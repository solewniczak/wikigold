import os.path

import click
from flask import current_app, g
from flask.cli import with_appcontext

from app.db import get_db
from DumpParser.dumpparser import DumpParser


@click.command('import-dump')
@click.argument('dir', type=click.Path(exists=True))
@click.argument('tag')
@with_appcontext
def import_dump_command(dir, tag):
    pages_meta_current_filepath = os.path.join(dir, f'{tag}-pages-meta-current.xml')
    all_titles_filepath = os.path.join(dir, f'{tag}-all-titles')
    all_titles_in_ns0_filepath = os.path.join(dir, f'{tag}-all-titles-in-ns0')

    with open(all_titles_filepath) as fp:
        all_titles_count = sum(1 for line in fp)

    with open(all_titles_in_ns0_filepath) as fp:
        all_titles_in_ns0 = [line.rstrip('\n') for line in fp]

    db = get_db()
    cursor = db.cursor()
    dump_parser = DumpParser()

    sql_add_dump = "INSERT INTO dumps (name, parser) VALUES (%s, %s)"
    data_dump = (tag, dump_parser.parser_name)
    cursor.execute(sql_add_dump, data_dump)
    dump_id = cursor.lastrowid


    sql_add_article = "INSERT INTO `articles` (`title`, `dump_id`) VALUES (%s, %s)"
    sql_add_line = "INSERT INTO `lines` (`article_id`, `nr`, `content`) VALUES (%s, %s, %s)"
    for title, lines in dump_parser.parse_xml(pages_meta_current_filepath, all_titles_in_ns0, all_titles_count):
        data_article = (title, dump_id)
        cursor.execute(sql_add_article, data_article)
        article_id = cursor.lastrowid
        for line_nr, content in enumerate(lines):
            data_line = (article_id, line_nr, content)
            cursor.execute(sql_add_line, data_line)

    # save labels
    sql_add_label = "INSERT INTO `labels` (`label`, `counter`) VALUES (%s, %s)"
    dict_labels_ids = {}
    for label, counter in dump_parser.links_labels.items():
        data_label = (label, counter)
        cursor.execute(sql_add_label, data_label)
        label_id = cursor.lastrowid
        dict_labels_ids[label] = label_id

    # save labels_titles
    sql_add_label_article = "INSERT INTO `labels_titles` (`label_id`, `title`, `counter`) VALUES (%s, %s, %s)"
    for label, titles in dump_parser.link_titles.items():
        for title, counter in titles.items():
            data_label_article = (dict_labels_ids[label], title, counter)
            cursor.execute(sql_add_label_article, data_label_article)

    # update article counters
    sql_update_article_counter = "UPDATE `articles` SET `counter`=%s WHERE `title`=%s AND `dump_id`=%s"
    for title, counter in dump_parser.links_titles_freq.items():
        data_article = (counter, title, dump_id)
        cursor.execute(sql_update_article_counter, data_article)

    db.commit()
    cursor.close()


def init_app(app):
    app.cli.add_command(import_dump_command)