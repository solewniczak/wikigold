import os

from flask import Flask, request


def create_app():
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', default='dev'),
        MYSQL_HOST=os.getenv('MYSQL_HOST'),
        MYSQL_USER=os.getenv('MYSQL_USER'),
        MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD'),
        MYSQL_DATABASE=os.getenv('MYSQL_DATABASE'),
        BASEURL=os.getenv('BASEURL'),
        MAX_NGRAMS=os.getenv('MAX_NGRAMS', default='5')
    )

    # config types mapping
    app.config['MAX_NGRAMS'] = int(app.config['MAX_NGRAMS'])

    from app import db
    db.init_app(app)

    from app import dump
    dump.init_app(app)

    from app import auth
    app.register_blueprint(auth.bp)

    from . import admin
    app.register_blueprint(admin.bp)

    from . import wikigold
    app.register_blueprint(wikigold.bp)
    app.add_url_rule('/', endpoint='index')

    from . import api
    app.register_blueprint(api.bp)

    return app
