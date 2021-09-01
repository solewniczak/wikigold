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

    sql_charter_maximum_length = '''SELECT character_maximum_length FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = %s'''
    cursor.execute(sql_charter_maximum_length, ('articles', 'title'))
    title_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('lines', 'content'))
    line_content_maximum_length = cursor.fetchone()[0]

    tag_split = tag.split('-')
    lang = tag_split[0][:-4] # remove "wiki" from lang
    dump_date = tag_split[1]

    sql_add_dump = "INSERT INTO dumps (`lang`, `date`, `parser`) VALUES (%s, %s, %s)"
    data_dump = (lang, dump_date, dump_parser.parser_name)
    cursor.execute(sql_add_dump, data_dump)
    dump_id = cursor.lastrowid


    sql_add_article = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
    sql_add_article_redirect = "INSERT INTO `articles` (`title`, `redirect_to_title`, `dump_id`) VALUES (%s, %s, %s)"
    dict_articles_ids = {}
    dict_articles_captions = {}
    dict_redirect_articles = {}
    sql_add_line = "INSERT INTO `lines` (`article_id`, `nr`, `content`) VALUES (%s, %s, %s)"
    for title, lines, redirect_to in dump_parser.parse_xml(pages_meta_current_filepath, all_titles_in_ns0, all_titles_count, early_stopping=None):
        if len(title) > title_maximum_length:
            print(f"title: '{title[:256]}...' exceeds maximum title length ({title_maximum_length}). skipping")
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
    sql_add_label = "INSERT INTO `labels` (`label`, `counter`) VALUES (%s, %s)"
    dict_labels_ids = {}
    for label, counter in dump_parser.links_labels.items():
        data_label = (label, counter)
        cursor.execute(sql_add_label, data_label)
        label_id = cursor.lastrowid
        dict_labels_ids[label] = label_id

    # save labels_titles
    sql_add_label_article = "INSERT INTO `labels_articles` (`label_id`, `title`, `article_id`, `counter`) VALUES (%s, %s, %s, %s)"
    for label, titles in dump_parser.link_titles.items():
        for title, counter in titles.items():
            article_id = None
            if title in dict_articles_ids:
                article_id = dict_articles_ids[title]
            data_label_article = (dict_labels_ids[label], title, article_id, counter)
            cursor.execute(sql_add_label_article, data_label_article)

    # update article counters
    sql_update_article_counter = "UPDATE `articles` SET `counter`=%s WHERE `title`=%s AND `dump_id`=%s"
    for title, counter in dump_parser.links_titles_freq.items():
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

    db.commit()
    cursor.close()


def init_app(app):
    app.cli.add_command(import_dump_command)