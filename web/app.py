import os
import sys
import json
#import csv
import requests
from requests.exceptions import HTTPError
import nmea
import urlparse
import urllib
import md5
import base64
from operator import itemgetter
import datetime
import time
from time import mktime

import logging
# *******************************************************************
# Debug Output defines
# Comment to enable/disable
# ********************************************************************
#debug_all = False
debug_all = True



requests_log = logging.getLogger("requests")
#requests_log.setLevel(logging.WARNING)
requests_log.setLevel(logging.INFO)

#logging.disable(logging.DEBUG)

logging.basicConfig(level=logging.INFO)
log = logging


from flask import (
  Flask,
  session,
  render_template,
  url_for,
  make_response,
  Response,
  stream_with_context,
  redirect,
  request,  
  jsonify
)


import db


from psycopg2.pool import ThreadedConnectionPool
db_pool = ThreadedConnectionPool(
  1, # min connections,
  int(os.environ.get('MAX_DB_CONNECTIONS',3)),
  **connection_from(os.environ['DATABASE_URL'])
)

@app.route('/')
def index():

    response = make_response(render_template('index.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


