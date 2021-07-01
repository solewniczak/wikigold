import os

from flask import Flask


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='dev',
        MYSQL_HOST=os.getenv('MYSQL_HOST'),
        MYSQL_USER=os.getenv('MYSQL_USER'),
        MYSQL_PASSWORD=os.getenv('MYSQL_PASSWORD'),
        MYSQL_DATABASE=os.getenv('MYSQL_DATABASE')
    )

    if test_config is not None:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        # Use os.getenv("key") to get environment variables
        app_name = os.getenv("APP_NAME")

        if app_name:
            return f"Hello from {app_name} running in a Docker container behind Nginx!"

        return "Hello from Flask"

    from . import db
    db.init_app(app)

    return app
