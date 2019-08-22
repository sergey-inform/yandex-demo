import os
import pytest

from app import create_app


@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test."""
    _app = create_app({"TESTING": True, 'DEBUG': True})

    #with _app.app_context():
    #    a = 1
    yield _app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

