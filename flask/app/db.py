import mysql.connector

import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash


def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DATABASE'],
        )

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    # create database if not exists
    mysql_connection = mysql.connector.connect(
        host=current_app.config['MYSQL_HOST'],
        user=current_app.config['MYSQL_USER'],
        password=current_app.config['MYSQL_PASSWORD']
    )
    cursor = mysql_connection.cursor()
    sql = f"CREATE DATABASE IF NOT EXISTS {current_app.config['MYSQL_DATABASE']} CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"
    cursor.execute(sql)
    cursor.close()
    mysql_connection.close()

    # connect to database
    db = get_db()

    cursor = db.cursor()
    with current_app.open_resource('schema.sql') as f:
        tables = f.read().decode('utf8').split(';')

    for table in tables:
        if table.strip() != '':
            cursor.execute(table)

    # create application superuser
    sql_add_user = "INSERT INTO `users` (`username`, `password`, `superuser`) VALUES (%s, %s, TRUE)"
    data_user = ('admin', generate_password_hash('admin'))
    cursor.execute(sql_add_user, data_user)
    db.commit()

    cursor.close()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('database initialized')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
