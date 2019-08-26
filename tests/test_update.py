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
    

def test_patch(client,):
    """ Test valid update.
    """
    import_id = pytest.import_id
    if not import_id:
        pytest.skip("import_id is {}".format(import_id))
    
    url = "/imports/{:d}/citizens/{:d}".format(import_id, 3)
    assert client.get(url).status_code == 405  # Method not allowed
    
    valid_data = {
	"name":	"Иванова Мария Леонидовна",
	"town":	"Москва",
	"street": "Льва Толстого",
	"building": "16к7стр5",
	"apartment": 7,
	"relatives": [1]
	}

    #valid patch
    r = client.patch(url, data=json.dumps(valid_data))
    assert r.status_code == 200

    #patch non-existant
    ne_url = "/imports/{:d}/citizens/{:d}".format(import_id, 99999)
    r = client.patch(ne_url, data=json.dumps(valid_data))
    assert r.status_code == 404

    #patch with wrong field
    invalid_data = valid_data.copy()
    invalid_data['no_such_field'] = 1
    r = client.patch(url, data=json.dumps(invalid_data))
    assert r.status_code == 400
    assert b'data must contain only specified properties' in r.data

    #patch with citizen_id
    invalid_data = valid_data.copy()
    invalid_data['citizen_id'] = 4
    r = client.patch(url, data=json.dumps(invalid_data))
    assert r.status_code == 400
    assert b'citizen_id' in r.data

    #patch check relatives update

    #patch check values updated







