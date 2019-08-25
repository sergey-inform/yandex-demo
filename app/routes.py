import logging
from datetime import datetime
from itertools import groupby

from flask import (g, request, abort, json)
from flask import current_app as app

from app.db import get_db
from app.schema_validate import expects_valid_json
from app.schema_definitions import imports_schema, patch_schema

logger = logging.getLogger('app')


from psycopg2.extras import execute_values, DictCursor  #
from psycopg2.errors import ForeignKeyViolation

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


def parse_date(s):
    return datetime.strptime(s,"%d.%m.%Y")


# Disclaimer: 
# When you think that this code is shitty, 
# keep in mind that it was written in hurry. 
#

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
                    'INSERT INTO Citizens'
                    ' (import_id, citizen_id, town,'
                    ' birth_date, gender, fields)' \
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
def patch(import_id, citizen_id):
    data = g.data
    if 'citizen_id' in data:
        abort(400, "citizen_id can't be patched")

    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)
   
    #TODO: move to blueprint or decorator \/
    cur.execute('SELECT * FROM Imports WHERE id = %s', [import_id])
    r = cur.fetchone()
    if not r:
        abort(404, 'No such import_id')
    
    #TODO: -----------------------

    cur.execute('SELECT * FROM Citizens_view'
                 ' WHERE import_id = %s and citizen_id = %s',
                    [import_id, citizen_id])
    r = cur.fetchone()
    if not r:
        abort(404, 'No citizen with citizen_id={:d}'.format(citizen_id))
    
    citizen = dict(r)

    columns  = ('town', 'birth_date', 'gender') 
    filtered = ('street', 'building', 'apartment', 'name')  #store in `fields`

    # Update `citizen` columns
    columns_update = { k: data[k] for k in columns
                    if k in data and citizen[k] != data[k] }
    # Update `citizen` fields
    fields_update =  { k: data[k] for k in filtered
                    if k in data and citizen[k] != data[k] }
    
    # Prepare `citizen` relatives
    rel_citizen = set(citizen['relatives'])
    rel_data = set(data['relatives']) if 'relatives' in data else set()

    rel_del = [_ for _ in rel_citizen - rel_data]
    rel_ins_pairs = [sorted((citizen_id, _)) for _ in rel_data - rel_citizen]
    
    placeholders = {
                **columns_update,
                'fields': json.dumps(fields_update or {},
                                        ensure_ascii=False), 
                'import_id': import_id,
                'citizen_id': citizen_id,
                'rel_del': tuple(rel_del), 
            }

    # Update `citizen` columns and fields
    if columns_update or fields_update:

        sql = cur.mogrify('UPDATE Citizens SET ' + \
                    ''.join( ('{} = %({})s, '.format(k,k) 
                            for k in columns_update.keys()) ) + \
                    ' fields = to_jsonb(fields) || %(fields)s::jsonb'
                    ' WHERE import_id = %(import_id)s'
                    ' AND citizen_id = %(citizen_id)s',
                    placeholders)

#        logger.info(sql.decode())
        cur.execute(sql)

    # Update `citizen` relatives
    
    if placeholders['rel_del']:
        sql = cur.mogrify('DELETE from Relatives WHERE'
                    ' import_id = %(import_id)s'
                    ' AND ('
                    '      (low in %(rel_del)s AND high = %(citizen_id)s)'
                    '   OR (high in %(rel_del)s AND low = %(citizen_id)s)'
                    ')',
                    placeholders
                    )

#        logger.info(sql.decode())
        cur.execute(sql)
    
    try:
        if rel_ins_pairs:
            for low, high in rel_ins_pairs:
                cur.execute('INSERT INTO Relatives' \
                            ' (import_id, low, high)' \
                            ' VALUES (%s, %s, %s)',
                            (import_id, low, high)
                            )
    except ForeignKeyViolation:
        return 'corresponging citizen_id does not exist', 400
   
    db.commit()
    
    #FIXME: fast and dirty, but race condition is possible
    cur.execute('SELECT * FROM Citizens_view'
                 ' WHERE import_id = %s and citizen_id = %s',
                    [import_id, citizen_id])
    r = cur.fetchone()
    if not r:
        abort(404, 'No citizen with citizen_id={:d}'.format(citizen_id))
    
    citizen = dict(r)
    citizen.pop('import_id')
    
    return jsonify(citizen), 200


@app.route('/imports/<int:import_id>/citizens', methods=['GET',])
def citizens(import_id):
    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)

    cur.execute('SELECT * FROM Imports WHERE id = %s', [import_id])
    res = cur.fetchone()
    if not res:
        abort(404, 'No such import_id')
    
    cur.execute('SELECT * FROM Citizens_view WHERE import_id = %s',
                [import_id])

    data = cur.fetchall()
    citizens = [ dict(_) for _ in data]

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


@app.route('/imports/<int:import_id>/towns/stat/percentile/age',
    methods=['GET', ])
def agestats(import_id):
    return '', 501


