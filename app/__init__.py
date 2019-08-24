import os
from flask import Flask

# Sometimes it's nice to keep __init__.py clean, but here
# we stick to flask's Application Factories approach. 
# https://flask.palletsprojects.com/en/1.1.x/patterns/appfactories/


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__) #FIXME: , instance_relative_config=True)
    
    app.config.from_mapping(
        DB_URL="postgresql://demo@localhost:5432/citizens",
        DB_CONF = {
            "host": "localhost",
            "port": 5432,
            "user": "demo",
            "password": "Q2da0wEn9",
            "dbname": "citizens",
            }
        )

    if test_config:
        app.config.update(test_config)

    else:
        app.config.from_pyfile('config.py') #TODO: , silent=True

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/ping')  # undocumented API functionality ;)
    def ping():
        return 'pong'
    
    with app.app_context():
        from . import routes

    from app import db
    db.init_app(app)

    return app
