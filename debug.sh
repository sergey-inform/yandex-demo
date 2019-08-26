#!/usr/bin/env sh

export FLASK_APP=app
export FLASK_DEBUG=1
export LOGLEVEL=DEBUG
flask run $*
