import os
import pytest

from app import create_app
from app.db import get_db, init_db, drop_db

#inspired by 
#https://github.com/pallets/flask/blob/1.0.4/examples/tutorial/tests/conftest.py

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test."""
    _app = create_app( {"TESTING": True, 'DEBUG': True})

    with _app.app_context():
        drop_db()
        init_db()
        
    yield _app

    #TODO: cleanup


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
