import glob
import json
import re
import time
from collections import defaultdict
from datetime import datetime
import os.path

from tqdm import tqdm

import click
from flask.cli import with_appcontext

from .db import get_db
from WHParallelParser import WHParallelParser
import mwparallelparser


@click.command('import-enterprise-dump')
@click.argument('lang')
@click.argument('dump_date')
@click.argument('dump_path')
@click.option('-e', '--early-stopping', type=int, default=-1, help='stop dump parsing after -e articles. -1 means no '
                                                                   'early stopping.')
@click.option('-d', '--dump-id', type=int, default=-1, help='continue the import for a specified dump id')
@click.option('-g', '--ground-truth-id', type=int, default=-1, help='continue the import for a specified ground truth')
@click.option('-s', '--start-step', type=int, default=1, help='continue the import from a specified step')
@with_appcontext
def import_enterprise_dump_command(lang, dump_date, dump_path, early_stopping, dump_id, ground_truth_id, start_step):
    filename_metadata = f'{lang}wiki-{dump_date}-enterprise-metadata.json'

    homedir = os.path.expanduser("~/")
    if homedir == "~/":
        raise ValueError('could not find a default download directory')

    download_dir = os.path.join(homedir, 'wikigold_data')
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)

    filepath_metadata = os.path.join(download_dir, filename_metadata)

    db = get_db()
    cursor = db.cursor()

    sql_charter_maximum_length = '''SELECT character_maximum_length FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = %s'''
    cursor.execute(sql_charter_maximum_length, ('articles', 'title'))
    title_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('lines', 'content'))
    line_content_maximum_length = cursor.fetchone()[0]

    cursor.execute(sql_charter_maximum_length, ('labels', 'label'))
    label_maximum_length = cursor.fetchone()[0]

    if dump_id == -1:
        parser_name = mwparallelparser.__name__
        parser_version = mwparallelparser.__version__
        sql_add_dump = "INSERT INTO dumps (`lang`, `name`, `parser_name`, `parser_version`, `timestamp`) VALUES (%s, %s, %s, %s, %s)"
        name = f'{lang}wiki-{dump_date}'
        data_dump = (lang, name, parser_name, parser_version, datetime.now().isoformat())
        cursor.execute(sql_add_dump, data_dump)
        dump_id = cursor.lastrowid

        sql_add_ground_truth = "INSERT INTO ground_truth (`name`, `description`, `dump_id`, `knowledge_base_id`) VALUES (%s, %s, %s, %s)"
        data_ground_truth = ("wikipedia", "Links created by Wikipedia contributors.", dump_id, dump_id)
        cursor.execute(sql_add_ground_truth, data_ground_truth)
        ground_truth_id = cursor.lastrowid

        db.commit()  # save dump into database

    def step_1():
        print(f'step 1. processing dump...')

        dump_filepaths = sorted(glob.glob(os.path.join(dump_path, '*.ndjson')),
                            key=lambda fn: int(re.sub(r'[^0-9]', '', fn)))
        dump_filenames = [os.path.basename(filepath) for filepath in dump_filepaths]

        if not os.path.exists(filepath_metadata):
            print('collecting metadata ...')
            articles_counter = {}
            for filename in dump_filenames:
                print(f'counting articles in {filename}...')
                articles_counter[filename] = 0
                filepath = os.path.join(dump_path, filename)
                with open(filepath) as fp:
                    for line in fp:
                        articles_counter[filename] += 1

            metadata = {'articles_counter': articles_counter}
            with open(filepath_metadata, 'w') as file:
                json.dump(metadata, file)
            print('done')
        else:
            print(f'loading metadata from: {filename_metadata}')
            with open(filepath_metadata, 'r') as file:
                metadata = json.load(file)

        sql_add_article = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
        sql_add_article_redirect = "INSERT INTO `articles` (`title`, `redirect_to_title`, `dump_id`) VALUES (%s, %s, %s)"

        sql_add_line = "INSERT INTO `lines` (`article_id`, `nr`, `content`) VALUES (%s, %s, %s)"
        sql_add_ground_truth_decisions = '''INSERT INTO `ground_truth_decisions`
        (`source_article_id`, `source_line_id`, `start`, `length`, `label`, `destination_title`, `ground_truth_id`) VALUES (%s, %s, %s, %s, %s, %s, %s)'''

        parser = WHParallelParser()

        def process_article(article):
            title = article['name']
            if len(title) > title_maximum_length:
                print(f"title '{article[:title_maximum_length]}...' exceeds maximum length ({title_maximum_length})")
                return

            # parse article before processing redirects
            try:
                article_parsed = parser.parse_html(article['article_body']['html'])
            except Exception:
                print(f'{title}: parser error')
                return

            if 'redirects' in article:
                for redirect in article['redirects']:
                    data_article_redirect = (redirect['name'], article['name'], dump_id)
                    cursor.execute(sql_add_article_redirect, data_article_redirect)

            try:
                caption = article_parsed.text[0]
            except IndexError:
                caption = None
            data_article = (title, caption, dump_id)
            cursor.execute(sql_add_article, data_article)
            article_id = cursor.lastrowid

            wikipedia_decisions = defaultdict(list)
            for tag in article_parsed.data:
                if tag['tag'] == 'a' and 'rel' in tag['attrs'] and 'mw:WikiLink' in tag['attrs']['rel'] \
                        and 'title' in tag['attrs'] and ':' not in tag['attrs']['title']:  # filtrowanie tylko linków Wikipedii
                    if tag['start'][0] != tag['end'][0]:
                        print(f'{title}: multiline links not supported')
                        continue
                    line = tag['start'][0]
                    length = tag['end'][1] - tag['start'][1] + 1
                    link = {
                        'start': tag['start'][1],
                        'length': length,
                        'destination': tag['attrs']['title'],
                    }
                    link['label'] = article_parsed.text[line][link['start']:link['start'] + link['length']]
                    wikipedia_decisions[line].append(link)

            for line_nr, content in enumerate(article_parsed.text):
                if len(content) > line_content_maximum_length:
                    print(
                        f"line {article['name']}({line_nr}): '{content[:50]}...' exceeds maximum length ({line_content_maximum_length})")
                    continue
                data_line = (article_id, line_nr, content)
                cursor.execute(sql_add_line, data_line)
                line_id = cursor.lastrowid
                if line_nr in wikipedia_decisions:
                    for link in wikipedia_decisions[line_nr]:
                        label = link['label']
                        if len(label) > label_maximum_length:
                            print(
                                f"label {label} in {article['name']}({line_nr}): '{label[:label_maximum_length]}...' "
                                f"exceeds length ({label_maximum_length})")
                            continue
                        destination = link['destination']
                        if len(destination) > title_maximum_length:
                            print(f"destination: '{destination[:title_maximum_length]}...' "
                                  f"exceeds maximum length ({title_maximum_length})")
                            continue

                        data_ground_truth_decision = (
                            article_id, line_id, link['start'], link['length'], label, destination, ground_truth_id)
                        cursor.execute(sql_add_ground_truth_decisions, data_ground_truth_decision)
            db.commit()  # commit after each article

        # main article processing loop
        articles_processed = 0
        stop_processing = False
        total_articles = sum(metadata['articles_counter'].values())
        with tqdm(total=total_articles) as pbar:
            for filename in dump_filenames:
                filepath = os.path.join(dump_path, filename)
                with open(filepath) as fp:
                    for line in fp:
                        article = json.loads(line)
                        process_article(article)
                        pbar.update(1)
                        articles_processed += 1
                        if early_stopping != -1 and articles_processed >= early_stopping:
                            stop_processing = True
                            break
                if stop_processing:
                    break

    def step_2():
        print('step 2. saving labels...', end=' ')
        start = time.time_ns()
        sql_create_labels = '''INSERT INTO `labels` (`label`, `dump_id`, `counter`)
                                SELECT `label`, `ground_truth_id`, COUNT(*) FROM `ground_truth_decisions` WHERE `ground_truth_id`=%s GROUP BY `label`'''
        cursor.execute(sql_create_labels, (ground_truth_id,))
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    def step_3():
        print('step 3. updating ground_truth_decisions destination_ids...', end=' ')
        start = time.time_ns()
        sql_update_ground_truth_decisions= '''
        UPDATE `ground_truth_decisions` INNER JOIN `articles` ON `ground_truth_decisions`.`destination_title`=`articles`.`title`
            SET `ground_truth_decisions`.`destination_article_id` = `articles`.`id`
            WHERE `ground_truth_decisions`.`ground_truth_id`=%s AND `articles`.`dump_id`=%s'''
        cursor.execute(sql_update_ground_truth_decisions, (ground_truth_id, dump_id))
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    def step_4():
        print('step 4. updating ground_truth_decisions label_ids...', end=' ')
        start = time.time_ns()
        sql_update_ground_truth_decisions = '''
            UPDATE `ground_truth_decisions` INNER JOIN `labels` ON `ground_truth_decisions`.`label`=`labels`.`label`
                SET `ground_truth_decisions`.`label_id` = `labels`.`id`
                WHERE `ground_truth_decisions`.`ground_truth_id`=%s AND `labels`.`dump_id`=%s'''
        cursor.execute(sql_update_ground_truth_decisions, (ground_truth_id, dump_id))
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    def step_5():
        print('step 5. updating articles redirects...', end=' ')
        start = time.time_ns()
        sql_update_article_redirect = '''
        UPDATE `articles` `a1` INNER JOIN `articles` `a2` ON `a1`.`redirect_to_title`=`a2`.`title`
            SET `a1`.`caption`=`a2`.`caption`, `a1`.`redirect_to_id`=`a2`.`id`
            WHERE `a1`.`dump_id`=%s AND `a2`.`dump_id`=%s'''
        data_article_redirect = (dump_id, dump_id)
        cursor.execute(sql_update_article_redirect, data_article_redirect)
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    def step_6():
        print('step 6. updating articles counters...', end=' ')
        start = time.time_ns()
        sql_update_article_counter = '''UPDATE `articles` INNER JOIN
                                            (SELECT `destination_title`, COUNT(*) AS `counter` FROM `ground_truth_decisions`
                                                WHERE `ground_truth_id`=%s GROUP BY `destination_title`) `wd1`
                                            ON `articles`.`title`=`wd1`.`destination_title`
                                            SET `articles`.`counter`=`wd1`.`counter`
                                            WHERE `articles`.`dump_id`=%s'''
        cursor.execute(sql_update_article_counter, (ground_truth_id, dump_id))
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    def step_7():
        print('step 7. saving labels_articles...', end=' ')
        start = time.time_ns()
        sql_create_labels_articles = '''INSERT INTO `labels_articles` (`label_id`, `title`, `article_id`, `counter`)
                                SELECT `wd`.`label_id`, `wd`.`destination_title`, `wd`.`destination_article_id`, COUNT(*)
                                    FROM `ground_truth_decisions` `wd`
                                    WHERE `wd`.`ground_truth_id`=%s
                                    GROUP BY `wd`.`label_id`, `wd`.`destination_title`, `wd`.`destination_article_id`'''
        cursor.execute(sql_create_labels_articles, (ground_truth_id,))
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    def step_8():
        print('step 8. save articles count...', end=' ')
        start = time.time_ns()
        sql_update_articles_count = '''UPDATE `dumps` SET `articles_count`=
                                (SELECT COUNT(*) FROM articles WHERE `dump_id`=%s AND `redirect_to_title` IS NULL)
                                                WHERE `id`=%s'''
        cursor.execute(sql_update_articles_count, (dump_id, dump_id))
        db.commit()
        elapsed = (time.time_ns() - start) / 1e9
        print(f'{elapsed:.2f} s')

    # apply selected steps
    for step in range(start_step, 9):
        locals()[f'step_{step}']()

    cursor.close()


def init_app(app):
    app.cli.add_command(import_enterprise_dump_command)
