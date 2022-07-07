import click
from flask.cli import with_appcontext


@click.command('load-dataset')
@click.argument('name')
@click.argument('path')
@with_appcontext
def load_dataset(name, path):
    from datetime import datetime
    from flask import current_app
    from .db import get_db

    if name not in globals():
        raise NameError('unknown loader')
    dataset_iterator = globals()[name]

    db = get_db()
    cursor = db.cursor()

    sql = "INSERT INTO dumps (`lang`, `name`, `timestamp`) VALUES (%s, %s, %s)"
    data = ('en', name, datetime.now().isoformat())
    cursor.execute(sql, data)
    dump_id = cursor.lastrowid

    knowledge_base_id = current_app.config['KNOWLEDGE_BASE']

    sql = "INSERT INTO ground_truth (`description`, `dump_id`, `knowledge_base_id`) VALUES (%s, %s, %s)"
    data = (dataset_iterator.__doc__, dump_id, knowledge_base_id)
    cursor.execute(sql, data)
    ground_truth_id = cursor.lastrowid

    for title, caption, metadata, lines, decisions in dataset_iterator(path):
        sql = "INSERT INTO `articles` (`title`, `caption`, `dump_id`) VALUES (%s, %s, %s)"
        data = (title, caption, dump_id)
        cursor.execute(sql, data)
        article_id = cursor.lastrowid

        for key, value in metadata.items():
            sql = "INSERT INTO `articles_metadata` (`article_id`, `key`, `value`) VALUES (%s, %s, %s)"
            data = (article_id, key, value)
            cursor.execute(sql, data)

        lines_nr_id = {}
        for nr, line in lines.items():
            sql = "INSERT INTO `lines` (`nr`, `content`, `article_id`) VALUES (%s, %s, %s)"
            data = (nr, line, article_id)
            cursor.execute(sql, data)
            lines_nr_id[nr] = cursor.lastrowid

        for link in decisions:
            sql = '''INSERT INTO `ground_truth_decisions`
            (`source_article_id`, `source_line_id`, `start`, `length`, `label`, `destination_title`, `ground_truth_id`)
            VALUES (%s, %s, %s, %s, %s, %s, %s)'''
            data = (article_id, lines_nr_id[link['line']], link['start'], link['length'], link['label'],
                    link['destination'], ground_truth_id)
            cursor.execute(sql, data)

    # update destination ids
    sql = '''UPDATE `ground_truth_decisions` INNER JOIN `articles` ON `ground_truth_decisions`.`destination_title`=`articles`.`title`
                SET `ground_truth_decisions`.`destination_article_id` = `articles`.`id`
                WHERE `ground_truth_decisions`.`ground_truth_id`=%s AND `articles`.`dump_id`=%s'''
    cursor.execute(sql, (ground_truth_id, knowledge_base_id))

    # update labels ids
    sql = '''UPDATE `ground_truth_decisions` INNER JOIN `labels` ON `ground_truth_decisions`.`label`=`labels`.`label`
                    SET `ground_truth_decisions`.`label_id` = `labels`.`id`
                    WHERE `ground_truth_decisions`.`ground_truth_id`=%s AND `labels`.`dump_id`=%s'''
    cursor.execute(sql, (ground_truth_id, knowledge_base_id))

    sql = 'UPDATE `dumps` SET `articles_count`=(SELECT COUNT(*) FROM articles WHERE `dump_id`=%s) WHERE `id`=%s'
    cursor.execute(sql, (dump_id, dump_id))

    # db.commit()


def aquaint(path):
    """http://community.nzdl.org/wikification/docs.html"""
    import glob
    import os.path
    from html.parser import HTMLParser

    class Tag:
        def __init__(self, name):
            self.name = name
            self.content = ''

        def append_content(self, content):
            self.content += content

    class AquaintHTMLParse(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tag_stack = []
            self.title = ''
            self.header = ''
            self.lines = []

        def handle_starttag(self, tag_name, attrs):
            tag = Tag(tag_name)
            self.tag_stack.append(tag)

        def handle_endtag(self, tag_name):
            tag = self.tag_stack.pop()
            if tag.name != tag_name:
                raise "parser error"
            content = tag.content.strip()
            if tag.name == 'title':
                self.title = content
            elif tag.name == 'h1':
                self.header = content
            elif tag.name == 'p':
                self.lines.append(content)

        def handle_data(self, data):
            if len(self.tag_stack):  # ignore content outside tags
                self.tag_stack[-1].append_content(data)

    def parse_links(raw_content):
        import re
        from .mediawikixml import normalize_title

        tokens = re.split(r'(\[\[.*?\]\])', raw_content)
        content = ''
        links = []
        for token in tokens:
            if len(token) == 0:
                pass
            elif token[0] == '[':  # link parsing
                link_content = token[2:-2]
                link_split = link_content.split('|')
                title = link_split[0]
                if len(link_split) == 1:
                    label = title
                else:
                    label = link_split[1]
                link_start = len(content)
                link_length = len(label)
                links.append({
                    'start': link_start,
                    'length': link_length,
                    'label': label,
                    'destination': normalize_title(title)
                })
                content += label
            else:
                content += token
        return content, links

    for file in glob.glob(os.path.join(path, '*.htm')):
        with open(file) as fp:
            content = fp.read()
            parser = AquaintHTMLParse()
            parser.feed(content)
            content_lines = parser.lines
            content_lines.insert(0, parser.header)  # add header as a first line to content since it also contains links
            metadata = {}
            lines = {}
            decisions = []
            for nr, line in enumerate(parser.lines):
                raw_content, line_links = parse_links(line)
                lines[nr] = raw_content
                for link in line_links:
                    decisions.append({
                        'line': nr,
                        'start': link['start'],
                        'length': link['length'],
                        'label': link['label'],
                        'destination': link['destination']
                    })
            yield parser.title, lines[0], metadata, lines, decisions


def init_app(app):
    app.cli.add_command(load_dataset)
