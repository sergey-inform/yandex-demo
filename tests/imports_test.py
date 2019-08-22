import os
import pytest
import json
import logging

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_path, "valid_import.json"), 'r') as f:
    valid_json = f.read()


@pytest.mark.parametrize("_type, _code", 
        [("text/plain", 201), ("application/json", 201)])

def test_valid(client, _type, _code):
    """ Check valid json from specification.
    """
    r = client.post("/imports", data=valid_json, content_type=_type)

    try:
        assert r.status_code == _code
    except:
        logging.info(r.data.decode())
        raise
    
