citizen_definitions = {
    'string': {
        'type': 'string',
        'minLength': 1
        },
    'citizen': {
        'type': 'object',
        'properties': {
            'citizen_id': {
                'type': 'integer',
                'minimum': 0
                },
            'town': {'$ref': '#definitions/string'},
            'street': {'$ref': '#definitions/string'},
            'building': {'$ref': '#definitions/string'},
            'apartment': {
                'type' : 'integer',
                'minimum': 0
                },
            'building': {'$ref': '#definitions/string'},
            'name': {'$ref': '#definitions/string'},
            'birth_date': {
                'type': 'string',
                'pattern': "^[0-9]{2}.[0-9]{2}.[0-9]{4}$"
                },
            'gender': {
                'type': 'string',
                'enum': ['male', 'female'],
                },
            'relatives': {
                'type': 'array',
                'items': {'$ref': '#definitions/citizen/properties/citizen_id'},
                'uniqueItems': True
                }
        },
       'additionalProperties': False,
    }
}