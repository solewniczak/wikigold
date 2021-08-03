import functools

from flask import (
    Blueprint, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        session.clear()
        session['username'] = username
        return redirect(url_for('index'))

    return render_template('auth/login.html')


@bp.before_app_request
def load_logged_in_user():
    username = session.get('username')
    g.username = username


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.username is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
