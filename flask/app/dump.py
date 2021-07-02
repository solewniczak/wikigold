import os.path

import click
from flask import current_app, g
from flask.cli import with_appcontext

from app.db import get_db


@click.command('import-dump')
@click.argument('filepath', type=click.Path(exists=True))
@with_appcontext
def import_dump_command(filepath):
    db = get_db()
    with db.cursor() as cursor:
        filename = os.path.basename(filepath)
        add_dump = "INSERT INTO dumps (name) VALUES (%s)"
        data_dump = (filename, )
        cursor.execute(add_dump, data_dump)
        db.commit()


def init_app(app):
    app.cli.add_command(import_dump_command)