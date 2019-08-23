import logging

from flask import (g, request, jsonify)
from flask import current_app as app

from flask_expects_json import expects_json

from app.db import get_db
from app.schema_validate import expects_valid_json
from app.schema_definitions import imports_schema, patch_schema

logger = logging.getLogger('app')


@app.route('/test', methods=['GET',])
def test():
    if app.config['TESTING']:
        logger.error('TEST')
        logger.warning('TEST')
        logger.info ('TEST')
        logger.debug('TEST')
    return 'OK'


@app.route('/imports', methods= ['POST',])
@expects_valid_json(imports_schema, force=True)
def imports():
    data = g.data
    resp_ok = {"data": {"import_id" : 1}}
    return jsonify(resp_ok), 201


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH', ])
@expects_valid_json(patch_schema, force=True)
def patch(import_id):
    pass


@app.route('/imports/<int:import_id>/citizens', methods=['GET',])
def list(import_id):
    pass


@app.route('/imports/<int:import_id>/birthdays', methods=['GET', ])
def birthdays(import_id):
    pass


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET', ])
def agestats(import_id):
    pass




