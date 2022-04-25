from datetime import datetime

import humanize
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, abort
)

from .auth import login_required
from .db import get_db
from .helper import normalize_algorithm_json, absolute_url_for

bp = Blueprint('wikigold', __name__)


@bp.route('/')
@login_required
def index():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql_select_dumps = "SELECT id, lang, name, parser_name, parser_version, timestamp FROM dumps ORDER BY id DESC"
    cursor.execute(sql_select_dumps)
    dumps = cursor.fetchall()
    cursor.close()

    try:
        algorithm = request.args['algorithm']
    except KeyError:
        algorithm = '{}'

    algorithm_key, algorithm_parsed = normalize_algorithm_json(algorithm)
    return render_template('wikigold/index.html', algorithm=algorithm_parsed, dumps=dumps)


@bp.route('/edls')
@bp.route('/edls/<int:another_user_id>')
@login_required
def edls(another_user_id=None):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if not g.user['superuser'] and another_user_id is not None \
        or g.user['superuser'] and another_user_id == g.user['id']:
        return redirect(absolute_url_for('wikigold.edls'))

    sql_select_edls = '''SELECT `edls`.`id`, `edls`.`algorithm`, `edls`.`timestamp`, `edls`.`article_id`,
                            `articles`.`title`, `articles`.`caption`,
                            `dumps`.`name`, `dumps`.`parser_name`, `dumps`.`parser_version`
                            FROM `edls` JOIN articles ON `edls`.`article_id` = `articles`.`id`
                            JOIN dumps ON `articles`.`dump_id` = `dumps`.`id`
                            WHERE `edls`.`user_id`=%s AND `edls`.`knowledge_base_id`=%s
                            ORDER BY `edls`.`timestamp` DESC'''
    data_edls = (g.user['id'] if another_user_id is None else another_user_id, current_app.config['KNOWLEDGE_BASE'])
    cursor.execute(sql_select_edls, data_edls)
    edls = cursor.fetchall()
    edls_decoded = []
    for row in edls:
        row['algorithm'] = row['algorithm'].decode('utf-8')
        row['caption'] = row['caption'].decode('utf-8')
        row['timedelta'] = humanize.naturaldelta(datetime.now() - row['timestamp'])
        edls_decoded.append(row)

    another_username = None
    if another_user_id is not None:
        cursor.execute('SELECT username FROM users WHERE id=%s', (another_user_id, ))
        another_username = cursor.fetchone()['username']
    cursor.close()
    return render_template('wikigold/edls.html', edls=edls_decoded, another_user_id=another_user_id, another_username=another_username)


def get_edl(id, check_user=True):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = 'SELECT `id`, `algorithm`, `timestamp`, `user_id`, `article_id`, `knowledge_base_id` FROM `edls`' \
          'WHERE `knowledge_base_id`=%s AND `id`=%s'
    cursor.execute(sql, (current_app.config['KNOWLEDGE_BASE'], id))
    edl = cursor.fetchone()
    cursor.close()

    if edl is None:
        abort(404, f"edl {id} doesn't exist")

    if check_user and edl['user_id'] != g.user['id']:
        abort(403)

    return edl


@bp.route('/edl/<int:id>/delete', methods=('POST', ))
@login_required
def edl_delete(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    get_edl(id)  # check permissions
    cursor.execute('DELETE FROM `decisions` WHERE `edl_id`=%s', (id, ))
    cursor.execute('DELETE FROM `edls` WHERE `id`=%s', (id,))

    db.commit()
    cursor.close()

    flash('The edl has been deleted.', 'success')
    return redirect(absolute_url_for('wikigold.edls'))
