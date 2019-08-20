
def test_test(client):
    """ Check our testing system works. """
    response = client.get("/test")
    assert response.data == b"OK"




