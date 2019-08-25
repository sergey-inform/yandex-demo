import os
import pytest
import json
import logging

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_path, "valid_import.json"), 'r') as f:
    valid_json = f.read()

def pytest_namespace():
    return {'import_id': None}

def test_pupulate(client,):
    """ Populate db with valid data.
    """
    r = client.post("/imports", data=valid_json)

    try:
        assert r.status_code == 201
    except:
        logging.info(r.data.decode())
        raise
    
    resp = json.loads(r.data.decode())
    import_id=resp['data']['import_id']
    
    logging.info('IMPORT_ID %d', import_id)
    pytest.import_id = import_id  #save globally
    

def test_update(client,):
    """ Test valid update.
    """
    import_id = pytest.import_id
    if not import_id:
        pytest.skip("import_id is {}".format(import_id))











