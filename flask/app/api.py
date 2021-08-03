import functools

from flask import (
    Blueprint, jsonify, request, g, redirect, render_template, request, session, url_for
)

from app.db import get_db

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/article', methods=('GET', ))
def article():
    db = get_db()

    cursor = db.cursor()
    sql = 'SELECT `id` FROM `articles` WHERE `title`=%s'
    data = (request.args['title'], )
    cursor.execute(sql, data)
    article = cursor.fetchone()

    return jsonify(article)