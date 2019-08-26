import logging
from datetime import datetime
import numpy as np

from flask import (g, request, abort, json, current_app, Blueprint)
from flask import current_app as app

from app.db import get_db
from app.schema_validate import expects_valid_json
from app.schema_definitions import imports_schema, patch_schema

logger = logging.getLogger('app')

from psycopg2.extras import execute_values, DictCursor  #
from psycopg2.errors import ForeignKeyViolation

def jsonify(x, ensure_ascii=False, sort_keys=False,**kvargs):  # change defaults
    return json.dumps(x, ensure_ascii=ensure_ascii,
                            sort_keys=sort_keys, **kvargs)

def parse_date(s):
    return datetime.strptime(s,"%d.%m.%Y")

# Disclaimer: 
# When you think this code is shitty in some places, 
# consider that it was written in hurry. 

imports = Blueprint('imports', __name__, 
                        url_prefix='/imports/<int:import_id>')

@app.route('/imports', methods= ['POST',])
@expects_valid_json(imports_schema, force=True)
def imports_():
    citizens = g.data['citizens']

    # Prepare for insert
    prepared = []
    relatives_pairs = []
    
    filtered = ('street', 'building', 'apartment', 'name')  #store in `fields`
    
    now_date = datetime.now()

    for c in citizens: 
        citizen_id = c['citizen_id']
        
        # Put filtered to `fields`
        fields = json.dumps( { _: c[_] for _ in filtered}, ensure_ascii=False)
        
        # Convert `birth_date` to postgres format, check date is valid
        try:
            birth_date =  parse_date(c['birth_date'])
            if birth_date >= now_date:
                raise ValueError('birth_date in future')
        
        except ValueError:
            return "wrong birth_date: {}".format(birth_date), 400
       
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


@imports.url_value_preprocessor
def check_import_id(endpoint, values):
    g.import_id = values.pop('import_id')
    
    db = get_db()
    cur = db.cursor()

    cur.execute('SELECT * FROM Imports WHERE id = %s', [g.import_id])
    res = cur.fetchone()
    if not res:
        abort(404, 'No such import_id.')


@imports.route('/citizens/<int:citizen_id>', methods=['PATCH', ])
@expects_valid_json(patch_schema, force=True)
def patch(citizen_id):
    data = g.data
    import_id = g.import_id 
    
    if 'citizen_id' in data:
        abort(400, "citizen_id can't be changed")

    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)

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
   
    cur.execute('SELECT * FROM Citizens_view'
                 ' WHERE import_id = %s and citizen_id = %s',
                    [import_id, citizen_id])
    r = cur.fetchone()
    if not r:
        abort(404, 'No citizen with citizen_id={:d}'.format(citizen_id))
        
    db.commit()
    
    citizen = dict(r)
    citizen.pop('import_id')  # remove 'import_id' fields according to spec.
    
    return jsonify(citizen), 200


@imports.route('/citizens', methods=['GET',])
def citizens():
    import_id = g.import_id
    
    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT * FROM Citizens_view WHERE import_id = %s',
                [import_id])

    data = cur.fetchall()
    citizens = [ dict(_) for _ in data]

    return jsonify({'data': citizens}), 200


@imports.route('/citizens/birthdays', methods=['GET', ])
def birthdays():
    import_id = g.import_id
    
    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT month::varchar, '
                '   array_agg(ARRAY[citizen_id, presents]) AS id_npres'
                ' FROM Birthdays_view'
                ' WHERE import_id = %s'
                ' GROUP BY month'
                , [import_id])
                
    #  month |   id_npres    
    # -------+---------------
    #      4 | {{1,1}}
    #     11 | {{1,1}}
    #     12 | {{2,1},{3,1}}

    data = cur.fetchall()

    birthdays = {str(m):[] for m in range(1,13) }  # 12 months
    
    for month, id_npres in data:
        values =[{"citizen_id": _[0], "presents": _[1]}
                    for _ in id_npres]
        birthdays[month] = values


    # Alternative implementation with itertools.groupby:

    #~ cur.execute('SELECT month::varchar, citizen_id, presents from Birthdays_view'
                #~ ' WHERE import_id = %s', [import_id])
    #~ #  month | citizen_id | presents 
    #~ # -------+------------+----------
    #~ #      4 |          1 |        1
    #~ #     11 |          1 |        1
    #~ #     12 |          2 |        1
    #~ #     12 |          3 |        1
    #~ data = cur.fetchall()
    #~ birthdays = {str(m):[] for m in range(1,13) }  # 12 months
    #~ #group data by month
    #~ from itertools import groupby
    #~ for month, g in groupby(data, lambda x: x['month']):
        #~ values =[{"citizen_id": _['citizen_id'], "presents": _['presents']}
                    #~ for _ in g]
        #~ birthdays[month] = values

    return jsonify({'data': birthdays}), 200


@imports.route('/towns/stat/percentile/age', methods=['GET', ])
def towns_percentile_age():
    """
    Returns age percentile per city:
    {"data": [{"town": "Москва", "p50": 35.0, "p75": 47.5, "p99": 59.5},
              {"town": "Питер" , "p50": 45.0, "p75": 52.5, "p99": 97.15}]}
    """
    import_id = g.import_id

    db = get_db()
    cur = db.cursor(cursor_factory=DictCursor)
    
    cur.execute('SELECT town, array_agg( ARRAY[age, "count"]) AS age_count,'
                '        sum("count")::int as sum '
                ' FROM towns_age_view WHERE import_id = %(import_id)s '
                ' GROUP BY town'
                ,{'import_id': import_id}
                )
                
    #   town  |    age_count    | sum 
    # --------+-----------------+-----
    #  Керчь  | {{32,1}}        |   1
    #  Москва | {{22,1},{32,1}} |   2

    percentiles = {"p50": 50, "p75": 75, "p90": 99}
    ret = cur.fetchall()
   
    data = []
     
    for r in ret:
        # Since numpy.percentile finds percentile roughly, unfold entire array
        # and calculate wrong values instead of calculating precise ones
        # on hisogram `age_count`, wich we already have.

        unfold = []
        for k,v in r['age_count']:
            unfold.extend( [k] * v)  # [k,k,k,....]

        vals = { k: np.percentile(unfold, v) 
                    for k,v in percentiles.items()}
        
        data.append( { 'town': r['town'], ** vals })

    return jsonify({'data': data}, indent=2) , 200


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
