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
    url_1 = "/imports/{:d}/citizens/{:d}".format(import_id, 1)
    assert client.get(url).status_code == 405  # Method not allowed
    
    valid_data = {
	"name":	"Иванова Мария Леонидовна",
	"town":	"Москва",
	"street": "Льва Толстого",
	"building": "16к7стр5",
	"apartment": 7,
	"relatives": [1]
	}

    def do(url, x): return client.patch( url, data=json.dumps(x))
    
    #valid patch
    r = do(url, valid_data)
    assert r.status_code == 200

    #patch non-existant
    ne_url = "/imports/{:d}/citizens/{:d}".format(import_id, 99999)
    r = do(ne_url, valid_data)
    assert r.status_code == 404

    #patch with wrong field
    invalid_data = valid_data.copy()
    invalid_data['no_such_field'] = 1
    r = do(url, invalid_data)
    assert r.status_code == 400
    assert b'only specified properties' in r.data

    #patch with citizen_id
    invalid_data = valid_data.copy()
    invalid_data['citizen_id'] = 4
    r = do(url,invalid_data)
    assert r.status_code == 400
    assert b'citizen_id' in r.data

    #patch check relatives update
    r = do(url,{'relatives':[]})
    assert r.status_code == 200
    r1 = do(url_1,{'name':'John Smith'})
    r1data = json.loads(r1.data)
    assert r1data['data']['relatives'] == [2]








