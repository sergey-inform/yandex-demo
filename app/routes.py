from flask import (g, request)
from flask import current_app as app

from werkzeug.exceptions import abort

from app.db import get_db

@app.route('/test', methods=['GET',])
def test():
    return 'OK'

@app.route('/imports', methods= ['POST',])
def imports():
    content = request.get_json(force=True, silent=False) #FIXME: silent=True
    print(content)
    return "OK"


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', methods=['PATCH', ])
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




