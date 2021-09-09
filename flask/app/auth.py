import functools
import mysql.connector

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash

from app.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            try:
                sql_add_user = "INSERT INTO `users` (`username`, `password`, `superuser`) VALUES (%s, %s, FALSE)"
                data_user = (username, generate_password_hash(password))
                cursor.execute(sql_add_user, data_user)
                db.commit()
            except mysql.connector.IntegrityError:
                error = f'User {username} is already registered.'
            else:
                info = 'User registered.'
                flash(info, 'info')
                return redirect(url_for("auth.login"))

        flash(error, 'danger')

    return render_template('auth/register.html')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)

        sql_select_user = 'SELECT `id`, `password` FROM `users` WHERE `username`=%s'
        data_user = (username,)
        cursor.execute(sql_select_user, data_user)
        user = cursor.fetchone()

        error = None
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error, 'danger')

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        sql_select_user = 'SELECT `id`, `username`, `superuser` FROM `users` WHERE `id`=%s'
        data_user = (user_id,)
        cursor.execute(sql_select_user, data_user)
        g.user = cursor.fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
