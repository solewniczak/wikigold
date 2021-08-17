import os

from flask import Flask, request


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('MYSQL_HOST', default='dev'),
        MYSQL_HOST=os.getenv('MYSQL_HOST'),
        MYSQL_USER=os.getenv('MYSQL_USER'),
        MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD'),
        MYSQL_DATABASE=os.getenv('MYSQL_DATABASE'),
        BASEURL=os.getenv('BASEURL'),
        MAX_NGRAMS=os.getenv('MAX_NGRAMS', default='5')
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # config types mapping
    app.config['MAX_NGRAMS'] = int(app.config['MAX_NGRAMS'])

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        # Use os.getenv("key") to get environment variables
        app_name = os.getenv("APP_NAME")

        if app_name:
            return f"Hello from {app_name} running in a Docker container behind Nginx!"

        return "Hello from Flask"

    from app import db
    db.init_app(app)

    from app import dump
    dump.init_app(app)

    from app import auth
    app.register_blueprint(auth.bp)

    from . import wiki
    app.register_blueprint(wiki.bp)
    app.add_url_rule('/', endpoint='index')

    from . import api
    app.register_blueprint(api.bp)

    return app
