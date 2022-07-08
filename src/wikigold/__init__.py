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


# create and configure the app
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.getenv('SECRET_KEY', default='dev'),
    MYSQL_HOST=os.getenv('MYSQL_HOST', default='localhost'),
    MYSQL_PORT=os.getenv('MYSQL_PORT', default='3306'),
    MYSQL_USER=os.getenv('MYSQL_USER', default='root'),
    MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD', default=''),
    MYSQL_DATABASE=os.getenv('MYSQL_DATABASE', default='wikigold'),
    REDIS_URL = os.getenv('REDIS_URL', default='redis://localhost:6379'),
    BASE_URL=os.getenv('BASE_URL', default=''),
    PREFIX=os.getenv('PREFIX', default=''),
    KNOWLEDGE_BASE=os.getenv('KNOWLEDGE_BASE', default='1'),
    KNOWLEDGE_BASE_URL=os.getenv('KNOWLEDGE_BASE_URL', default='https://en.wikipedia.org/wiki/'),
    MAX_NGRAMS=os.getenv('MAX_NGRAMS', default='5'),
    TOKENS_LIMIT=os.getenv('TOKENS_LIMIT', default='0')  # 0 means no limit
)

# config types mapping
app.config['MYSQL_PORT'] = int(app.config['MYSQL_PORT'])
app.config['KNOWLEDGE_BASE'] = int(app.config['KNOWLEDGE_BASE'])
app.config['MAX_NGRAMS'] = int(app.config['MAX_NGRAMS'])
app.config['TOKENS_LIMIT'] = int(app.config['TOKENS_LIMIT'])

app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=app.config['PREFIX'])

from . import db
db.init_app(app)

from . import dump
dump.init_app(app)

from . import cache
cache.init_app(app)

from . import auth
app.register_blueprint(auth.bp)

from . import wikigold
app.register_blueprint(wikigold.bp)
app.add_url_rule('/', endpoint='index')

from . import api
app.register_blueprint(api.bp)

from . import admin
app.register_blueprint(admin.bp)

from . import datasets
datasets.init_app(app)

from . import evaluate
evaluate.init_app(app)