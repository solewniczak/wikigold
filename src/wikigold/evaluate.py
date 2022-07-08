import click
from flask.cli import with_appcontext

import yaml


@click.command('evaluate')
@click.argument('evaluate_config_path')
@with_appcontext
def evaluate(evaluate_config_path):
    with open(evaluate_config_path, 'r') as fp:
        print(yaml.safe_load(fp))


def init_app(app):
    app.cli.add_command(evaluate)
