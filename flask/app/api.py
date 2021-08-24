import functools
import json

from flask import (
    Blueprint, jsonify, request, abort, url_for, redirect
)

from app.db import get_db
from app.labels import get_labels_exact

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/article', methods=('GET',))
def search_article():
    db = get_db()

    if 'title' not in request.args:
        abort(404)

    cursor = db.cursor(dictionary=True)
    sql = 'SELECT `id` FROM `articles` WHERE `title`=%s'
    data = (request.args['title'],)
    cursor.execute(sql, data)
    article = cursor.fetchone()
    cursor.close()

    if article is None:
        abort(404)

    return redirect(url_for('api.get_article', id=article['id']))


def get_lines(article_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = "SELECT `content` FROM `lines` WHERE `article_id`=%s ORDER BY `nr`"
    data = (article_id,)
    cursor.execute(sql, data)
    lines = cursor.fetchall()
    cursor.close()

    lines = list(map(lambda line: line['content'].decode('utf-8').split(), lines))
    return lines


@bp.route('/article/<int:id>', methods=('GET',))
def get_article(id):
    db = get_db()

    cursor = db.cursor(dictionary=True)
    sql = '''SELECT `articles`.`id`, `articles`.`title`, `dumps`.`parser`, `dumps`.`name`
                FROM `articles` JOIN `dumps` ON `articles`.`dump_id` = `dumps`.`id`
                WHERE `articles`.`id`=%s'''
    data = (id,)
    cursor.execute(sql, data)
    article = cursor.fetchone()
    cursor.close()

    if article is None:
        abort(404)

    article['lines'] = get_lines(id)

    return jsonify(article)


@bp.route('/candidateLabels/<int:article_id>', methods=('GET',))
def get_candidate_labels(article_id):
    if 'algorithm' not in request.args:
        abort(400, "algorithm not given")

    params = json.loads(request.args['algorithm'])
    lines = get_lines(article_id)

    if params['algorithm'] == 'exact':
        labels = get_labels_exact(lines, params)
    else:
        abort(400, "unknown algorithm")

    return jsonify(labels)