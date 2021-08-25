import functools
import json

from flask import (
    Blueprint, g, jsonify, request, abort, url_for, redirect
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
    sql = "SELECT `id`, `content` FROM `lines` WHERE `article_id`=%s ORDER BY `nr`"
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


def normalize_algorithm_json(algorithm):
    algorithm_parsed = json.loads(algorithm)

    if algorithm_parsed['algorithm'] == 'exact':
        if 'skipstopwords' not in algorithm_parsed:
            algorithm_parsed['skipstopwords'] = False
        else:
            algorithm_parsed['skipstopwords'] = bool(int(algorithm_parsed['skipstopwords']))

    return json.dumps(algorithm_parsed, sort_keys=True), algorithm_parsed


@bp.route('/candidateLabels/<int:article_id>', methods=('GET',))
def get_candidate_labels(article_id):
    if 'algorithm' not in request.args:
        abort(400, "algorithm not given")

    _, algorithm_normalized_json = normalize_algorithm_json(request.args['algorithm'])
    lines = get_lines(article_id)

    if algorithm_normalized_json['algorithm'] == 'exact':
        labels = get_labels_exact(lines, algorithm_normalized_json)
    else:
        abort(400, "unknown algorithm")

    return jsonify(labels)


@bp.route('/decision', methods=('POST',))
def post_decision():
    db = get_db()

    algorithm_key, _ = normalize_algorithm_json(request.form['algorithm'])
    author = g.username
    article_id = request.form['source_article_id']
    source_line_nr = request.form['source_line_nr']
    start = request.form['start']
    length = request.form['length']
    decision_article_id = request.form['decision_article_id']

    cursor = db.cursor(dictionary=True)

    # check if EDL exists
    sql_select_edl = "SELECT `id` FROM `edls` WHERE `algorithm`=%s AND `author`=%s AND `article_id`=%s"
    data_edl = (algorithm_key, author, article_id)
    cursor.execute(sql_select_edl, data_edl)
    edl = cursor.fetchone()

    if edl is None:
        # create new EDL
        sql_insert_edl = "INSERT INTO `edls` (algorithm, author, article_id) VALUES (%s, %s, %s)"
        cursor.execute(sql_insert_edl, data_edl)
        edl_id = cursor.lastrowid
    else:
        edl_id = edl['id']

    # get decision's source_line_id
    sql_select_line = "SELECT `id` FROM `lines` WHERE `nr`=%s AND `article_id`=%s"
    data_edl = (source_line_nr, article_id)
    cursor.execute(sql_select_line, data_edl)
    line = cursor.fetchone()
    source_line_id = line['id']

    # check if decision already exists
    sql_select_decision = "SELECT `id` FROM `decisions`" \
                          "WHERE `edl_id`=%s AND `source_line_id`=%s AND `start`=%s AND `length`=%s"
    data_decision = (edl_id, source_line_id, start, length)
    cursor.execute(sql_select_decision, data_decision)
    decision = cursor.fetchone()

    if decision is None:
        sql_insert_decision = "INSERT INTO `decisions`" \
                              "(`edl_id`, `source_line_id`, `start`, `length`, `destination_article_id`)" \
                              "VALUES (%s, %s, %s, %s, %s)"
        data_decision += (decision_article_id,)
        cursor.execute(sql_insert_decision, data_decision)
    else:
        decision_id = cursor.lastrowid
        sql_update_decision = "UPDATE `decisions` SET `destination_article_id`=%s WHERE `id`=%s"
        data_decision = (decision_article_id, decision_id)
        cursor.execute(sql_update_decision, data_decision)

    db.commit()
    cursor.close()

    return jsonify({'edl_id': edl_id})
