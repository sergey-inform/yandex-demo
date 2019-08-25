#TODO: import postgress stuff

import click
from flask import current_app, g
from flask.cli import with_appcontext

import psycopg2
import logging
    

def get_db():
    """Connect to the application's configured database. The connection
    is unique for each request and will be reused if this is called
    again.
    """
    if 'db' not in g:
        dbconf = current_app.config['DB_CONF']
        try:
            g.db = psycopg2.connect(**dbconf)
        except psycopg2.DatabaseError as e:
            logging.error(e)
        finally:
            logging.info('db connected')
            
    return g.db


def close_db(e=None):
    """If this request connected to the database, close the connection.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Clear existing data and create new tables."""
    db = get_db()

    with current_app.open_resource('db.sql') as f:
        cursor=db.cursor()
        cursor.execute(f.read().decode('utf8'))
        db.commit()
        logging.info("db initialized")


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    """Register database functions with the Flask app.
    This is called by the application factory.
    """
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
