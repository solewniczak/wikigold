from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)

from .auth import superuser
from .cache import cached_labels, get_redis
from .db import get_db

bp = Blueprint('admin', __name__, url_prefix='/admin')
redis = Blueprint('redis', __name__, url_prefix='/redis')

@bp.route('/redis')
@superuser
def redis():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql_select_dumps = '''SELECT id, lang, date, parser_name, parser_version, timestamp, labels_count FROM dumps ORDER BY id DESC'''
    cursor.execute(sql_select_dumps)
    dumps = []
    for row in cursor:
        dump = row
        dump['cached_labels'] = cached_labels(dump['id'])
        dumps.append(dump)

    cursor.close()

    return render_template('admin/redis.html', dumps=dumps)


@bp.route('/redis/flushLabels/<int:dump_id>')
@superuser
def redis_flush_labels(dump_id):
    r = get_redis(dump_id)
    r.flushdb()
    return redirect(url_for('.redis'))


@bp.route('/redis/countCachedLabels/<int:dump_id>')
@superuser
def redis_count_cached_labels(dump_id):
    return jsonify({'cached_labels': cached_labels(dump_id)})


@bp.route('/redis/cacheLabels/<int:dump_id>')
@superuser
def redis_cache_labels(dump_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    r = get_redis(dump_id)

    sql = '''SELECT `id`, `label` FROM `labels` WHERE `labels`.`dump_id`=%s'''
    data = (dump_id,)
    cursor.execute(sql, data)
    counter = 0
    for row in cursor:
        key = row['label']
        value = row['id']
        r.set(key, value)
        counter += 1
    cursor.close()
    return jsonify({'cached_labels': counter})
