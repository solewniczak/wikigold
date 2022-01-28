from datetime import datetime


from flask import (
    Blueprint, g, jsonify, request, abort, url_for, redirect
)

from .db import get_db
from .disambiguation import commonness
from .helper import get_lines, normalize_algorithm_json, get_user_decisions, get_wikipedia_decisions
from .labels import get_labels_exact
from .mediawikixml import normalize_title

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/article', methods=('GET',))
def search_article():
    db = get_db()

    if 'title' not in request.args:
        abort(400, "title parameter required")

    cursor = db.cursor(dictionary=True)

    dump_id = int(request.args['article_source'])

    sql = 'SELECT `id` FROM `articles` WHERE `title`=%s AND `dump_id`=%s'
    title = normalize_title(request.args['title'])
    data = (title, dump_id)
    cursor.execute(sql, data)
    article = cursor.fetchone()
    cursor.close()

    if article is None:
        abort(404)

    return redirect(url_for('api.get_article', id=article['id']))


@bp.route('/article/<int:id>', methods=('GET',))
def get_article(id):
    db = get_db()

    cursor = db.cursor(dictionary=True)
    sql = '''SELECT `articles`.`id`, `articles`.`title`, `dumps`.`parser_name`, `dumps`.`parser_version`, `dumps`.`lang`, `dumps`.`date`
                FROM `articles` JOIN `dumps` ON `articles`.`dump_id` = `dumps`.`id`
                WHERE `articles`.`id`=%s'''
    data = (id,)
    cursor.execute(sql, data)
    article = cursor.fetchone()
    cursor.close()

    if article is None:
        abort(404)

    article['lines'] = get_lines(id)
    article['wikipedia_decisions'] = get_wikipedia_decisions(id)

    return jsonify(article)


@bp.route('/candidateLabels/<int:article_id>', methods=('GET',))
def get_candidate_labels(article_id):
    if 'algorithm' not in request.args:
        abort(400, "retrieval algorithm not given")

    algorithm_normalized_json_key, algorithm_normalized_json = normalize_algorithm_json(request.args['algorithm'])
    lines = get_lines(article_id, algorithm_normalized_json['paragraphs_limit'])

    if algorithm_normalized_json['retrieval'] == 'exact':
        labels = get_labels_exact(lines, knowledge_base=algorithm_normalized_json['knowledge_base'],
                                  skip_stop_words=algorithm_normalized_json['skip_stop_words'],
                                  min_label_count=algorithm_normalized_json['min_label_count'],
                                  min_label_articles_count=algorithm_normalized_json['min_label_articles_count'])
    else:
        abort(400, "unknown retrieval algorithm")

    if algorithm_normalized_json['disambiguation'] == 'commonness':
        commonness(labels)

    # apply saved decisions
    decisions_dict = get_user_decisions(article_id, algorithm_normalized_json_key)
    for label in labels:
        if (label['line'], label['start'], label['ngrams']) in decisions_dict:
            label['decision'] = decisions_dict[(label['line'], label['start'], label['ngrams'])]

    return jsonify({'edl': labels, 'algorithm_key': algorithm_normalized_json_key})


@bp.route('/decision', methods=('POST',))
def post_decision():
    db = get_db()

    content = request.get_json()

    algorithm_normalized_json_key, algorithm_normalized_json = normalize_algorithm_json(content['algorithm'])
    user_id = g.user['id']
    article_id = int(content['source_article_id'])
    knowledge_base_id = algorithm_normalized_json['knowledge_base']
    source_line_nr = int(content['source_line_nr'])
    start = int(content['start'])
    length = int(content['length'])
    destination_article_id = content['destination_article_id']
    if destination_article_id is not None:
        destination_article_id = int(destination_article_id)

    cursor = db.cursor(dictionary=True)

    # check if EDL exists
    sql_select_edl = "SELECT `id` FROM `edls` WHERE `algorithm`=%s AND `user_id`=%s AND `article_id`=%s AND `knowledge_base_id`=%s"
    data_edl = (algorithm_normalized_json_key, user_id, article_id, knowledge_base_id)
    cursor.execute(sql_select_edl, data_edl)
    edl = cursor.fetchone()

    if edl is None:
        # create new EDL
        sql_insert_edl = "INSERT INTO `edls` (algorithm, user_id, article_id, `knowledge_base_id`, `timestamp`) VALUES (%s, %s, %s, %s, %s)"
        data_edl += (datetime.now().isoformat(), )
        cursor.execute(sql_insert_edl, data_edl)
        edl_id = cursor.lastrowid
    else:
        edl_id = edl['id']
        sql_update_edl = "UPDATE `edls` SET `timestamp`=%s WHERE `id`=%s"
        data_edl = (datetime.now().isoformat(), edl_id)
        cursor.execute(sql_update_edl, data_edl)

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
        if destination_article_id != -1:
            sql_insert_decision = "INSERT INTO `decisions`" \
                                  "(`edl_id`, `source_line_id`, `start`, `length`, `destination_article_id`)" \
                                  "VALUES (%s, %s, %s, %s, %s)"
            data_decision += (destination_article_id,)
            cursor.execute(sql_insert_decision, data_decision)
    elif destination_article_id == -1:
        decision_id = decision['id']
        sql_delete_decision = "DELETE FROM `decisions` WHERE id=%s"
        data_decision = (decision_id,)
        cursor.execute(sql_delete_decision, data_decision)
    else:
        decision_id = decision['id']
        sql_update_decision = "UPDATE `decisions` SET `destination_article_id`=%s WHERE `id`=%s"
        data_decision = (destination_article_id, decision_id)
        cursor.execute(sql_update_decision, data_decision)

    db.commit()
    cursor.close()

    return jsonify({'edl_id': edl_id})
