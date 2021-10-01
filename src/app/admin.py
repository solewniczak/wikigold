from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from app.auth import login_required, superuser
from app.db import get_db
from app.dbconfig import get_dbconfig, update_dbconfig

bp = Blueprint('admin', __name__)


@bp.route('/config', methods=('GET', 'POST'))
@login_required
@superuser
def config():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        update_dbconfig(request.form)
        flash('Config saved.', 'success')

    dbconfig = get_dbconfig()

    sql_select_dumps = "SELECT id, lang, date, parser_name, parser_version FROM dumps"
    cursor.execute(sql_select_dumps)
    all_dumps = cursor.fetchall()

    cursor.close()

    return render_template('admin/config.html', dbconfig=dbconfig, all_dumps=all_dumps)