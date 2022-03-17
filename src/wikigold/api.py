import json
from datetime import datetime


from flask import (
    Blueprint, g, jsonify, request, abort, redirect, current_app, make_response
)

from .db import get_db
from .disambiguation import rate_by_commonness, rate_by_topic_proximity, apply_links_to_text_ratio
from .helper import get_lines, normalize_algorithm_json, get_user_decisions, get_wikipedia_decisions, absolute_url_for
from .labels import get_labels_exact
from .mediawikixml import normalize_title

bp = Blueprint('api', __name__, url_prefix='/api')


def search_article_by_title(title, dump_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = 'SELECT `id` FROM `articles` WHERE `title`=%s AND `dump_id`=%s'
    data = (title, dump_id)
    cursor.execute(sql, data)
    article = cursor.fetchone()
    if article is None:  # try with normalized title
        data = (normalize_title(title), dump_id)
        cursor.execute(sql, data)
        article = cursor.fetchone()
    if article is None:  # normalized title doesn't work
        response = make_response(jsonify({'title': 'article not found'}), 404)
        abort(response)
    cursor.close()
    return redirect(absolute_url_for('api.get_article', id=article['id']))


def search_article_by_metadata(query, dump_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = 'SELECT am0.article_id FROM articles_metadata am0 JOIN articles ON am0.article_id=articles.id '
    for i in range(1, len(query)):
        sql += f'JOIN articles_metadata am{i} ON am0.article_id=am{i}.article_id '
    data = [dump_id]
    where = ['articles.dump_id=%s']
    for i, (key, value) in enumerate(query.items()):
        where.extend([f'am{i}.key=%s', f'am{i}.value=%s'])
        data.extend([key, value])
    sql += 'WHERE ' + ' AND '.join(where)
    cursor.execute(sql, data)
    articles = cursor.fetchall()
    if len(articles) > 1:
        response = make_response(jsonify({'metadata': 'metadata query ambiguous'}), 400)
        abort(response)
    elif len(articles) == 0:
        response = make_response(jsonify({'metadata': 'article not found'}), 404)
        abort(response)
    cursor.close()
    return redirect(absolute_url_for('api.get_article', id=articles[0]['article_id']))


@bp.route('/article', methods=('GET',))
def search_article():
    if 'article_source' not in request.args:
        abort(400, 'article_source parameter required')
    dump_id = int(request.args['article_source'])

    if 'title' in request.args:
        return search_article_by_title(request.args['title'], dump_id)
    elif 'metadata' in request.args:
        try:
            query = json.loads(request.args['metadata'])
            if len(query) == 0:
                response = make_response(jsonify({'metadata': 'metadata query can\'t be empty'}), 400)
                abort(response)
            return search_article_by_metadata(query, dump_id)
        except json.decoder.JSONDecodeError as e:
            response = make_response(jsonify({'metadata': 'JSON parsing error: ' + e.msg}), 400)
            abort(response)
    else:
        abort(400, 'title or metadata parameter required')


@bp.route('/article/<int:id>', methods=('GET',))
def get_article(id):
    db = get_db()

    cursor = db.cursor(dictionary=True)
    sql = 'SELECT `id`, `title`, `dump_id` FROM `articles` WHERE `articles`.`id`=%s'
    data = (id,)
    cursor.execute(sql, data)
    article = cursor.fetchone()

    # get article metadata
    sql = 'SELECT `key`, `value` FROM `articles_metadata` WHERE `article_id`=%s'
    data = (id,)
    cursor.execute(sql, data)
    metadata = {row['key']: row['value'].decode('utf-8') for row in cursor}
    cursor.close()

    if article is None:
        abort(404)

    article['metadata'] = json.dumps(metadata)
    article['lines'] = get_lines(id)
    article['wikipedia_decisions'] = get_wikipedia_decisions(id)

    return jsonify(article)


@bp.route('/articles', methods=('GET',))
def get_articles():
    if 'ids' not in request.args:
        abort(400, "article ids not given")

    articles_ids = json.loads(request.args['ids'])

    db = get_db()
    cursor = db.cursor(dictionary=True)
    article_ids_str = ','.join(map(str, articles_ids))
    sql = f'SELECT `id`, `title`, `caption` FROM `articles` WHERE `id` IN ({article_ids_str})'
    cursor.execute(sql)
    articles_dict = {}
    for row in cursor:
        article = {
            'title': row['title'],
            'caption': row['caption']
        }
        if article['caption'] is not None:
            article['caption'] = article['caption'].decode('utf-8')
        articles_dict[row['id']] = article

    return jsonify(articles_dict)


@bp.route('/candidateLabels/<int:article_id>', methods=('GET',))
def get_candidate_labels(article_id):
    if 'algorithm' not in request.args:
        abort(400, "retrieval algorithm not given")

    algorithm_normalized_json_key, algorithm_normalized_json = normalize_algorithm_json(request.args['algorithm'])
    lines = get_lines(article_id, algorithm_normalized_json['paragraphs_limit'])

    tokens_limit = current_app.config['TOKENS_LIMIT']
    if tokens_limit > 0:  # 0 means no limit
        tokens_count = sum([len(line['tokens']) for line in lines])
        if tokens_count >= tokens_limit:
            response = make_response(jsonify({'paragraphs_limit': f'tokens limit ({tokens_limit}) exceeded'}), 400)
            abort(response)

    if algorithm_normalized_json['retrieval'] == 'exact':
        labels = get_labels_exact(lines, skip_stop_words=algorithm_normalized_json['skip_stop_words'],
                                  min_label_count=algorithm_normalized_json['min_label_count'],
                                  min_label_articles_count=algorithm_normalized_json['min_label_articles_count'],
                                  min_link_probability=algorithm_normalized_json['min_link_probability'])
    else:
        response = make_response(jsonify({'retrieval': 'unknown retrieval algorithm'}), 400)
        abort(response)

    if algorithm_normalized_json['disambiguation'] == 'commonness':
        rate_by_commonness(labels)
    elif algorithm_normalized_json['disambiguation'] == 'topic_proximity':
        rate_by_topic_proximity(labels, algorithm_normalized_json['max_context_terms'])

    if algorithm_normalized_json['disambiguation'] != '':
        apply_links_to_text_ratio(labels, lines, algorithm_normalized_json['links_to_text_ratio'])

    for label in labels:
        if 'disambiguation' in label and 'article_id' in label['disambiguation']:
            label['decision'] = label['disambiguation']['article_id']

    # apply saved decisions
    user_decisions_dict = get_user_decisions(article_id, algorithm_normalized_json_key)
    for label in labels:
        if (label['line'], label['start'], label['ngrams']) in user_decisions_dict:
            label['decision'] = user_decisions_dict[(label['line'], label['start'], label['ngrams'])]

    return jsonify({'edl': labels, 'algorithm_key': algorithm_normalized_json_key})


@bp.route('/decision', methods=('POST',))
def post_decision():
    db = get_db()

    content = request.get_json()

    algorithm_normalized_json_key, algorithm_normalized_json = normalize_algorithm_json(content['algorithm'])
    user_id = g.user['id']
    article_id = int(content['source_article_id'])
    knowledge_base_id = current_app.config['KNOWLEDGE_BASE']
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
