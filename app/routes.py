import logging
from datetime import datetime
from itertools import groupby

from flask import (g, request, abort, json)
from flask import current_app as app

from flask_expects_json import expects_json

from app.db import get_db
from app.schema_validate import expects_valid_json
from app.schema_definitions import imports_schema, patch_schema

logger = logging.getLogger('app')


from psycopg2.extras import execute_values, DictCursor  #

def jsonify(x, ensure_ascii=False, sort_keys=False):  # change defaults
    return json.dumps(x, ensure_ascii=ensure_ascii, sort_keys=sort_keys)

@app.route('/test', methods=['GET',])
def test():
    if app.config['TESTING']:
        logger.error('TEST')
        logger.warning('TEST')
        logger.info ('TEST')
        logger.debug('TEST')
        return 'OK'
    else:
        abort(404)


def parse_date(s): return datetime.strptime(s,"%d.%m.%Y")

@app.route('/imports', methods= ['POST',])
@expects_valid_json(imports_schema, force=True)
def imports():
    citizens = g.data['citizens']

    # Prepare for insert
    prepared = []
    relatives_pairs = []
    
    filtered = ('street', 'building', 'apartment', 'name')  #store in `fields`
    
    for c in citizens: 
        citizen_id = c['citizen_id']
        
        # Put filtered to `fields`
        fields = json.dumps( { _: c[_] for _ in filtered}, ensure_ascii=False)
        
        # Convert `birth_date` to postgres format, check date is valid
        try:
            birth_date =  parse_date(c['birth_date'])
        except ValueError:
            return "wrong birth_date: {:.42}".format(date), 400
       
        # Prepare relatives 
        relatives_pairs.extend( (citizen_id, rel) for rel in c['relatives'] )
        
        prepared.append( { 
                'citizen_id': citizen_id,
                'birth_date': birth_date,
                'town': c['town'],
                'gender': c['gender'],
                'fields': fields,
                })
    
    # Check relatives 
    # NB: the `citizen` can be relative to itself, so not '>' but '>='!
    
    def isle(x): return x[0] <= x[1]
    def swap(x): return (x[1], x[0])

    # get little endian pairs and reversed big endian pairs
    le = filter(isle, relatives_pairs)  # [(a,b),..]
    be = filter(isle, map(swap, relatives_pairs))  #((b,a),..) --> ((a,b),..)

    relatives = list(le)

    if relatives:
        if set(relatives) != set(be):
            abort(400, "inconsistent relatives pairs")
    
    # Insert to db
    db = get_db()
    cur = db.cursor()

    shard = ''  #TODO: implement in-app sharding if necessary

    # Imports
    cur.execute('INSERT INTO Imports (shard)'
                ' VALUES(%s) RETURNING id', [shard]) 
    import_id = cur.fetchone()[0]
    
    # Citizens
    template_citizens = '(' + str(import_id) + \
                ', %(citizen_id)s, %(town)s,' + \
                ' %(birth_date)s, %(gender)s, %(fields)s)'

    execute_values( cur,
                    'INSERT INTO Citizens' \
                    ' (import_id, citizen_id, town, birth_date, gender, fields)' \
                    ' VALUES %s',
                    prepared,
                    template = template_citizens,
                    )
    # Relatives
    if relatives:
        template_relatives = '(' + str(import_id) + ', %s, %s)'
        execute_values( cur,
                        'INSERT INTO Relatives' \
                        ' (import_id, low, high)' \
                        ' VALUES %s',
                        relatives,
                        template = template_relatives,
                        )
    db.commit()

    resp_ok = {"data": {"import_id" : import_id}}
    return jsonify(resp_ok), 201


@app.route('/imports/<int:import_id>/citizens/<int:citizen_id>', 
            methods=['PATCH', ])
@expects_valid_json(patch_schema, force=True)
def patch(import_id):
    data = g.data
    print(data)

    #TODO: 400 if set citizen_id
    pass


@app.route('/imports/<int:import_id>/citizens', methods=['GET',])
def citizens(import_id):
    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)

    fields = ('citizen_id', 'town', 'street', 'building', 'apartment',
                'name', 'birth_date', 'gender', 'relatives');

    cur.execute('SELECT * FROM Imports WHERE id = %s', [import_id])
    res = cur.fetchone()
    if not res:
        abort(404, 'No such import_id')
    
    cur.execute('SELECT * FROM Citizens_view WHERE import_id = %s',
                [import_id])

    data = cur.fetchall()
    citizens = [ {k:_[k] for k in fields} for _ in data]

    return jsonify({'data': citizens}), 200


@app.route('/imports/<int:import_id>/birthdays', methods=['GET', ])
def birthdays(import_id):
    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)

    cur.execute('SELECT * FROM Imports WHERE id = %s', [import_id])
    res = cur.fetchone()
    if not res:
        abort(404, 'No such import_id')
    
    cur.execute('SELECT month, citizen_id, presents from Birthdays_view'
                ' WHERE import_id = %s', [import_id])

    data = cur.fetchall()

    birthdays = {}
    #group data by month
    for k, g in groupby(data, lambda x: x['month']):
        month = str(int(k))
        values =[{"citizen_id": _['citizen_id'], "presents": _['presents']}
                    for _ in g]
        birthdays[month] = values

    return jsonify({'data': birthdays}, 200)


@app.route('/imports/<int:import_id>/towns/stat/percentile/age', methods=['GET', ])
def agestats(import_id):
    pass


