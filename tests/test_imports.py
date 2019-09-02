import os
import pytest
import json
import logging
import copy

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_path, "valid_import.json"), 'r') as f:
    valid_json = f.read()

valid = json.loads(valid_json)

# should work with any content_type
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

def test_resp(client):
    """ Check response
    """
    def do(x): return client.post("/imports", data=json.dumps(x))

    # empty citizens
    r = do('{"citizens": []}')
    assert r.status_code == 400

    # valid response
    r = do(valid)
    rdata = json.loads(r.data)
    import_id = rdata['data']['import_id']
    rdata_ok = json.loads('{"data": {"import_id": %d }}' % import_id)
    assert rdata == rdata_ok 
    assert r.status_code == 201


def test_validation(client):
    """ Check fields validation
    """
    def do(x): return client.post("/imports", data=json.dumps(x))

    # negative citizen_id
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['citizen_id'] = -1 
    r = do(invalid)
    assert r.status_code == 400

    # zero citizen_id 
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['citizen_id'] = 0
    invalid['citizens'][1]['relatives'] = [0]
    r = do(invalid)
    assert r.status_code == 201

    # zero citizen_id 
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['citizen_id'] = 0
    invalid['citizens'][1]['relatives'] = [0]
    r = do(invalid)
    assert r.status_code == 201

    # empty town 
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['town'] = ''
    r = do(invalid)
    assert r.status_code == 400

    # town is not a string
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['town'] = 1
    r = do(invalid)
    assert r.status_code == 400

    # town is a string
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['town'] = "1"
    r = do(invalid)
    assert r.status_code == 201

    # apartment is integer (1.0 is valid)
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['apartment'] = 1.1
    r = do(invalid)
    assert r.status_code == 400

    # name is a string
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['name'] = 1
    r = do(invalid)
    assert r.status_code == 400

    # birthdate
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['birth_date'] = "30.02.1996"
    r = do(invalid)
    assert r.status_code == 400
    
    # birthdate format
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['birth_date'] = "01-01-2001"
    r = do(invalid)
    assert r.status_code == 400

    # birthdate in future
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['birth_date'] = "01.01.2050"
    r = do(invalid)
    assert r.status_code == 400

    # gender
    invalid = copy.deepcopy(valid)
    invalid['citizens'][0]['gender'] = "unspecified"
    r = do(invalid)
    assert r.status_code == 400

    # relatives nosuch
    invalid = copy.deepcopy(valid)
    invalid['citizens'][1]['relatives'].append(100)
    r = do(invalid)
    assert r.status_code == 400

    # relatives integrity
    invalid = copy.deepcopy(valid)
    invalid['citizens'][1]['relatives'].append(3)
    r = do(invalid)
    assert r.status_code == 400

    # relative to itself
    invalid = copy.deepcopy(valid)
    invalid['citizens'][1]['relatives'].append(2)
    r = do(invalid)
    assert r.status_code == 201

