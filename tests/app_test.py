import pytest
import logging


def test_test(client, caplog):
    """ Check our testing system works. """

    r = client.get("/test")
    assert r.status_code == 200
    assert b"OK" in r.data

    # check logging
    with caplog.at_level(logging.DEBUG):
        levels = [ _.levelname for _ in caplog.records]
    assert levels == ['ERROR', 'WARNING', 'INFO', 'DEBUG']

