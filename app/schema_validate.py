"""
Validate request against JSON-schema.

"""
from functools import wraps

from werkzeug.exceptions import abort
from  flask import (request,g)

import fastjsonschema
from fastjsonschema.exceptions import JsonSchemaException


def expects_valid_json(schema=None, force=True):
# Inspired by https://github.com/Fischerfredl/flask-expects-json
    if schema is None:
        schema = dict()
   
    validator = fastjsonschema.compile(schema)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json(force=force)

            if data is None:
                return abort(400, 'Failed to decode JSON object')
            
            try: validator(data)
            except JsonSchemaException as e:
                return abort(400, e.message)

            g.data = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator
