from datetime import datetime
import json

import humanize
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from app.auth import login_required
from app.db import get_db

bp = Blueprint('wikigold', __name__)


@bp.route('/')
@login_required
def index():
    algorithm = {'algorithm': ''}
    if 'algorithm' in request.args:
        algorithm = json.loads(request.args['algorithm'])
    return render_template('wikigold/index.html', algorithm=algorithm)


@bp.route('/edls')
@login_required
def edls():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql_select_edls = '''SELECT `edls`.`id`, `edls`.`algorithm`, `edls`.`timestamp`, `edls`.`article_id`,
                            `articles`.`title`, `articles`.`caption`,
                            `dumps`.`lang`, `dumps`.`date`, `dumps`.`parser_name`, `dumps`.`parser_version`
                            FROM `edls` JOIN articles ON `edls`.`article_id` = `articles`.`id`
                            JOIN dumps ON `articles`.`dump_id` = `dumps`.`id`
                            WHERE `edls`.`user_id`=%s
                            ORDER BY timestamp DESC'''
    data_edls = (g.user['id'], )
    cursor.execute(sql_select_edls, data_edls)
    my_edls = cursor.fetchall()
    my_edls_decoded = []
    for row in my_edls:
        row['algorithm'] = row['algorithm'].decode('utf-8')
        row['caption'] = row['caption'].decode('utf-8')
        row['timedelta'] = humanize.naturaldelta(datetime.now() - row['timestamp'])

        my_edls_decoded.append(row)

    cursor.close()

    return render_template('wikigold/edls.html', my_edls=my_edls_decoded)