import os

from flask import Flask


class PrefixMiddleware(object):

    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]


def create_app():
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', default='dev'),
        MYSQL_HOST=os.getenv('MYSQL_HOST'),
        MYSQL_USER=os.getenv('MYSQL_USER'),
        MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD'),
        MYSQL_DATABASE=os.getenv('MYSQL_DATABASE'),
        PREFIX=os.getenv('PREFIX', default=''),
        MAX_NGRAMS=os.getenv('MAX_NGRAMS', default='5')
    )
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=app.config['PREFIX'])

    # config types mapping
    app.config['MAX_NGRAMS'] = int(app.config['MAX_NGRAMS'])
    # app.config['APPLICATION_ROOT'] = '/wikigold'

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