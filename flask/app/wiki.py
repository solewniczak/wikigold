from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from app.auth import login_required
from app.db import get_db

bp = Blueprint('wiki', __name__)


@bp.route('/')
@login_required
def index():
    return render_template('wiki/index.html')