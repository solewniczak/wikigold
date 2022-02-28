from mysql.connector.errors import IntegrityError
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, jsonify
)
from werkzeug.security import generate_password_hash

from .auth import superuser
from .db import get_db

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/users')
@superuser
def users():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = 'SELECT id, username FROM users'
    cursor.execute(sql)
    users = cursor.fetchall()

    cursor.close()

    return render_template('admin/users.html', users=users)


def get_user(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    sql = 'SELECT id, username, superuser FROM users WHERE id=%s'
    cursor.execute(sql, (id, ))
    user = cursor.fetchone()

    cursor.close()
    return user


@bp.route('/user/<int:id>/delete', methods=('POST', ))
@superuser
def user_delete(id):
    user = get_user(id)
    if user['superuser']:
        flash('Cannot delete superuser.', 'danger')
    else:
        try:
            db = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute('DELETE FROM `users` WHERE `id`=%s', (id,))
            db.commit()
        except IntegrityError:
            flash('Cannot delete user with edls.', 'danger')
        else:
            flash('The user has been deleted.', 'success')
        finally:
            cursor.close()

    return redirect(url_for('admin.users'))


@bp.route('/user/<int:id>/update', methods=('POST', ))
@superuser
def user_update(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    password = request.form['password']

    if password == '':
        flash('Password cannot be empty.', 'danger')
    else:
        sql = "UPDATE `users` SET `password`=%s WHERE `id`=%s"
        data = (generate_password_hash(password), id)
        cursor.execute(sql, data)
        db.commit()
        cursor.close()
        flash('Password has been updated.', 'success')
    return redirect(url_for('admin.users'))
