import pytest
import logging

from app import create_app


def test_test(client, caplog):
    """ Check our testing system works. """

    r = client.get("/test")
    assert r.status_code == 200
    assert b"OK" in r.data

    # check logging
    with caplog.at_level(logging.DEBUG):
        levels = [ _.levelname for _ in caplog.records]
    assert levels == ['ERROR', 'WARNING', 'INFO', 'DEBUG']


def test_config():
    """Test create_app without passing test config."""
    assert not create_app().testing
    assert create_app({'TESTING': True}).testing


def test_ping(client):
    response = client.get('/ping')
    assert response.data == b'pong'
