import pytest
import socket as s


@pytest.fixture(scope='module')
def Server():
    class _:
        host_port = 'localhost', 5000
        uri = 'http://{}:{}'.format(*host_port)
    return _

@pytest.yield_fixture
def socket():
    _sock = s.socket(s.AF_INET, s.SOCK_STREAM)
    yield _sock
    _sock.close()

def test_server_connect(socket, Server):
    socket.connect(Server.host_port)
    assert socket

