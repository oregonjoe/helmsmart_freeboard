import os
from os import environ
import sys
import json
#import csv
import requests
from requests.exceptions import HTTPError
#import nmea
#import urlparse
import urllib
from urlparse import urlparse
import md5
import base64
import fnmatch
from operator import itemgetter
import numpy as np
from geopy.distance import vincenty
from calendar import timegm
import datetime
import time
from time import mktime
import pytz
from pytz import timezone
#from datetime import datetime
from itertools import groupby
import pyonep
from pyonep import onep
from meteocalc import Temp, dew_point, heat_index, wind_chill, feels_like
#import urlparse

#from iron_cache import *
import logging
import psycopg2  
import pylibmc
from os import environ as env, path
#test comment
# *******************************************************************
# Debug Output defines
# Comment to enable/disable
# ********************************************************************
#debug_all = False
debug_all = True

   

requests_log = logging.getLogger("requests")
#requests_log.setLevel(logging.WARNING)
#requests_log.setLevel(logging.INFO)
requests_log.setLevel(logging.DEBUG)
#logging.disable(logging.DEBUG)

#logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)
log = logging

#added 032315 jlb
#from influxdb import client as influxdb
#from influxdb.influxdb08 import InfluxDBClient as influxdb
from influxdb.influxdb08 import InfluxDBClient

from influxdb import InfluxDBClient as InfluxDBCloud
from influxdb.client import InfluxDBClientError

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

from flask.ext.cors import CORS, cross_origin




def connection_from(url):
  #config = urlparse.urlparse(url)
  config = urlparse(url)
  return dict(
    host=config.hostname, 
    port=config.port, 
    dbname=config.path[1:],
    user=config.username,
    password=config.password
  )


from psycopg2.pool import ThreadedConnectionPool
db_pool = ThreadedConnectionPool(
  1, # min connections,
  int(os.environ.get('MAX_DB_CONNECTIONS',3)),
  **connection_from(os.environ['DATABASE_URL'])
)



app = Flask(__name__)
CORS(app) 
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['DEBUG'] = True
app.debug = True



#Adding auth0
from auth0.v3.authentication import GetToken
from auth0.v3.authentication import Users

AUTH0_CALLBACK_URL = environ.get('AUTH0_CALLBACK_URL')
AUTH0_CLIENT_ID = environ.get('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = environ.get('AUTH0_CLIENT_SECRET')
AUTH0_DOMAIN = environ.get('AUTH0_DOMAIN')



mcservers = os.environ.get('MEMCACHIER_SERVERS', '').split(',')
mcuser = os.environ.get('MEMCACHIER_USERNAME', '')
mcpass = os.environ.get('MEMCACHIER_PASSWORD', '')

mc = pylibmc.Client(mcservers, binary=True,
                    username=mcuser, password=mcpass,
                    behaviors={
                      # Faster IO
                      "tcp_nodelay": True,

                      # Keep connection alive
                      'tcp_keepalive': True,

                      # Timeout for set/get requests
                      'connect_timeout': 2000, # ms
                      'send_timeout': 750 * 1000, # us
                      'receive_timeout': 750 * 1000, # us
                      '_poll_timeout': 2000, # ms

                      # Better failover
                      'ketama': True,
                      'remove_failed': 1,
                      'retry_timeout': 2,
                      'dead_timeout': 30,
                    })



"""
from flask_stormpath import StormpathManager, User, login_required, login_user, logout_user, user
from stormpath.error import Error as StormpathError
from os import environ

app.secret_key = environ.get('SECRET_KEY')

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
app.config['STORMPATH_API_KEY_ID'] = environ.get('STORMPATH_API_KEY_ID')
app.config['STORMPATH_API_KEY_SECRET'] = environ.get('STORMPATH_API_KEY_SECRET')
#app.config['STORMPATH_APPLICATION'] = environ.get('STORMPATH_URL')
app.config['STORMPATH_ENABLE_FORGOT_PASSWORD'] = True
app.config['STORMPATH_APPLICATION'] = 'helmsmart-freeboard'
#app.config['STORMPATH_LOGIN_TEMPLATE'] = 'stormpath/login.html'
#app.config['STORMPATH_REGISTRATION_TEMPLATE'] = 'stormpath/register.html'
app.config['STORMPATH_ENABLE_GOOGLE'] = True


app.config['STORMPATH_SOCIAL'] = {
      'GOOGLE': {
          'client_id': '740357019563-kbkkg3ggk1jol4ujl3kpe37dn4jimr3h.apps.googleusercontent.com',
          'client_secret': '0UQsadTsKWoiSd0VerCZICPg',
      }
  }



stormpath_manager = StormpathManager()

# some code which creates your app
stormpath_manager.init_app(app)
"""

def hash_string(string):
    #salted_hash = string + application.config['SECRET_KEY']
    salted_hash = string + app.secret_key
    return md5.new(salted_hash).hexdigest()


  
#calculate baro offset in milibars from altitude in feet
def getAtmosphericCompensation(feet):

  if feet == '---':
    return 0

  if int(feet) < 0:
    return 0
  
  if int(feet) > 10000:
    return 317
  
  index = 0
  
  try:
    # divide by 200
    index = int(feet * 0.005)
  except:
    return 0

  #index range is 0 to 50
  gAtmosphericCompensation = [0,7,15,22,29,36,43,50,57,64,71,78,85,92,98,105,112,118,125,132,138,145,151,157,164,170,176,183,189,195,201,207,213,219,225,231,237,243,249,255,261,266,272,278,283,289,295,300,306,311,316]

  baro_milibars = gAtmosphericCompensation[index]
  baro_pascals = float(baro_milibars * 0.1)
  # convert to pascals
  return baro_pascals


#Convert Units between US and Metric
def convertunittype(units, value):


  if units == 'temperature':
    if value == 'US':
      return 0
    elif value == 'metric':
      return 1
    elif value == 'si':
      return 2
    elif value == 'nautical':
      return 0


    

  elif units == 'pressure':
    if value == 'US':
      return 8
    elif value == 'metric':
      return 9
    elif value == 'nautical':
      return 4
    elif value == 'si':
      return 9

  elif units == 'baro_pressure':
    if value == 'US':
      return 10
    elif value == 'metric':
      return 11
    elif value == 'nautical':
      return 10
    elif value == 'si':
      return 9



    

  elif units == 'speed':
    if value == 'US':
      return 5
    elif value == 'metric':
      return 6
    elif value == 'nautical':
      return 4
    elif value == 'si':
      return 7


    

  elif units == 'volume':
    if value == 'US':
      return 21
    elif value == 'metric':
      return 20
    elif value == 'si':
      return 22
    elif value == 'nautical':
      return 20



    
    
  elif units == 'flow':
    if value == 'US':
      return 18
    elif value == 'metric':
      return 19
    elif value == 'nautical':
      return 19
    elif value == 'si':
      return 19




    

  elif units == 'depth':
    if value == 'US':
      return 32
    elif value == 'metric':
      return 33    
    elif value == 'nautical':
      return 36
    elif value == 'si':
      return 33


  elif units == 'rain':
    if value == 'US':
      return 45
    elif value == 'metric':
      return 44    
    elif value == 'nautical':
      return 32
    elif value == 'si':
      return 33


  elif units == 44: #//= RAIN IN mm
       return float("{0:.2f}".format(value * 1000))  

  elif units == 45: #//=RAIN in inches
      return float("{0:.2f}".format(value * 39.3))
    

  elif units == 'distance':
    if value == 'US':
      return 34
    elif value == 'metric':
      return 33    
    elif value == 'nautical':
      return 35
    elif value == 'si':
      return 33



  elif units == 'degree':
    return 16

  elif units == 'radian':
    return 17

  
  elif units == 'rpm':
    return 24
  
  elif units == 'rps':
    return 25

  elif units == '%':
    return 26


  elif units == 'volts':
    return 27
  
  elif units == 'amps':
    return 28

  elif units == 'watts':
    return 29
  
  elif units == 'watthrs':
    return 30

  elif units == 'count':
    return 100
  
  elif units == 'time':
    return 37
  
  elif units == 'date':
    return 38
  
  elif units == 'hours':
    return 39

  else:
    return 44
  
    
#Convert Units used for freeboard numerical displays
def convertfbunits(value, units):
  units = int(units)

  #if not value:
  #  return "---"

  if value is None:
    return "---"

  if value == 'None':
    return "---"



  if units == 0: #//="0">Fahrenheit</option>
      return float("{0:.0f}".format((value * 1.8) - 459) )


  elif units ==  1: #//="1">Celsius</option>
      return float("{0:.0f}".format((value * 1.0) - 273) )


  elif units == 2: #//e="2">Kelvin</option>
      return float("{0:.0f}".format((value * 1.0) ) )


  #//  case 3: //="3">- - -</option> 


  elif units == 4: #//="4">Knots</option>
      return float("{0:.2f}".format(value * 1.94384449))


  elif units == 5: #//="5">MPH</option>
      return float("{0:.2f}".format(value * 2.23694) )


  elif units == 6: #//e="6">KPH</option>
      return float("{0:.2f}".format(value * 1.0) )



  #// case 7: //="7">- - -</option>
  elif units == 8: #//="8">PSI</option>
      return float("{0:.2f}".format(value * 0.145037738007) )



  elif units == 9: #//e="9">KPASCAL</option>
      return float("{0:.2f}".format(value * 1.0))



  elif units == 10: #//="10">INHG</option>
      return float("{0:.2f}".format(value * 0.295229) )



  elif units == 11: #//e="9">HPASCAL</option>
      return float("{0:.2f}".format(value * 10.0))


  #//  case 11: //="11">- - -</option>
  # //  case 12: //="12">TRUE</option>
  #//   case 13: //="13">MAGNETIC</option>
  #//   case 14: //="14">- - -</option>
  #//   case 15: //="15">- - -</option>
  elif units == 15:            #//   case 15: //="15">Lat/Lng</option>
    return float("{0:.8f}".format(value * 1.0 ) )

  elif units == 16:            #//   case 16: //="16">DEGREES</option>
    return float("{0:.0f}".format(value * 1.0 ) )

  #//   case 17: //="17">Radians</option>
  elif units == 18: #//="18">Gallons/hs</option>
      return float("{0:.2f}".format(value * 0.264172052 ) )


  elif units == 19: #//="19">Liters/hr</option>
      return float("{0:.2f}".format(value * 0.1 ) )


  #case 20: //="20">Liters</option>
  elif units == 21: #//="18">Gallons/hs</option>
      return float("{0:.2f}".format(value * 0.264172052 ) )


  #case 22: //="22">CubicMeter</option>
  #case 23: //="23">- - -</option>
  #case 24: //="24">RPM</option>
    
  elif units == 24: #//="24">RPM</option>
      return float("{0:.0f}".format(value *1.0))

    
  #case 25: //="25">RPS</option>   
    
  elif units == 26: #//="26">%</option>
      return float("{0:.0f}".format(value *1.0))


    
  elif units == 27: #//="27">Volts</option>
      return float("{0:.2f}".format(value *1.00))


  elif units == 31: #//="31">kWhrs</option>
      return float("{0:.2f}".format(value *01.0))
  # case 28: //="28">Amps</option>
            
  elif units == 32: #//="32">Feet</option>
      return float("{0:.2f}".format(value * 3.28084)) 

  elif units == 33: #//="33">Meters</option>
      return float("{0:.2f}".format(value * 1.0))

  elif units == 34: #//="34">Miles</option>
      return float("{0:.2f}".format(value * 0.000621371))              

  elif units == 35: #//="35">Nautical Mile</option>
      return float("{0:.2f}".format(value * 0.0005399568))                
  
  elif units == 36: #//="36">Fathoms</option>
      return float("{0:.2f}".format(value * 0.546806649))



  elif units == 44: #//= RAIN IN mm
       return float("{0:.2f}".format(value * 1000))  

  elif units == 45: #//=RAIN in inches
      return float("{0:.2f}".format(value * 39.3))


  elif units == 37: #//="37">Time</option>
      #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))
      return datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S')

  elif units == 38: #//="38">Date/time</option>
      #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
      return (datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
    
  elif units == 39: #//="39">Hours</option>
      #Engine Hours (value / (60*60))
       return float("{0:.2f}".format(value * 0.000277777))  

  elif units == 43: #//="43">Volts 10</option>
      return float("{0:.2f}".format(value * 0.1))

  elif units ==100: #//=convert to integer
      return int(value)
    
  else:
      return float("{0:.2f}".format(value))

def convertunits(value, units):
  units = int(units)


  if not value:
    return "---"

  if value is None:
    return "---"

  if value == 'None':
    return "---"

  if units == 0: #//="0">Fahrenheit</option>
      return float("{0:.2f}".format((value * 1.8) - 459) )


  elif units ==  1: #//="1">Celsius</option>
      return float("{0:.2f}".format((value * 1.0) - 273) )


  elif units == 2: #//e="2">Kelvin</option>
      return value 


  #//  case 3: //="3">- - -</option> 


  elif units == 4: #//="4">Knots</option>
      return float("{0:.2f}".format(value * 1.94384449))


  elif units == 5: #//="5">MPH</option>
      return float("{0:.2f}".format(value * 2.23694) )


  elif units == 6: #//e="6">KPH</option>
      return float("{0:.2f}".format(value * 1.0) )



  #// case 7: //="7">- - -</option>
  elif units == 8: #//="8">PSI</option>
      return float("{0:.2f}".format(value * 0.145037738007) )



  elif units == 9: #//e="9">KPASCAL</option>
      return float("{0:.2f}".format(value * 1.0))



  elif units == 10: #//="10">INHG</option>
      return float("{0:.2f}".format(value * 0.295229) )


  #//  case 11: //="11">- - -</option>
  # //  case 12: //="12">TRUE</option>
  #//   case 13: //="13">MAGNETIC</option>
  #//   case 14: //="14">- - -</option>
  #//   case 15: //="15">- - -</option>
  elif units == 16:            #//   case 16: //="16">DEGREES</option>
    return float("{0:.2f}".format(value * 1.0 ) )

  #//   case 17: //="17">Radians</option>
  elif units == 18: #//="18">Gallons/hs</option>
      return float("{0:.2f}".format(value * 0.264172052 ) )


  elif units == 19: #//="19">Liters/hr</option>
      return float("{0:.2f}".format(value * 0.1 ) )


  elif units == 20:# //="20">Liters</option>
       return float("{0:.2f}".format(value * 0.1 ) )
      
  elif units == 21:# //="21">Gallons</option>
      return float("{0:.2f}".format(value * 0.264172052 ) )
    
  #case 22: //="22">CubicMeter</option>
  #case 23: //="23">- - -</option>
  #case 24: //="24">RPM</option>
  #case 25: //="25">RPS</option>   
  #case 26: //="26">%</option>
  elif units == 27: #//="27">Volts</option>
      return float("{0:.2f}".format(value *1.00))


  elif units == 31: #//="31">kWhrs</option>
      return float("{0:.2f}".format(value *1.00))
  # case 28: //="28">Amps</option>
  
  elif units == 32: #//="32">Feet</option>
      return float("{0:.2f}".format(value * 3.28084)) 

  elif units == 33: #//="33">Meters</option>
      return float("{0:.2f}".format(value * 1.0))


  elif units == 44: #//= RAIN IN mm
       return float("{0:.2f}".format(value * 1000.0))  

  elif units == 45: #//=RAIN in inches
      return float("{0:.2f}".format(value * 39.3))
    

  elif units == 34: #//="34">Miles</option>
      return float("{0:.2f}".format(value * 0.000621371))              

  elif units == 35: #//="35">Nautical Mile</option>
      return float("{0:.2f}".format(value * 0.0005399568))                
  
  elif units == 36: #//="36">Fathoms</option>
      return float("{0:.2f}".format(value * 0.546806649))


  elif units == 37: #//="37">Time</option>
      #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))
      return (datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))

  elif units == 38: #//="38">Date/time</option>
      #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
      return (datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
    
  elif units == 39: #//="39">Hours</option>
    #Engine Hours (value / (60*60))
    return float("{0:.2f}".format(value * 0.000277777))

  elif units == 43: #//="43">Volts 10</option>
    return float("{0:.2f}".format(value * 0.1))

  else:
      return float("{0:.2f}".format(value * 1.0))

def getepochtimes(Interval):

    epochtimes=[]
    starttime = 0

    
    try:
        # if 0 then use current time 
        if starttime == 0:
            nowtime = datetime.datetime.now()
            endepoch =  int(time.time())

            if Interval== "1min":
                resolution = 60
                startepoch = endepoch - (resolution * 2)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=2)
            elif Interval == "2min":
                resolution = 60*2
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=3)                
            elif Interval == "5min":
                resolution = 60*5
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=5)
            elif Interval== "10min":
                resolution = 60*10
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=10)
            elif Interval == "15min":
                resolution = 60*15
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=15)
            elif Interval== "30min":
                resolution = 60*30
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=30)
            elif Interval== "1hour":
                resolution = 60*60
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(hours=1)
            elif Interval == "4hour":
                resolution = 60*60*4
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(hours=4)
            elif Interval == "6hour":
                resolution = 60*60*6
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(hours=6)
            elif Interval == "8hour":
                resolution = 60*60*8
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(hours=8)
            elif Interval == "12hour":
                resolution = 60*60*12
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(hours=12)
            elif Interval == "1day":
                resolution = 60*60*24
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(days=1)
            elif Interval == "2day":
                resolution = 60*60*24*2
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(days=2)                
            elif Interval== "7day":
                resolution = 60*60*24*7
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(days=7)
            elif Interval == "1month":
                resolution = 60*60*24*30
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(months=1)
            else:
                resolution = 60
                startepoch = endepoch - (resolution * 1)
                oldtime = datetime.datetime.now() - datetime.timedelta(minutes=2)

                
        epochtimes.append(startepoch)
        epochtimes.append(endepoch)
        epochtimes.append(resolution)

    except TypeError, e:
        log.info('freeboard: TypeError in geting Interval parameters %s:  ', Interval)
        log.info('freeboard: TypeError in geting Interval parameters %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: KeyError in geting Interval parameters %s:  ', Interval)
        log.info('freeboard: KeyError in geting Interval parameters %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: NameError in geting Interval parameters %s:  ', Interval)
        log.info('freeboard: NameError in geting Interval parameters %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: IndexError in geting Interval parameters %s:  ', Interval)
        log.info('freeboard: IndexError in geting Interval parameters %s:  ' % str(e))  


    except:
        log.info('freeboard: Error in geting  Intervalparameters %s:  ', Interval)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting Interval parameters %s:  ' % str(e))

    return(epochtimes)

def convert_influxdbcloud_json(key, mytime, value):

  try:

    mydtt = time.strptime(mytime, "%Y-%m-%d %H:%M:%S")    
    #mydtt = datetime.strptime(mytime, "%Y-%m-%d %H:%M:%S")
    #"2009-11-10T23:00:00Z"
    #dtt = mytime.timetuple()
    ts = int(mktime(mydtt) * 1000)
    #ts = mytime.replace(' ','T')
    #ts = ts + 'Z'


    

    tagpairs = key.split(".")
    log.info('freeboard: convert_influxdbcloud_json tagpairs %s:  ', tagpairs)

    myjsonkeys={}

    tag0 = tagpairs[0].split(":")
    tag1 = tagpairs[1].split(":")
    tag2 = tagpairs[2].split(":")
    tag3 = tagpairs[3].split(":")
    tag4 = tagpairs[4].split(":")
    tag5 = tagpairs[5].split(":")

    #"deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:temperature.HelmSmart"
    myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':tag5[1]}
    log.info('freeboard: convert_influxdbcloud_json tagpairs %s:  ', myjsonkeys)

    values = {'value':value}

    ifluxjson ={"measurement":tagpairs[6], "time": ts, "tags":myjsonkeys, "fields": values}
    log.info('freeboard: convert_influxdbcloud_json %s:  ', ifluxjson)

    return ifluxjson

  except AttributeError, e:
    if debug_all: log.info('Sync: AttributeError in convert_influxdbcloud_json %s:  ', mytime)
    #e = sys.exc_info()[0]

    if debug_all: log.info('Sync: AttributeError in convert_influxdbcloud_json %s:  ' % str(e))
    
  except TypeError, e:
    if debug_all: log.info('Sync: TypeError in convert_influxdbcloud_json %s:  ', mytime)
    #e = sys.exc_info()[0]

    if debug_all: log.info('Sync: TypeError in convert_influxdbcloud_json %s:  ' % str(e))
    
  except NameError, e:
    if debug_all: log.info('Sync: NameError in convert_influxdbcloud_json %s:  ', mytime)
    #e = sys.exc_info()[0]

    if debug_all: log.info('Sync: NameError in convert_influxdbcloud_json %s:  ' % str(e))
    
  except:
    if debug_all: log.info('Sync: Error convert_influxdbcloud_json %s:', mytime)

    e = sys.exc_info()[0]
    if debug_all: log.info("Sync.py Error in convert_influxdbcloud_json: %s" % e)


def getdashboardlists(userid):


    conn = db_pool.getconn()

    log.info("freeboard getdashboardlists data Query %s", userid)

    try:
    # first check db to see if deviceapikey is matched to device id

        cursor = conn.cursor()

        cursor.execute("select prefuid, prefname  from dashboard_prefs where userid = %s" , (userid,))

        #log.info("freeboard getdashboardlists response %s", cursor)            

        # see we got any matches
        if cursor.rowcount == 0:
            return jsonify( message='Could not get prefuids', status='error')
            db_pool.putconn(conn) 
            return ""
        
        else:
          preferences = [dict((cursor.description[i][0], value) \
            for i, value in enumerate(row)) for row in cursor.fetchall()]

          log.info("freeboard getdashboardlists response %s", preferences)     
          db_pool.putconn(conn) 
          return preferences


    except TypeError, e:
        log.info('freeboard: getdashboardlists TypeError in geting deviceid  %s:  ', userid)
        log.info('freeboard: getdashboardlists TypeError in geting deviceid  %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: getdashboardlists KeyError in geting deviceid  %s:  ', userid)
        log.info('freeboard: getdashboardlists KeyError in geting deviceid  %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: getdashboardlists NameError in geting deviceid  %s:  ', userid)
        log.info('freeboard: getdashboardlists NameError in geting deviceid  %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: getdashboardlists IndexError in geting deviceid  %s:  ', userid)
        log.info('freeboard: getdashboardlists IndexError in geting deviceid  %s:  ' % str(e))  


    except:
        log.info('freeboard: getdashboardlists Error in geting  deviceid %s:  ', userid)
        e = sys.exc_info()[0]
        log.info('freeboard: getdashboardlists Error in geting deviceid  %s:  ' % str(e))

    # cursor.close
    db_pool.putconn(conn)                       

    return ""  

def getdashboardjson(prefuid):


    conn = db_pool.getconn()

    log.info("freeboard getdashboardjson data Query %s", prefuid)

    try:
    # first check db to see if deviceapikey is matched to device id

        cursor = conn.cursor()
        #cursor.execute(query, (deviceapikey,))
        #cursor.execute("select deviceid from user_devices where deviceapikey = '%s'" % deviceapikey)
        #key=('bfeba0c3c5244269b4c8d276872519a6',)
        cursor.execute("select jsondata  from dashboard_prefs where prefuid = %s" , (prefuid,))
        #response= cursor.query(query)
        i = cursor.fetchone()
        log.info("freeboard getdashboardjson response %s", i)            
        # see we got any matches
        if cursor.rowcount == 0:
        #if not response:
            # cursor.close
            db_pool.putconn(conn) 
            return ""
        
        else:
            jsondata = str(i[0])
            db_pool.putconn(conn) 
            return jsondata 


    except TypeError, e:
        log.info('freeboard: getdashboardjson TypeError in geting deviceid  %s:  ', prefuid)
        log.info('freeboard: getdashboardjson TypeError in geting deviceid  %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: getdashboardjson KeyError in geting deviceid  %s:  ', prefuid)
        log.info('freeboard: getdashboardjson KeyError in geting deviceid  %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: getdashboardjson NameError in geting deviceid  %s:  ', prefuid)
        log.info('freeboard: getdashboardjson NameError in geting deviceid  %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: getdashboardjson IndexError in geting deviceid  %s:  ', prefuid)
        log.info('freeboard: getdashboardjson IndexError in geting deviceid  %s:  ' % str(e))  


    except:
        log.info('freeboard: getdashboardjson Error in geting  deviceid %s:  ', prefuid)
        e = sys.exc_info()[0]
        log.info('freeboard: getdashboardjson Error in geting deviceid  %s:  ' % str(e))

    # cursor.close
    db_pool.putconn(conn)                       

    return ""  



def getedeviceid(deviceapikey):

    conn = db_pool.getconn()

    log.info("freeboard getedeviceid data Query %s", deviceapikey)
    #query = "select deviceid from user_devices where deviceapikey = %s"

    #query = ("select deviceid from user_devices where deviceapikey = '{}' ") \
    #            .format(deviceapikey )


    #log.info("freeboard getedeviceid Query %s", query)


    try:
    # first check db to see if deviceapikey is matched to device id

        cursor = conn.cursor()
        #cursor.execute(query, (deviceapikey,))
        #cursor.execute("select deviceid from user_devices where deviceapikey = '%s'" % deviceapikey)
        #key=('bfeba0c3c5244269b4c8d276872519a6',)
        cursor.execute("select deviceid from user_devices where deviceapikey = %s" , (deviceapikey,))
        #response= cursor.query(query)
        i = cursor.fetchone()
        log.info("freeboard getedeviceid response %s", i)            
        # see we got any matches
        if cursor.rowcount == 0:
        #if not response:
            # cursor.close
            db_pool.putconn(conn) 
            return ""
        
        else:
            deviceid = str(i[0])
            db_pool.putconn(conn) 
            return deviceid 


    except TypeError, e:
        log.info('freeboard: TypeError in geting deviceid  %s:  ', deviceapikey)
        log.info('freeboard: TypeError in geting deviceid  %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: KeyError in geting deviceid  %s:  ', deviceapikey)
        log.info('freeboard: KeyError in geting deviceid  %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: NameError in geting deviceid  %s:  ', deviceapikey)
        log.info('freeboard: NameError in geting deviceid  %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: IndexError in geting deviceid  %s:  ', deviceapikey)
        log.info('freeboard: IndexError in geting deviceid  %s:  ' % str(e))  


    except:
        log.info('freeboard: Error in geting  deviceid %s:  ', deviceapikey)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting deviceid  %s:  ' % str(e))

    # cursor.close
    db_pool.putconn(conn)                       

    return ""



def getedevicename(deviceapikey):

    conn = db_pool.getconn()

    log.info("freeboard getedevicename data Query %s", deviceapikey)
    #query = "select deviceid from user_devices where deviceapikey = %s"

    #query = ("select deviceid from user_devices where deviceapikey = '{}' ") \
    #            .format(deviceapikey )


    #log.info("freeboard getedeviceid Query %s", query)


    try:
    # first check db to see if deviceapikey is matched to device id

        cursor = conn.cursor()
        #cursor.execute(query, (deviceapikey,))
        #cursor.execute("select deviceid from user_devices where deviceapikey = '%s'" % deviceapikey)
        #key=('bfeba0c3c5244269b4c8d276872519a6',)
        cursor.execute("select devicename from user_devices where deviceapikey = %s" , (deviceapikey,))
        #response= cursor.query(query)
        i = cursor.fetchone()
        log.info("freeboard getedevicename response %s", i)            
        # see we got any matches
        if cursor.rowcount == 0:
        #if not response:
            # cursor.close
            db_pool.putconn(conn) 
            return ""
        
        else:
            devicename = str(i[0])
            db_pool.putconn(conn) 
            return devicename 


    except TypeError, e:
        log.info('freeboard: TypeError in geting devicename  %s:  ', deviceapikey)
        log.info('freeboard: TypeError in geting devicename  %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: KeyError in geting devicename  %s:  ', deviceapikey)
        log.info('freeboard: KeyError in geting devicename  %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: NameError in geting devicename  %s:  ', deviceapikey)
        log.info('freeboard: NameError in geting devicename  %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: IndexError in geting devicename  %s:  ', deviceapikey)
        log.info('freeboard: IndexError in geting devicename  %s:  ' % str(e))  


    except:
        log.info('freeboard: Error in geting  devicename %s:  ', deviceapikey)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting devicename  %s:  ' % str(e))

    # cursor.close
    db_pool.putconn(conn)                       

    return ""




def getuseremail(deviceapikey):

    conn = db_pool.getconn()

    log.info("freeboard getuseremail data Query %s", deviceapikey)
    #query = "select deviceid from user_devices where deviceapikey = %s"

    #query = ("select deviceid from user_devices where deviceapikey = '{}' ") \
    #            .format(deviceapikey )


    #log.info("freeboard getedeviceid Query %s", query)


    try:
    # first check db to see if deviceapikey is matched to device id

        cursor = conn.cursor()
        #cursor.execute(query, (deviceapikey,))
        #cursor.execute("select deviceid from user_devices where deviceapikey = '%s'" % deviceapikey)
        #key=('bfeba0c3c5244269b4c8d276872519a6',)
        cursor.execute("select useremail from user_devices where deviceapikey = %s" , (deviceapikey,))
        #response= cursor.query(query)
        i = cursor.fetchone()
        log.info("freeboard getuseremail response %s", i)            
        # see we got any matches
        if cursor.rowcount == 0:
        #if not response:
            # cursor.close
            db_pool.putconn(conn) 
            return ""
        
        else:
            useremail = str(i[0])
            db_pool.putconn(conn) 
            return useremail 


    except TypeError, e:
        log.info('freeboard: TypeError in geting useremail  %s:  ', deviceapikey)
        log.info('freeboard: TypeError in geting deviceid  %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: KeyError in geting useremail  %s:  ', deviceapikey)
        log.info('freeboard: KeyError in geting useremail  %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: NameError in geting useremail  %s:  ', deviceapikey)
        log.info('freeboard: NameError in geting useremail  %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: IndexError in geting useremail  %s:  ', deviceapikey)
        log.info('freeboard: IndexError in geting useremail  %s:  ' % str(e))  


    except:
        log.info('freeboard: Error in geting  useremail %s:  ', deviceapikey)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting useremail  %s:  ' % str(e))

    # cursor.close
    db_pool.putconn(conn)                       

    return ""

  

@app.route('/freeboard_test/<apikey>', methods=['GET','POST'])
@cross_origin()
def freeboard_test(apikey):

    deviceapikey =apikey
    Interval = "1min"
     
    #deviceapikey = request.args.get('apikey','')
    #serieskey = request.args.get('datakey','')
    #Interval = request.args.get('Interval',"1min")

    return jsonify(result="OK")


@app.route('/devices/<device_id>/PushCache/<partition>', methods=['POST'])
@cross_origin()
def events_endpoint(device_id, partition):
  #log.info("partition: %s", partition )
  #log.info("content_type: %s", request.content_type )
  #log.info("data: %s", request.data)
  try:
    
    log.info("Que SQS:device_id %s: %s ", device_id, partition)
    log.info("Que SQS:data recieved %s ", len(request.data))
  #log.info("data: %s", request.data)
    epochtime =  int(time.time())
    return jsonify(result="OK", epochtime=epochtime)

  except TypeError, e:
    log.info('freeboard: TypeError in geting deviceid  %s:  ', device_id)
    log.info('freeboard: TypeError in geting deviceid  %s:  ' % str(e))

  except ValueError, e:
    log.info('freeboard: ValueError in geting deviceid  %s:  ', device_id)
    log.info('freeboard: ValueError in geting deviceid  %s:  ' % str(e))
    
  except KeyError, e:
    log.info('freeboard: KeyError in geting deviceid  %s:  ', device_id)
    log.info('freeboard: KeyError in geting deviceid  %s:  ' % str(e))

  except NameError, e:
    log.info('freeboard: NameError in geting deviceid  %s:  ', device_id)
    log.info('freeboard: NameError in geting deviceid  %s:  ' % str(e))
        
  except IndexError, e:
    log.info('freeboard: IndexError in geting deviceid  %s:  ', device_id)
    log.info('freeboard: IndexError in geting deviceid  %s:  ' % str(e))  


  except:
    log.info('freeboard: Error in geting  deviceid %s:  ', device_id)
    e = sys.exc_info()[0]
    log.info('freeboard: Error in geting deviceid  %s:  ' % str(e))


  
@app.route('/freeboard_savedashboardjson' , methods=['POST'])
@cross_origin()
def freeboard_savedashboardjson():
  conn = db_pool.getconn()
  
  prefuid = request.args.get('prefuid',1)
  log.info('freeboard_savedashboardjson: prefuid  %s:  ', prefuid)

  
  mymessage = request.data
  #mymessage = json.loads(request.data)
  log.info('freeboard_savedashboardjson: json data  %s:  ', mymessage)

  try:
    cursor = conn.cursor()
    sqlstr = " update dashboard_prefs SET jsondata =%s where  prefuid = %s;" 
    cursor.execute(sqlstr, (mymessage, prefuid, ))   
    conn.commit()
    
    return jsonify(result="OK")  


  except psycopg2.ProgrammingError, e:
    log.info('freeboard_savedashboardjson: ProgrammingError in  update pref %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: ProgrammingError in  update pref  %s:  ' % str(e))
    return jsonify(result="ProgrammingError error")

  except psycopg2.DataError, e:
    log.info('freeboard_savedashboardjson: DataError in  update pref %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: DataError in  update pref  %s:  ' % str(e))
    return jsonify(result="DataError error")
  
  except TypeError, e:
    log.info('freeboard_savedashboardjson: TypeError in  update pref %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: TypeError in  update pref  %s:  ' % str(e))

  except ValueError, e:
    log.info('freeboard_savedashboardjson: ValueError in  update pref  %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: ValueError in  update pref %s:  ' % str(e))
    
  except KeyError, e:
    log.info('freeboard_savedashboardjson: KeyError in  update pref  %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: KeyError in  update pref  %s:  ' % str(e))

  except NameError, e:
    log.info('freeboard_savedashboardjson: NameError in  update pref  %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: NameError in  update pref %s:  ' % str(e))
        
  except IndexError, e:
    log.info('freeboard_savedashboardjson: IndexError in  update pref  %s:  ', prefuid)
    log.info('freeboard_savedashboardjson: IndexError in  update pref  %s:  ' % str(e))  


  except:
    e = sys.exc_info()[0]
    log.info('freeboard_savedashboardjson: Error in update pref  %s:  ' % str(e))
    return jsonify(result="error") 

  
  finally:
    db_pool.putconn(conn)

@app.route('/freeboard_deletedashboard')
@cross_origin()
def freeboard_deletedashboard():
  conn = db_pool.getconn()
  

  prefuid = request.args.get('prefuid',1)



  log.info('freeboard_deletedashboard: prefuid  %s:  ', prefuid)
  


  try:
    cursor = conn.cursor()
    
    sqlstr = "delete from dashboard_prefs where prefuid = %s;"
                                                                                    
    cursor.execute(sqlstr, (prefuid,))   
    conn.commit()
    
    return jsonify(result="OK")  


  except psycopg2.ProgrammingError, e:
    log.info('freeboard_deletedashboard: ProgrammingError in  edit pref %s:  ', prefuid)
    log.info('freeboard_deletedashboard: ProgrammingError in  edit pref  %s:  ' % str(e))
    return jsonify(result="ProgrammingError error")
  
  except TypeError, e:
    log.info('freeboard_editdashboard: TypeError in  edit pref %s:  ', prefuid)
    log.info('freeboard_editdashboard: TypeError in  edit pref  %s:  ' % str(e))

  except ValueError, e:
    log.info('freeboard_deletedashboard: ValueError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_deletedashboard: ValueError in  edit pref %s:  ' % str(e))
    
  except KeyError, e:
    log.info('freeboard_deletedashboard: KeyError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_deletedashboard: KeyError in  edit pref  %s:  ' % str(e))

  except NameError, e:
    log.info('freeboard_deletedashboard: NameError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_deletedashboard: NameError in  edit pref %s:  ' % str(e))
        
  except IndexError, e:
    log.info('freeboard_deletedashboard: IndexError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_deletedashboard: IndexError in  edit pref  %s:  ' % str(e))  


  except:
    e = sys.exc_info()[0]
    log.info('freeboard_deletedashboard: Error in edit pref  %s:  ' % str(e))
    return jsonify(result="error") 

  
  finally:
    db_pool.putconn(conn)


    

@app.route('/freeboard_editdashboard')
@cross_origin()
def freeboard_editdashboard():
  conn = db_pool.getconn()
  

  prefname = request.args.get('prefname',1)
  prefuid = request.args.get('prefuid',1)


  

  log.info('freeboard_editdashboard: prefname  %s:  ', prefname)
  log.info('freeboard_editdashboard: prefuid  %s:  ', prefuid)
  


  try:
    cursor = conn.cursor()
    
    sqlstr = "update dashboard_prefs set prefname = %s where prefuid = %s;"
                                                                                    
    cursor.execute(sqlstr, (prefname, prefuid))   
    conn.commit()
    
    return jsonify(result="OK")  


  except psycopg2.ProgrammingError, e:
    log.info('freeboard_editdashboard: ProgrammingError in  edit pref %s:  ', prefuid)
    log.info('freeboard_editdashboard: ProgrammingError in  edit pref  %s:  ' % str(e))
    return jsonify(result="ProgrammingError error")
  
  except TypeError, e:
    log.info('freeboard_editdashboard: TypeError in  edit pref %s:  ', prefuid)
    log.info('freeboard_editdashboard: TypeError in  edit pref  %s:  ' % str(e))

  except ValueError, e:
    log.info('freeboard_editdashboard: ValueError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_editdashboard: ValueError in  edit pref %s:  ' % str(e))
    
  except KeyError, e:
    log.info('freeboard_editdashboard: KeyError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_editdashboard: KeyError in  edit pref  %s:  ' % str(e))

  except NameError, e:
    log.info('freeboard_editdashboard: NameError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_editdashboard: NameError in  edit pref %s:  ' % str(e))
        
  except IndexError, e:
    log.info('freeboard_editdashboard: IndexError in  edit pref  %s:  ', prefuid)
    log.info('freeboard_editdashboard: IndexError in  edit pref  %s:  ' % str(e))  


  except:
    e = sys.exc_info()[0]
    log.info('freeboard_editdashboard: Error in edit pref  %s:  ' % str(e))
    return jsonify(result="error") 

  
  finally:
    db_pool.putconn(conn)



    
@app.route('/freeboard_addnewdashboard')
@cross_origin()
def freeboard_addnewdashboard():
  conn = db_pool.getconn()
  
  userid = request.args.get('userid',1)
  useremail = request.args.get('useremail',1)
  prefname = request.args.get('prefname',1)

  defaultjson = '{"version": 1,"allow_edit": true}'
  
  log.info('freeboard_addnewdashboard: userid  %s:  ', userid)
  log.info('freeboard_addnewdashboard: useremail  %s:  ', useremail)
  log.info('freeboard_addnewdashboard: prefname  %s:  ', prefname)
  
  prefuid=hash_string(useremail+prefname)
  log.info('freeboard_addnewdashboard: prefuid  %s:  ', prefuid)

  try:
    cursor = conn.cursor()
    
    sqlstr = " insert into dashboard_prefs (prefuid, userid, useremail, prefname, jsondata ) Values (%s,%s,%s,%s,%s);"
                                                                                    
    cursor.execute(sqlstr, (prefuid, userid, useremail, prefname, defaultjson))   
    conn.commit()
    
    return jsonify(result="OK")  


  except psycopg2.ProgrammingError, e:
    log.info('freeboard_addnewdashboard: ProgrammingError in  update pref %s:  ', userid)
    log.info('freeboard_addnewdashboard: ProgrammingError in  update pref  %s:  ' % str(e))
    return jsonify(result="ProgrammingError error")
  
  except TypeError, e:
    log.info('freeboard_addnewdashboard: TypeError in  update pref %s:  ', userid)
    log.info('freeboard_addnewdashboard: TypeError in  update pref  %s:  ' % str(e))

  except ValueError, e:
    log.info('freeboard_addnewdashboard: ValueError in  update pref  %s:  ', userid)
    log.info('freeboard_addnewdashboard: ValueError in  update pref %s:  ' % str(e))
    
  except KeyError, e:
    log.info('freeboard_addnewdashboard: KeyError in  update pref  %s:  ', userid)
    log.info('freeboard_addnewdashboard: KeyError in  update pref  %s:  ' % str(e))

  except NameError, e:
    log.info('freeboard_addnewdashboard: NameError in  update pref  %s:  ', userid)
    log.info('freeboard_addnewdashboard: NameError in  update pref %s:  ' % str(e))
        
  except IndexError, e:
    log.info('freeboard_addnewdashboard: IndexError in  update pref  %s:  ', userid)
    log.info('freeboard_addnewdashboard: IndexError in  update pref  %s:  ' % str(e))  


  except:
    e = sys.exc_info()[0]
    log.info('freeboard_addnewdashboard: Error in update pref  %s:  ' % str(e))
    return jsonify(result="error") 

  
  finally:
    db_pool.putconn(conn)


    
@app.route('/freeboard_getdashboardjson')
@cross_origin()
def freeboard_getdashboardjson():

  prefuid = request.args.get('prefuid',1)


  dashboardjson = getdashboardjson(prefuid)
  
  log.info("freeboard_GetDashboardJSON prefuid %s -> %s", prefuid, dashboardjson)


  #return dashboardjson  
  #  result = json.dumps(r, cls=DateEncoder)

  response = make_response(dashboardjson)
  response.headers['Cache-Control'] = 'public, max-age=0'
  response.headers['content-type'] = "application/json"
  return response


@app.route('/freeboard_getdashboardlist')
@cross_origin()
def freeboard_getdashboardlist():

  userid = request.args.get('userid',1)


  dashboardlists = getdashboardlists(userid)
  
  log.info("freeboard_GetDashboardJSON prefuid %s -> %s", userid, dashboardlists)


  return jsonify({'preferences':dashboardlists})
  #  result = json.dumps(r, cls=DateEncoder)

  #response = make_response(dashboardlists)
  #response.headers['Cache-Control'] = 'public, max-age=0'
  #response.headers['content-type'] = "application/json"
  #return response




@app.route('/help')
@cross_origin()
def help():

    response = make_response(render_template('index.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response



@app.route('/callback')
def callback_handling():
    code = request.args.get('code')
    get_token = GetToken(AUTH0_DOMAIN)
    auth0_users = Users(AUTH0_DOMAIN)
    token = get_token.authorization_code(AUTH0_CLIENT_ID,
                                         AUTH0_CLIENT_SECRET, code, AUTH0_CALLBACK_URL)
    user_info = auth0_users.userinfo(token['access_token'])
    log.info('auth0callback: user_info %s:  ' , user_info)



    try:
      #session['profile'] = json.loads(user_info)
      user_info_json = json.dumps(user_info)
      log.info('auth0callback: TypeError in user_info %s:  ', user_info_json)
      
      session['profile'] =json.loads(user_info_json)
      log.info('auth0callback: TypeError in session user_info %s:  ', session)
      
    except TypeError, e:
      log.info('auth0callback: TypeError in user_info %s:  ', user_info_json)
      #e = sys.exc_info()[0]

      log.info('auth0callback: TypeError in user_info %s:  ' % str(e))
      
    except:
      e = sys.exc_info()[0]
      log.info('auth0callback: Error in geting username  %s:  ' % str(e))
    
 

    
    
    if 'profile' in session:
      try:
        mydata = session['profile']   
        log.info("authcallback: customdata:%s", mydata)

        if 'name' in mydata:
          myusername = mydata['name']
          session['username'] = myusername
          log.info("authcallback: username:%s", myusername)

      except TypeError, e:
        log.info('auth0callback: TypeError in customdata %s:  ', mydata)
        #e = sys.exc_info()[0]
          
      except:
        e = sys.exc_info()[0]
        log.info('auth0callback: Error in geting username  %s:  ' % str(e))
        pass

        
    return redirect('/dashboards_list')

@app.route('/auth0logout')
def auth0logout():
    session.clear()
    log.info('auth0logout: AUTH0_CALLBACK_URL %s:  ' , AUTH0_CALLBACK_URL)
    parsed_base_url = urlparse(AUTH0_CALLBACK_URL)
    #base_url = parsed_base_url.scheme + '://' + parsed_base_url.netloc
    base_url = 'http://' + parsed_base_url.netloc
    log.info('auth0logout: base_url %s:  ' , base_url)
    
    log.info('auth0logout: https://%s/v2/logout?returnTo=%s&client_id=%s' % (AUTH0_DOMAIN, base_url, AUTH0_CLIENT_ID))
    #return jsonify(status='ok' )
      
    return redirect('https://%s/v2/logout?returnTo=%s&client_id=%s' % (AUTH0_DOMAIN, base_url, AUTH0_CLIENT_ID))
  






@app.route('/login')
@cross_origin()
#@login_required
def login():

    #response = make_response(render_template('index.html', features = []))
    #response.headers['Cache-Control'] = 'public, max-age=0'
    #return response
  
    response = make_response(render_template('freeboard.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    #response.headers['Cache-Control'] = 'public, no-cache, no-store, max-age=0'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response  
  
@app.route('/freeboard')
@cross_origin()
def freeboard():

    response = make_response(render_template('freeboard.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    #response.headers['Cache-Control'] = 'public, no-cache, no-store, max-age=0'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/dashboards')
@cross_origin()
def dashboards():



    response = make_response(render_template('dashboards.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    #response.headers['Cache-Control'] = 'public, no-cache, no-store, max-age=0'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
  

@app.route('/dashboard')
#@login_required
@cross_origin()
#@requires_auth
def dashboard():


    try:
      
      if session['profile'] is not None:
        
        try:
          mydata = session['profile']
          log.info("dashboard: customdata:%s", mydata)
          
        
          if mydata is not None:
            user_email = mydata['name']
            log.info("dashboard.html: user exists:%s", user_email)
           
        except:
          e = sys.exc_info()[0]
          log.info('dashboard.html: Error in geting user.custom_data  %s:  ' % str(e))
          return render_template('dashboards_list.html', user=session['profile'], env=env) 

        try:
          if user_email is not None:

            conn = db_pool.getconn()
            session['username'] = user_email
            
            log.info("dashboard.html: email:%s", user_email )

            query = "select userid from user_devices where useremail = %s group by userid"
            
            cursor = conn.cursor()
            cursor.execute(query, [user_email])
            i = cursor.fetchone()       
            if cursor.rowcount > 0:

                session['userid'] = str(i[0])
                #session['adminid'] = verificationdata['email']
            else:
                session['userid'] = hash_string('helmsmart@mockmyid.com')

            # cursor.close
            db_pool.putconn(conn)

            log.info("dashboard.html: userid:%s", session['userid'])

            response = make_response(render_template('dashboard.html', features = []))
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            return response
  
        except:
          e = sys.exc_info()[0]
          log.info('dashboard.html: Error in geting user_email  %s:  ' % str(e))
          pass
          
    except:
      e = sys.exc_info()[0]
      log.info('dashboard.html: Error in geting user  %s:  ' % str(e))
      pass


    return render_template('dashboards_list.html', user=session['profile'], env=env) 

#mydatetimestr = str(point['time'])
#mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

#mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
#mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))
    
#dtt = mydatetimetz.timetuple()
#ts = int(mktime(dtt)*1000)

  
def convert_to_time_ms(timestamp):
    return 1000 * timegm( datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').timetuple())



@app.route('/freeboad_simplejson_test/search', methods=['POST'])
@cross_origin()
def simplejson_search():
  
  #req = request.get_json()
  req="something"
  log.info("simplejson_search: req:%s", req)
  
  return jsonify(['ac_line_neutral_volts', 'ac_amps', 'ac_watts'])

@app.route('/freeboad_simplejson_test/query', methods=['POST'])
@cross_origin()
def simplejson_query():

  #log.info("simplejson_query.authorization: %s", request.authorization)
  log.info("simplejson_query.authorization username: %s", request.authorization.username)


  #deviceapikey = request.args.get('apikey','')
  #serieskey = request.args.get('datakey','')
  #Interval = request.args.get('interval',"5min")
  #Instance = request.args.get('instance','0')
  #resolution = request.args.get('resolution',"")
  #actype = request.args.get('type','UTIL')
  #mytimezone = request.args.get('timezone',"UTC")
  #mode = request.args.get('mode',"mean")

  mode = "median"
  Interval = "6hour"
  Instance = "0"
  resolution = 60
  actype = 'GEN'
  mytimezone = "UTC"

  
  #req = request.get_json()
  req="something"
  log.info("simplejson_query: req:%s", request.get_json())

  req = request.get_json()
  targets = req['targets']

  acphases  = []
  actypes = []

  
  for target in targets:
    search_key =  target.get("target","ac_amps")
    # this may not exist
    targetdata = target.get("data")
    log.info("freeboard targetdata %s", targetdata)
    #acphases.append(targetdata.get("acphase","0"))
    #actypes.append(targetdata.get("actype","GEN"))
    
    try:
      #acphases=targetdata["acphase"]
      log.info("freeboard acphase1 %s", targetdata['acphase'])
      myacphases = json.loads(targetdata['acphase'])
      
      log.info("freeboard acphase2 %s", targetdata['acphase'])
      #for acphase in myacphases:
      for acphase in json.loads(targetdata['acphase']):
        
        log.info("freeboard acphase3 %s",acphase)
        acphases.append(acphase)

        
      log.info("freeboard acphase4 %s", acphases)

        


    except TypeError, e:
      #log.info('dashboards_list: TypeError in  update pref %s:  ', userid)
      log.info('acphase1: TypeError in  update pref  %s:  ' % str(e))

    except ValueError, e:
      #log.info('dashboards_list: ValueError in  update pref  %s:  ', userid)
      log.info('acphase1: ValueError in  update pref %s:  ' % str(e))
      
    except KeyError, e:
      #log.info('dashboards_list: KeyError in  update pref  %s:  ', userid)
      log.info('acphase1: KeyError in  update pref  %s:  ' % str(e))

    except NameError, e:
      #log.info('dashboards_list: NameError in  update pref  %s:  ', userid)
      log.info('acphase1: NameError in  update pref %s:  ' % str(e))
          
    except IndexError, e:
      #log.info('dashboards_list: IndexError in  update pref  %s:  ', userid)
      log.info('acphase1: IndexError in  update pref  %s:  ' % str(e))  

    except:
      e = sys.exc_info()[0]
      log.info('acphase1.html: Error in geting user  %s:  ' % str(e))
      acphases.append("2")
      pass




      
      
    try:
      #actypes=targetdata["actype"]
      for actype in  json.loads(targetdata['actype']):
        actypes.append(actype)

               
    except:
      actypes.append("GEN") 


    log.info("freeboard acphases %s", acphases)
    log.info("freeboard actypes %s", actypes)

    
    actype = actypes[0]
    Instance = acphases[0]

  log.info("freeboard search_key %s", search_key)


  """
  adhocFilters =  req['adhocFilters']

  for adhocFilter in adhocFilters:
    
    if adhocFilter['key'] == 'Type':
      actype = adhocFilter['value']

    elif adhocFilter['key'] == 'Phase':   
      Instance = str(int(adhocFilter['value']) - 1)


  adhocFilters =  req['adhocFilters']

  for adhocFilter in adhocFilters:
    
    if adhocFilter['key'] == 'Type':
      actype = adhocFilter['value']

    elif adhocFilter['key'] == 'Phase':   
      Instance = str(int(adhocFilter['value']) - 1)
  """

     
  log.info("simplejson_query: actype:%s", actype)
  log.info("simplejson_query: Instance:%s",Instance)


  rangeRaw = req['rangeRaw']

  rangeFrom = rangeRaw['from']
  rangeTo = rangeRaw['to']

  log.info("simplejson_query: rangeFrom:%s rangeTo %s",rangeFrom,  rangeTo)

  Interval = req['interval']  


  log.info("simplejson_query: Interval:%s  ",Interval)

  queryRange = req['range']
  queryFrom = queryRange['from']  
  queryTo = queryRange['to']

  log.info("simplejson_query: queryFrom:%s queryTo %s",queryFrom,  queryTo)
  
  Interval = "6hour"

  
  #deviceapikey= "fa876d387ee521bd79aac4c0092cd7d0"
  deviceapikey= request.authorization.username
  
  response = None
  
  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  if resolution == "":
    resolution = epochtimes[2]


  deviceid = getedeviceid(deviceapikey)
  
  log.info("freeboard deviceid %s", deviceid)

  if deviceid == "":
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


  host = 'hilldale-670d9ee3.influxcloud.net' 
  port = 8086
  username = 'helmsmart'
  password = 'Salm0n16'
  database = 'pushsmart-cloud'

  measurement = "HelmSmart"
  measurement = 'HS_' + str(deviceid)

  volts=[]
  amps=[]
  power=[]
  energy=[]
  energy_caluculated=[]

  mydatetime = datetime.datetime.now()
  myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

  serieskeys=" deviceid='"
  serieskeys= serieskeys + deviceid + "' AND "
  #serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='fluid_level') AND "
  serieskeys= serieskeys +  " (sensor='ac_basic' OR sensor='ac_watthours'  ) "
  serieskeys= serieskeys +  "  AND type = '" + actype + "' AND "
  serieskeys= serieskeys +  " (instance='" + Instance + "') "
  

  dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  #if mode == "median":
    
  query = ('select  median({}) AS value FROM {} '
                   'where {} AND time > {}s and time < {}s '
                   'group by time({}s)') \
              .format( search_key, measurement, serieskeys,
                      startepoch, endepoch,
                      resolution)

  log.info("freeboard data Query %s", query)

  #try:
  response= dbc.query(query)


  if response is None:
    log.info('freeboard: InfluxDB Query has no data ')
    return jsonify({'update':'False', 'status':'no data' })

  if not response:
    log.info('freeboard: InfluxDB Query has no data ')
    return jsonify({'update':'False', 'status':'no data' })


  ts =startepoch*1000       
  points = list(response.get_points())

  #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

  values = []

  for point in points:
    
    if point['time'] is not None:
      mydatetimestr = str(point['time'])
      mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
      mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))
   
      dtt = mydatetimetz.timetuple()
      ts = int(mktime(dtt)*1000)
      
    
    if point['value'] is not None:
      #value1 = convertfbunits( point['volts'], 27)
      #value1 = point['volts'], 27)
      #value = []
      #value.append([point['value'], ts])
      value=[point['value'], ts]
      #values.append({'value': point['value'], 'epoch':ts})
      values.append(value)


  data = [{ "target": search_key, "datapoints": values}]
  
  """      
  data = [
        {
            "target": search_key,
            "datapoints": [
                [862, convert_to_time_ms(req['range']['from'])],
                [768, convert_to_time_ms(req['range']['to'])]
            ]
        }
    ]
  """
  
  return jsonify(data)
  



@app.route('/freeboad_simplejson_test/annotations', methods=['POST'])
@cross_origin()
def simplejson_annotations():
  #req = request.get_json()
  req="something"
  log.info("simplejson_query: req:%s", req)
    
  data = [
        {
            "annotation": 'This is the annotation',
            "time": (convert_to_time_ms(req['range']['from']) +
                     convert_to_time_ms(req['range']['to'])) / 2,
            "title": 'Deployment notes',
            "tags": ['tag1', 'tag2'],
            "text": 'Hm, something went wrong...'
        }
    ]
  return jsonify(data)


@app.route('/freeboad_simplejson_test/tag-keys', methods=['POST'])
@cross_origin()
def simplejson_tag_keys():
  data = [
      {"type": "string", "text": "Type"},
      {"type": "string", "text": "Phase"}
  ]
  return jsonify(data)


@app.route('/freeboad_simplejson_test/tag-values', methods=['POST'])
@cross_origin()
def simplejson_tag_values():
  req = request.get_json()
  if req['key'] == 'Type':
      return jsonify([
          {'text': 'GEN'},
          {'text': 'UTIL'}
      ])
  elif req['key'] == 'Phase':
      return jsonify([
          {'text': '1'},
          {'text': '2'},
          {'text': '3'}
      ])


@app.route('/freeboad_simplejson_test')
@cross_origin()
def freeboad_simplejson_test():
  
  #req = request.get_json()
  #deviceapikey = request.args.get('apikey','')
  #log.info("freeboad_simplejson_test: %s", request)
  #log.info("freeboad_simplejson_test: %s", request.headers)
  log.info("freeboad_simplejson_testrequest.authorization: %s", request.authorization)
  
  return jsonify([
    {
      "target":"upper_76", #The field being queried for
      "datapoints":[
        [622,1599938657000],  #Metric value as a float , unixtimestamp in milliseconds
        [365,1599938658000]
      ]
    },
    {
      "target":"upper_91",
      "datapoints":[
        [861,1599938657000],
        [767,1599938658000]
      ]
    }
  ])




  

@app.route('/')
@app.route('/dashboards_list')
@cross_origin()
def dashboards_list():

    log.info("dashboards_list.html: Start")

      
    try:
      
      if session['profile'] is not None:
        try:
          mydata = session['profile']
          log.info("dashboards_list.html: customdata:%s", mydata)
         

          if mydata['name'] is not None:
            myusername = mydata['name']
            log.info("dashboards_list.html: myusername:%s", myusername)


          """
          if mydata['devices'] is not None:
            mydevices = mydata['devices']
            log.info("index.html: mydevices:%s", mydevices)

            for device in mydevices:
              log.info("index.html: mydevice  %s:%s", device['devicename'], device['deviceid'])
          """
          
        except:
          e = sys.exc_info()[0]
          log.info('dashboards_list.html: Error in geting user.custom_data  %s:  ' % str(e))
          pass

        try:
          if myusername is not None:

            conn = db_pool.getconn()
            session['username'] = myusername
            
            log.info("dashboards_list.html: email:%s", myusername )

            query = "select userid from user_devices where useremail = %s group by userid"

            cursor = conn.cursor()
            cursor.execute(query, [myusername])
            i = cursor.fetchone()       
            if cursor.rowcount > 0:

                session['userid'] = str(i[0])
                #session['adminid'] = verificationdata['email']
            else:
                session['userid'] = hash_string('helmsmart@mockmyid.com')
                
            log.info('dashboards_list.html: userid is  %s:  ' , session['userid'] )
            # cursor.close
            db_pool.putconn(conn)
            
        except:
          e = sys.exc_info()[0]
          log.info('dashboards_list.html: Error in geting user.email  %s:  ' % str(e))
          pass


        return render_template('dashboards_list.html', user=session['profile'], env=env)

      


    except TypeError, e:
      #log.info('dashboards_list: TypeError in  update pref %s:  ', userid)
      log.info('dashboards_list: TypeError in  update pref  %s:  ' % str(e))

    except ValueError, e:
      #log.info('dashboards_list: ValueError in  update pref  %s:  ', userid)
      log.info('dashboards_list: ValueError in  update pref %s:  ' % str(e))
      
    except KeyError, e:
      #log.info('dashboards_list: KeyError in  update pref  %s:  ', userid)
      log.info('dashboards_list: KeyError in  update pref  %s:  ' % str(e))

    except NameError, e:
      #log.info('dashboards_list: NameError in  update pref  %s:  ', userid)
      log.info('dashboards_list: NameError in  update pref %s:  ' % str(e))
          
    except IndexError, e:
      #log.info('dashboards_list: IndexError in  update pref  %s:  ', userid)
      log.info('dashboards_list: IndexError in  update pref  %s:  ' % str(e))  

    except:
      e = sys.exc_info()[0]
      log.info('dashboards_list.html: Error in geting user  %s:  ' % str(e))
      pass

    
    return render_template('dashboards_list.html',  env=env)
    #response = make_response(render_template('index.html', features = []))
    #response.headers['Cache-Control'] = 'public, max-age=0'
    #return response





@app.route('/olddashboards_list')
#@login_required
@cross_origin()
#@requires_auth
def olddashboards_list():


    try:
      
      if session['profile'] is not None:
          
        try:
          mydata = session['profile']
          log.info("dashboards_list: customdata:%s", mydata)
          
        except:
          e = sys.exc_info()[0]
          log.info('dashboards_list: Error in geting user.custom_data  %s:  ' % str(e))
          pass
        
      if user is not None:
        log.info("dashboards_list.html: user exists:%s", user)
        try:
           log.info("dashboards_list.html: customdata:%s", user.custom_data)
           mydata = user.custom_data

           
           mydevices = mydata['devices']
           log.info("dashboards_list.html: mydevices:%s", mydevices)

           for device in mydevices:
             log.info("dashboards_list.html: mydevice  %s:%s", device['devicename'], device['deviceid'])
           
        except:
          e = sys.exc_info()[0]
          log.info('dashboards_list.html: Error in geting user.custom_data  %s:  ' % str(e))
          pass

        try:
          if user.email is not None:

            conn = db_pool.getconn()
            session['username'] = user.email
            
            log.info("dashboards_list.html: email:%s", user.email )

            query = "select userid from user_devices where useremail = %s group by userid"
            
            cursor = conn.cursor()
            cursor.execute(query, [user.email])
            i = cursor.fetchone()       
            if cursor.rowcount > 0:

                session['userid'] = str(i[0])
                #session['adminid'] = verificationdata['email']
            else:
                session['userid'] = hash_string('helmsmart@mockmyid.com')

            # cursor.close
            db_pool.putconn(conn)

            log.info("dashboards_list.html: email:%s", session['userid'])
            
        except:
          e = sys.exc_info()[0]
          log.info('dashboards_list.html: Error in geting user.email  %s:  ' % str(e))
          pass
          
    except:
      e = sys.exc_info()[0]
      log.info('dashboards_list.html: Error in geting user  %s:  ' % str(e))
      pass


    response = make_response(render_template('dashboards_list.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    #response.headers['Cache-Control'] = 'public, no-cache, no-store, max-age=0'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
  

@app.route('/freeboard_InfluxDB')
@cross_origin()
def freeboard_InfluxDB():
  
  host = 'hilldale-670d9ee3.influxcloud.net' 
  port = 8086
  username = 'helmsmart'
  password = 'Salm0n16'
  database = 'pushsmart-cloud'
  
  db = InfluxDBCloud(host, port, username, password, database)

@app.route('/freeboard_ImportSeries')
@cross_origin()
def freeboard_ImportSeries():

  deviceapikey = request.args.get('apikey','')
  serieskey = request.args.get('serieskey','')
  #Interval = request.args.get('Interval',"1day")
  #Instance = request.args.get('instance','0')
  #StartTime = request.args.get('start','0')
  #Repeat = int(request.args.get('repeat','1'))
  #Sensor = request.args.get('sensor','environmental_data')

  deviceid = request.args.get('deviceid', '')
  startepoch = int(request.args.get('startepoch', 0))
  endepoch = int(request.args.get('endepoch', 0))
  #query samle interval
  resolution = int(request.args.get('resolution', 60))

  response = None
  Sensor = None
    
  starttime = 0

  days = 0
  
  #maximum period to get points for = 1 day max
  period = int(60*60*24)


  periodstartepoch = endepoch - period

  tagpairs = serieskey.split(".")
  #log.info('freeboard: convert_influxdbcloud_json tagpairs %s:  ', tagpairs)

  #DeviceID
  tag0 = tagpairs[0].split(":")
  #Sensor
  tag1 = tagpairs[1].split(":")
  #Source
  tag2 = tagpairs[2].split(":")
  #Instance
  tag3 = tagpairs[3].split(":")
  #Type
  tag4 = tagpairs[4].split(":")
  #Parameter
  tag5 = tagpairs[5].split(":")

  Sensor = tag1[1]
    
  #deviceid = getedeviceid(deviceapikey)
  
  log.info("freeboard deviceid %s : Sensor %s", deviceid, Sensor)

  if deviceid == "":
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

  if Sensor == None:
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'Sensor error' })
  
  dchost = 'hilldale-670d9ee3.influxcloud.net' 
  dcport = 8086
  dcusername = 'helmsmart'
  dcpassword = 'Salm0n16'
  dcdatabase = 'pushsmart-cloud'

  measurement = "HS_" + str(deviceid)
  #epochtimes = getepochtimes(Interval)
  #startepoch = epochtimes[0]
  #endepoch = epochtimes[1]
  #resolution = epochtimes[2]


  host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
  port = 8086
  username = 'root'
  password = 'c73d5a8b1b07d17b'
  database = 'pushsmart-final'

  db = InfluxDBClient(host, port, username, password, database)
  dbc = InfluxDBCloud(dchost, dcport, dcusername, dcpassword, dcdatabase,  ssl=True)

  periodendepoch = endepoch

  while (periodstartepoch > startepoch):

    #serieskeys = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:*.type:*.parameter:*.HelmSmart'
    serieskeys = 'deviceid:' + deviceid + '.sensor:' + Sensor + '.source:*.instance:*.type:*.parameter:*.HelmSmart'

    if Sensor == 'position_rapid':
      
      gpskey = 'deviceid:' + deviceid + '.sensor:position_rapid.source:.*.instance:0.type:NULL.parameter:latlng.HelmSmart'
      
      query = ('select median(valuelat) as lat, median(valuelng) as lng from /{}/ '
                   'where time > {}s and time < {}s '
                   'group by time({}s)') \
              .format( gpskey,
                      periodstartepoch, periodendepoch,
                      resolution)
        
    elif serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select median(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        periodstartepoch, periodendepoch,
                        resolution)
    else:
        query = ('select median(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        periodstartepoch, periodendepoch,
                        resolution)


    log.info("freeboard data Query %s", query)


    response= db.query(query)

    #log.info("freeboard Get InfluxDB response %s", response)

    keys=[]
    """
    for series in response:
      log.info("influxdb response..%s", series )
      keys.append(series['name'])

    return jsonify(series = keys,  status='success')
    """
    seriescount=0
    
    for series in response:
      log.info("influxdb response..%s", series['name'] )
      seriescount = seriescount + 1
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        mytime = int(fields['time'])
        #mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        
        #mydtt = mytime.timetuple()
        #ts = int(mktime(mydtt) * 1000)
        ts = int(mytime * 1000)
        #ts = mytime.replace(' ','T')
        #ts = ts + 'Z'


        

        tagpairs = series['name'].split(".")
        #log.info('freeboard: convert_influxdbcloud_json tagpairs %s:  ', tagpairs)

        myjsonkeys={}

        tag0 = tagpairs[0].split(":")
        tag1 = tagpairs[1].split(":")
        tag2 = tagpairs[2].split(":")
        tag3 = tagpairs[3].split(":")
        tag4 = tagpairs[4].split(":")
        tag5 = tagpairs[5].split(":")

        #myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':tag5[1]}
        #log.info('freeboard: convert_influxdbcloud_json tagpairs %s:  ', myjsonkeys)

        if Sensor == 'position_rapid':
          #myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':'lat'}
          myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':'lat'}
          #values ={'lat':float(fields['lat'])}
          values ={'lat':float(fields['lat']), 'source':tag2[1]}
          #ifluxjson ={"measurement":tagpairs[6], "time": ts, "tags":myjsonkeys, "fields": values}
          ifluxjson ={"measurement":measurement, "time": ts, "tags":myjsonkeys, "fields": values}          
          #log.info('freeboard: convert_influxdbcloud_json_gps_lat %s:  ', ifluxjson)
          keys.append(ifluxjson)
          
          #myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':'lng'}
          myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':'lng'}
          #values ={'lng':float(fields['lng'])}
          values ={'lng':float(fields['lng']), 'source':tag2[1]}
          #ifluxjson ={"measurement":tagpairs[6], "time": ts, "tags":myjsonkeys, "fields": values}
          ifluxjson ={"measurement":measurement, "time": ts, "tags":myjsonkeys, "fields": values}          
          #log.info('freeboard: convert_influxdbcloud_json_gps_lng %s:  ', ifluxjson)
          keys.append(ifluxjson)

          
        else:
          #myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':tag5[1]}
          myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1],  'instance':tag3[1], 'type':tag4[1], 'parameter':tag5[1]}
          #values = {tag5[1]:float(fields['mean'])}
          values = {tag5[1]:float(fields['median']),'source':tag2[1]}
          #ifluxjson ={"measurement":tagpairs[6], "time": ts, "tags":myjsonkeys, "fields": values}
          ifluxjson ={"measurement":measurement, "time": ts, "tags":myjsonkeys, "fields": values}          
          #log.info('freeboard: convert_influxdbcloud_json %s:  ', ifluxjson)
          keys.append(ifluxjson)
        
    #return jsonify(series = keys,  status='success')
        
    log.info("freeboard Import InfluxDB series %s", seriescount)

    try:
      #dbc = InfluxDBCloud(dchost, dcport, dcusername, dcpassword, dcdatabase,  ssl=True)

      """    
      try:
        dbc.create_database(dcdatabase)
        #dbc.drop_database(dcdatabase)
      except InfluxDBClientError, e:
        log.info('freeboard_ImportInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))
        # Drop and create
        dbc.drop_database(dcdatabase)
        dbc.create_database(dcdatabase)
      """          
      #return jsonify(series = keys,  status='success')    
      """        
      for tags in keys:
        log.info('freeboard: delete tags %s:  ', tags['tags'])
        #dbc.delete_series(tags)
      """          
      #dbc.drop_database(dcdatabase)
      if debug_all: log.info('freeboard_ImportSeries:  InfluxDB-Cloud write ')
      #db.write_points_with_precision(mydata, time_precision='ms')
      dbc.write_points(keys, time_precision='ms')
      #shim.write_multi(mydata)

    #except influxdb.InfluxDBClientError as e:   
    except InfluxDBClientError as e:
      if debug_all: log.info('freeboard_ImportSeries: inFlux error in InfluxDB-Cloud write %s:  ' % str(e))
      return jsonify(count = days,  status='error')
    
    except TypeError, e:
      if debug_all: log.info('freeboard_ImportSeries: TypeError in InfluxDB-Cloud write %s:  ', keys)
      #e = sys.exc_info()[0]

      if debug_all: log.info('freeboard_ImportSeries: TypeError in InfluxDB-Cloud write %s:  ' % str(e))
      return jsonify(count = days,  status='error')
    
    except KeyError, e:
      if debug_all: log.info('freeboard_ImportSeries: KeyError in InfluxDB-Cloud write %s:  ', keys)
      #e = sys.exc_info()[0]

      if debug_all: log.info('freeboard_ImportSeries: KeyError in InfluxDB-Cloud write %s:  ' % str(e))
      return jsonify(count = days,  status='error')
    
    except NameError, e:
      if debug_all: log.info('freeboard_ImportSeries: NameError in InfluxDB-Cloud write %s:  ', keys)
      #e = sys.exc_info()[0]

      if debug_all: log.info('freeboard_ImportSeries: NameError in InfluxDB-Cloud write %s:  ' % str(e))   
      return jsonify(count = days,  status='error')      
      
    except:
      if debug_all: log.info('freeboard_ImportSeries: Error in InfluxDB-Cloud write %s:  ', keys)
      e = sys.exc_info()[0]
      if debug_all: log.info("Error: %s" % e)
      return jsonify(count = days,  status='error')

    days = days + 1

    periodendepoch = periodstartepoch
    periodstartepoch = periodendepoch - period 

  return jsonify(count = days,  status='success')
  """
  query = ("select mean(speed) as speed from HelmSmart where deviceid='001EC010AD69' and sensor='engine_parameters_rapid_update' and time > {}s and time < {}s group by time(60s)") \
        .format( startepoch, endepoch)
    

  log.info("freeboard Get InfluxDB query %s", query)

    
  result = dbc.query(query)

  log.info("freeboard Get InfluxDB results %s", result)



  return jsonify(series = keys,  status='success')
  """
  """
      seriesname = series['name']
      seriestags = seriesname.split(".")
      seriessourcetag = seriestags[2]
      seriessource = seriessourcetag.split(":")

      seriestypetag = seriestags[4]
      seriestype = seriestypetag.split(":")

      seriesparametertag = seriestags[5]
      seriesparameter = seriesparametertag.split(":")
      
      mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
      #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

      log.info('freeboard: freeboard_engine got data seriesname %s:  ', seriesname)

      if  seriesparameter[1] == 'speed':
          value1 =  fields['mean']

          
      elif  seriesparameter[1] == 'engine_temp':
          value2 =  fields['mean']

          
      elif  seriesparameter[1] == 'oil_pressure':
          value3=   fields['mean']


      elif  seriesparameter[1] == 'alternator_potential':
          value4 =  fields['mean']

          
      elif  seriesparameter[1] == 'boost_pressure':
          value5=  fields['mean']


      elif  seriesparameter[1] == 'trip_fuel_used':
          value5=  fields['mean']
          
      elif  seriesparameter[1] == 'fuel_rate':
          value6 =  fields['mean']

      elif  seriesparameter[1] == 'level':
          value7=  fields['mean']


      elif  seriesparameter[1] == 'total_engine_hours':
          value8 = fields['mean']
  """    
          
  callback = request.args.get('callback')
  myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
  return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})


          



  
  try:
    dcdb = InfluxDBCloud(dchost, dcport, dcusername, dcpassword, dcdatabase,  ssl=True)
    
    log.info("freeboard InfluxDBCloud - connected to %s", dcdatabase)
    #db.create_database(database)
    try:
      dcdb.create_database(database)
    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))
      # Drop and create
      dcdb.drop_database(database)
      dcdb.create_database(database)
        
    log.info("freeboard List InfluxDB database%s", dcdatabase)


    
    dcquery = ("select  * from HelmSmart "
           "where deviceid='{}'  AND  time > {}s AND  time < {}s group by * limit 1") \
        .format(deviceid,
              startepoch, endepoch)
    

    log.info("freeboard Get InfluxDB query %s", dcquery)

    
    result = dcdb.query(dcquery)

    #log.info("freeboard Get InfluxDB results %s", result)

 
    #keys = result.raw.get('series',[])
    keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)

    jsondata=[]
    for series in keys:
      #log.info("freeboard Get InfluxDB series key %s", series)
      #log.info("freeboard Get InfluxDB series tag %s ", series[1])
      #log.info("freeboard Get InfluxDB series tag deviceid %s ", series[1]['deviceid'])
      strvalue = {'deviceid':series[1]['deviceid'], 'sensor':series[1]['sensor'], 'source': series[1]['source'], 'instance':series[1]['instance'], 'type':series[1]['type'], 'parameter': series[1]['parameter'], 'epoch':endepoch}

      jsondata.append(strvalue)
      #for tags in series[1]:
      #  log.info("freeboard Get InfluxDB tags %s ", tags)


      
 
    #return jsonify( message='freeboard_createInfluxDB', status='error')
    return jsonify(series = jsondata,  status='success')

  
  except TypeError, e:
    #log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Type Error in InfluxDB  %s:  ' % str(e))

  except KeyError, e:
    #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Key Error in InfluxDB  %s:  ' % str(e))

  except NameError, e:
    #log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Name Error in InfluxDB  %s:  ' % str(e))
            
  except IndexError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Index Error in InfluxDB  %s:  ' % str(e))  
            
  except ValueError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

  except AttributeError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

  #except InfluxDBCloud.exceptions.InfluxDBClientError, e:
    #log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))

  except InfluxDBClientError, e:
    log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))

  except:
    #log.info('freeboard: Error in InfluxDB mydata append %s:', response)
    e = sys.exc_info()[0]
    log.info("freeboard_createInfluxDB: Error: %s" % e)

  return jsonify( message='freeboard_GetSeries', status='error')


@app.route('/freeboard_GetSeries')
@cross_origin()
def freeboard_GetSeries():

  deviceapikey = request.args.get('apikey','')
  serieskey = request.args.get('datakey','')
  Interval = request.args.get('Interval',"5min")

  response = None

  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]


  deviceid = getedeviceid(deviceapikey)
  
  log.info("freeboard deviceid %s", deviceid)

  if deviceid == "":
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

  
  host = 'hilldale-670d9ee3.influxcloud.net' 
  port = 8086
  username = 'helmsmart'
  password = 'Salm0n16'
  database = 'pushsmart-cloud'
  measurement = "HS" + str(deviceid)

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]




  try:
    db = InfluxDBCloud(host, port, username, password, database,  ssl=True)
    
    log.info("freeboard InfluxDBCloud - connected to %s", database)
    #db.create_database(database)
    try:
      db.create_database(database)
    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))
      # Drop and create
      db.drop_database(database)
      db.create_database(database)
        
    log.info("freeboard List InfluxDB database%s", database)


    
    query = ("select  * from {} "
           "where deviceid='{}'  AND  time > {}s AND  time < {}s group by * limit 1") \
        .format(measurement, deviceid,
              startepoch, endepoch)
    

    log.info("freeboard Get InfluxDB query %s", query)

    
    result = db.query(query)

    #log.info("freeboard Get InfluxDB results %s", result)

 
    #keys = result.raw.get('series',[])
    keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)

    jsondata=[]
    for series in keys:
      #log.info("freeboard Get InfluxDB series key %s", series)
      #log.info("freeboard Get InfluxDB series tag %s ", series[1])
      #log.info("freeboard Get InfluxDB series tag deviceid %s ", series[1]['deviceid'])
      strvalue = {'deviceid':series[1]['deviceid'], 'sensor':series[1]['sensor'], 'source': series[1]['source'], 'instance':series[1]['instance'], 'type':series[1]['type'], 'parameter': series[1]['parameter'], 'epoch':endepoch}

      jsondata.append(strvalue)
      #for tags in series[1]:
      #  log.info("freeboard Get InfluxDB tags %s ", tags)
 
    #return jsonify( message='freeboard_createInfluxDB', status='error')
    return jsonify(series = jsondata,  status='success')

  
  except TypeError, e:
    #log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Type Error in InfluxDB  %s:  ' % str(e))

  except KeyError, e:
    #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Key Error in InfluxDB  %s:  ' % str(e))

  except NameError, e:
    #log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Name Error in InfluxDB  %s:  ' % str(e))
            
  except IndexError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Index Error in InfluxDB  %s:  ' % str(e))  
            
  except ValueError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

  except AttributeError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

  #except InfluxDBCloud.exceptions.InfluxDBClientError, e:
    #log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))

  except InfluxDBClientError, e:
    log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))

  except:
    #log.info('freeboard: Error in InfluxDB mydata append %s:', response)
    e = sys.exc_info()[0]
    log.info("freeboard_createInfluxDB: Error: %s" % e)

  return jsonify( message='freeboard_GetSeries', status='error')

@app.route('/freeboard_createInfluxDB')
@cross_origin()
def freeboard_createInfluxDB():

  Interval = request.args.get('Interval',"5min")

  
  host = 'hilldale-670d9ee3.influxcloud.net' 
  port = 8086
  username = 'helmsmart'
  password = 'Salm0n16'
  database = 'pushsmart-cloud'

  response = None

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]

  """  
  json_body = [
        {
            "measurement": "SeaDream",
            
            "tags": {
                "deviceid": " 001EC0B415C2",
                "sensor": "engine_parameters_rapid_update",
                "source": "0F",
                "instance": "0",
                "type": "NULL",
                "parameter": "speed"
            },
            #"time": "2009-11-10T23:00:00Z",
            "fields": {
                "value": 1.26
            }
        }
    ]
  """
  json_body=[]
  timestamp = "2016-08-06 18:05:24"

  Key1="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:temperature.HelmSmart"
  Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
  Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"

  
  json_body.append(convert_influxdbcloud_json(Key1, timestamp, 140.0))
  json_body.append(convert_influxdbcloud_json(Key2, timestamp, 50.0))
  json_body.append(convert_influxdbcloud_json(Key3, timestamp, 24234.0))

  log.info("freeboard Create InfluxDB json_body:%s", json_body)
  log.info("freeboard Create InfluxDB %s", database)

  try:
    db = InfluxDBCloud(host, port, username, password, database,  ssl=True)
    
    log.info("freeboard InfluxDBCloud - connected to %s", database)
    #db.create_database(database)
    try:
      db.create_database(database)
    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))
      # Drop and create
      db.drop_database(database)
      db.create_database(database)
        
    log.info("freeboard List InfluxDB database%s", database)
    #dbs=db.get_list_database()

    #db.write_points(json_body, time_precision='ms')

    #return dbs
    #series = db.get_list_series(database)

    #log.info("freeboard Get InfluxDB points %s", series)

    #query = 'select * from HelmSmart;'
    #query = "select value from HelmSmart WHERE parameter='temperature'"
    query = "select value from HelmSmart WHERE parameter='temperature'"

    query = ("select mean(value) from HelmSmart "
             "where  time > {}s and time < {}s "
             "group by time({}s)") \
        .format(
                startepoch, endepoch,
                resolution)

    query = ("select * from HelmSmart "
           "where  time > {}s ") \
        .format(
              startepoch)

    query = ("select value from HelmSmart "
           "where deviceid='001EC010AD69' and sensor='environmental_data' AND  time > {}s ") \
        .format(
              startepoch)

    query = ("select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity from HelmSmart "
           "where deviceid='001EC010AD69' and sensor='environmental_data' AND  time > {}s AND  time < {}s group by time(300s)") \
        .format(
              startepoch, endepoch)

    query = ("select  tags  from HelmSmart "
           "where deviceid='001EC010AD69' and sensor='environmental_data' AND  time > {}s AND  time < {}s group by time(300s)") \
        .format(
              startepoch, endepoch)


    query = ("select  tags  from HelmSmart "
           "where deviceid='001EC010AD69' and sensor='environmental_data' AND  time > {}s AND  time < {}s ") \
        .format(
              startepoch, endepoch)

    query = ("select  *  from HelmSmart "
           "where deviceid='001EC010AD69'  AND  time > {}s AND  time < {}s ") \
        .format(
              startepoch, endepoch)


    query = ("select  *  from HelmSmart "
           "where deviceid='001EC010AD69'  AND  time > {}s AND  time < {}s Group by * limit 1") \
        .format(
              startepoch, endepoch)      


    query = ("select  mean(value)  from HelmSmart "
           "where deviceid='001EC010AD69' and sensor='environmental_data'  Group by * limit 100") \
        .format(
              startepoch, endepoch)      

    query = ("select mean(value) from HelmSmart "
             "where  deviceid='001EC010AD69' and sensor='environmental_data' and time > {}s and time < {}s "
             "group by time({}s)") \
        .format(
                startepoch, endepoch,
                resolution)
    
    query = ("select mean(value) from HelmSmart "
             "where  deviceid='001EC010AD69' and sensor='environmental_data' and time > {}s and time < {}s "
             "group by * limit 1") \
        .format(
                startepoch, endepoch
                )

    
    query = ("select mean(value) from HelmSmart "
             "where  deviceid='001EC010AD69' and sensor='environmental_data' and time > {}s and time < {}s "
             "group by * limit 1") \
        .format(
                startepoch, endepoch
                )

    startepoch = 1470675813
    endepoch = 1470679413
    
    query = ("select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity from HelmSmart "
           "where deviceid='001EC010AD69' and sensor='environmental_data' AND  time > {}s AND  time < {}s group by time(300s)") \
        .format(
              startepoch, endepoch)

    query = ("select  * from HelmSmart "
           "where deviceid='001EC010AD69'  AND  time > {}s AND  time < {}s group by * limit 1") \
        .format(
              startepoch, endepoch)

    
    query = ("select  * from HelmSmart "
           "where deviceid='001EC010AD69'  AND  time > {}s AND  time < {}s group by * limit 1") \
        .format(
              startepoch, endepoch)
    
    measurement = "HS_" + str(deviceid)
    query = ("select  * from {} "
           "where deviceid='001EC010AD69'  AND  time > {}s AND  time < {}s group by * limit 1") \
        .format(measurement,
              startepoch, endepoch)  

    log.info("freeboard Get InfluxDB query %s", query)

    
    result = db.query(query)

    log.info("freeboard Get InfluxDB results %s", result)

 
    #keys = result.raw.get('series',[])
    keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)

    jsondata=[]
    for series in keys:
      log.info("freeboard Get InfluxDB series key %s", series)
      log.info("freeboard Get InfluxDB series tag %s ", series[1])
      log.info("freeboard Get InfluxDB series tag deviceid %s ", series[1]['deviceid'])
      #strvalue = {'deviceid':series[1]['deviceid'], 'sensor':series[1]['sensor'], 'source': series[1]['source'], 'instance':series[1]['instance'], 'type':series[1]['type'], 'parameter': series[1]['parameter'], 'epoch': fields['time']}
      strvalue = {'deviceid':series[1]['deviceid'], 'sensor':series[1]['sensor'], 'source': series[1]['source'], 'instance':series[1]['instance'], 'type':series[1]['type'], 'parameter': series[1]['parameter'], 'epoch':endepoch}

      jsondata.append(strvalue)
      #for tags in series[1]:
      #  log.info("freeboard Get InfluxDB tags %s ", tags)
 
    #return jsonify( message='freeboard_createInfluxDB', status='error')
    return jsonify(series = jsondata)

    strvalue=""
    
    for series in keys:
      #log.info("freeboard Get InfluxDB series key %s", series)
      log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
      #log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
      #log.info("freeboard Get InfluxDB series values %s ", series['values'])
      values = series['values']
      for value in values:
        log.info("freeboard Get InfluxDB series time %s", value[0])
        log.info("freeboard Get InfluxDB series mean %s", value[1])

      for point in series['values']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val
          
      log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields['mean'])

      tag = series['tags']
      log.info("freeboard Get InfluxDB series tags2 %s ", tag)

      mydatetimestr = str(fields['time'])
      
      if tag['type'] == 'Outside Temperature' and tag['parameter']== 'temperature':
          value1 = convertfbunits(fields['mean'], 0)
          strvalue = strvalue + ':' + str(value1)
          
      elif tag['type']  == 'Outside Temperature' and tag['parameter'] == 'atmospheric_pressure':
          value2 = convertfbunits(fields['mean'], 10)
          strvalue = strvalue + ':' + str(value2)
          
      elif tag['type']  == 'Outside Humidity' and tag['parameter'] == 'humidity':
          value3=  convertfbunits(fields['mean'], 26)
          strvalue = strvalue + ':' + str(value3)

      log.info("freeboard Get InfluxDB series tags3 %s ", strvalue)


    mydatetimestr = mydatetimestr.split(".")
    log.info("freeboard Get InfluxDB time string%s ", mydatetimestr[0])


    #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%S.%fZ')
    mydatetime = datetime.datetime.strptime(mydatetimestr[0], '%Y-%m-%dT%H:%M:%S')

    callback = request.args.get('callback')
    myjsondate =""
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
    
    return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':value1, 'baro':value2, 'humidity':value3})

      

    points=list(result.get_points(tags={'deviceid':'001EC010AD69'}))
    log.info("freeboard Get InfluxDB series points%s", points)
    
    #series = db.get_list_series(database)
    for point in points:
      log.info("freeboard Get InfluxDB series points%s", point)
    
    #log.info("freeboard Get InfluxDB series%s", series)
    return jsonify( status='success')    
    #return jsonify( results=json.dumps(result), status='success')

  except TypeError, e:
    #log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Type Error in InfluxDB  %s:  ' % str(e))

  except KeyError, e:
    #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Key Error in InfluxDB  %s:  ' % str(e))

  except NameError, e:
    #log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Name Error in InfluxDB  %s:  ' % str(e))
            
  except IndexError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Index Error in InfluxDB  %s:  ' % str(e))  
            
  except ValueError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

  except AttributeError, e:
    #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
    log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

  #except InfluxDBCloud.exceptions.InfluxDBClientError, e:
    #log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))

  except InfluxDBClientError, e:
    log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))

  except:
    #log.info('freeboard: Error in InfluxDB mydata append %s:', response)
    e = sys.exc_info()[0]
    log.info("freeboard_createInfluxDB: Error: %s" % e)

  return jsonify( message='freeboard_createInfluxDB', status='error')
           

           

@app.route('/freeboard_locationXX')
@cross_origin()
def freeboard_locationXX():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)




    influxdb_keys=[]
    influxdb_gpskeys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:position_rapid.source:*.instance:0.type:NULL.parameter:latlng.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
     

    #SERIES_KEY = 'deviceid:001EC0B415C2.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select median(valuelat) as lat, median(valuelng) as lng from /({})/ '
                           'where time > {}s and time < {}s '
                           'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select median(valuelat) as lat, median(valuelng) as lng from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= db.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

      
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    strvalue = ""
    lat = 'missing'
    lng = 'missing'

    
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        #seriestags = seriesname.split(".")
        #seriessourcetag = seriestags[2]
        #seriessource = seriessourcetag.split(":")

        #seriestypetag = seriestags[4]
        #seriestype = seriestypetag.split(":")

        #seriesparametertag = seriestags[5]
        #seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard got data seriesname %s:  ', seriesname)

        lat =  fields['lat']
        strvalue = strvalue + ':' + str(lat)
            
        lng =  fields['lng']
        strvalue = strvalue + ':' + str(lng)


            
        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard got data values %s:  ', strvalue)

         
        #jsondata.append(strvalue)
        
    try:
        #jsondata = sorted(jsondata,key=itemgetter('epoch'))
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)    
        #return jsonify(date_time=mydatetime, update=True, lat=lat, lng=lng)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':lat, 'lng':lng})
      
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })



  

    #jasondata = {'datatime':nowtime}

    #log.info('freeboard_io:  keys %s:%s  ', deviceapikey, serieskey)

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

@app.route('/freeboard_winddataXX')
@cross_origin()
def freeboard_winddataXX():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
         #return jsonify(status="deviceid error", update=False )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)


    influxdb_keys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""
    SERIES_KEY2 = ""
    SERIES_KEY3 = ""
    SERIES_KEY4 = ""
    SERIES_KEY5 = ""
    SERIES_KEY6 = ""
    SERIES_KEY7 = ""  
    SERIES_KEY8 = ""

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:wind_data.source:*.instance:0.type:TWIND True North.parameter:wind_speed.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
    SERIES_KEY2 = 'deviceid:' + deviceid + '.sensor:wind_data.source:*.instance:0.type:TWIND True North.parameter:wind_direction.HelmSmart'
    influxdb_keys.append(SERIES_KEY2)    
    SERIES_KEY3 = 'deviceid:' + deviceid + '.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'
    influxdb_keys.append(SERIES_KEY3)   
    SERIES_KEY4 = 'deviceid:' + deviceid + '.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_direction.HelmSmart'
    influxdb_keys.append(SERIES_KEY4)       

    #SERIES_KEY = 'deviceid:001EC0B415C2.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select mean(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select mean(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= db.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #return jsonify(update=False )
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

      
    strvalue = ""
    truewindspeed = '---'
    appwindspeed = '---'
    truewinddir = '---'
    appwinddir = '---'
    
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        seriestags = seriesname.split(".")
        seriessourcetag = seriestags[2]
        seriessource = seriessourcetag.split(":")

        seriestypetag = seriestags[4]
        seriestype = seriestypetag.split(":")

        seriesparametertag = seriestags[5]
        seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard got data seriesname %s:  ', seriesname)

        if seriestype[1] == 'TWIND True North' and seriesparameter[1] == 'wind_speed':
            truewindspeed =  convertfbunits(fields['mean'],4)
            strvalue = strvalue + ':' + str(truewindspeed)
            
        elif seriestype[1] == 'Apparent Wind' and seriesparameter[1] == 'wind_speed':
            appwindspeed =  convertfbunits(fields['mean'], 4)
            strvalue = strvalue + ':' + str(appwindspeed)
            
        elif seriestype[1] == 'TWIND True North' and seriesparameter[1] == 'wind_direction':
            truewinddir=  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(truewinddir)
            
        elif seriestype[1] == 'Apparent Wind' and seriesparameter[1] == 'wind_direction':
            appwinddir =  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(appwinddir)

        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard got data values %s:  ', strvalue)

        #callback = request.args.get('callback')
        #log.info('freeboard: callback %s:  ', callback) 

        
    try:
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)
        #myjson = jsonify(date_time=mydatetime, update=True, truewindspeed=truewindspeed, appwindspeed=appwindspeed, truewinddir=truewinddir, appwinddir=appwinddir)
        #myjson = jsonify(date_time=mydatetime)
        #log.info('freeboard: datetime %s:  ', myjson) 
        #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
        #log.info('freeboard: datetime %s:  ', myjsondate) 
        #return jsonify(date_time=mydatetime, update=True, truewindspeed=truewindspeed, appwindspeed=appwindspeed, truewinddir=truewinddir, appwinddir=appwinddir)
        #return '{0}({1})'.format(callback, myjson)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','truewindspeed':truewindspeed,'appwindspeed':appwindspeed,'truewinddir':truewinddir, 'appwinddir':appwinddir})

    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify( update=False )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(update=False)
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

@app.route('/freeboard_environmentalXX')
@cross_origin()
def freeboard_environmentalXX():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)


    influxdb_keys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""
    SERIES_KEY2 = ""
    SERIES_KEY3 = ""
    SERIES_KEY4 = ""
    SERIES_KEY5 = ""
    SERIES_KEY6 = ""
    SERIES_KEY7 = ""  
    SERIES_KEY8 = ""

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:0.type:Outside Temperature.parameter:temperature.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
    SERIES_KEY2 = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:0.type:Outside Temperature.parameter:atmospheric_pressure.HelmSmart'
    influxdb_keys.append(SERIES_KEY2)    
    SERIES_KEY3 = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:0.type:Outside Humidity.parameter:humidity.HelmSmart'
    influxdb_keys.append(SERIES_KEY3)   
    #SERIES_KEY4 = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:0.type:Apparent Wind.parameter:wind_direction.HelmSmart'
    #influxdb_keys.append(SERIES_KEY4)       

    #SERIES_KEY = 'deviceid:001EC0B415C2.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select mean(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select mean(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= db.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

      
    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        seriestags = seriesname.split(".")
        seriessourcetag = seriestags[2]
        seriessource = seriessourcetag.split(":")

        seriestypetag = seriestags[4]
        seriestype = seriestypetag.split(":")

        seriesparametertag = seriestags[5]
        seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard got data seriesname %s:  ', seriesname)

        if seriestype[1] == 'Outside Temperature' and seriesparameter[1] == 'temperature':
            value1 = convertfbunits(fields['mean'], 0)
            strvalue = strvalue + ':' + str(value1)
            
        elif seriestype[1] == 'Outside Temperature' and seriesparameter[1] == 'atmospheric_pressure':
            value2 = convertfbunits(fields['mean'], 10)
            strvalue = strvalue + ':' + str(value2)
            
        elif seriestype[1] == 'Outside Humidity' and seriesparameter[1] == 'humidity':
            value3=  convertfbunits(fields['mean'], 26)
            strvalue = strvalue + ':' + str(value3)
            


        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard got data values %s:  ', strvalue)

        
    try:
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)    
        #return jsonify(date_time=mydatetime, update=True, temperature=value1, baro=value2, humidity=value3)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':value1, 'baro':value2, 'humidity':value3})
     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

@app.route('/freeboard_navXX')
@cross_origin()
def freeboard_navXX():

    deviceapikey = request.args.get('apikey','')
    Instance = request.args.get('instance','0')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })



    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)


    influxdb_keys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""
    SERIES_KEY2 = ""
    SERIES_KEY3 = ""
    SERIES_KEY4 = ""
    SERIES_KEY5 = ""
    SERIES_KEY6 = ""
    SERIES_KEY7 = ""  
    SERIES_KEY8 = ""

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:cogsog.source:*.instance:0.type:True.parameter:course_over_ground.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
    SERIES_KEY2 = 'deviceid:' + deviceid + '.sensor:cogsog.source:*.instance:0.type:True.parameter:speed_over_ground.HelmSmart'
    influxdb_keys.append(SERIES_KEY2)    
    SERIES_KEY3 = 'deviceid:' + deviceid + '.sensor:heading.source:*.instance:0.type:True.parameter:heading.HelmSmart'
    influxdb_keys.append(SERIES_KEY3)   
    SERIES_KEY4 = 'deviceid:' + deviceid + '.sensor:heading.source:*.instance:0.type:Magnetic.parameter:heading.HelmSmart'
    influxdb_keys.append(SERIES_KEY4)    

    #SERIES_KEY = 'deviceid:001EC0B415C2.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select mean(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select mean(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= db.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        seriestags = seriesname.split(".")
        seriessourcetag = seriestags[2]
        seriessource = seriessourcetag.split(":")

        seriestypetag = seriestags[4]
        seriestype = seriestypetag.split(":")

        seriesparametertag = seriestags[5]
        seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard got data seriesname %s:  ', seriesname)

        if  seriesparameter[1] == 'course_over_ground':
            value1 =  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(value1)
            
        elif  seriesparameter[1] == 'speed_over_ground':
            value2 = convertfbunits(fields['mean'], 4)
            strvalue = strvalue + ':' + str(value2)
            
        elif  seriestype[1] == 'True' and seriesparameter[1] == 'heading':
            value3=  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(value3)
            
        elif  seriestype[1] == 'Magnetic' and seriesparameter[1] == 'heading':
            value4=  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(value4)

        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard got data values %s:  ', strvalue)

        
    try:
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)    
        #return jsonify(date_time=mydatetime, update=True, cog=value1, sog=value2, heading_true=value3, heading_mag=value4)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','cog':value1, 'sog':value2, 'heading_true':value3, 'heading_mag':value4})
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(update=False, status='missing' )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
@app.route('/freeboard_batteryXX')
@cross_origin()
def freeboard_batteryXX():

    deviceapikey = request.args.get('apikey','')
    Instance = request.args.get('instance','0')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)


    influxdb_keys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""
    SERIES_KEY2 = ""
    SERIES_KEY3 = ""
    SERIES_KEY4 = ""
    SERIES_KEY5 = ""
    SERIES_KEY6 = ""
    SERIES_KEY7 = ""  
    SERIES_KEY8 = ""

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:battery_status.source:*.instance:' + Instance + '.type:NULL.parameter:voltage.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
    SERIES_KEY2 = 'deviceid:' + deviceid + '.sensor:battery_status.source:*.instance:' + Instance + '.type:NULL.parameter:current.HelmSmart'
    influxdb_keys.append(SERIES_KEY2)    
    SERIES_KEY3 = 'deviceid:' + deviceid + '.sensor:battery_status.source:*.instance:' + Instance + '.type:NULL.parameter:temperature.HelmSmart'
    influxdb_keys.append(SERIES_KEY3)   
    #SERIES_KEY4 = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:0.type:Apparent Wind.parameter:wind_direction.HelmSmart'
    #influxdb_keys.append(SERIES_KEY4)       

    #SERIES_KEY = 'deviceid:001EC0B415C2.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select mean(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select mean(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= db.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })


      
    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        seriestags = seriesname.split(".")
        seriessourcetag = seriestags[2]
        seriessource = seriessourcetag.split(":")

        seriestypetag = seriestags[4]
        seriestype = seriestypetag.split(":")

        seriesparametertag = seriestags[5]
        seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard got data seriesname %s:  ', seriesname)

        if  seriesparameter[1] == 'voltage':
            value1 =  convertfbunits(fields['mean'], 27)
            strvalue = strvalue + ':' + str(value1)
            
        elif  seriesparameter[1] == 'current':
            value2 =  fields['mean']
            strvalue = strvalue + ':' + str(value2)
            
        elif  seriesparameter[1] == 'temperature':
            value3=  convertfbunits(fields['mean'], 0)
            strvalue = strvalue + ':' + str(value3)
            


        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard got data values %s:  ', strvalue)

        
    try:
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)    
        #return jsonify(date_time=mydatetime, update=True, voltage=value1, current=value2, temperature=value3)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':value1, 'current':value2, 'temperature':value3})
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(status='error' , update=False)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

      
@app.route('/freeboard_engineXX')
@cross_origin()
def freeboard_engineXX():

    deviceapikey = request.args.get('apikey','')
    Instance = request.args.get('instance','0')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard_engine deviceid %s", deviceid)

    if deviceid == "":
      #return jsonify(update=False, status='deviceid error' )
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)


    influxdb_keys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""
    SERIES_KEY2 = ""
    SERIES_KEY3 = ""
    SERIES_KEY4 = ""
    SERIES_KEY5 = ""
    SERIES_KEY6 = ""
    SERIES_KEY7 = ""  
    SERIES_KEY8 = ""



    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    value5 = '---'
    value6 = '---'
    value7 = '---'
    value8 = '---'
    
    

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:engine_parameters_rapid_update.source:*.instance:' + Instance + '.type:NULL.parameter:speed.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
    SERIES_KEY2 = 'deviceid:' + deviceid + '.sensor:engine_parameters_dynamic.source:*.instance:' + Instance + '.type:NULL.parameter:engine_temp.HelmSmart'
    influxdb_keys.append(SERIES_KEY2)    
    SERIES_KEY3 = 'deviceid:' + deviceid + '.sensor:engine_parameters_dynamic.source:*.instance:' + Instance + '.type:NULL.parameter:oil_pressure.HelmSmart'
    influxdb_keys.append(SERIES_KEY3)
    SERIES_KEY4 = 'deviceid:' + deviceid + '.sensor:engine_parameters_dynamic.source:*.instance:' + Instance + '.type:NULL.parameter:alternator_potential.HelmSmart'
    influxdb_keys.append(SERIES_KEY4)
    #SERIES_KEY5 = 'deviceid:' + deviceid + '.sensor:engine_parameters_rapid_update.source:*.instance:' + Instance + '.type:NULL.parameter:boost_pressure.HelmSmart'
    #influxdb_keys.append(SERIES_KEY5)
    SERIES_KEY5 = 'deviceid:' + deviceid + '.sensor:trip_parameters_engine.source:*.instance:' + Instance + '.type:NULL.parameter:trip_fuel_used.HelmSmart'
    influxdb_keys.append(SERIES_KEY5)    
    SERIES_KEY6 = 'deviceid:' + deviceid + '.sensor:engine_parameters_dynamic.source:*.instance:' + Instance + '.type:NULL.parameter:fuel_rate.HelmSmart'
    influxdb_keys.append(SERIES_KEY6)
    SERIES_KEY7 = 'deviceid:' + deviceid + '.sensor:fluid_level.source:*.instance:' + Instance + '.type:0.parameter:level.HelmSmart'
    influxdb_keys.append(SERIES_KEY7)    
    SERIES_KEY8 = 'deviceid:' + deviceid + '.sensor:engine_parameters_dynamic.source:*.instance:' + Instance + '.type:NULL.parameter:total_engine_hours.HelmSmart'
    influxdb_keys.append(SERIES_KEY8)
    
    #SERIES_KEY4 = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:0.type:Apparent Wind.parameter:wind_direction.HelmSmart'
    #influxdb_keys.append(SERIES_KEY4)       

    #SERIES_KEY = 'deviceid:001EC0B415C2.sensor:wind_data.source:*.instance:0.type:Apparent Wind.parameter:wind_speed.HelmSmart'

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select mean(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select mean(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard_engine data Query %s", query)

    try:
        response= db.query(query)
        
    except TypeError, e:
        log.info('freeboard_engine: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard_engine: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard_engine: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard_engine: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard_engine: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard_engine: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard_engine: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard_engine: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard_engine: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard_engine: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard_engine: InfluxDB Query has no data ')
        mydatetime = datetime.datetime.now()
        #return jsonify(date_time=mydatetime, update=False, status='missing', rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})




        #return jsonify(update=False, status='missing' )
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        seriestags = seriesname.split(".")
        seriessourcetag = seriestags[2]
        seriessource = seriessourcetag.split(":")

        seriestypetag = seriestags[4]
        seriestype = seriestypetag.split(":")

        seriesparametertag = seriestags[5]
        seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard_engine got data seriesname %s:  ', seriesname)

        if  seriesparameter[1] == 'speed':
            value1 =  fields['mean']
            strvalue = strvalue + ':' + str(value1)
            
        elif  seriesparameter[1] == 'engine_temp':
            value2 =  convertfbunits(fields['mean'], 0)
            strvalue = strvalue + ':' + str(value2)
            
        elif  seriesparameter[1] == 'oil_pressure':
            value3=  convertfbunits(fields['mean'], 8)
            strvalue = strvalue + ':' + str(value3)

        elif  seriesparameter[1] == 'alternator_potential':
            value4 =  convertfbunits(fields['mean'], 27)
            strvalue = strvalue + ':' + str(value4)
            
        elif  seriesparameter[1] == 'boost_pressure':
            value5=  convertfbunits(fields['mean'], 8)
            strvalue = strvalue + ':' + str(value5)

        elif  seriesparameter[1] == 'trip_fuel_used':
            value5=  convertfbunits(fields['mean'], 21)
            strvalue = strvalue + ':' + str(value5)
            
            
        elif  seriesparameter[1] == 'fuel_rate':
            value6 =  convertfbunits(fields['mean'], 18)
            strvalue = strvalue + ':' + str(value6)
            
        elif  seriesparameter[1] == 'level':
            value7=  convertfbunits(fields['mean'], 26)
            strvalue = strvalue + ':' + str(value7)

        elif  seriesparameter[1] == 'total_engine_hours':
            value8 = convertfbunits(fields['mean'], 37)
            strvalue = strvalue + ':' + str(value8)
            
 

            


        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard_engine got data values %s:  ', strvalue)


        
    try:
        log.info('freeboard: freeboard_engine returning data values %s:  ', strvalue)    
        #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
   
    except:
        log.info('freeboard: Error in geting freeboard_engine  %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard_engine  %s:  ' % e)
        #return jsonify(status='error' , update=False)
        mydatetime = datetime.datetime.now()
        #return jsonify(date_time=mydatetime, update=False, status='error', rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False','status':'error', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})

    mydatetime = datetime.datetime.now()
    #return jsonify(date_time=mydatetime, update=False, status='error', rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
    callback = request.args.get('callback')
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S") 
    return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False','status':'error', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})

@app.route('/freeboard_statusXX')
@cross_origin()
def freeboard_statusXX():

    deviceapikey = request.args.get('apikey','')
    Instance = request.args.get('instance','0')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
      #return jsonify(update=False, status='deviceid error' )
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'pinheads-wedontneedroads-1.c.influxdb.com' 
    port = 8086
    username = 'root'
    password = 'c73d5a8b1b07d17b'
    database = 'pushsmart-final'
  
    db = InfluxDBClient(host, port, username, password, database)


    influxdb_keys=[]

    SERIES_KEYS=[]
    SERIES_KEY1 = ""
    SERIES_KEY2 = ""
    SERIES_KEY3 = ""
    SERIES_KEY4 = ""
    SERIES_KEY5 = ""
    SERIES_KEY6 = ""
    SERIES_KEY7 = ""  
    SERIES_KEY8 = ""

    series_elements = 0

    SERIES_KEY1 = 'deviceid:' + deviceid + '.sensor:seasmartswitch.source:*.instance:' + Instance + '.type:NULL.parameter:bank0.HelmSmart'
    influxdb_keys.append(SERIES_KEY1)
    SERIES_KEY2 = 'deviceid:' + deviceid + '.sensor:seasmartswitch.source:*.instance:' + Instance + '.type:NULL.parameter:bank1.HelmSmart'
    influxdb_keys.append(SERIES_KEY2)    

    

    if influxdb_keys != []:
        serieskeys = '|'.join(influxdb_keys)
      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select median(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
        query = ('select median(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= db.query(query) 
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  
            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })



    strvalue = ""
    value1 = '---'
    value2 = '---'


    status0=False
    status1=False
    status2=False
    status3=False
    status4=False
    status5=False
    status6=False
    status7=False
    status8=False
    status9=False
    status10=False
    status11=False

    
    #for point in response.points:
    for series in response:
      #log.info("influxdb results..%s", series )
      for point in series['points']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val


        seriesname = series['name']
        seriestags = seriesname.split(".")
        seriessourcetag = seriestags[2]
        seriessource = seriessourcetag.split(":")

        seriestypetag = seriestags[4]
        seriestype = seriestypetag.split(":")

        seriesparametertag = seriestags[5]
        seriesparameter = seriesparametertag.split(":")
        
        mydatetime = datetime.datetime.fromtimestamp(float(fields['time']))
        #strvalue = {'datetime': datetime.datetime.fromtimestamp(float(fields['time'])), 'epoch': fields['time'], 'source':seriessource[1], 'True_'+seriesparameter: fields['mean']}

        log.info('freeboard: freeboard got data seriesname %s:  ', seriesname)

        if  seriesparameter[1] == 'bank0':
          value1 =  fields['median']
          strvalue = strvalue + ':' + str(value1)

          if value1 != '---':
            if value1 & 0x1 == 0x1:
              status0 = True

            if value1 & 0x2 == 0x2:
              status1 = True

            if value1 & 0x4 == 0x4:
              status2 = True

            if value1 & 0x8 == 0x8:
              status3 = True

            if value1 & 0x10 == 0x10:
              status4 = True

            if value1 & 0x20 == 0x20:
              status5 = True

            if value1 & 0x40 == 0x40:
              status6 = True

            if value1 & 0x80 == 0x80:
              status7 = True


        elif  seriesparameter[1] == 'bank1':
          value2 =  fields['median']
          strvalue = strvalue + ':' + str(value2)
            
          if value2 != '---':
            if value1 & 0x1 == 0x01:
              status8 = True

            if value2 & 0x2 == 0x02:
              status9 = True

            if value2 & 0x4 == 0x04:
              status10 = True

            if value2 & 0x8 == 0x08:
              status11 = True

            
 

            


        #print 'freeboard processing data points:', strvalue
        log.info('freeboard: freeboard got data values %s:  ', strvalue)

        
    try:
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)    
        #return jsonify(date_time=mydatetime, update=True, bank0=value1, status0=status0, status1=status1, status2=status2, status3=status3, status4=status4, status5=status5, status6=status6, status7=status7, status8=status8, status9=status9, status10=status10, status11=status11)
        callback = request.args.get('callback')
        myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'bank0':value1, 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11})
   
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(status='error' , update=False)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })



@app.route('/freeboard_environmental')
@cross_origin()
def freeboard_environmental():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    env_type = request.args.get('type',"outside")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]
    #resolution = 60


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'

    temperature=[]
    atmospheric_pressure=[]
    humidity=[]
    
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    if env_type == "inside":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Inside Temperature' OR type='Inside Humidity')"

    elif env_type == "inside mesh":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='" + Instance + "' "

      
    elif env_type == "sea":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Sea Temperature' OR type='Inside Humidity')"

      
    else:
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"





      
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
        query = ('select  max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity, max(altitude) AS altitude from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
        query = ('select  min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity, min(altitude) AS altitude from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

        
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity, mean(altitude) AS altitude from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 

    """
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 
    """    

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      temperature=[]
      atmospheric_pressure=[]
      atmospheric_pressure_sea=[]
      humidity=[]
      altitude=[]
      ts =startepoch*1000


      
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
      
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          value1 = convertfbunits(point['temperature'],  convertunittype('temperature', units))
        temperature.append({'epoch':ts, 'value':value1})
          
        if point['atmospheric_pressure'] is not None:         
          value2 = convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))
        atmospheric_pressure.append({'epoch':ts, 'value':value2})
                    
        if point['humidity'] is not None:         
          value3 = convertfbunits(point['humidity'], 26)
        humidity.append({'epoch':ts, 'value':value3})

                    
        if point['altitude'] is not None:         
          value4 = convertfbunits(point['altitude'], 32)
        altitude.append({'epoch':ts, 'value':value4})

        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value2 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value4 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value5 = getAtmosphericCompensation(value4)
          #add offset if any in KPa
          value5 = convertfbunits(value2 + value5, convertunittype('baro_pressure', units))
          
        atmospheric_pressure_sea.append({'epoch':ts, 'value':value5})        
 

          
        #mydatetimestr = str(point['time'])

        #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      #log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)

      """
      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'air_temperature'
      val_to_write =float(value1)

      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

       """     

      callback = request.args.get('callback')
      myjsondatetz = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':value1, 'baro':value2, 'humidity':value3})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     

    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      log.info('freeboard_environmental: ValueError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: ValueError in freeboard_environmental point%s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: NameError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      log.info('freeboard_environmental: IndexError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: IndexError in freeboard_environmental %s:  ' % str(e))
      
    except pyonep.exceptions.JsonRPCRequestException as ex:
        print('JsonRPCRequestException: {0}'.format(ex))
        
    except pyonep.exceptions.JsonRPCResponseException as ex:
        print('JsonRPCResponseException: {0}'.format(ex))
        
    except pyonep.exceptions.OnePlatformException as ex:
        print('OnePlatformException: {0}'.format(ex))
       
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })


@app.route('/freeboard_environmental_calculated')
@cross_origin()
def freeboard_environmental_calculated():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    env_type = request.args.get('type',"outside")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]
    #resolution = 60


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'

    temperature=[]
    atmospheric_pressure=[]
    humidity=[]
    wind_speed=[]
    
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    if env_type == "inside":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Inside Temperature' OR type='Inside Humidity')"

    elif env_type == "inside mesh":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='" + Instance + "' "

      
    elif env_type == "sea":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Sea Temperature' OR type='Inside Humidity')"

      
    else:
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"




      
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude, median(wind_speed) AS  wind_speed from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
        query = ('select  max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity, max(altitude) AS altitude, max(wind_speed) AS  wind_speed from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
        query = ('select  min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity, min(altitude) AS altitude, min(wind_speed) AS  wind_speed from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

        
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity, mean(altitude) AS altitude, mean(wind_speed) AS  wind_speed from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 

    """
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 
    """    

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      temperature=[]
      atmospheric_pressure=[]
      atmospheric_pressure_sea=[]
      humidity=[]
      altitude=[]
      windchill=[]
      heatindex=[]
      dewpoint=[]
      feelslike=[]

      
      ts =startepoch*1000


      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        tempF='---'
        tempC='---'
        humidity100='---'
        windmph='---'
      
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          value1 = convertfbunits(point['temperature'],  convertunittype('temperature', units))
          tempF=convertfbunits(point['temperature'],  0)
          tempC=convertfbunits(point['temperature'],  1)          
        temperature.append({'epoch':ts, 'value':value1})
          
        if point['atmospheric_pressure'] is not None:         
          value2 = convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))
        atmospheric_pressure.append({'epoch':ts, 'value':value2})
                    
        if point['humidity'] is not None:         
          value3 = convertfbunits(point['humidity'], 26)
          humidity100 = convertfbunits(point['humidity'], 26)
        humidity.append({'epoch':ts, 'value':value3})

                    
        if point['altitude'] is not None:         
          value4 = convertfbunits(point['altitude'], 32)
        altitude.append({'epoch':ts, 'value':value4})

        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value2 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value4 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value5 = getAtmosphericCompensation(value4)
          #add offset if any in KPa
          value5 = convertfbunits(value2 + value5, convertunittype('baro_pressure', units))
          
        atmospheric_pressure_sea.append({'epoch':ts, 'value':value5})        
 

        if point['wind_speed'] is not None:         
          value6 = convertfbunits(point['wind_speed'], convertunittype('speed', units))
          windmph = convertfbunits(point['wind_speed'], 5)
        wind_speed.append({'epoch':ts, 'value':value6})

        try:

          # calculate dew_point
          if tempC != '---' and  humidity100 != '---':
            #dp = dew_point(temperature=tempF, humidity=humidity100)
            dp = dew_point(temperature=tempC, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated dew_point  %s:', dp.k)
            dewpoint.append({'epoch':ts, 'value':convertfbunits(dp.k,  convertunittype('temperature', units))})

            
          # calculate heat_index
          if tempF != '---' and  humidity100 != '---':        
            hi= heat_index(temperature=tempF, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated heat_index %s:', hi.k)
            heatindex.append({'epoch':ts, 'value':convertfbunits(hi.k,  convertunittype('temperature', units))})

            
          # calculate feels_like
          if tempF != '---' and  humidity100 != '---' and  windmph != '---':
            fl = feels_like(temperature=tempF, humidity= humidity100 , wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated feels_like  %s:', fl.k)
            feelslike.append({'epoch':ts, 'value':convertfbunits(fl.k,  convertunittype('temperature', units))})

          # calculate Wind Chill
          if tempF != '---' and  windmph != '---':
            wc = wind_chill(temperature=tempF, wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated wind chill %s:', wc.k)
            windchill.append({'epoch':ts, 'value':convertfbunits(wc.k,  convertunittype('temperature', units))})
 

        except AttributeError, e:
          log.info('freeboard_environmental_calculated: AttributeError in calculated %s:  ' % str(e))
          
        except TypeError, e:
          log.info('freeboard_environmental_calculated: TypeError in calculated %s:  ' % str(e))
          
        except ValueError, e:
          log.info('freeboard_environmental_calculated: ValueError in calculated %s:  ' % str(e))            
          
        except NameError, e:
          log.info('freeboard_environmental_calculated: NameError in calculated %s:  ' % str(e))           

        except IndexError, e:
          log.info('freeboard_environmental_calculated: IndexError in calculated %s:  ' % str(e))
          
        except:
          e = sys.exc_info()[0]
          log.info('freeboard_environmental_calculated: Error in geting calculated ststs %s:  ' % e)



        
        #mydatetimestr = str(point['time'])

        #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      #log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)

      """
      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'air_temperature'
      val_to_write =float(value1)

      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

       """     

      callback = request.args.get('callback')
      myjsondatetz = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':value1, 'baro':value2, 'humidity':value3})
      return '{0}({1})'.format(callback, {'date_time':myjsondate,
                                          'update':'True','temperature':list(reversed(temperature)),
                                          'atmospheric_pressure':list(reversed(atmospheric_pressure)),

                                           'humidity':list(reversed(humidity)),
                                           'altitude':list(reversed(altitude)),
                                          
                                           'dewpoinr':list(reversed(dewpoint)),
                                           'heatindex':list(reversed(heatindex)),
                                           'feelslike':list(reversed(feelslike)),
                                           'windchill':list(reversed(windchill)),

                                           'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     

    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      log.info('freeboard_environmental: ValueError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: ValueError in freeboard_environmental point%s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: NameError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      log.info('freeboard_environmental: IndexError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: IndexError in freeboard_environmental %s:  ' % str(e))
      
    except pyonep.exceptions.JsonRPCRequestException as ex:
        print('JsonRPCRequestException: {0}'.format(ex))
        
    except pyonep.exceptions.JsonRPCResponseException as ex:
        print('JsonRPCResponseException: {0}'.format(ex))
        
    except pyonep.exceptions.OnePlatformException as ex:
        print('OnePlatformException: {0}'.format(ex))
       
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })



@app.route('/freeboard_environmental_metar')
@cross_origin()
def freeboard_environmental_metar():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"1min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    env_type = request.args.get('type',"outside")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]
    #resolution = 60


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'

    temperature=[]
    atmospheric_pressure=[]
    humidity=[]
    wind_speed=[]
    
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

    devicename = getedevicename(deviceapikey)
    
    log.info("freeboard devicename %s", devicename)

    if devicename == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'devicename error' })




    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    if env_type == "inside":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Inside Temperature' OR type='Inside Humidity')"

    elif env_type == "inside mesh":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='" + Instance + "' "

      
    elif env_type == "sea":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Sea Temperature' OR type='Inside Humidity')"

      
    else:
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"




      
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude, median(wind_speed) AS  wind_speed , median(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
        query = ('select  max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity, max(altitude) AS altitude, max(wind_speed) AS  wind_speed , max(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
        query = ('select  min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity, min(altitude) AS altitude, min(wind_speed) AS  wind_speed , min(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

        
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity, mean(altitude) AS altitude, mean(wind_speed) AS  wind_speed , mean(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 

    """
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 
    """    

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      temperature=""
      atmospheric_pressure=""
      atmospheric_pressure_sea=""
      humidity=""
      altitude=""
      windchill=""
      wind_speed=""
      wind_dir=""
      heatindex=""
      dewpoint=""
      feelslike=""

      
      ts =startepoch*1000


      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        tempF='---'
        tempC='---'
        humidity100='---'
        windmph='---'
        winddir='---'
      
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          temperature = int(convertfbunits(point['temperature'],  1)   )
          temperature1hr = str(temperature * 10 ).zfill(4)
          temperature = str(temperature).zfill(2)

          tempF=convertfbunits(point['temperature'],  0)
          tempC=convertfbunits(point['temperature'],  1)          

          
        if point['atmospheric_pressure'] is not None:         
          atmospheric_pressure = int((convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))) * 100)
          atmospheric_pressure = str(atmospheric_pressure).zfill(4)
                    
        if point['humidity'] is not None:         
          humidity = convertfbunits(point['humidity'], 26)
          humidity100 = convertfbunits(point['humidity'], 26)


                    
        if point['altitude'] is not None:         
          altitude = convertfbunits(point['altitude'], 32)


        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value2 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value4 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value5 = getAtmosphericCompensation(value4)
          #add offset if any in KPa
          atmospheric_pressure_sea = int((convertfbunits(value2 + value5, convertunittype('baro_pressure', units))) * 10)
          
   
 

        if point['wind_speed'] is not None:         
          wind_speed = int(convertfbunits(point['wind_speed'], 4))
          windmph = int(convertfbunits(point['wind_speed'], 5))
          wind_speed =str(wind_speed).zfill(2)
       

        if point['wind_direction'] is not None:         
          wind_dir = int(convertfbunits(point['wind_direction'], 16))
          wind_dir =str(wind_dir).zfill(3)

        try:

          # calculate dew_point
          if tempC != '---' and  humidity100 != '---':
            #dp = dew_point(temperature=tempF, humidity=humidity100)
            dp = dew_point(temperature=tempC, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated dew_point  %s:', dp.k)
            dewpoint=int(convertfbunits(dp.k, 1))
            dewpoint1hr = str(dewpoint * 10).zfill(4)
            dewpoint = str(dewpoint).zfill(2)


            
          # calculate heat_index
          if tempF != '---' and  humidity100 != '---':        
            hi= heat_index(temperature=tempF, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated heat_index %s:', hi.k)
            heatindex=convertfbunits(hi.k,  convertunittype('temperature', units))

            
          # calculate feels_like
          if tempF != '---' and  humidity100 != '---' and  windmph != '---':
            fl = feels_like(temperature=tempF, humidity= humidity100 , wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated feels_like  %s:', fl.k)
            feelslike=convertfbunits(fl.k,  convertunittype('temperature', units))

          # calculate Wind Chill
          """
          if tempF != '---' and  windmph != '---':
            wc = wind_chill(temperature=tempF, wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated wind chill %s:', wc.k)
            windchill=convertfbunits(wc.k,  convertunittype('temperature', units))
          """ 

        except AttributeError, e:
          log.info('freeboard_environmental_calculated: AttributeError in calculated %s:  ' % str(e))
          
        except TypeError, e:
          log.info('freeboard_environmental_calculated: TypeError in calculated %s:  ' % str(e))
          
        except ValueError, e:
          log.info('freeboard_environmental_calculated: ValueError in calculated %s:  ' % str(e))            
          
        except NameError, e:
          log.info('freeboard_environmental_calculated: NameError in calculated %s:  ' % str(e))           

        except IndexError, e:
          log.info('freeboard_environmental_calculated: IndexError in calculated %s:  ' % str(e))
          
        except:
          e = sys.exc_info()[0]
          log.info('freeboard_environmental_calculated: Error in geting calculated ststs %s:  ' % e)



        
        #mydatetimestr = str(point['time'])

        #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      #log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)

      """
      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'air_temperature'
      val_to_write =float(value1)

      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

       """     

      callback = request.args.get('callback')
      myjsondatetz = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      myjsondatetz = mydatetime.strftime("%d%H%M")

      stationid = devicename[0:4]

      if Interval == '1hour':
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s RMK T%s%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure, temperature1hr, dewpoint1hr))
        
      else:
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure))
        
      return metarstr


    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      log.info('freeboard_environmental: ValueError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: ValueError in freeboard_environmental point%s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: NameError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      log.info('freeboard_environmental: IndexError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: IndexError in freeboard_environmental %s:  ' % str(e))
      
    except pyonep.exceptions.JsonRPCRequestException as ex:
        print('JsonRPCRequestException: {0}'.format(ex))
        
    except pyonep.exceptions.JsonRPCResponseException as ex:
        print('JsonRPCResponseException: {0}'.format(ex))
        
    except pyonep.exceptions.OnePlatformException as ex:
        print('OnePlatformException: {0}'.format(ex))
       
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })



def degToCompass(num):
    val=int((num/22.5)+.5)
    arr=["N","NNE","NE","ENE","E","ESE", "SE", "SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return arr[(val % 16)]


def wind_deg_to_compass(deg):
  if    deg >= 0.0 and deg < 11.25: return 'NNE'
  elif deg >=  11.25 and deg <  33.75: return 'NNE'
  elif deg >=  33.75 and deg <  56.25: return 'NE'
  elif deg >=  56.25 and deg <  78.75: return 'ENE'
  elif deg >=  78.75 and deg < 101.25: return 'E'
  elif deg >= 101.25 and deg < 123.75: return 'ESE'
  elif deg >= 123.75 and deg < 146.25: return 'SE'
  elif deg >= 146.25 and deg < 168.75: return 'SSE'
  elif deg >= 168.75 and deg < 191.25: return 'S'
  elif deg >= 191.25 and deg < 213.75: return 'SSW'
  elif deg >= 213.75 and deg < 236.25: return 'SW'
  elif deg >= 236.25 and deg < 258.75: return 'WSW'
  elif deg >= 258.75 and deg < 281.25: return 'W'
  elif deg >= 281.25 and deg < 303.75: return 'WNW'
  elif deg >= 303.75 and deg < 326.25: return 'NW'
  elif deg >= 326.25 and deg < 348.75: return 'NNW'
  elif deg >= 348.75 and deg < 359.99: return 'N'
  else: return ''

@app.route('/helmsmart_environmental_baroncsv')
@cross_origin()
def helmsmart_environmental_baroncsv():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"1min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    env_type = request.args.get('type',"outside")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]
    #resolution = 60


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'

    temperature=[]
    atmospheric_pressure=[]
    humidity=[]
    wind_speed=[]
    
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

    devicename = getedevicename(deviceapikey)
    
    log.info("freeboard devicename %s", devicename)

    if devicename == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'devicename error' })




    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    if env_type == "inside":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Inside Temperature' OR type='Inside Humidity')"

    elif env_type == "inside mesh":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='" + Instance + "' "

      
    elif env_type == "sea":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Sea Temperature' OR type='Inside Humidity')"

      
    else:
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"




      
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude, median(wind_speed) AS  wind_speed , median(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
        query = ('select  max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity, max(altitude) AS altitude, max(wind_speed) AS  wind_speed , max(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
        query = ('select  min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity, min(altitude) AS altitude, min(wind_speed) AS  wind_speed , min(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

        
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity, mean(altitude) AS altitude, mean(wind_speed) AS  wind_speed , mean(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 

    """
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 
    """    

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      temperature=""
      atmospheric_pressure=""
      atmospheric_pressure_sea=""
      humidity=""
      altitude=""
      windchill=""
      wind_speed=""
      wind_dir=""
      wind_gust=""
      heatindex=""
      dewpoint=""
      feelslike=""
      rain=""
      temphigh=""
      templow=""

      

      
      ts =startepoch*1000


      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        tempF='---'
        tempC='---'
        humidity100='---'
        windmph='---'
        winddir='---'
      
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          temperature = convertfbunits(point['temperature'],  0)   
          temperature1hr = str(temperature * 10 ).zfill(4)
          #temperature = str(temperature).zfill(2)

          tempF=convertfbunits(point['temperature'],  0)
          tempC=convertfbunits(point['temperature'],  1)          

          
        if point['atmospheric_pressure'] is not None:         
          atmospheric_pressure = ((convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))) )
          #atmospheric_pressure = str(atmospheric_pressure).zfill(4)
                    
        if point['humidity'] is not None:         
          humidity = convertfbunits(point['humidity'], 26)
          humidity100 = convertfbunits(point['humidity'], 26)


                    
        if point['altitude'] is not None:         
          altitude = convertfbunits(point['altitude'], 32)


        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value2 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value4 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value5 = getAtmosphericCompensation(value4)
          #add offset if any in KPa
          atmospheric_pressure_sea = int((convertfbunits(value2 + value5, convertunittype('baro_pressure', units))) )
          
   
 

        if point['wind_speed'] is not None:         
          wind_speed = convertfbunits(point['wind_speed'], 4)
          windmph = int(convertfbunits(point['wind_speed'], 5))
          #wind_speed =str(wind_speed).zfill(2)
       

        if point['wind_direction'] is not None:         
          wind_dir = int(convertfbunits(point['wind_direction'], 16))
          #wind_dir = str(degToCompass(wind_dir))
          wind_dir = str(wind_deg_to_compass(wind_dir))
          #wind_dir =str(wind_dir).zfill(3)

        try:

          # calculate dew_point
          if tempC != '---' and  humidity100 != '---':
            #dp = dew_point(temperature=tempF, humidity=humidity100)
            dp = dew_point(temperature=tempC, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated dew_point  %s:', dp.k)
            dewpoint=int(convertfbunits(dp.k, 0))
            dewpoint1hr = str(dewpoint * 10).zfill(4)
            dewpoint = str(dewpoint).zfill(2)


            
          # calculate heat_index
          if tempF != '---' and  humidity100 != '---':        
            hi= heat_index(temperature=tempF, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated heat_index %s:', hi.k)
            heatindex=convertfbunits(hi.k,  0)

            
          # calculate feels_like
          if tempF != '---' and  humidity100 != '---' and  windmph != '---':
            fl = feels_like(temperature=tempF, humidity= humidity100 , wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated feels_like  %s:', fl.k)
            #feelslike=convertfbunits(fl.k,  convertunittype('temperature', units))
            feelslike=convertfbunits(fl.k,  0)

          # calculate Wind Chill
          """
          if tempF != '---' and  windmph != '---':
            if temperature < 50 and wind_speed > 3:
              wc = wind_chill(temperature=tempF, wind_speed=windmph)
              log.info('freeboard:  freeboard_environmental_calculated wind chill %s:', wc.k)
              windchill=convertfbunits(wc.k,  convertunittype('temperature', units))
          """ 

        except AttributeError, e:
          log.info('freeboard_environmental_calculated: AttributeError in calculated %s:  ' % str(e))
          
        except TypeError, e:
          log.info('freeboard_environmental_calculated: TypeError in calculated %s:  ' % str(e))
          
        except ValueError, e:
          log.info('freeboard_environmental_calculated: ValueError in calculated %s:  ' % str(e))            
          
        except NameError, e:
          log.info('freeboard_environmental_calculated: NameError in calculated %s:  ' % str(e))           

        except IndexError, e:
          log.info('freeboard_environmental_calculated: IndexError in calculated %s:  ' % str(e))
          
        except:
          e = sys.exc_info()[0]
          log.info('freeboard_environmental_calculated: Error in geting calculated ststs %s:  ' % e)



        
        #mydatetimestr = str(point['time'])

        #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      #log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)

      """
      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'air_temperature'
      val_to_write =float(value1)

      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

       """     

      callback = request.args.get('callback')
      #myjsondatetz = mydatetime.strftime("%m %d, %Y %H:%M:%S")
      #myjsondatetz = mydatetime.strftime("%d%H%M")

      mycsvdate = mydatetime.strftime("%m/%d/%Y")
      mycsvtime = mydatetime.strftime("%H:%M:%S")
      mycsvtime = mydatetime.strftime("%H:%M")
 
      stationid = devicename[0:4]

      """
      if Interval == '1hour':
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s RMK T%s%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure, temperature1hr, dewpoint1hr))
        
      else:
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure))
        
      return metarstr

      """

      #csvstr ="ID,DATE,TIME,TEMP,RH,DEWPT,WINDCHILL,HEATINDEX,WDIR,WSPEED,WGUST,PRESSURE,PRECIP,HIGH,LOW\r\n"


      #csvstr = ('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\r\n' %  (stationid, mycsvdate, mycsvtime , temperature, humidity, dewpoint, windchill, heatindex, wind_dir, wind_speed, wind_gust, atmospheric_pressure, rain, temphigh, templow))

      csvstr = "ALBN,05/27/2020,12:20,76.0,68.0,64.0,76,76,S,7,12,,0.1,79,64"
      
      csvstr = "ALBN,05/27/2020,12:20,76.0,68.0,64.0,76,76,S,7,12,,0.1,79,64"

      csvstr = ('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' %  (stationid, mycsvdate, mycsvtime, temperature, humidity,dewpoint, windchill, heatindex, wind_dir, wind_speed, wind_gust, atmospheric_pressure,rain, temphigh, templow  ))

        
      csvout =  "ID,DATE,TIME,TEMP,RH,DEWPT,WINDCHILL,HEATINDEX,WDIR,WSPEED,WGUST,PRESSURE,PRECIP,HIGH,LOW" + '\r\n' + csvstr + '\r\n'


      return csvout


    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      log.info('freeboard_environmental: ValueError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: ValueError in freeboard_environmental point%s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: NameError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      log.info('freeboard_environmental: IndexError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: IndexError in freeboard_environmental %s:  ' % str(e))
      
    except pyonep.exceptions.JsonRPCRequestException as ex:
        print('JsonRPCRequestException: {0}'.format(ex))
        
    except pyonep.exceptions.JsonRPCResponseException as ex:
        print('JsonRPCResponseException: {0}'.format(ex))
        
    except pyonep.exceptions.OnePlatformException as ex:
        print('OnePlatformException: {0}'.format(ex))
       
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })


@app.route('/helmsmart_environmental_nmea0183')
@cross_origin()
def helmsmart_environmental_nmea0183():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"1min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    env_type = request.args.get('type',"outside")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]
    #resolution = 60


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'

    temperature=[]
    atmospheric_pressure=[]
    humidity=[]
    wind_speed=[]
    
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

    devicename = getedevicename(deviceapikey)
    
    log.info("freeboard devicename %s", devicename)

    if devicename == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'devicename error' })




    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    if env_type == "inside":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Inside Temperature' OR type='Inside Humidity')"

    elif env_type == "inside mesh":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='" + Instance + "' "

      
    elif env_type == "sea":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Sea Temperature' OR type='Inside Humidity')"

      
    else:
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"




      
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude, median(wind_speed) AS  wind_speed , median(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
        query = ('select  max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity, max(altitude) AS altitude, max(wind_speed) AS  wind_speed , max(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
        query = ('select  min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity, min(altitude) AS altitude, min(wind_speed) AS  wind_speed , min(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

        
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity, mean(altitude) AS altitude, mean(wind_speed) AS  wind_speed , mean(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 

    """
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 
    """    

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      temperature=""
      atmospheric_pressure=""
      atmospheric_pressure_sea=""
      humidity=""
      altitude=""
      windchill=""
      wind_speed=""
      wind_dir=""
      wind_gust=""
      heatindex=""
      dewpoint=""
      feelslike=""
      rain=""
      temphigh=""
      templow=""

      

      
      ts =startepoch*1000


      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        tempF='---'
        tempC='---'
        humidity100='---'
        windmph='---'
        winddir='---'
      
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          temperature = convertfbunits(point['temperature'],  0)   
          temperature1hr = str(temperature * 10 ).zfill(4)
          #temperature = str(temperature).zfill(2)

          tempF=convertfbunits(point['temperature'],  0)
          tempC=convertfbunits(point['temperature'],  1)          

          
        if point['atmospheric_pressure'] is not None:         
          atmospheric_pressure = ((convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))) )
          #atmospheric_pressure = str(atmospheric_pressure).zfill(4)
                    
        if point['humidity'] is not None:         
          humidity = convertfbunits(point['humidity'], 26)
          humidity100 = convertfbunits(point['humidity'], 26)


                    
        if point['altitude'] is not None:         
          altitude = convertfbunits(point['altitude'], 32)


        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value2 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value4 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value5 = getAtmosphericCompensation(value4)
          #add offset if any in KPa
          atmospheric_pressure_sea = int((convertfbunits(value2 + value5, convertunittype('baro_pressure', units))) )
          
   
 

        if point['wind_speed'] is not None:         
          wind_speed = convertfbunits(point['wind_speed'], 4)
          windmph = int(convertfbunits(point['wind_speed'], 5))
          #wind_speed =str(wind_speed).zfill(2)
       

        if point['wind_direction'] is not None:         
          wind_dir = int(convertfbunits(point['wind_direction'], 16))
          #wind_dir = str(degToCompass(wind_dir))
          wind_dir = str(wind_deg_to_compass(wind_dir))
          #wind_dir =str(wind_dir).zfill(3)

        try:

          # calculate dew_point
          if tempC != '---' and  humidity100 != '---':
            #dp = dew_point(temperature=tempF, humidity=humidity100)
            dp = dew_point(temperature=tempC, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated dew_point  %s:', dp.k)
            dewpoint=int(convertfbunits(dp.k, 0))
            dewpoint1hr = str(dewpoint * 10).zfill(4)
            dewpoint = str(dewpoint).zfill(2)


            
          # calculate heat_index
          if tempF != '---' and  humidity100 != '---':        
            hi= heat_index(temperature=tempF, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated heat_index %s:', hi.k)
            heatindex=convertfbunits(hi.k,  0)

            
          # calculate feels_like
          if tempF != '---' and  humidity100 != '---' and  windmph != '---':
            fl = feels_like(temperature=tempF, humidity= humidity100 , wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated feels_like  %s:', fl.k)
            #feelslike=convertfbunits(fl.k,  convertunittype('temperature', units))
            feelslike=convertfbunits(fl.k,  0)

          # calculate Wind Chill
          """
          if tempF != '---' and  windmph != '---':
            if temperature < 50 and wind_speed > 3:
              wc = wind_chill(temperature=tempF, wind_speed=windmph)
              log.info('freeboard:  freeboard_environmental_calculated wind chill %s:', wc.k)
              windchill=convertfbunits(wc.k,  convertunittype('temperature', units))
          """ 

        except AttributeError, e:
          log.info('freeboard_environmental_calculated: AttributeError in calculated %s:  ' % str(e))
          
        except TypeError, e:
          log.info('freeboard_environmental_calculated: TypeError in calculated %s:  ' % str(e))
          
        except ValueError, e:
          log.info('freeboard_environmental_calculated: ValueError in calculated %s:  ' % str(e))            
          
        except NameError, e:
          log.info('freeboard_environmental_calculated: NameError in calculated %s:  ' % str(e))           

        except IndexError, e:
          log.info('freeboard_environmental_calculated: IndexError in calculated %s:  ' % str(e))
          
        except:
          e = sys.exc_info()[0]
          log.info('freeboard_environmental_calculated: Error in geting calculated ststs %s:  ' % e)



        
        #mydatetimestr = str(point['time'])

        #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      #log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)

      """
      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'air_temperature'
      val_to_write =float(value1)

      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

       """     

      callback = request.args.get('callback')
      #myjsondatetz = mydatetime.strftime("%m %d, %Y %H:%M:%S")
      #myjsondatetz = mydatetime.strftime("%d%H%M")

      mycsvdate = mydatetime.strftime("%m/%d/%Y")
      mycsvtime = mydatetime.strftime("%H:%M:%S")
      mycsvtime = mydatetime.strftime("%H:%M")
 
      stationid = devicename[0:4]

      """
      if Interval == '1hour':
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s RMK T%s%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure, temperature1hr, dewpoint1hr))
        
      else:
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure))
        
      return metarstr

      """

      #csvstr ="ID,DATE,TIME,TEMP,RH,DEWPT,WINDCHILL,HEATINDEX,WDIR,WSPEED,WGUST,PRESSURE,PRECIP,HIGH,LOW\r\n"


      #csvstr = ('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\r\n' %  (stationid, mycsvdate, mycsvtime , temperature, humidity, dewpoint, windchill, heatindex, wind_dir, wind_speed, wind_gust, atmospheric_pressure, rain, temphigh, templow))

      #csvstr = "ALBN,05/27/2020,12:20,76.0,68.0,64.0,76,76,S,7,12,,0.1,79,64"
      
      #csvstr = "ALBN,05/27/2020,12:20,76.0,68.0,64.0,76,76,S,7,12,,0.1,79,64"

      csvstr = ('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' %  (stationid, mycsvdate, mycsvtime, temperature, humidity,dewpoint, windchill, heatindex, wind_dir, wind_speed, wind_gust, atmospheric_pressure,rain, temphigh, templow  ))

      checksum =0

      for c in csvstr:
        checksum ^= ord(c)

      #checksumstr = format(checksum, "02X")
      checksumstr = ('%02X' % checksum)
      
      #csvout =  "ID,DATE,TIME,TEMP,RH,DEWPT,WINDCHILL,HEATINDEX,WDIR,WSPEED,WGUST,PRESSURE,PRECIP,HIGH,LOW" + '\r\n' + csvstr + '\r\n'
      csvout =  "$"  + csvstr + '*' + checksumstr + '\r\n'


      return csvout


    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      log.info('freeboard_environmental: ValueError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: ValueError in freeboard_environmental point%s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: NameError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      log.info('freeboard_environmental: IndexError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: IndexError in freeboard_environmental %s:  ' % str(e))
      
    except pyonep.exceptions.JsonRPCRequestException as ex:
        print('JsonRPCRequestException: {0}'.format(ex))
        
    except pyonep.exceptions.JsonRPCResponseException as ex:
        print('JsonRPCResponseException: {0}'.format(ex))
        
    except pyonep.exceptions.OnePlatformException as ex:
        print('OnePlatformException: {0}'.format(ex))
       
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/helmsmart_environmental_baroncsv_text')
@cross_origin()
def helmsmart_environmental_baroncsv_text():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"1min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    env_type = request.args.get('type',"outside")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]
    #resolution = 60


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'

    temperature=[]
    atmospheric_pressure=[]
    humidity=[]
    wind_speed=[]
    
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

    devicename = getedevicename(deviceapikey)
    
    log.info("freeboard devicename %s", devicename)

    if devicename == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'devicename error' })




    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    if env_type == "inside":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Inside Temperature' OR type='Inside Humidity')"

    elif env_type == "inside mesh":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='" + Instance + "' "

      
    elif env_type == "sea":
      serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Sea Temperature' OR type='Inside Humidity')"

      
    else:
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"




      
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude, median(wind_speed) AS  wind_speed , median(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
        query = ('select  max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity, max(altitude) AS altitude, max(wind_speed) AS  wind_speed , max(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
        query = ('select  min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity, min(altitude) AS altitude, min(wind_speed) AS  wind_speed , min(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

        
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity, mean(altitude) AS altitude, mean(wind_speed) AS  wind_speed , mean(wind_direction) AS  wind_direction from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 

    """
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 
    """    

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing', 'update':'False','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      temperature=""
      atmospheric_pressure=""
      atmospheric_pressure_sea=""
      humidity=""
      altitude=""
      windchill=""
      wind_speed=""
      wind_dir=""
      wind_gust=""
      heatindex=""
      dewpoint=""
      feelslike=""
      rain=""
      temphigh=""
      templow=""

      

      
      ts =startepoch*1000


      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        tempF='---'
        tempC='---'
        humidity100='---'
        windmph='---'
        winddir='---'
      
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          temperature = convertfbunits(point['temperature'],  0)   
          temperature1hr = str(temperature * 10 ).zfill(4)
          #temperature = str(temperature).zfill(2)

          tempF=convertfbunits(point['temperature'],  0)
          tempC=convertfbunits(point['temperature'],  1)          

          
        if point['atmospheric_pressure'] is not None:         
          atmospheric_pressure = ((convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))) )
          #atmospheric_pressure = str(atmospheric_pressure).zfill(4)
                    
        if point['humidity'] is not None:         
          humidity = convertfbunits(point['humidity'], 26)
          humidity100 = convertfbunits(point['humidity'], 26)


                    
        if point['altitude'] is not None:         
          altitude = convertfbunits(point['altitude'], 32)


        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value2 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value4 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value5 = getAtmosphericCompensation(value4)
          #add offset if any in KPa
          atmospheric_pressure_sea = int((convertfbunits(value2 + value5, convertunittype('baro_pressure', units))) )
          
   
 

        if point['wind_speed'] is not None:         
          wind_speed = convertfbunits(point['wind_speed'], 4)
          windmph = int(convertfbunits(point['wind_speed'], 5))
          #wind_speed =str(wind_speed).zfill(2)
       

        if point['wind_direction'] is not None:         
          wind_dir = int(convertfbunits(point['wind_direction'], 16))
          #wind_dir = str(degToCompass(wind_dir))
          wind_dir = str(wind_deg_to_compass(wind_dir))
          #wind_dir =str(wind_dir).zfill(3)

        try:

          # calculate dew_point
          if tempC != '---' and  humidity100 != '---':
            #dp = dew_point(temperature=tempF, humidity=humidity100)
            dp = dew_point(temperature=tempC, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated dew_point  %s:', dp.k)
            dewpoint=int(convertfbunits(dp.k, 0))
            dewpoint1hr = str(dewpoint * 10).zfill(4)
            dewpoint = str(dewpoint).zfill(2)


            
          # calculate heat_index
          if tempF != '---' and  humidity100 != '---':        
            hi= heat_index(temperature=tempF, humidity=humidity100)
            log.info('freeboard:  freeboard_environmental_calculated heat_index %s:', hi.k)
            heatindex=convertfbunits(hi.k,  0)

            
          # calculate feels_like
          if tempF != '---' and  humidity100 != '---' and  windmph != '---':
            fl = feels_like(temperature=tempF, humidity= humidity100 , wind_speed=windmph)
            log.info('freeboard:  freeboard_environmental_calculated feels_like  %s:', fl.k)
            #feelslike=convertfbunits(fl.k,  convertunittype('temperature', units))
            feelslike=convertfbunits(fl.k,  0)

          # calculate Wind Chill
          """
          if tempF != '---' and  windmph != '---':
            if temperature < 50 and wind_speed > 3:
              wc = wind_chill(temperature=tempF, wind_speed=windmph)
              log.info('freeboard:  freeboard_environmental_calculated wind chill %s:', wc.k)
              windchill=convertfbunits(wc.k,  convertunittype('temperature', units))
          """ 

        except AttributeError, e:
          log.info('freeboard_environmental_calculated: AttributeError in calculated %s:  ' % str(e))
          
        except TypeError, e:
          log.info('freeboard_environmental_calculated: TypeError in calculated %s:  ' % str(e))
          
        except ValueError, e:
          log.info('freeboard_environmental_calculated: ValueError in calculated %s:  ' % str(e))            
          
        except NameError, e:
          log.info('freeboard_environmental_calculated: NameError in calculated %s:  ' % str(e))           

        except IndexError, e:
          log.info('freeboard_environmental_calculated: IndexError in calculated %s:  ' % str(e))
          
        except:
          e = sys.exc_info()[0]
          log.info('freeboard_environmental_calculated: Error in geting calculated ststs %s:  ' % e)



        
        #mydatetimestr = str(point['time'])

        #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      #log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)

      """
      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'air_temperature'
      val_to_write =float(value1)

      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

       """     

      callback = request.args.get('callback')
      #myjsondatetz = mydatetime.strftime("%m %d, %Y %H:%M:%S")
      #myjsondatetz = mydatetime.strftime("%d%H%M")

      mycsvdate = mydatetime.strftime("%m/%d/%Y")
      mycsvtime = mydatetime.strftime("%H:%M:%S")
      mycsvtime = mydatetime.strftime("%H:%M")
 
      stationid = devicename[0:4]

      """
      if Interval == '1hour':
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s RMK T%s%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure, temperature1hr, dewpoint1hr))
        
      else:
        metarstr = ('METAR %s %sZ AUTO %s%sKT %s/%s A%s' %  (stationid, myjsondatetz,  wind_dir, wind_speed, temperature, dewpoint, atmospheric_pressure))
        
      return metarstr

      """

      #csvstr ="ID,DATE,TIME,TEMP,RH,DEWPT,WINDCHILL,HEATINDEX,WDIR,WSPEED,WGUST,PRESSURE,PRECIP,HIGH,LOW\r\n"


      csvstr = ('%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\r\n' %  (stationid, mycsvdate, mycsvtime , temperature, humidity, dewpoint, windchill, heatindex, wind_dir, wind_speed, wind_gust, atmospheric_pressure, rain, temphigh, templow))
        
      csvout =  "ID,DATE,TIME,TEMP,RH,DEWPT,WINDCHILL,HEATINDEX,WDIR,WSPEED,WGUST,PRESSURE,PRECIP,HIGH,LOW" + '\r\n' + csvstr + '\r\n'

      response = make_response(csvout)
      response.headers['Content-Type'] = 'text/csv'
      return response


    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      log.info('freeboard_environmental: ValueError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]

      log.info('freeboard_environmental: ValueError in freeboard_environmental point%s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: NameError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      log.info('freeboard_environmental: IndexError in freeboard_environmental point %s:  ', point)
      #e = sys.exc_info()[0]
      log.info('freeboard_environmental: IndexError in freeboard_environmental %s:  ' % str(e))
      
    except pyonep.exceptions.JsonRPCRequestException as ex:
        print('JsonRPCRequestException: {0}'.format(ex))
        
    except pyonep.exceptions.JsonRPCResponseException as ex:
        print('JsonRPCResponseException: {0}'.format(ex))
        
    except pyonep.exceptions.OnePlatformException as ex:
        print('OnePlatformException: {0}'.format(ex))
       
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })





@app.route('/freeboard_weather')
@cross_origin()
def freeboard_weather():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    windtype = request.args.get('type',"true")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    wind_speed=[]
    wind_direction=[]
    temperature=[]
    atmospheric_pressure=[]
    atmospheric_pressure_sea=[]
    humidity=[]
    altitude=[]
      
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    
    if  windtype =="apparent":
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"

    else  :
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      #serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND type='TWIND True North' "
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='TWIND True North' OR type='Outside Temperature' OR type='Outside Humidity')"
  
    #serieskeys= serieskeys +  " sensor='wind_data'  "


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
      
      query = ('select  median(wind_direction) AS wind_direction, median(wind_speed) AS  wind_speed, median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
      
    elif mode == "max":
      
      query = ('select  max(wind_direction) AS wind_direction, max(wind_speed) AS  wind_speed, max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity , max(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

      
    elif mode == "min":
      
      query = ('select  min(wind_direction) AS wind_direction, min(wind_speed) AS  wind_speed, min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity , min(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)      
      
    else:       
      query = ('select  mean(wind_direction) AS wind_direction, mean(wind_speed) AS  wind_speed, mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity , mean(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        
        if  windtype =="apparent":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
      
        if  windtype =="apparent":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
   

      

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)


    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      wind_speed=[]
      wind_direction=[]

      ts =startepoch*1000
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'
        
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['wind_speed'] is not None:       
          value1 = convertfbunits(point['wind_speed'],  convertunittype('speed', units))
        wind_speed.append({'epoch':ts, 'value':value1})
          
        if point['wind_direction'] is not None:       
          value2 = convertfbunits(point['wind_direction'], 16)
        wind_direction.append({'epoch':ts, 'value':value2})

        if point['temperature'] is not None: 
          value3 = convertfbunits(point['temperature'],  convertunittype('temperature', units))
        temperature.append({'epoch':ts, 'value':value3})
          
        if point['atmospheric_pressure'] is not None:         
          value4 = convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))
        atmospheric_pressure.append({'epoch':ts, 'value':value4})
                    
        if point['humidity'] is not None:         
          value5 = convertfbunits(point['humidity'], 26)
        humidity.append({'epoch':ts, 'value':value5})

                    
        if point['altitude'] is not None:         
          value6 = convertfbunits(point['altitude'], 32)
        altitude.append({'epoch':ts, 'value':value6})

        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value4 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value6 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value7 = getAtmosphericCompensation(value6)
          #add offset if any in KPa
          value7 = convertfbunits(value4 + value7, convertunittype('baro_pressure', units))
          
        atmospheric_pressure_sea.append({'epoch':ts, 'value':value7})    



        
       

      callback = request.args.get('callback')
      myjsondate = mydatetimetz.strftime("%B %d, %Y %H:%M:%S")

      
      if  windtype =="apparent":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)),'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)),'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
   

      

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })


@app.route('/freeboard_rain_gauge')
@cross_origin()
def freeboard_rain_gauge():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    windtype = request.args.get('type',"true")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    accumulation=[]
    duration=[]
    rate=[]
    peak=[]

      
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='rain_gauge' "
  
    #serieskeys= serieskeys +  " sensor='wind_data'  "


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
      
      query = ('select  median(accumulation) AS accumulation, median("duration") AS  "duration", median(rate) AS rate, median(peak) AS  peak from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
      
    elif mode == "max":
      
      query = ('select  max(accumulation) AS accumulation, max("duration") AS  "duration", max(rate) AS rate, max(peak) AS  peak  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

      
    elif mode == "min":
      
      query = ('select  min(accumulation) AS accumulation, min("duration") AS  "duration", min(rate) AS rate, min(peak) AS  peak from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)      
      
    else:       
      query = ('select  mean(accumulation) AS accumulation, mean("duration") AS  "duration", mean(rate) AS rate, mean(peak) AS  peak  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard_rain_gauge data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        

        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','accumulation':list(reversed(accumulation)), 'duration':list(reversed(duration)), 'rate':list(reversed(rate)), 'peak':list(reversed(peak))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
      

        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','accumulation':list(reversed(accumulation)), 'duration':list(reversed(duration)), 'rate':list(reversed(rate)), 'peak':list(reversed(peak))})     
   

      

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)


    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      accumulation=[]
      duration=[]
      duration_min=[]
      rate=[]
      peak=[]


      ts =startepoch*1000
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'
        
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['accumulation'] is not None:       
          value1 = convertfbunits((float(point['accumulation'])),  convertunittype('rain', units))
        accumulation.append({'epoch':ts, 'value':value1})
          
        if point['duration'] is not None:       
          value2 = convertfbunits(point['duration'], 37)
        duration.append({'epoch':ts, 'value':value2})

        if point['duration'] is not None:       
          #value5 = convertfbunits(point['duration'], 37)
          value5 = float("{0:.2f}".format(point['duration'] * 0.0166666))  
        duration_min.append({'epoch':ts, 'value':value5})

        if point['rate'] is not None: 
          value3 = convertfbunits((float(point['rate'])),  convertunittype('rain', units))
        rate.append({'epoch':ts, 'value':value3})
          
        if point['peak'] is not None:         
          value4 = convertfbunits((float(point['peak'])), convertunittype('rain', units))
        peak.append({'epoch':ts, 'value':value4})
                    
 

        
       

      callback = request.args.get('callback')
      myjsondate = mydatetimetz.strftime("%B %d, %Y %H:%M:%S")

      

      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','accumulation':list(reversed(accumulation)), 'duration':list(reversed(duration)), 'duration_minutes':list(reversed(duration_min)), 'rate':list(reversed(rate)), 'peak':list(reversed(peak))})     
   

      

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })






@app.route('/freeboard_rain_wung')
@cross_origin()
def freeboard_rain_wung():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')

    wunstation = request.args.get('wunstation','')
    wunpassword = request.args.get('wunpw','')
    
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    windtype = request.args.get('type',"true")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"last")
    
    response = None


    rain_hour=[]
    rain_day=[]

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='rain_gauge'"



    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    query = ('select  difference(last(accumulation)) AS accumulation from {} '
                   'where {} AND time > {}s and time < {}s '
                   'group by time({}s)  ') \
              .format( measurement, serieskeys,
                      startepoch, endepoch,
                      resolution)

  

    log.info("freeboard freeboard_rain_wung data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        

        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','accumulation':list(reversed(accumulation))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
      

        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','accumulation':list(reversed(accumulation))})     
   

      

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)


    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    
    try:
    
      strvalue = ""
      accumulation = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      wind_speed=[]
      wind_direction=[]

      ts =startepoch*1000
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'
        
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
          #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%S.%fZ')
          mydatetime = datetime.datetime.strptime(mydatetimestr[:19]+'Z', '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['accumulation'] is not None:

          accumulation = float("{0:.2f}".format(point['accumulation'] * 0.0393701))


        
       

      callback = request.args.get('callback')
      myjsondate = mydatetimetz.strftime("%B %d, %Y %H:%M:%S")


      # Setup Weather Underground Post
      if wunstation != "" and wunpassword != "":

        mywundate = mydatetimetz.strftime("%Y-%m-%d %H:%M:%S")
        
        devicedataurl = " https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php?ID=" + wunstation + "&PASSWORD=" + wunpassword + "&dateutc=" + str(mywundate)

 
        if accumulation != '---':        
          devicedataurl = devicedataurl + "&rainin=" + str(value1)

        
        devicedataurl = devicedataurl + "&action=updateraw" 

        

        log.info("freeboard_rain_wung:  WUNG HTTP GET: %s", devicedataurl)

        
        try:      
          headers = {'content-type': 'application/json'}
          response = requests.get(devicedataurl)

          if response.ok:
            log.info('freeboard_rain_wung:  WUNG HTTP GET OK %s: ', response.text )


          else:
            log.info('freeboard_rain_wung:  WUNG HTTP GET ERROR %s: ', response.text )


        except:
          e = sys.exc_info()[0]
          log.info("freeboard_rain_wung:: update_wun_url error: %s" % e)

      #End of  Weather Underground Post

      

        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','accumulation':list(reversed(accumulation))})    
   

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Error in geting freeboard response  %s:  ' % str(e))     

      e = sys.exc_info()[0]
      log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })
     
    
    except:
      log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
      e = sys.exc_info()[0]
      log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })






@app.route('/freeboard_weather_wung')
@cross_origin()
def freeboard_weather_wung():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')

    wunstation = request.args.get('wunstation','')
    wunpassword = request.args.get('wunpw','')
    
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    windtype = request.args.get('type',"true")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"last")
    
    response = None


    wind_speed=[]
    wind_direction=[]
    temperature=[]
    atmospheric_pressure=[]
    atmospheric_pressure_sea=[]
    humidity=[]
    altitude=[]
      
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    
    if  windtype =="apparent":
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='Apparent Wind'  OR type='Outside Temperature' OR type='Outside Humidity')"
      #serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"

    else  :
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      #serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND type='TWIND True North' "
      serieskeys= serieskeys +  " (sensor='wind_data' OR sensor='environmental_data') AND instance='0' AND (type='TWIND True North' OR type='Outside Temperature' OR type='Outside Humidity')"
  
    #serieskeys= serieskeys +  " sensor='wind_data'  "


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
      
      query = ('select  median(wind_direction) AS wind_direction, median(wind_speed) AS  wind_speed, median(temperature) AS temperature, median(atmospheric_pressure) AS  atmospheric_pressure, median(humidity) AS humidity , median(altitude) AS altitude from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
      
    elif mode == "max":
      
      query = ('select  max(wind_direction) AS wind_direction, max(wind_speed) AS  wind_speed, max(temperature) AS temperature, max(atmospheric_pressure) AS  atmospheric_pressure, max(humidity) AS humidity , max(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

      
    elif mode == "min":
      
      query = ('select  min(wind_direction) AS wind_direction, min(wind_speed) AS  wind_speed, min(temperature) AS temperature, min(atmospheric_pressure) AS  atmospheric_pressure, min(humidity) AS humidity , min(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)      
      
    elif mode == "mean":    
      query = ('select  mean(wind_direction) AS wind_direction, mean(wind_speed) AS  wind_speed, mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity , mean(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "last":        
      query = ('select  last(wind_direction) AS wind_direction, last(wind_speed) AS  wind_speed, last(temperature) AS temperature, last(atmospheric_pressure) AS  atmospheric_pressure, last(humidity) AS humidity , last(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch )


    else:       
      query = ('select  last(wind_direction) AS wind_direction, last(wind_speed) AS  wind_speed, last(temperature) AS temperature, last(atmospheric_pressure) AS  atmospheric_pressure, last(humidity) AS humidity , last(altitude) AS altitude  from {} '
                     'where {} AND time > {}s and time < {}s  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch )

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        
        if  windtype =="apparent":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
      
        if  windtype =="apparent":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)), 'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
   

      

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)


    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      wind_speed=[]
      wind_direction=[]

      ts =startepoch*1000
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'
        
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
          #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%S.%fZ')
          mydatetime = datetime.datetime.strptime(mydatetimestr[:19]+'Z', '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['wind_speed'] is not None:       
          value1 = convertfbunits(point['wind_speed'],  convertunittype('speed', units))
        wind_speed.append({'epoch':ts, 'value':value1})
          
        if point['wind_direction'] is not None:       
          value2 = convertfbunits(point['wind_direction'], 16)
        wind_direction.append({'epoch':ts, 'value':value2})

        if point['temperature'] is not None: 
          value3 = convertfbunits(point['temperature'],  convertunittype('temperature', units))
        temperature.append({'epoch':ts, 'value':value3})
          
        if point['atmospheric_pressure'] is not None:         
          value4 = convertfbunits(point['atmospheric_pressure'], convertunittype('baro_pressure', units))
        atmospheric_pressure.append({'epoch':ts, 'value':value4})
                    
        if point['humidity'] is not None:         
          value5 = convertfbunits(point['humidity'], 26)
        humidity.append({'epoch':ts, 'value':value5})

                    
        if point['altitude'] is not None:         
          value6 = convertfbunits(point['altitude'], 32)
        altitude.append({'epoch':ts, 'value':value6})

        if point['atmospheric_pressure'] is not None and point['altitude'] is not None:
          #get pressure in KPa
          value8 = convertfbunits(point['atmospheric_pressure'], 9)
          #get altitde in feet
          value6 = convertfbunits(point['altitude'], 32)
          # get adjustment for altitude in KPa
          value7 = getAtmosphericCompensation(value6)
          #add offset if any in KPa
          value7 = convertfbunits(value8 + value7, convertunittype('baro_pressure', units))
          
        atmospheric_pressure_sea.append({'epoch':ts, 'value':value7})    



        
       

      callback = request.args.get('callback')
      myjsondate = mydatetimetz.strftime("%B %d, %Y %H:%M:%S")


      # Setup Weather Underground Post
      if wunstation != "" and wunpassword != "":

        mywundate = mydatetimetz.strftime("%Y-%m-%d %H:%M:%S")
        
        devicedataurl = " https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php?ID=" + wunstation + "&PASSWORD=" + wunpassword + "&dateutc=" + str(mywundate)

        
        if value2 != '---':
          devicedataurl = devicedataurl + "&winddir=" + str(value2)
          
        if value1 != '---':        
          devicedataurl = devicedataurl + "&windspeedmph=" + str(value1)
          
        if value2 != '---':
          devicedataurl = devicedataurl + "&tempf=" + str(value3)
          
        if value4 != '---':
          devicedataurl = devicedataurl + "&baromin=" + str(value4)
          
        if value5 != '---':
          devicedataurl = devicedataurl + "&humidity=" + str(value5)
        
        devicedataurl = devicedataurl + "&action=updateraw" 

        

        log.info("freeboard_weather_wung:  WUNG HTTP GET: %s", devicedataurl)

        
        try:      
          headers = {'content-type': 'application/json'}
          response = requests.get(devicedataurl)

          if response.ok:
            log.info('freeboard_weather_wung:  WUNG HTTP GET OK %s: ', response.text )


          else:
            log.info('freeboard_weather_wung:  WUNG HTTP GET ERROR %s: ', response.text )


        except:
          e = sys.exc_info()[0]
          log.info("freeboard_weather_wung:: update_wun_url error: %s" % e)

      #End of  Weather Underground Post

      
      if  windtype =="apparent":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)),'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)),'temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity)), 'altitude':list(reversed(altitude)), 'atmospheric_pressure_sea':list(reversed(atmospheric_pressure_sea))})     
   

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Error in geting freeboard response  %s:  ' % str(e))     

      e = sys.exc_info()[0]
      log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })
     
    
    except:
      log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
      e = sys.exc_info()[0]
      log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })






@app.route('/freeboard_winddata')
@cross_origin()
def freeboard_winddata():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    windtype = request.args.get('type',"true")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    
    response = None


    wind_speed=[]
    wind_direction=[]
    wind_gusts=[]
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    
    if  windtype =="apparent":
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND (type='Apparent Wind' OR type='Gust' ) "
    else  :
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND (type='TWIND True North' OR type='Gust' ) "
  
    #serieskeys= serieskeys +  " sensor='wind_data'  "


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
      
      query = ('select  median(wind_direction) AS wind_direction, median(wind_speed) AS  wind_speed , median(wind_gusts) AS  wind_gusts from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
      
    elif mode == "max":
      
      query = ('select  max(wind_direction) AS wind_direction, max(wind_speed) AS  wind_speed , max(wind_gusts) AS  wind_gusts from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

      
    elif mode == "min":
      
      query = ('select  min(wind_direction) AS wind_direction, min(wind_speed) AS  wind_speed, min(wind_gusts) AS  wind_gusts from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)      
      
    else:       
      query = ('select  mean(wind_direction) AS wind_direction, mean(wind_speed) AS  wind_speed, mean(wind_gusts) AS  wind_gusts from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)  ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        
        if  windtype =="apparent":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction))})
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction))})
   


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
      
        if  windtype =="apparent":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction))})
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction))})
   

      

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)


    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      wind_speed=[]
      wind_direction=[]
      wind_gusts=[]

      ts =startepoch*1000
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['wind_speed'] is not None:       
          value1 = convertfbunits(point['wind_speed'],  convertunittype('speed', units))
        wind_speed.append({'epoch':ts, 'value':value1})
          
        if point['wind_direction'] is not None:       
          value2 = convertfbunits(point['wind_direction'], 16)
        wind_direction.append({'epoch':ts, 'value':value2})

        if point['wind_gusts'] is not None:       
          value3 = convertfbunits(point['wind_gusts'],  convertunittype('speed', units))
        wind_gusts.append({'epoch':ts, 'value':value3})
       

      callback = request.args.get('callback')
      myjsondate = mydatetimetz.strftime("%B %d, %Y %H:%M:%S")

      
      if  windtype =="apparent":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction)), 'windgusts':list(reversed(wind_gusts))})
      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)), 'windgusts':list(reversed(wind_gusts))})
   

      

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

@app.route('/freeboard_winddata_apparent')
@cross_origin()
def freeboard_winddata_apparent():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"5min")
    mytimezone = request.args.get('timezone',"UTC")
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"

    


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND type='Apparent Wind' "
    #serieskeys= serieskeys +  " sensor='wind_data'  "


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

  

      
    query = ('select  mean(wind_direction) AS wind_direction, mean(wind_speed) AS  wind_speed from {} '
                   'where {} AND time > {}s and time < {}s '
                   'group by time({}s)') \
              .format( measurement, serieskeys,
                      startepoch, endepoch,
                      resolution)
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)


    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
 
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = convertfbunits(point['wind_speed'],  4)
        value2 = convertfbunits(point['wind_direction'], 16)

        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', value1,value2)            

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','wind_speed':value1, 'wind_direction':value2,})
      

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
@app.route('/freeboard_environmental2')
@cross_origin()
def freeboard_environmental2():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"

    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


      

    query = ("select mean(value) from HelmSmart "
             "where  deviceid='001EC010AD69' and sensor='environmental_data' and time > {}s and time < {}s "
             "group by * limit 1") \
        .format(
                startepoch, endepoch
                )
    

    log.info("freeboard Get InfluxDB query %s", query)

    try:    
      result = dbc.query(query)

      log.info("freeboard Get InfluxDB results %s", result)

      keys = result.raw.get('series',[])
      #log.info("freeboard Get InfluxDB series keys %s", keys)

      """
      for series in response:
        #log.info("influxdb results..%s", series )
        for point in series['points']:
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val
      """  



      strvalue=""
      
      for series in keys:
        #log.info("freeboard Get InfluxDB series key %s", series)
        log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
        #log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
        #log.info("freeboard Get InfluxDB series values %s ", series['values'])
        values = series['values']
        for value in values:
          log.info("freeboard Get InfluxDB series time %s", value[0])
          log.info("freeboard Get InfluxDB series mean %s", value[1])

        for point in series['values']:
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val
            
        log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields['mean'])

        tag = series['tags']
        log.info("freeboard Get InfluxDB series tags2 %s ", tag)

        mydatetimestr = str(fields['time'])
        
        if tag['type'] == 'Outside Temperature' and tag['parameter']== 'temperature':
            value1 = convertfbunits(fields['mean'],  0)
            strvalue = strvalue + ':' + str(value1)
            
        elif tag['type']  == 'Outside Temperature' and tag['parameter'] == 'atmospheric_pressure':
            value2 = convertfbunits(fields['mean'], 10)
            strvalue = strvalue + ':' + str(value2)
            
        elif tag['type']  == 'Outside Humidity' and tag['parameter'] == 'humidity':
            value3=  convertfbunits(fields['mean'], 26)
            strvalue = strvalue + ':' + str(value3)

        log.info("freeboard Get InfluxDB series tags3 %s ", strvalue)


      mydatetimestr = mydatetimestr.split(".")
      log.info("freeboard Get InfluxDB time string%s ", mydatetimestr[0])


      #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%S.%fZ')
      mydatetime = datetime.datetime.strptime(mydatetimestr[0], '%Y-%m-%dT%H:%M:%S')
      
      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':value1, 'baro':value2, 'humidity':value3})

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', query)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

@app.route('/freeboard_winddataTrue')
@cross_origin()
def freeboard_winddataTrue():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    windtype = request.args.get('type',"true")
    Interval = request.args.get('Interval',"5min")

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"

    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='environmental_data' AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity')"
    #serieskeys= serieskeys +  " sensor='environmental_data'  AND type='Outside_Temperature'"
    #serieskeys= serieskeys +  " sensor='environmental_data'  "
    
    Key2="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:humidity.HelmSmart"
    Key3="deviceid:001EC010AD69.sensor:environmental_data.source:0.instance:0.type:Outside_Temperature.parameter:atmospheric_pressure.HelmSmart"



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


      

    query = ("select mean(value) from HelmSmart "
             "where  deviceid='001EC010AD69' and sensor='wind_data' and time > {}s and time < {}s "
             "group by * limit 1") \
        .format(
                startepoch, endepoch
                )
    

    log.info("freeboard Get InfluxDB query %s", query)

    try:    
      result = dbc.query(query)

      log.info("freeboard Get InfluxDB results %s", result)

      keys = result.raw.get('series',[])
      #log.info("freeboard Get InfluxDB series keys %s", keys)

      """
      for series in response:
        #log.info("influxdb results..%s", series )
        for point in series['points']:
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val
      """  



      strvalue=""
      
      for series in keys:
        #log.info("freeboard Get InfluxDB series key %s", series)
        log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
        #log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
        #log.info("freeboard Get InfluxDB series values %s ", series['values'])
        values = series['values']
        for value in values:
          log.info("freeboard Get InfluxDB series time %s", value[0])
          log.info("freeboard Get InfluxDB series mean %s", value[1])

        for point in series['values']:
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val
            
        log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields['mean'])

        tag = series['tags']
        log.info("freeboard Get InfluxDB series tags2 %s ", tag)

        mydatetimestr = str(fields['time'])
        


        if tag['type'] == 'TWIND True North' and tag['parameter'] == 'wind_speed':
            truewindspeed =  convertfbunits(fields['mean'], convertunittype('speed', units))
            strvalue = strvalue + ':' + str(truewindspeed)
            
        elif tag['type'] == 'Apparent Wind' and tag['parameter'] == 'wind_speed':
            appwindspeed =  convertfbunits(fields['mean'],  convertunittype('speed', units))
            strvalue = strvalue + ':' + str(appwindspeed)
            
        elif tag['type'] == 'TWIND True North' and tag['parameter'] == 'wind_direction':
            truewinddir=  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(truewinddir)
            
        elif tag['type'] == 'Apparent Wind' and tag['parameter'] == 'wind_direction':
            appwinddir =  convertfbunits(fields['mean'], 16)
            strvalue = strvalue + ':' + str(appwinddir)
            

        log.info("freeboard Get InfluxDB series tags3 %s ", strvalue)


      mydatetimestr = mydatetimestr.split(".")
      log.info("freeboard Get InfluxDB time string%s ", mydatetimestr[0])


      #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%S.%fZ')
      mydatetime = datetime.datetime.strptime(mydatetimestr[0], '%Y-%m-%dT%H:%M:%S')
      
      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','truewindspeed':truewindspeed,'appwindspeed':appwindspeed,'truewinddir':truewinddir, 'appwinddir':appwinddir})

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', query)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error',  update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/freeboard_location')
@cross_origin()
def freeboard_location():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    postype = request.args.get('type',"NULL")
    mytimezone = request.args.get('timezone',"UTC")
    
    response = None
    log.info("freeboard_location deviceapikey %s", deviceapikey)
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    lat=[]
    lng=[]
    position=[]
    siv=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")



    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='position_rapid' "
    serieskeys= serieskeys +  "  AND type='" + postype + "' "
 

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(lat) AS lat, median(lng) AS  lng  , median(siv) AS  siv from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(lat) AS lat, median(lng) AS  lng  , median(siv) AS  siv from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing', 'lat':list(reversed(lat)), 'lng':list(reversed(lng)), 'position':list(reversed(position)), 'siv':list(reversed(siv))})     



    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing', 'lat':list(reversed(lat)), 'lng':list(reversed(lng)), 'position':list(reversed(position)), 'siv':list(reversed(siv))})     


    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      lat=[]
      lng=[]
      position=[]
      siv=[]
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
       # log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        
        if (point['lat'] is not None)  :
          if (point['lng'] is not None) :
            
            value1 = convertfbunits(point['lat'], 15)
            #log.info("freeboard freeboard_location lat %s", value1)
            if abs(value1) > 0.1:
              #log.info("freeboard freeboard_location adding lat %s", value1)
              lat.append({'epoch':ts, 'value':value1})


            value2 = convertfbunits(point['lng'], 15)
            #log.info("freeboard freeboard_location lng %s", value2)
            if abs(value2) > 0.1:
              #log.info("freeboard freeboard_location adding lng %s", value2)
              lng.append({'epoch':ts, 'value':value2})

            #log.info("freeboard freeboard_location lat %s lng %s", value1, value2)
            if abs(value1) > 0.1 and abs(value2) > 0.1:
              #log.info("freeboard freeboard_location adding position %s", value2)
              position.append({'epoch':ts, 'lat':value1, 'lng':value2})


        if point['siv'] is not None:       
          value3 = int(point['siv'])
          siv.append({'epoch':ts, 'siv':value3})            
 
      """

      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'GPDdata'
      
      latDD=int(value1)
      lngDD=int(value2)
      #latMM = 60*(value1 - latDD)
      #lngMM = 60*(value2 - lngDD)
      
      latMM = float("{0:.4f}".format(60*(value1 - latDD)) )
      lngMM = float("{0:.4f}".format(60*(value2 - lngDD)) )

      latlng = str((latDD*100) + latMM) + "_" + str((lngDD*100) + lngMM)
      
      val_to_write =str(latlng)
      log.info('freeboard: after exosite latlng:%s', val_to_write)

      
      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

      """
      

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':list(reversed(lat)), 'lng':list(reversed(lng)), 'position':list(reversed(position)), 'siv':list(reversed(siv))})     
        

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/freeboard_location_wind')
@cross_origin()
def freeboard_location_wind():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    postype = request.args.get('type',"NULL")
    mytimezone = request.args.get('timezone',"UTC")
    units= request.args.get('units',"US")
    mode  = request.args.get('mode',"median")
    source  = request.args.get('source',"")

        
    response = None
    log.info("freeboard_location_wind deviceapikey %s", deviceapikey)
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    lat=[]
    lng=[]
    position=[]
    siv=[]
    wind_speed=[]
    wind_direction=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")



    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "

    if source != "":
      serieskeys= serieskeys + "source = '" + source + "' AND "

      
    serieskeys= serieskeys +  " sensor='position_rapid' OR sensor='wind_data'"
    serieskeys= serieskeys +  "  AND type='" + postype + "' OR type='TWIND True North' "
 

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  median(lat) AS lat, median(lng) AS  lng  , median(wind_direction) AS wind_direction, median(wind_speed) AS  wind_speed  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  median(lat) AS lat, median(lng) AS  lng  , median(wind_direction) AS wind_direction, median(wind_speed) AS  wind_speed  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing', 'lat':list(reversed(lat)), 'lng':list(reversed(lng)), 'position':list(reversed(position)), 'siv':list(reversed(siv))})     



    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing', 'lat':list(reversed(lat)), 'lng':list(reversed(lng)), 'position':list(reversed(position)), 'siv':list(reversed(siv))})     


    log.info('freeboard_location_wind:  InfluxDB-Cloud response  %s:', response)

    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      lat=[]
      lng=[]
      position=[]
      position_wind=[]
      wind_speed=[]
      wind_direction=[]
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
       # log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        
        if (point['lat'] is not None)  :
          if (point['lng'] is not None) :
            
            value1 = convertfbunits(point['lat'], 15)

            value2 = convertfbunits(point['lng'], 15)


            #log.info("freeboard freeboard_location lat %s lng %s", value1, value2)
            if abs(value1) > 0.1 and abs(value2) > 0.1:
              #log.info("freeboard freeboard_location adding position %s", value2)
              position.append({'epoch':ts, 'lat':value1, 'lng':value2})


              if point['wind_speed'] is not None:       
                value3 = convertfbunits(point['wind_speed'],  convertunittype('speed', units))
              wind_speed.append({'epoch':ts, 'value':value3})
                
              if point['wind_direction'] is not None:       
                value4 = convertfbunits(point['wind_direction'], 16)
              wind_direction.append({'epoch':ts, 'value':value4})

              position_wind.append({'epoch':ts, 'lat':value1, 'lng':value2, 'truewindspeed':value3, 'truewinddir':value4  })


       
 
      """

      log.info('freeboard: before exosite write:')
      o = onep.OnepV1()

      cik = '5b38da024d8a1f252e575202afb431ef22d3eb66'
      #dataport_alias = 'Device'
      #val_to_write = 'Data'
      dataport_alias = 'GPDdata'
      
      latDD=int(value1)
      lngDD=int(value2)
      #latMM = 60*(value1 - latDD)
      #lngMM = 60*(value2 - lngDD)
      
      latMM = float("{0:.4f}".format(60*(value1 - latDD)) )
      lngMM = float("{0:.4f}".format(60*(value2 - lngDD)) )

      latlng = str((latDD*100) + latMM) + "_" + str((lngDD*100) + lngMM)
      
      val_to_write =str(latlng)
      log.info('freeboard: after exosite latlng:%s', val_to_write)

      
      #testvar = o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      #log.info('freeboard: fter exosite write:%s', testvar)
      o.write(cik, {"alias": dataport_alias}, val_to_write,{})
      log.info('freeboard: after exosite write:')

      """
      

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'position':list(reversed(position)),'truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction)), 'location_wind':list(reversed(position_wind))})     
        

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/freeboard_nav')
@cross_origin()
def freeboard_nav():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    navtype = request.args.get('type',"true")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode = request.args.get('mode',"mean")
    
    response = None

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    cog=[]
    sog=[]
    heading=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

    
    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    if navtype == "magnetic":
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " (sensor='cogsog' OR sensor='heading') AND "
      serieskeys= serieskeys +  " (type='Magnetic') " 

    else:
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " (sensor='cogsog' OR sensor='heading') AND "
      serieskeys= serieskeys +  " (type='True') " 


    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


      

    if serieskeys.find("*") > 0:
      serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":      

      query = ('select  median(course_over_ground) AS cog, median(speed_over_ground) AS  sog, median(heading) AS heading  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
      
    elif mode == "max":      

      query = ('select  max(course_over_ground) AS cog, max(speed_over_ground) AS  sog, max(heading) AS heading  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
      
    elif mode == "min":      

      query = ('select  min(course_over_ground) AS cog, min(speed_over_ground) AS  sog, min(heading) AS heading  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)      
      
    else:
      
      query = ('select  mean(course_over_ground) AS cog, mean(speed_over_ground) AS  sog, mean(heading) AS heading  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        if navtype == "magnetic":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_mag':list(reversed(heading))})     
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_true':list(reversed(heading))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        if navtype == "magnetic":
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_mag':list(reversed(heading))})     
        else:
          return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_true':list(reversed(heading))})     


    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      
      cog=[]
      sog=[]
      heading=[]
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        
        if point['cog'] is not None: 
          value1 = convertfbunits(point['cog'], 16)
        cog.append({'epoch':ts, 'value':value1})
          
        if point['sog'] is not None:         
          value2 = convertfbunits(point['sog'], convertunittype('speed', units))
        sog.append({'epoch':ts, 'value':value2})
          
        if point['heading'] is not None:         
          value3 = convertfbunits(point['heading'], 16)
        heading.append({'epoch':ts, 'value':value3})
          


      #log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', value1,value2)            

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      if navtype == "magnetic":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_mag':list(reversed(heading))})     
      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_true':list(reversed(heading))})     
        

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/freeboard_water_depth')
@cross_origin()
def freeboard_water_depth():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    navtype = request.args.get('type',"Paddle Wheel")
    units= request.args.get('units',"US")
    dataformat = request.args.get('format', 'json')
    mytimezone = request.args.get('timezone',"UTC")
    mode = request.args.get('mode',"mean")
    
    response = None

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    depth=[]
    speed=[]
    temperature=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

    
    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    #serieskeys= serieskeys +  " (sensor='water_depth' )  "
    serieskeys= serieskeys +  " (sensor='water_depth' OR sensor='water_speed' OR sensor='temperature') AND "
    serieskeys= serieskeys +  " (type='Sea Temperature' OR type='Paddle Wheel' OR type='Correlation Log'  OR type='NULL' ) "

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


    if serieskeys.find("*") > 0:
      serieskeys = serieskeys.replace("*", ".*")

    if mode == "median":
      
      query = ('select  median(depth) AS depth, median(waterspeed) AS waterspeed, median(actual_temperature) AS temperature   from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "max":
      
      query = ('select  max(depth) AS depth, max(waterspeed) AS waterspeed, max(actual_temperature) AS temperature    from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)

    elif mode == "min":
      
      query = ('select  min(depth) AS depth, min(waterspeed) AS waterspeed, min(actual_temperature) AS temperature    from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)      
      
    else:

      query = ('select  mean(depth) AS depth, mean(waterspeed) AS waterspeed, mean(actual_temperature) AS temperature  from {} '            
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e: 
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #if navtype == "magnetic":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing', 'depth':list(reversed(depth)), 'speed':list(reversed(speed)), 'temperature':list(reversed(temperature))})    
        #else:
        #  return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_true':list(reversed(heading))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #if navtype == "magnetic":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'depth':list(reversed(depth)), 'speed':list(reversed(speed)), 'temperature':list(reversed(temperature))})    
        #else:
        #  return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_true':list(reversed(heading))})     


    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    #keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      
      depth=[]
      waterspeed=[]
      temperature=[]
 
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)
      csvout = "Time, Depth" + '\r\n'
      
      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'


        


        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        
        if point['depth'] is not None: 
          value1 = convertfbunits(point['depth'], convertunittype('depth', units))
        depth.append({'epoch':ts, 'value':value1})
        csvout = csvout + str(ts) + ', '+ str(value1)  + '\r\n'

        if point['waterspeed'] is not None:         
          value2 = convertfbunits(point['waterspeed'], convertunittype('speed', units))
        speed.append({'epoch':ts, 'value':value2})

          
        if point['temperature'] is not None:         
          value3 = convertfbunits(point['temperature'], convertunittype('temperature', units))
        temperature.append({'epoch':ts, 'value':value3})
               
        
        """                  
        if point['temperature'] is not None:          
          value3 = convertfbunits(point['temperature'], 0)
        temperature.append({'epoch':ts, 'value':value3})
        """              

      if dataformat == 'csv':
        response = make_response(csvout)
        response.headers['Content-Type'] = 'text/csv'
        response.headers["Content-Disposition"] = "attachment; filename=HelmSmart_WaterDepth.csv"
        return response

      #log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', value1,value2)
      
      #elif dataformat == 'json':
      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      #if navtype == "magnetic":
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','depth':list(reversed(depth)), 'speed':list(reversed(speed)), 'temperature':list(reversed(temperature))})     
      #else:
       # return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','cog':list(reversed(cog)), 'sog':list(reversed(sog)), 'heading_true':list(reversed(heading))})     
        

     
    except KeyError, e: 
       #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except TypeError, e: 
       #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))        
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)


        
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })






@app.route('/freeboard_attitude')
@cross_origin()
def freeboard_attitude():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode  = request.args.get('mode',"median")
    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    pitch=[]
    roll=[]
    yaw=[]      

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

    
    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='attitude' "
    #serieskeys= serieskeys +  " instance='" + Instance + "' "

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":
      
      query = ('select  median(pitch) AS pitch, median(roll) AS  roll, median(yaw) AS yaw  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    elif mode == "max":
      
      query = ('select  max(pitch) AS pitch, max(roll) AS  roll, max(yaw) AS yaw  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    elif mode == "min":
      
      query = ('select  min(pitch) AS pitch, min(roll) AS  roll, min(yaw) AS yaw  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    else:
      
      query = ('select  mean(pitch) AS pitch, mean(roll) AS  roll, mean(yaw) AS yaw  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing', 'update':'False', 'pitch':list(reversed(pitch)), 'roll':list(reversed(roll)), 'yaw':list(reversed(yaw))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing', 'update':'False', 'pitch':list(reversed(pitch)), 'roll':list(reversed(roll)), 'yaw':list(reversed(yaw))})     

    log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      
      pitch=[]
      roll=[]
      yaw=[]

      ts =startepoch*1000

      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'


        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['pitch'] is not None: 
          value1 = convertfbunits(point['pitch'], 16)
        pitch.append({'epoch':ts, 'value':value1})
          
        if point['roll'] is not None:         
          value2 = convertfbunits(point['roll'], 16)
        roll.append({'epoch':ts, 'value':value2})
          
        if point['yaw'] is not None:         
          value3 = convertfbunits(point['yaw'], 16)
        yaw.append({'epoch':ts, 'value':value3})
               

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':value1, 'current':value2, 'temperature':value3})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','pitch':list(reversed(pitch)), 'roll':list(reversed(roll)), 'yaw':list(reversed(yaw))})     
        

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })







@app.route('/freeboard_battery')
@cross_origin()
def freeboard_battery():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode  = request.args.get('mode',"median")
    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    voltage=[]
    current=[]
    temperature=[]
    stateofcharge=[]
    timeremaining=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

    
    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='battery_status'  AND "
    serieskeys= serieskeys +  " instance='" + Instance + "' "

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":
      
      query = ('select  median(voltage) AS voltage, median(current) AS  current, median(temperature) AS temperature,  median(stateofcharge) AS stateofcharge ,  median(timeremaining) AS timeremaining from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    elif mode == "max":
      
      query = ('select  max(voltage) AS voltage, max(current) AS  current, max(temperature) AS temperature,  max(stateofcharge) AS stateofcharge ,  max(timeremaining) AS timeremaining  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    elif mode == "min":
      
      query = ('select  min(voltage) AS voltage, min(current) AS  current, min(temperature) AS temperature,  min(stateofcharge) AS stateofcharge ,  min(timeremaining) AS timeremaining  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    else:
      
      query = ('select  mean(voltage) AS voltage, mean(current) AS  current, mean(temperature) AS temperature,  mean(stateofcharge) AS stateofcharge ,  mean(timeremaining) AS timeremaining  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing', 'update':'False', 'voltage':list(reversed(voltage)), 'current':list(reversed(current)), 'temperature':list(reversed(temperature)), 'stateofcharge':list(reversed(stateofcharge)), 'timeremaining':list(reversed(timeremaining))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing', 'update':'False', 'voltage':list(reversed(voltage)), 'current':list(reversed(current)), 'temperature':list(reversed(temperature)), 'stateofcharge':list(reversed(stateofcharge)), 'timeremaining':list(reversed(timeremaining))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      
      voltage=[]
      current=[]
      temperature=[]
      stateofcharge=[]
      timeremaining=[]

      ts =startepoch*1000

      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['voltage'] is not None: 
          value1 = convertfbunits(point['voltage'], convertunittype('volts', units))
        voltage.append({'epoch':ts, 'value':value1})
          
        if point['current'] is not None:         
          value2 = convertfbunits(point['current'], convertunittype('amps', units))
        current.append({'epoch':ts, 'value':value2})
          
        if point['temperature'] is not None:         
          value3 = convertfbunits(point['temperature'], convertunittype('temperature', units))
        temperature.append({'epoch':ts, 'value':value3})
                      
        if point['stateofcharge'] is not None:         
          value4 = convertfbunits(point['stateofcharge'], convertunittype('%', units))
        stateofcharge.append({'epoch':ts, 'value':value4})
          
        if point['timeremaining'] is not None:         
          value5 = convertfbunits(point['timeremaining'], convertunittype('time', units))
        timeremaining.append({'epoch':ts, 'value':value5})
               

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':value1, 'current':value2, 'temperature':value3})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':list(reversed(voltage)), 'current':list(reversed(current)), 'temperature':list(reversed(temperature)), 'stateofcharge':list(reversed(stateofcharge)), 'timeremaining':list(reversed(timeremaining))})     
        

     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })






@app.route('/freeboard_engine_aux')
@cross_origin()
def freeboard_engine_aux():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode =  request.args.get('mode',"mean")

    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    value5 = '---'
    value6 = '---'
    value7 = '---'
    value8 = '---'
    value9 = '---'

    boost_pressure=[]
    coolant_pressure=[]
    fuel_pressure=[]
    oil_temp=[]
    egt_temperature=[]
    fuel_rate_average=[]
    instantaneous_fuel_economy=[]
    #tilt_or_trim=[]
    throttle_position=[]
    fuel_used=[]    

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'   OR  sensor='trip_parameters_engine') AND "   
    serieskeys= serieskeys +  " (instance='" + Instance + "') "

    """
    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='temperature'  OR  sensor='trip_parameters_engine') AND "
    if Instance == 1:
      serieskeys= serieskeys +  " (type='NULL' OR type='Reserved 134')  AND "
    else:
      serieskeys= serieskeys +  " (type='NULL' OR type='Reserved 135')  AND "
      
    serieskeys= serieskeys +  " (instance='" + Instance + "') "
    """



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":
      query = ('select  median(throttle_position) AS throttle_position, median(boost_pressure) AS  boost_pressure, median(coolant_pressure) AS coolant_pressure, median(fuel_pressure) AS fuel_pressure, median(oil_temp) AS oil_temp ,  median(egt_temp) AS egt_temperature , median(fuel_rate_average) AS fuel_rate_average  , median(instantaneous_fuel_economy) AS instantaneous_fuel_economy  , median(trip_fuel_used) AS fuel_used from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    elif mode == "max":
      query = ('select  max(throttle_position) AS throttle_position, max(boost_pressure) AS  boost_pressure, max(coolant_pressure) AS coolant_pressure, max(fuel_pressure) AS fuel_pressure, max(oil_temp) AS oil_temp ,  max(egt_temp) AS egt_temperature , max(fuel_rate_average) AS fuel_rate_average  , max(instantaneous_fuel_economy) AS instantaneous_fuel_economy, max(trip_fuel_used) AS fuel_used  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    elif mode == "min":
      query = ('select  min(throttle_position) AS throttle_position, min(boost_pressure) AS  boost_pressure, min(coolant_pressure) AS coolant_pressure, min(fuel_pressure) AS fuel_pressure, min(oil_temp) AS oil_temp ,  min(egt_temp) AS egt_temperature , min(fuel_rate_average) AS fuel_rate_average  , min(instantaneous_fuel_economy) AS instantaneous_fuel_economy from, min(trip_fuel_used) AS fuel_used  {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    else:        
      query = ('select  mean(throttle_position) AS throttle_position, mean(boost_pressure) AS  boost_pressure, mean(coolant_pressure) AS coolant_pressure, mean(fuel_pressure) AS fuel_pressure, mean(oil_temp) AS oil_temp ,  mean(egt_temp) AS egt_temperature , mean(fuel_rate_average) AS fuel_rate_average  , mean(instantaneous_fuel_economy) AS instantaneous_fuel_economy from, mean(trip_fuel_used) AS fuel_used  {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
   


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','boost_pressure':list(reversed(boost_pressure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)),'fuel_used':list(reversed(fuel_used)), 'throttle_position':list(reversed(throttle_position))})     

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','boost_pressure':list(reversed(boost_pressure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)),'fuel_used':list(reversed(fuel_used)), 'throttle_position':list(reversed(throttle_position))})     

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','boost_pressure':list(reversed(boost_pressure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)),'fuel_used':list(reversed(fuel_used)), 'throttle_position':list(reversed(throttle_position))})     

    log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      value8 = '---'
      value9 = '---'

      boost_pressure=[]
      coolant_pressure=[]
      fuel_pressure=[]
      oil_temp=[]
      egt_temperature=[]
      fuel_rate_average=[]
      instantaneous_fuel_economy=[]
      throttle_position=[]
      fuel_used=[]
      
      ts =startepoch*1000
      
      points = list(response.get_points())


      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'
        value9 = '---'        

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['boost_pressure'] is not None:
          value1 = convertfbunits( point['boost_pressure'], convertunittype('pressure', units))
          boost_pressure.append({'epoch':ts, 'value':value1})
          
        
        if point['coolant_pressure'] is not None:
          value2 =  convertfbunits(point['coolant_pressure'], convertunittype('pressure', units))
        coolant_pressure.append({'epoch':ts, 'value':value2})
          
        
        if point['fuel_pressure'] is not None:
          value3=  convertfbunits(point['fuel_pressure'], convertunittype('pressure', units))
        fuel_pressure.append({'epoch':ts, 'value':value3})
          
        
        if point['oil_temp'] is not None:
          value4 =  convertfbunits(point['oil_temp'], convertunittype('temperature', units))
        oil_temp.append({'epoch':ts, 'value':value4})
          
        
        if point['egt_temperature'] is not None:
          value5 =  convertfbunits(point['egt_temperature'], convertunittype('temperature', units))
        egt_temperature.append({'epoch':ts, 'value':value5})
          
       
        if point['fuel_rate_average'] is not None:
          value6=  convertfbunits(point['fuel_rate_average'], convertunittype('flow', units))
        fuel_rate_average.append({'epoch':ts, 'value':value6})
          
        
        if point['instantaneous_fuel_economy'] is not None:
          value7 = convertfbunits(point['instantaneous_fuel_economy'],convertunittype('flow', units))
        instantaneous_fuel_economy.append({'epoch':ts, 'value':value7})

          
        
        if point['throttle_position'] is not None:
          value8 = convertfbunits(point['throttle_position'], convertunittype('%', units))
        throttle_position.append({'epoch':ts, 'value':value8})
          
         
        if point['fuel_used'] is not None:
          value9 = convertfbunits(point['fuel_used'], convertunittype('volume', units))
        fuel_used.append({'epoch':ts, 'value':value9})
          
         

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','rpm':list(reversed(speed)), 'eng_temp':list(reversed(engine_temp)), 'oil_pressure':list(reversed(oil_pressure)),'alternator':list(reversed(alternator_potential)), 'tripfuel':list(reversed(tripfuel)), 'fuel_rate':list(reversed(fuel_rate)), 'fuel_level':list(reversed(level)), 'eng_hours':list(reversed(total_engine_hours))})     
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'success','update':'True','boost_pressure':list(reversed(boost_pressure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)), 'throttle_position':list(reversed(throttle_position))})     
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'success','update':'True','boost_pressure':list(reversed(boost_pressure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)),  'fuel_used':list(reversed(fuel_used)), 'throttle_position':list(reversed(throttle_position))})     



    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })



@app.route('/freeboard_engine')
@cross_origin()
def freeboard_engine():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode = request.args.get('mode',"mean")
    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    value5 = '---'
    value6 = '---'
    value7 = '---'
    value8 = '---'


    speed=[]
    engine_temp=[]
    oil_pressure=[]
    alternator_potential=[]
    tripfuel=[]
    fuel_rate=[]
    level=[]
    total_engine_hours=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='fluid_level') AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":      
      query = ('select  median(speed) AS speed, median(engine_temp) AS  engine_temp, median(oil_pressure) AS oil_pressure, median(alternator_potential) AS alternator_potential, median(fuel_rate) AS fuel_rate ,  median(level) AS level , max(total_engine_hours) AS total_engine_hours from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    elif mode == "max":      
      query = ('select  max(speed) AS speed, max(engine_temp) AS  engine_temp, max(oil_pressure) AS oil_pressure, max(alternator_potential) AS alternator_potential, max(fuel_rate) AS fuel_rate ,  max(level) AS level , max(total_engine_hours) AS total_engine_hours from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    elif mode == "min":      
      query = ('select  min(speed) AS speed, min(engine_temp) AS  engine_temp, min(oil_pressure) AS oil_pressure, min(alternator_potential) AS alternator_potential, min(fuel_rate) AS fuel_rate ,  min(level) AS level , max(total_engine_hours) AS total_engine_hours from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
  
    else:      
      query = ('select  mean(speed) AS speed, mean(engine_temp) AS  engine_temp, mean(oil_pressure) AS oil_pressure, mean(alternator_potential) AS alternator_potential, mean(fuel_rate) AS fuel_rate ,  mean(level) AS level , max(total_engine_hours) AS total_engine_hours from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','rpm':list(reversed(speed)), 'eng_temp':list(reversed(engine_temp)), 'oil_pressure':list(reversed(oil_pressure)),'alternator':list(reversed(alternator_potential)), 'tripfuel':list(reversed(tripfuel)), 'fuel_rate':list(reversed(fuel_rate)), 'fuel_level':list(reversed(level)), 'eng_hours':list(reversed(total_engine_hours))})     

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','rpm':list(reversed(speed)), 'eng_temp':list(reversed(engine_temp)), 'oil_pressure':list(reversed(oil_pressure)),'alternator':list(reversed(alternator_potential)), 'tripfuel':list(reversed(tripfuel)), 'fuel_rate':list(reversed(fuel_rate)), 'fuel_level':list(reversed(level)), 'eng_hours':list(reversed(total_engine_hours))})     

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','rpm':list(reversed(speed)), 'eng_temp':list(reversed(engine_temp)), 'oil_pressure':list(reversed(oil_pressure)),'alternator':list(reversed(alternator_potential)), 'tripfuel':list(reversed(tripfuel)), 'fuel_rate':list(reversed(fuel_rate)), 'fuel_level':list(reversed(level)), 'eng_hours':list(reversed(total_engine_hours))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      value8 = '---'


      speed=[]
      engine_temp=[]
      oil_pressure=[]
      alternator_potential=[]
      tripfuel=[]
      fuel_rate=[]
      level=[]
      total_engine_hours=[]

      ts =startepoch*1000       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'
        
        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['speed'] is not None:
          value1 = convertfbunits( point['speed'], convertunittype('rpm', units))
          speed.append({'epoch':ts, 'value':value1})
          
        
        if point['engine_temp'] is not None:
          value2 =  convertfbunits(point['engine_temp'], convertunittype('temperature', units))
        engine_temp.append({'epoch':ts, 'value':value2})
          
        
        if point['oil_pressure'] is not None:
          value3=  convertfbunits(point['oil_pressure'], convertunittype('pressure', units))
        oil_pressure.append({'epoch':ts, 'value':value3})
          
        
        if point['alternator_potential'] is not None:
          value4 =  convertfbunits(point['alternator_potential'], convertunittype('volts', units))
        alternator_potential.append({'epoch':ts, 'value':value4})
          
        
        if point['fuel_rate'] is not None:
          value6 =  convertfbunits(point['fuel_rate'], convertunittype('flow', units))
        fuel_rate.append({'epoch':ts, 'value':value6})
          
       
        if point['level'] is not None:
          value7=  convertfbunits(point['level'], convertunittype('%', units))
        level.append({'epoch':ts, 'value':value7})
          
        
        if point['total_engine_hours'] is not None:
          value8 = convertfbunits(point['total_engine_hours'], convertunittype('hours', units))
        total_engine_hours.append({'epoch':ts, 'value':value8})
          

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','rpm':list(reversed(speed)), 'eng_temp':list(reversed(engine_temp)), 'oil_pressure':list(reversed(oil_pressure)),'alternator':list(reversed(alternator_potential)), 'tripfuel':list(reversed(tripfuel)), 'fuel_rate':list(reversed(fuel_rate)), 'fuel_level':list(reversed(level)), 'eng_hours':list(reversed(total_engine_hours))})     



    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })





@app.route('/freeboard_fluidlevels')
@cross_origin()
def freeboard_fluidlevels():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode = request.args.get('mode',"mean")
    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    value5 = '---'
    value6 = '---'
    value7 = '---'
    value8 = '---'


    fuel_port=[]
    fuel_strbd=[]
    fuel_center=[]
    water_port=[]
    water_strbd=[]
    water_center=[]
    waste_port=[]
    waste_strbd=[]
    waste_center=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='fluid_level' ) "
    #serieskeys= serieskeys +  " (instance='" + Instance + "') "





    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":      
      query = ('select  median(level) AS level,  median(tank_capacity) AS capacity  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s), type, instance') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
      
    elif mode == "max":      
      query = ('select  max(level) AS level,  median(tank_capacity) AS capacity  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s), type, instance') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    elif mode == "min":      
      query = ('select  min(level) AS level,  median(tank_capacity) AS capacity  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s), type, instance') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
  
    else:      
      query = ('select  mean(level) AS level,  median(tank_capacity) AS capacity  from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s), type, instance') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing','update':'False','fuel_port':list(reversed(fuel_port)), 'fuel_strbd':list(reversed(fuel_strbd)), 'fuel_center':list(reversed(fuel_center)),'water_port':list(reversed(water_port)), 'water_strbd':list(reversed(water_strbd)), 'water_center':list(reversed(water_center)), 'waste_port':list(reversed(waste_port)), 'waste_strbd':list(reversed(waste_strbd)), 'waste_center':list(reversed(waste_center))})     

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing','update':'False','fuel_port':list(reversed(fuel_port)), 'fuel_strbd':list(reversed(fuel_strbd)), 'fuel_center':list(reversed(fuel_center)),'water_port':list(reversed(water_port)), 'water_strbd':list(reversed(water_strbd)), 'water_center':list(reversed(water_center)), 'waste_port':list(reversed(waste_port)), 'waste_strbd':list(reversed(waste_strbd)), 'waste_center':list(reversed(waste_center))})     

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing','update':'False','fuel_port':list(reversed(fuel_port)), 'fuel_strbd':list(reversed(fuel_strbd)), 'fuel_center':list(reversed(fuel_center)),'water_port':list(reversed(water_port)), 'water_strbd':list(reversed(water_strbd)), 'water_center':list(reversed(water_center)), 'waste_port':list(reversed(waste_port)), 'waste_strbd':list(reversed(waste_strbd)), 'waste_center':list(reversed(waste_center))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)
    """
    for series in keys:
      log.info("freeboard Get InfluxDB series key %s", series)
      log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
      tags = series['tags']

      log.info("freeboard Get InfluxDB series tag type  %s ", tags['type'])
      log.info("freeboard Get InfluxDB series tag instance  %s ", tags['instance'])

      fluidtype = tags['type']
      fluidinstance = tags['instance']
        #log.info("freeboard Get InfluxDB series values %s ", series['values'])
      
      log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
      log.info("freeboard Get InfluxDB series values %s ", series['values'])
    """
      
    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      value8 = '---'


      fuel_port=[]
      fuel_strbd=[]
      fuel_center=[]
      water_port=[]
      water_strbd=[]
      water_center=[]
      waste_port=[]
      waste_strbd=[]
      waste_center=[]

      ts =startepoch*1000       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)


      for series in keys:
        #log.info("freeboard Get InfluxDB series key %s", series)
        #log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
        tags = series['tags']

        #log.info("freeboard Get InfluxDB series tag type  %s ", tags['type'])
        #log.info("freeboard Get InfluxDB series tag instance  %s ", tags['instance'])

        fluidtype = int(tags['type'])
        fluidinstance = int(tags['instance'])

        #log.info("freeboard Get InfluxDB series tag type  %s ",fluidtype)
        #log.info("freeboard Get InfluxDB series tag instance  %s ", fluidinstance)


        points =  series['values']
        for point in points:
          #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
          volume = '---'

          
          if point[0] is not None and  point[1] is not None:
            capacity = '---'
            level =  point[1] #is in percent 100% = 1.0

            # make asignment if not NULL
            if point[2] is not None:
              capacity = point[2] # is in liters
            
            mydatetimestr = str(point[0])
            mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

            mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
            mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

            #dtt = mydatetime.timetuple()       
            dtt = mydatetimetz.timetuple()
            ts = int(mktime(dtt)*1000)
            

              
            if units == 'US': # we will calculate in gallons
              #check if we have a good capacity value before making volume calculation
              if capacity != '---':
                volgallons = convertfbunits( int(capacity), 21)
                volume =  float("{0:.1f}".format(level * 0.01 *  volgallons))
               
                
            elif units == 'metric': # we will calculate in liters
              #check if we have a good capacity value before making volume calculation
              if capacity != '---':
                volliters = capacity # is in liters
                volume =  float("{0:.1f}".format(level * 0.01 *  volliters))
                
            else : #default will be in %
                volume =  float("{0:.1f}".format(level * 1.0 ))

            
            if fluidtype == 0 and fluidinstance ==0 and volume != '---':
              fuel_port.append({'epoch':ts, 'value':volume})
            elif fluidtype == 0 and fluidinstance ==1 and volume != '---':
              fuel_strbd.append({'epoch':ts, 'value':volume})          
            elif fluidtype == 0 and fluidinstance ==2 and volume != '---':
              fuel_center.append({'epoch':ts, 'value':volume})          

            elif fluidtype == 1 and fluidinstance ==0 and volume != '---':
              water_port.append({'epoch':ts, 'value':volume})
            elif fluidtype == 1 and fluidinstance ==1 and volume != '---':
              water_strbd.append({'epoch':ts, 'value':volume})          
            elif fluidtype == 1 and fluidinstance ==2 and volume != '---':
              water_center.append({'epoch':ts, 'value':volume})          

            elif fluidtype == 2 and fluidinstance ==0 and volume != '---':
              waste_port.append({'epoch':ts, 'value':volume})
            elif fluidtype == 2 and fluidinstance ==1 and volume != '---':
              waste_strbd.append({'epoch':ts, 'value':volume})          
            elif fluidtype == 2 and fluidinstance ==2 and volume != '---':
              waste_center.append({'epoch':ts, 'value':volume})          

         

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','fuel_port':list(reversed(fuel_port)), 'fuel_strbd':list(reversed(fuel_strbd)), 'fuel_center':list(reversed(fuel_center)),'water_port':list(reversed(water_port)), 'water_strbd':list(reversed(water_strbd)), 'water_center':list(reversed(water_center)), 'waste_port':list(reversed(waste_port)), 'waste_strbd':list(reversed(waste_strbd)), 'waste_center':list(reversed(waste_center))})     


    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })



@app.route('/freeboard_ac_status')
@cross_origin()
def freeboard_ac_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    actype = request.args.get('type','UTIL')
    mytimezone = request.args.get('timezone',"UTC")
    mode = request.args.get('mode',"mean")
    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    volts=[]
    amps=[]
    power=[]
    energy=[]
    energy_caluculated=[]

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    #serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='fluid_level') AND "
    serieskeys= serieskeys +  " (sensor='ac_basic' OR sensor='ac_watthours'  ) "
    serieskeys= serieskeys +  "  AND type = '" + actype + "' AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":
      
      query = ('select  median(ac_line_neutral_volts) AS volts, median(ac_amps) AS  amps, median(ac_watts) AS power, median(ac_kwatthours) AS energy, median(status) AS status FROM {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)

      
    elif mode == "max":
      
      query = ('select  max(ac_line_neutral_volts) AS volts, max(ac_amps) AS  amps, max(ac_watts) AS power, max(ac_kwatthours) AS energy, max(status) AS status FROM {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)


    elif mode == "min":
      
      query = ('select  min(ac_line_neutral_volts) AS volts, min(ac_amps) AS  amps, min(ac_watts) AS power, min(ac_kwatthours) AS energy, min(status) AS status FROM {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)

    else:
      
      query = ('select  mean(ac_line_neutral_volts) AS volts, mean(ac_amps) AS  amps, mean(ac_watts) AS power, mean(ac_kwatthours) AS energy, mean(status) AS status FROM {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
   


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'volts':list(reversed(volts)), 'amps':list(reversed(amps)), 'power':list(reversed(power)), 'energy':list(reversed(energy)), 'energy_interval':list(reversed(energy_caluculated))})     

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'volts':list(reversed(volts)), 'amps':list(reversed(amps)), 'power':list(reversed(power)), 'energy':list(reversed(energy)), 'energy_interval':list(reversed(energy_caluculated))})     

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'False', 'status':'missing' ,'volts':list(reversed(volts)), 'amps':list(reversed(amps)), 'power':list(reversed(power)), 'energy':list(reversed(energy)), 'energy_interval':list(reversed(energy_caluculated))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      value8 = '---'

      volts=[]
      amps=[]
      power=[]
      energy=[]
      status=[]
      energy_caluculated=[]
      energy_period = float(0.0)

      ts =startepoch*1000       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        value8 = '---'

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        
        if point['volts'] is not None:
          value1 = convertfbunits( point['volts'], 27)
        volts.append({'epoch':ts, 'value':value1})    
        
        if point['amps'] is not None:
          value2 =  convertfbunits(point['amps'],28)
          energy_period = energy_period +(( float(value2)*float(value1)) * 0.001)
        amps.append({'epoch':ts, 'value':value2})
        energy_caluculated.append({'epoch':ts, 'value':energy_period})
        
        if point['power'] is not None:
          value3=  convertfbunits(point['power'], 29)
        power.append({'epoch':ts, 'value':value3})

        if point['energy'] is not None:
          value4 =  convertfbunits(point['energy'], 31)
        energy.append({'epoch':ts, 'value':value4})
          
          
        if point['status'] is not None:
          value5=  convertfbunits(point['status'], 44)
        status.append({'epoch':ts, 'value':value5})
        
        

      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'volts':value1, 'amps':value2, 'power':value3, 'energy':value4})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','volts':list(reversed(volts)), 'amps':list(reversed(amps)), 'power':list(reversed(power)), 'energy':list(reversed(energy)), 'status':list(reversed(status)), 'energy_interval':list(reversed(energy_caluculated))})     

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })








@app.route('/freeboard_status')
@cross_origin()
def freeboard_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='seasmartswitch'  AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      bankvalue1 = '---'
      bankvalue2 = '---'

      bank0=[]
      bank1=[]
      
      status0=[]
      status1=[]
      status2=[]
      status3=[]
      status4=[]
      status5=[]
      status6=[]
      status7=[]
      status8=[]
      status9=[]
      status10=[]
      status11=[]
      status12=[]
      status13=[]
      status14=[]
      status15=[]


      value0=0
      value1=0
      value2=0
      value3=0
      value4=0
      value5=0
      value6=0
      value7=0
      value8=0
      value9=0
      value10=0
      value11=0
      value12=0
      value13=0
      value14=0
      value15=0
       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
  

        if point['bank0'] is not None:
          bankvalue1 =  point['bank0']
          bank0.append({'epoch':ts, 'value':bankvalue1})
          
          if bankvalue1 != '---':
            if bankvalue1 & 0x1 == 0x1:
              status0.append({'epoch':ts, 'value':1})
            else:
              status0.append({'epoch':ts, 'value':0})

              
            if bankvalue1 & 0x2 == 0x2:
              status1.append({'epoch':ts, 'value':1})
            else:
              status1.append({'epoch':ts, 'value':0})


            if bankvalue1 & 0x4 == 0x4:
              status2.append({'epoch':ts, 'value':1})
            else:
              status2.append({'epoch':ts, 'value':0})


            if bankvalue1 & 0x8 == 0x8:
              status3.append({'epoch':ts, 'value':1})
            else:
              status3.append({'epoch':ts, 'value':0})


            if bankvalue1 & 0x10 == 0x10:
              status4.append({'epoch':ts, 'value':1})
            else:
              status4.append({'epoch':ts, 'value':0})


            if bankvalue1 & 0x20 == 0x20:
              status5.append({'epoch':ts, 'value':1})
            else:
              status5.append({'epoch':ts, 'value':0})


            if bankvalue1 & 0x40 == 0x40:
              status6.append({'epoch':ts, 'value':1})
            else:
              status6.append({'epoch':ts, 'value':0})


            if bankvalue1 & 0x80 == 0x80:
              status7.append({'epoch':ts, 'value':1})
            else:
              status7.append({'epoch':ts, 'value':0})



        if point['bank1'] is not None:
          bankvalue2 =  point['bank1']
          bank1.append({'epoch':ts, 'value':bankvalue2})
          
          if bankvalue2 != '---':
            if bankvalue2 & 0x1 == 0x1:
              status8.append({'epoch':ts, 'value':1})
            else:
              status8.append({'epoch':ts, 'value':0})

              
            if bankvalue2 & 0x2 == 0x2:
              status9.append({'epoch':ts, 'value':1})
            else:
              status9.append({'epoch':ts, 'value':0})


            if bankvalue2 & 0x4 == 0x4:
              status10.append({'epoch':ts, 'value':1})
            else:
              status10.append({'epoch':ts, 'value':0})


            if bankvalue2 & 0x8 == 0x8:
              status11.append({'epoch':ts, 'value':1})
            else:
              status11.append({'epoch':ts, 'value':0})


            if bankvalue2 & 0x10 == 0x10:
              status12.append({'epoch':ts, 'value':1})
            else:
              status12.append({'epoch':ts, 'value':0})


            if bankvalue2 & 0x20 == 0x20:
              status13.append({'epoch':ts, 'value':1})
            else:
              status13.append({'epoch':ts, 'value':0})


            if bankvalue2 & 0x40 == 0x40:
              status146.append({'epoch':ts, 'value':1})
            else:
              status14.append({'epoch':ts, 'value':0})


            if bankvalue2 & 0x80 == 0x80:
              status15.append({'epoch':ts, 'value':1})
            else:
              status15.append({'epoch':ts, 'value':0})




      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'bank0':value1, 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','status0':list(reversed(status0)), 'status1':list(reversed(status1)), 'status2':list(reversed(status2)),'status3':list(reversed(status3)), 'status4':list(reversed(status4)), 'status5':list(reversed(status5)),'status6':list(reversed(status6)), 'status7':list(reversed(status7)), 'status8':list(reversed(status8)),'status9':list(reversed(status9)), 'status10':list(reversed(status10)), 'status11':list(reversed(status11)),'status12':list(reversed(status12)), 'status13':list(reversed(status13)), 'status14':list(reversed(status14)), 'status15':list(reversed(status15))})     

      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True',  'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7})

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })


@app.route('/freeboard_indicator_status')
@cross_origin()
def freeboard_indicator_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    Indicator = request.args.get('indicator','0')
    resolution = request.args.get('resolution',"")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    switchstatus=[]
    mydatetime = datetime.datetime.now()
    myjsondate= mydatetime.strftime("%B %d, %Y %H:%M:%S")      
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_indicator_status deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='seasmartswitch'  AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "


    parameter = "value" + str(Indicator)


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    query = ('select  median({}) as indicator '
                     ' FROM {} '             
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format(parameter,  measurement,  serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard freeboard_indicator_status data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})    

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})    

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})    

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""


      switchstatus=[]
       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
  
        
        if point['indicator'] is not None:
          statusvalues=(int(point['indicator']))
        else:
          statusvalues=(int(3))


        # check if array was all NONE  - if so disgard it
        if not (statusvalues == 3 ):
          switchstatus.append({'epoch':ts, 'value':statusvalues})
          #log.info('freeboard_switch_bank_status:  switchstatus%s:', switchstatus)          


      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'bank0':value1, 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','status0':list(reversed(status0)), 'status1':list(reversed(status1)), 'status2':list(reversed(status2)),'status3':list(reversed(status3)), 'status4':list(reversed(status4)), 'status5':list(reversed(status5)),'status6':list(reversed(status6)), 'status7':list(reversed(status7)), 'status8':list(reversed(status8)),'status9':list(reversed(status9)), 'status10':list(reversed(status10)), 'status11':list(reversed(status11)),'status12':list(reversed(status12)), 'status13':list(reversed(status13)), 'status14':list(reversed(status14)), 'status15':list(reversed(status15))})     
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','indicator':list(reversed(switchstatus))})     

      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True',  'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7})

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/freeboard_indicator_runtime')
@cross_origin()
def freeboard_indicator_runtime():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    mode =  request.args.get('mode',"mean")
    indicator = request.args.get('indicator',"0")
    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    strvalue = ""
    value1 = '---'
    value2 = '---'
    value3 = '---'
    value4 = '---'
    value5 = '---'
    value6 = '---'
    value7 = '---'
    value8 = '---'


    status=[]
    runtime=[]
    cycles=[]


    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")      


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='seasmartindicator') AND "
    serieskeys= serieskeys +  " (type='" + indicator + "') AND "   
    serieskeys= serieskeys +  " (instance='" + Instance + "') "

    """
    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='temperature'  OR  sensor='trip_parameters_engine') AND "
    if Instance == 1:
      serieskeys= serieskeys +  " (type='NULL' OR type='Reserved 134')  AND "
    else:
      serieskeys= serieskeys +  " (type='NULL' OR type='Reserved 135')  AND "
      
    serieskeys= serieskeys +  " (instance='" + Instance + "') "
    """



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    if mode == "median":
      query = ('select  median(value) AS status, median(runtime_sec) AS  runtime, median(cycles) AS cycles from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    elif mode == "max":
      query = ('select  max(value) AS status, max(runtime_sec) AS  runtime, max(cycles) AS cycles from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    elif mode == "min":
      query = ('select  min(value) AS status, min(runtime_sec) AS  runtime, min(cycles) AS cycles from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 

    else:        
      query = ('select  mean(value) AS status, mean(runtime_sec) AS  runtime, mean(cycles) AS cycles from {} '
                       'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution) 
   


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','value':list(reversed(status)), 'runtime':list(reversed(runtime)), 'cycles':list(reversed(cycles ))}) 

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','value':list(reversed(status)), 'runtime':list(reversed(runtime)), 'cycles':list(reversed(cycles ))}) 
      
    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','value':list(reversed(status)), 'runtime':list(reversed(runtime)), 'cycles':list(reversed(cycles ))}) 
    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      value8 = '---'


      indicator=[]
      runtime=[]
      runtime_secs=[]
      cycles=[]


      ts =startepoch*1000
      
      points = list(response.get_points())


      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        value1 = '---'
        value2 = '---'
        value3 = '---'
        value4 = '---'
        value5 = '---'
        value6 = '---'
        value7 = '---'
        rttime = '---'

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['status'] is not None:
          value1 = convertfbunits( point['status'], convertunittype('', units))
        indicator.append({'epoch':ts, 'value':value1})
          
        
        if point['runtime'] is not None:
          #value2 = datetime.datetime.fromtimestamp(int(point['runtime'])).strftime('%H.%M')
          value2 = point['runtime']
          rthours = int(value2 / (60*60))
          rtmin = int((value2 % (60*60))/60)
          rttime = str(rthours) + "." + str(rtmin)
          #value2 =  convertfbunits(point['runtime'], convertunittype('time', units))
          #value2 =  convertfbunits(point['cycles'], convertunittype('', units))
        runtime.append({'epoch':ts, 'value':rttime})
        runtime_secs.append({'epoch':ts, 'value':value2})
          
        
        if point['cycles'] is not None:
          value3=  convertfbunits(point['cycles'], convertunittype('', units))
        cycles.append({'epoch':ts, 'value':value3})
          
        
                 

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'success','update':'True','indicator':list(reversed(status)), 'runtime':list(reversed(runtime)), 'cycles':list(reversed(cycles ))})     
      return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'success','update':'True','indicator':list(reversed(indicator)), 'runtime_hours':list(reversed(runtime)), 'runtime_seconds':list(reversed(runtime_secs)), 'cycles':list(reversed(cycles ))})     
  






    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })




@app.route('/freeboard_dimmer_status')
@cross_origin()
def freeboard_dimmer_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    dimmerIndex = request.args.get('indicator','0')
    resolution = request.args.get('resolution',"")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    dimmerstatus=[]
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_indicator_status deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='seasmartdimmer'  AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "


    parameter = "value" + str(dimmerIndex)


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    query = ('select  median({}) as dimmer '
                     ' FROM {} '             
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format(parameter,  measurement,  serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard freeboard_dimmer_status data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','dimmer_bank':list(reversed(dimmerstatus))})    

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','dimmer_bank':list(reversed(dimmerstatus))})    

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','dimmer_bank':list(reversed(dimmerstatus))})    

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""


      dimmerstatus=[]
       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
  
        
        if point['dimmer'] is not None:
          statusvalues=(int(point['dimmer']))
        else:
          statusvalues=(int(255))


        # check if array was all NONE  - if so disgard it
        if not (statusvalues == 255 ):
          dimmerstatus.append({'epoch':ts, 'value':statusvalues})
          #log.info('freeboard_switch_bank_status:  dimmerstatus%s:', dimmerstatus)          


      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'bank0':value1, 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','status0':list(reversed(status0)), 'status1':list(reversed(status1)), 'status2':list(reversed(status2)),'status3':list(reversed(status3)), 'status4':list(reversed(status4)), 'status5':list(reversed(status5)),'status6':list(reversed(status6)), 'status7':list(reversed(status7)), 'status8':list(reversed(status8)),'status9':list(reversed(status9)), 'status10':list(reversed(status10)), 'status11':list(reversed(status11)),'status12':list(reversed(status12)), 'status13':list(reversed(status13)), 'status14':list(reversed(status14)), 'status15':list(reversed(status15))})     
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','dimmer':list(reversed(dimmerstatus))})     

      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True',  'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7})

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))   

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })


@app.route('/freeboard_get_engine_values')
@cross_origin()
def freeboard_get_engine_values():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mode= request.args.get('mode',"last")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    dimmerstatus=[]
    temperature=[]
    dimmer1=[]
    dimmer2=[]
    dimmer3=[]
    dimmer4=[]

      
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_get_engine_values deviceid %s", deviceid)

    if deviceid == "":
      return jsonify(result="ERROR")

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='fluid_level') AND "
    serieskeys= serieskeys +  " (instance='" + instance + "') "


    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    #SELECT LAST()...WHERE time > now() - 1h       
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    log.info("freeboard_get_engine_values mode = %s", mode)
    
    if mode == 'min':
      #log.info("freeboard_get_weather_values mode is min")
      query = ('select  min(engine_temp)  as engine_temp, '
                       'min(alternator_potential)  as alt_volts, '
                       'min(oil_pressure) as oil_pressure, '
                        'min(speed)  as rpm, '
                        'min(level)  as fuel_level '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   
    elif mode == 'max':      
      query = ('select  max(engine_temp)  as engine_temp, '
                       'max(alternator_potential)  as alt_volts, '
                       'max(oil_pressure) as oil_pressure, '
                        'max(speed)  as rpm, '
                        'max(level)  as fuel_level '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   


    elif mode == 'avg':      
      query = ('select  percentile(engine_temp, 50)  as engine_temp, '
                       'percentile(alternator_potential, 50)  as alt_volts, '
                       'percentile(oil_pressure, 50) as oil_pressure, '
                        'percentile(speed, 50)  as rpm, '
                        'percentile(level, 50)  as fuel_level '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   
   


    else:      
      query = ('select  last(engine_temp)  as engine_temp, '
                       'last(alternator_potential)  as alt_volts, '
                       'last(oil_pressure) as oil_pressure, '
                        'last(speed)  as rpm, '
                        'last(level)  as fuel_level '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
  
   


    log.info("freeboard_get_engine_values data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        return jsonify(result="error")

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")

      
    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")


    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'

    #log.info("freeboard jsonkey..%s", jsonkey )
    try:

      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        if point['engine_temp'] is not None:
          engine_temp=convertfbunits(point['engine_temp'],  convertunittype('temperature', units))
        else:
          engine_temp='unavailable'

        if point['alt_volts'] is not None:
          alt_volts=convertfbunits(point['alt_volts'], convertunittype('volts', units))
        else:
          alt_volts='unavailable'

        if point['oil_pressure'] is not None:
          oil_pressure=convertfbunits(point['oil_pressure'], convertunittype('pressure', units))
        else:
          oil_pressure='unavailable'
          
        if point['rpm'] is not None:
          rpm=convertfbunits(point['rpm'], convertunittype('rpm', units))
        else:
          rpm='unavailable'

        if point['fuel_level'] is not None:
          fuel_level=convertfbunits(point['fuel_level'],  convertunittype('%', units)) 
        else:
          fuel_level='unavailable'


        
      return jsonify(result="OK",  instance=instance,  engine_temp=engine_temp, alt_volts=alt_volts, oil_pressure=oil_pressure, rpm=rpm, fuel_level=fuel_level)


    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)

        return jsonify(result="ERROR")

    return jsonify(result="ERROR")


@app.route('/freeboard_get_rain_gauge')
@cross_origin()
def freeboard_get_rain_gauge():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mode= request.args.get('mode',"last")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    accumulation=[]
    duration=[]
    rate=[]
    peak=[]


      
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_get_rain_gauge deviceid %s", deviceid)

    if deviceid == "":
      return jsonify(result="ERROR")

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='rain_gauge' "



    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    #SELECT LAST()...WHERE time > now() - 1h       
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    log.info("freeboard_get_rain_gauge mode = %s", mode)
    
    if mode == 'min':
      #log.info("freeboard_get_weather_values mode is min")
      query = ('select  min(accumulation)  as accumulation, '
                       'min("duration")  as "duration", '
                        'min(rate)  as rate, '
                        'min(peak)  as peak '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   
    elif mode == 'max':      
      query = ('select  max(accumulation)  as accumulation, '
                       'max("duration")  as "duration", '
                        'max(rate)  as rate, '
                        'max(peak)  as peak '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   


    elif mode == 'avg':      
      query = ('select  percentile(accumulation,50)  as accumulation, '
                       'percentile("duration",50)  as "duration", '
                        'percentile(rate,50)  as rate, '
                        'percentile(peak,50)  as peak '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   
   


    else:      
      query = ('select  last(accumulation)  as accumulation, '
                       'last("duration)  as "duration", '
                        'last(rate)  as rate, '
                        'last(peak)  as peak '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
  
   


    log.info("freeboard freeboard_get_rain_gauge data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        return jsonify(result="error")

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")

      
    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")


    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:

      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        if point['accumulation'] is not None:
          accumulation=convertfbunits(point['accumulation'],  convertunittype('accumulation', units))
        else:
          accumulation='unavailable'

        if point['duration'] is not None:
          duration=convertfbunits(point['duration'], 10)
        else:
          duration='unavailable'

        if point['rate'] is not None:
          rate=convertfbunits(point['rate'], 26)
        else:
          rate='unavailable'
          
        if point['peak'] is not None:
          peak=convertfbunits(point['peak'], 16)
        else:
          peak='unavailable'




        
      return jsonify(result="OK",  instance=instance,  accumulation=accumulation, duration=duration, rate=rate, peak=peak)


    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)

        return jsonify(result="ERROR")

    return jsonify(result="ERROR")



  

@app.route('/freeboard_get_weather_values')
@cross_origin()
def freeboard_get_weather_values():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mode= request.args.get('mode',"last")
    units= request.args.get('units',"US")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    dimmerstatus=[]
    temperature=[]
    dimmer1=[]
    dimmer2=[]
    dimmer3=[]
    dimmer4=[]

      
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_get_weather_values deviceid %s", deviceid)

    if deviceid == "":
      return jsonify(result="ERROR")

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " (sensor='environmental_data' OR sensor='wind_data') AND instance='0' AND (type='Outside Temperature' OR type='Outside Humidity' OR type='TWIND True North')"



    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    #SELECT LAST()...WHERE time > now() - 1h       
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    log.info("freeboard_get_weather_values mode = %s", mode)
    
    if mode == 'min':
      #log.info("freeboard_get_weather_values mode is min")
      query = ('select  min(temperature)  as temperature, '
                       'min(atmospheric_pressure)  as atmospheric_pressure, '
                       'min(humidity) as humidity, '
                        'min(wind_direction)  as wind_direction, '
                        'min(wind_speed)  as wind_speed '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   
    elif mode == 'max':      
      query = ('select  max(temperature)  as temperature, '
                       'max(atmospheric_pressure)  as atmospheric_pressure, '
                       'max(humidity) as humidity, '
                        'max(wind_direction)  as wind_direction, '
                        'max(wind_speed)  as wind_speed '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   


    elif mode == 'avg':      
      query = ('select  percentile(temperature,50)  as temperature, '
                       'percentile(atmospheric_pressure,50)  as atmospheric_pressure, '
                       'percentile(humidity,50) as humidity, '
                        'percentile(wind_direction,50)  as wind_direction, '
                        'percentile(wind_speed,50)  as wind_speed '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
   
   


    else:      
      query = ('select  last(temperature)  as temperature, '
                       'last(atmospheric_pressure)  as atmospheric_pressure, '
                       'last(humidity) as humidity, '
                        'last(wind_direction)  as wind_direction, '
                        'last(wind_speed)  as wind_speed '
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( measurement, serieskeys, startepoch, endepoch ) 
  
   


    log.info("freeboard freeboard_get_weather_values data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        return jsonify(result="error")

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")

      
    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")


    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:

      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        if point['temperature'] is not None:
          temperature=convertfbunits(point['temperature'],  convertunittype('temperature', units))
        else:
          temperature='unavailable'

        if point['atmospheric_pressure'] is not None:
          atmospheric_pressure=convertfbunits(point['atmospheric_pressure'], 10)
        else:
          atmospheric_pressure='unavailable'

        if point['humidity'] is not None:
          humidity=convertfbunits(point['humidity'], 26)
        else:
          humidity='unavailable'
          
        if point['wind_direction'] is not None:
          wind_direction=convertfbunits(point['wind_direction'], 16)
        else:
          wind_direction='unavailable'

        if point['wind_speed'] is not None:
          wind_speed=convertfbunits(point['wind_speed'],  convertunittype('speed', units)) 
        else:
          wind_speed='unavailable'


        
      return jsonify(result="OK",  instance=instance,  temperature=temperature, atmospheric_pressure=atmospheric_pressure, humidity=humidity, wind_direction=wind_direction, wind_speed=wind_speed)


    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)

        return jsonify(result="ERROR")

    return jsonify(result="ERROR")

  

@app.route('/freeboard_get_weather_minmax_value')
@cross_origin()
def freeboard_get_weather_minmax_value():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    instance = request.args.get('instance','0')
    parameter = request.args.get('parameter',"air temp")
    mode= request.args.get('mode',"last")
    units= request.args.get('units',"US")
    mytimezone= request.args.get('timezone',"UTC")
    response = None

    dimmerstatus=[]
    temperature=[]


      
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    #if resolution == "":
    #  resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_get_weather_minmax_value deviceid %s", deviceid)

    if deviceid == "":
      return jsonify(result="ERROR")

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)


    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "

    if parameter == 'air temp':
      serieskeys= serieskeys +  " (sensor='environmental_data' ) AND instance='0' AND (type='Outside Temperature' )"
      query_parameter = 'temperature'

    elif parameter == 'barometric pressure':
      serieskeys= serieskeys +  " (sensor='environmental_data' ) AND instance='0' AND (type='Outside Temperature' )"
      query_parameter = 'atmospheric_pressure'
      
    elif parameter == 'humidity':
      serieskeys= serieskeys +  " (sensor='environmental_data' ) AND instance='0' AND ( type='Outside Humidity' )"
      query_parameter = 'humidity'
      
    elif parameter == 'wind speed':
      serieskeys= serieskeys +  " (sensor='wind_data') AND instance='0' AND ( type='TWIND True North')"
      query_parameter = 'wind_speed'
      
    elif parameter == 'wind direction':
      serieskeys= serieskeys +  " ( sensor='wind_data') AND instance='0' AND ( type='TWIND True North')"
      query_parameter = 'wind_direction'

    else :
      serieskeys= serieskeys +  " (sensor='environmental_data' ) AND instance='0' AND (type='Outside Temperature' )"
      query_parameter = 'temperature'

      
    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    #SELECT LAST()...WHERE time > now() - 1h       
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    log.info("freeboard_get_weather_minmax_value mode = %s", mode)
    
    if mode == 'min':
      #log.info("freeboard_get_weather_values mode is min")
      query = ('select  min({})  as {}, '
                       ' time as time'
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( query_parameter, query_parameter, measurement, serieskeys, startepoch, endepoch ) 
   
    elif mode == 'max':      
      query = ('select  max({})  as {}, '
                       ' time as time'
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( query_parameter, query_parameter, measurement, serieskeys, startepoch, endepoch ) 
   


    elif mode == 'avg':      
      query = ('select  percentile({},50)  as {}, '
                       ' time as time'
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( query_parameter, query_parameter, measurement, serieskeys, startepoch, endepoch ) 
   
   


    else:      
      query = ('select  last({})  as {}, '
                       'last(atmospheric_pressure)  as atmospheric_pressure, '
                       ' time as time'
                       ' FROM {} '             
                       'where {} AND time > {}s and time < {}s') \
                  .format( query_parameter, query_parameter, measurement, serieskeys, startepoch, endepoch ) 
  
   


    log.info("freeboard freeboard_get_weather_minmax_value data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        return jsonify(result="error")

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")

      
    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="error")


    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
      
      temperature='unavailable'
      atmospheric_pressure='unavailable'
      humidity='unavailable'
      wind_direction='unavailable'
      wind_speed='unavailable'
      myjsondate='unavailable'

      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if parameter == 'air temp':        
          if point['temperature'] is not None:
            temperature=convertfbunits(point['temperature'],  convertunittype('temperature', units))

            
        if parameter == 'barometric pressure':     
          if point['atmospheric_pressure'] is not None:
            atmospheric_pressure=convertfbunits(point['atmospheric_pressure'], 10)

            
        if parameter == 'humidity':     
          if point['humidity'] is not None:
            humidity=convertfbunits(point['humidity'], 26)

            
        if parameter == 'wind direction':                 
          if point['wind_direction'] is not None:
            wind_direction=convertfbunits(point['wind_direction'], 16)

            
        if parameter == 'wind speed':     
          if point['wind_speed'] is not None:
            wind_speed=convertfbunits(point['wind_speed'],  convertunittype('speed', units)) 


        if point['time'] is not None:
          #mydatetimestr = int(point['time']*1000)
          #mydatetime = datetime.datetime.fromtimestamp(mydatetimestr)
          #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
          #myjsondate = mydatetime.strftime("%A %B, %Y at %I,%M,%S, %Z")
          mydatetimestr = str(point['time'])
          #myjsondate = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
          log.info('freeboard_get_weather_minmax_value:  mydatetime %s:', mydatetime)
          #myjsondate = mydatetime.strftime( '%A, %B, %Y, at %I,%M,%p, %Z')
          #localtz = timezone('US/Pacific')
          #mydatetimetz = localtz.localize(mydatetime)

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          log.info('freeboard_get_weather_minmax_value:  mydatetimetz %s:', mydatetime_utctz)

          #mytimezone= "US/Pacific"
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))
          log.info('freeboard_get_weather_minmax_value:  mydatetimetz %s:', mydatetimetz)
          
          #myjsondate = mydatetimetz.strftime( '%A,  at %I %M,%p, G M T')
          myjsondate = mydatetimetz.strftime( '%A,  at, %I:%M,%p, %Z')
          #from pytz import timezone
          #localtz = timezone('Europe/Lisbon')
          #dt_aware = localtz.localize(dt_unware)
          #def ms_to_datetime(epoch_ms):
          #return datetime.datetime.fromtimestamp(epoch_ms / 1.0, tz=pytz.utc)
          #location.timezone = 'US/Pacific'
          #timezone = location.timezone
          #log.info("getSunRiseSet:  in proc getSunRiseSet Astral timezone: %s", timezone)
          #mylocal = pytz.timezone(timezone)
          
          
      return jsonify(result="OK",  time=myjsondate, instance=instance,  temperature=temperature, atmospheric_pressure=atmospheric_pressure, humidity=humidity, wind_direction=wind_direction, wind_speed=wind_speed)


    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)

        return jsonify(result="ERROR")

    return jsonify(result="ERROR")

  



@app.route('/freeboard_get_dimmer_values')
@cross_origin()
def freeboard_get_dimmer_values():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    gwtype = request.args.get('type',"hub")
    Interval = request.args.get('interval',"5min")
    instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    dimmerstatus=[]
    dimmer0=[]
    dimmer1=[]
    dimmer2=[]
    dimmer3=[]
    dimmer4=[]

      
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_dimmer_values deviceid %s", deviceid)

    if deviceid == "":
      return jsonify(result="ERROR")

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='seasmartdimmer'  AND "
    serieskeys= serieskeys +  " (instance='" + instance + "') "





    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

    #SELECT LAST()...WHERE time > now() - 1h       
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    query = ('select  last(value0) as dv0, '
                     'last(value1) as dv1, '
                     'last(value2) as dv2, '
                      'last(value3) as dv3, '
                      'last(value4) as dv4 '
                     ' FROM {} '             
                     'where {} ') \
                .format( measurement, serieskeys ) 
 


    log.info("freeboard freeboard_dimmer_values data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        return jsonify(result="ERROR")

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="ERROR")

      
    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        return jsonify(result="ERROR")


    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:

      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        if point['dv0'] is not None:
          dimmer0=int(point['dv0'])
        else:
          dimmer0='---'

        if point['dv1'] is not None:
          dimmer1=int(point['dv1'])
        else:
          dimmer1='---'

        if point['dv2'] is not None:
          dimmer2=int(point['dv2'])
        else:
          dimmer2='---'
          
        if point['dv3'] is not None:
          dimmer3=int(point['dv3'])
        else:
          dimmer3='---'

        if point['dv4'] is not None:
          dimmer4=int(point['dv4'])
        else:
          dimmer4='---'

        
      return jsonify(result="OK",  instance=instance, oldvalue0=dimmer0, oldvalue1=dimmer1, oldvalue2=dimmer2, oldvalue3=dimmer3, oldvalue4=dimmer4)


    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)

        return jsonify(result="ERROR")

    return jsonify(result="ERROR")

  

@app.route('/freeboard_dimmer_values')
@cross_origin()
def freeboard_dimmer_values():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    gwtype = request.args.get('type',"hub")
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    dimmerstatus=[]
    dimmer0=[]
    dimmer1=[]
    dimmer2=[]
    dimmer3=[]
    dimmer4=[]

      
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_dimmer_values deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='seasmartdimmer'  AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    query = ('select  median(value0) as dv0, '
                     'median(value1) as dv1, '
                     'median(value2) as dv2, '
                      'median(value3) as dv3, '
                      'median(value4) as dv4 '
                     ' FROM {} '             
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard freeboard_dimmer_values data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','dimmer0_value':list(reversed(dimmer0)),'dimmer1_value':list(reversed(dimmer1)),'dimmer2_value':list(reversed(dimmer2)),'dimmer3_value':list(reversed(dimmer3)),'dimmer4_value':list(reversed(dimmer4))})     


    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','dimmer0_value':list(reversed(dimmer0)),'dimmer1_value':list(reversed(dimmer1)),'dimmer2_value':list(reversed(dimmer2)),'dimmer3_value':list(reversed(dimmer3)),'dimmer4_value':list(reversed(dimmer4))})     

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','dimmer0_value':list(reversed(dimmer0)),'dimmer1_value':list(reversed(dimmer1)),'dimmer2_value':list(reversed(dimmer2)),'dimmer3_value':list(reversed(dimmer3)),'dimmer4_value':list(reversed(dimmer4))})     

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""

      
      status0=0x255
      status1=0x255
      status2=0x255
      status3=0x255
      status4=0x255


      dimmerstatus=[]
      dimmer0=[]
      dimmer1=[]
      dimmer2=[]
      dimmer3=[]
      dimmer4=[]
      dimmer_override=[]
      dimmer_switchoverride=[]
      dimmer_photooverride=[]
      dimmer_status=[]
      dimmer_motion=[]
       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
  
        statusvalues=[]
        
        if point['dv0'] is not None:
          dimmer0.append({'epoch':ts, 'value':int(point['dv0'])})
        else:
          dimmer0.append({'epoch':ts, 'value':'---'})

        
        if point['dv1'] is not None:
          dimmer1.append({'epoch':ts, 'value':int(point['dv1'])})
        else:
          dimmer1.append({'epoch':ts, 'value':'---'})

        
        if point['dv2'] is not None:
          dimmer2.append({'epoch':ts, 'value':int(point['dv2'])})
          #dimmer_motion.append({'epoch':ts, 'value':((int(point['dv2']) & 0x10) * 6.25)})
          
        else:
          dimmer2.append({'epoch':ts, 'value':'---'})


        
        if point['dv3'] is not None:
          dimmer3.append({'epoch':ts, 'value':int(point['dv3'])})
        else:
          dimmer3.append({'epoch':ts, 'value':'---'})

        
        if point['dv4'] is not None:
          dimmer4.append({'epoch':ts, 'value':int(point['dv4'])})
          dimmer_override.append({'epoch':ts, 'value':((int(point['dv4']) & 0x40) )})
          dimmer_status.append({'epoch':ts, 'value':(int(point['dv4']) & 0x0F)})
          dimmer_motion.append({'epoch':ts, 'value':((int(point['dv4']) & 0x10) )})
          dimmer_photooverride.append({'epoch':ts, 'value':((int(point['dv4']) & 0x20) )})
          dimmer_switchoverride.append({'epoch':ts, 'value':((int(point['dv4']) & 0x80) )})

          
        else:
          dimmer4.append({'epoch':ts, 'value':'---'})
          dimmer_override.append({'epoch':ts, 'value':'---'})
          dimmer_status.append({'epoch':ts, 'value':'---'})
          dimmer_motion.append({'epoch':ts, 'value':'---'})
          dimmer_photooverride.append({'epoch':ts, 'value':'---'})       
          dimmer_switchoverride.append({'epoch':ts, 'value':'---'})   

        #log.info('freeboard_dimmer_values:  statusvalues%s:', statusvalues)
        #statusvalues.append(int(Instance))

        # check if array was all NONE  - if so disgard it
        #if not (statusvalues[0] == 255 and statusvalues[1] == 255 and statusvalues[2] == 255 and statusvalues[3] == 255 and statusvalues[4] == 255 ):
        #  dimmerstatus.append(statusvalues)
   

      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")

      if gwtype == "mesh":

        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','dimmer_value':list(reversed(dimmer0)),'dimmer_dio_adc3':list(reversed(dimmer2)),'dimmer_adc':list(reversed(dimmer3)),'dimmer_adc2':list(reversed(dimmer1)),'dimmer_motion':list(reversed(dimmer_motion)),'dimmer_override':list(reversed(dimmer_override)), 'dimmer_switchoverride':list(reversed(dimmer_switchoverride)), 'dimmer_photooverride':list(reversed(dimmer_photooverride)), 'dimmer_status':list(reversed(dimmer_status))})     

      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','dimmer0_value':list(reversed(dimmer0)),'dimmer1_value':list(reversed(dimmer1)),'dimmer2_value':list(reversed(dimmer2)),'dimmer3_value':list(reversed(dimmer3)),'dimmer4_value':list(reversed(dimmer4))})     

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  

@app.route('/freeboard_switch_bank_status')
@cross_origin()
def freeboard_switch_bank_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    mytimezone = request.args.get('timezone',"UTC")
    response = None

    switchstatus=[]
    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    if resolution == "":
      resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard freeboard_bank_status deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='seasmartswitch'  AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    #log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    #query = ('select  median(bank0) AS bank0, median(bank1) AS  bank1 FROM {} '
    query = ('select  median(value0) as sw0, '
                     'median(value1) as sw1, '
                     'median(value2) as sw2, '
                      'median(value3) as sw3, '
                      'median(value4) as sw4, '
                      'median(value5) as sw5, '
                      'median(value6) as sw6, '
                      'median(value7) as sw7, '
                      'median(value8) as sw8, '
                      'median(value9) as sw9, '
                      'median(value10) as sw10, '
                      'median(value11) as sw11, '
                      'median(value12) as sw12, '
                      'median(value13) as sw13, '
                      'median(value14) as sw14, '
                      'median(value15) as sw15 '
                     ' FROM {} '             
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard freeboard_bank_status data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})    

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})    

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})    

    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      bankvalue0 = 0xFFFF
      bankvalue1 = 0xFFFF

      byte0 = 0xFF
      byte1 = 0xFF
      byte2 = 0xFF
      byte3 = 0xFF
      
      status0=0x03
      status1=0x03
      status2=0x03
      status3=0x03
      status4=0x03
      status5=0x03
      status6=0x03
      status7=0x03
      status8=0x03
      status9=0x03
      status10=0x03
      status11=0x03
      status12=0x03
      status13=0x03
      status14=0x03
      status15=0x03

      switchstatus=[]
       
      points = list(response.get_points())

      #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        #log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)
  
        statusvalues=[]
        
        if point['sw0'] is not None:
          statusvalues.append(int(point['sw0']))
        else:
          statusvalues.append(int(3))

        
        if point['sw1'] is not None:
          statusvalues.append(int(point['sw1']))
        else:
          statusvalues.append(int(3))

        
        if point['sw2'] is not None:
          statusvalues.append(int(point['sw2']))
        else:
          statusvalues.append(int(3))

        
        if point['sw3'] is not None:
          statusvalues.append(int(point['sw3']))
        else:
          statusvalues.append(int(3))

        
        if point['sw4'] is not None:
          statusvalues.append(int(point['sw4']))
        else:
          statusvalues.append(int(3))

        
        if point['sw5'] is not None:
          statusvalues.append(int(point['sw5']))
        else:
          statusvalues.append(int(3))

        
        if point['sw6'] is not None:
          statusvalues.append(int(point['sw6']))
        else:
          statusvalues.append(int(3))

        
        if point['sw7'] is not None:
          statusvalues.append(int(point['sw7']))
        else:
          statusvalues.append(int(3))

        
        if point['sw8'] is not None:
          statusvalues.append(int(point['sw8']))
        else:
          statusvalues.append(int(3))

        
        if point['sw9'] is not None:
          statusvalues.append(int(point['sw9']))
        else:
          statusvalues.append(int(3))

        
        if point['sw10'] is not None:
          statusvalues.append(int(point['sw10']))
        else:
          statusvalues.append(int(3))

        
        if point['sw11'] is not None:
          statusvalues.append(int(point['sw11']))
        else:
          statusvalues.append(int(3))

        
        if point['sw12'] is not None:
          statusvalues.append(int(point['sw12']))
        else:
          statusvalues.append(int(3))

        
        if point['sw13'] is not None:
          statusvalues.append(int(point['sw13']))
        else:
          statusvalues.append(int(3))

        
        if point['sw14'] is not None:
          statusvalues.append(int(point['sw14']))
        else:
          statusvalues.append(int(3))

        
        if point['sw15'] is not None:
          statusvalues.append(int(point['sw15']))
        else:
          statusvalues.append(int(3))

        #log.info('freeboard_switch_bank_status:  statusvalues%s:', statusvalues)
        statusvalues.append(int(Instance))

        # check if array was all NONE  - if so disgard it
        if not (statusvalues[0] == 3 and statusvalues[1] == 3 and statusvalues[2] == 3 and statusvalues[3] == 3 and statusvalues[4] == 3 and statusvalues[5] == 3 and statusvalues[6] == 3 and statusvalues[7] == 3 and statusvalues[8] == 3 and statusvalues[9] == 3 and statusvalues[10] == 3 and statusvalues[11] == 3 and statusvalues[12] == 3 and statusvalues[13] == 3 and statusvalues[14] == 3 and statusvalues[15] == 3):
          switchstatus.append(statusvalues)
          #log.info('freeboard_switch_bank_status:  switchstatus%s:', switchstatus)          




          
        """
        if point['bank0'] is not None:
          bankvalue0 =  point['bank0']

          if bankvalue0 & 0x1 == 0x1:
            status0=0x01
          else:
            status0=0x00
            
          if bankvalue0 & 0x2 == 0x2:
            status1=0x04
          else:
            status1=0x00

          if bankvalue0 & 0x4 == 0x4:
            status2=0x10
          else:
            status2=0x00

          if bankvalue0 & 0x8 == 0x8:
            status3=0x40
          else:
            status3=0x00

          byte0= status0 | status1 | status2 | status3
            

          if bankvalue0 & 0x10 == 0x10:
            status4=0x01
          else:
            status4=0x00

          if bankvalue0 & 0x20 == 0x20:
            status5=0x04
          else:
            status5=0x00

          if bankvalue0 & 0x40 == 0x40:
            status6=0x10
          else:
            status6=0x00

          if bankvalue0 & 0x80 == 0x80:
            status7=0x40
          else:
            status7=0x00

          byte1= status4 | status5 | status6 | status7

        if point['bank1'] is not None:
          bankvalue1 =  point['bank1']


          if bankvalue1 & 0x1 == 0x1:
            status8=0x01
          else:
            status8=0x00
            
          if bankvalue1 & 0x2 == 0x2:
            status9=0x04
          else:
            status9=0x00

          if bankvalue1 & 0x4 == 0x4:
            status10=0x10
          else:
            status10=0x00

          if bankvalue1 & 0x8 == 0x8:
            status11=0x40
          else:
            status11=0x00

          byte2= status8 | status9 | status10 | status11
            

          if bankvalue1 & 0x10 == 0x10:
            status12=0x01
          else:
            status12=0x00

          if bankvalue1 & 0x20 == 0x20:
            status13=0x04
          else:
            status13=0x00

          if bankvalue1 & 0x40 == 0x40:
            status14=0x10
          else:
            status14=0x00

          if bankvalue1 & 0x80 == 0x80:
            status15=0x40
          else:
            status15=0x00

          byte3= status12 | status13 | status14 | status15    

        log.info('freeboard:  InfluxDB-Cloud bankvalues %s:%s', bankvalue0, bankvalue1)
        
        #switchstates =  "{:02X}".format(int(Instance))  +  "{:01X}".format(int(byte1))  +  "{:01X}".format(int(byte0)) +  "{:01X}".format(int(byte3)) +  "{:01X}".format(int(byte3))

        switchstates = []

        switchstates.append("{:02X}".format(int(Instance)))
        switchstates.append("{:01X}".format(int(byte0)))
        switchstates.append("{:01X}".format(int(byte1)))
        switchstates.append("{:01X}".format(int(byte2)))
        switchstates.append("{:01X}".format(int(byte3)))
  
        log.info('freeboard:  InfluxDB-Cloud switchstates %s:', switchstates)
          
        switchstatus.append({'epoch':ts, 'value':switchstates})
          
        """       


      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate= mydatetimetz.strftime("%B %d, %Y %H:%M:%S")  
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'bank0':value1, 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','status0':list(reversed(status0)), 'status1':list(reversed(status1)), 'status2':list(reversed(status2)),'status3':list(reversed(status3)), 'status4':list(reversed(status4)), 'status5':list(reversed(status5)),'status6':list(reversed(status6)), 'status7':list(reversed(status7)), 'status8':list(reversed(status8)),'status9':list(reversed(status9)), 'status10':list(reversed(status10)), 'status11':list(reversed(status11)),'status12':list(reversed(status12)), 'status13':list(reversed(status13)), 'status14':list(reversed(status14)), 'status15':list(reversed(status15))})     
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','switch_bank':list(reversed(switchstatus))})     

      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True',  'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7})

    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  

@app.route('/get_dbstats')
@cross_origin()
def get_dbstats():

  deviceapikey = request.args.get('apikey','')
  Interval = request.args.get('Interval',"5min")
  rollup = request.args.get('rollup',"sum")

  response = None

  
  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]

  useremail = getuseremail(deviceapikey)
    
  log.info("freeboard get_dbstats useremail %s", useremail)

  response = None
  
  measurement = "HelmSmartDB"
  stat0 = '---'
  stat1 = '---'
  stat2 = '---'
  stat3 = '---'
  stat4 = '---'
  stat5 = '---'
  stat6 = '---'
  stat7 = '---'
  stat8 = '---'
  stat9 = '---'
  stat10 = '---'
  stat11 = '---'
  stat12 = '---'
  stat13 = '---'
  stat14 = '---'
  stat15 = '---'
  stat16 = '---'


  conn = db_pool.getconn()

  cursor = conn.cursor()
  cursor.execute("select deviceid, devicename from user_devices")
  records = cursor.fetchall()

  db_pool.putconn(conn)   



  try:
   

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'


    db = InfluxDBCloud(host, port, username, password, database,  ssl=True)
     

    
    start = datetime.datetime.fromtimestamp(float(startepoch))
    

    end = datetime.datetime.fromtimestamp(float(endepoch))
    resolutionstr = "PT" + str(resolution) + "S"

    #rollup = "mean"

 

    query = ('select {}(records) AS records FROM {} '
                     'where time > {}s and time < {}s '
                     'group by *, time({}s) LIMIT 1') \
                .format(rollup,  measurement, 
                        startepoch, endepoch,
                        resolution) 

    #query =(' select records as records from HelmSmartDB')      
      
    
    log.info("inFlux-cloud Query %s", query)
    

    try:
      response= db.query(query)
    except:
      e = sys.exc_info()[0]
      log.info('inFluxDB: Error in geting inFluxDB data %s:  ' % e)
        
      return jsonify( message='Error in inFluxDB query 2', status='error')
      #raise

    
    #return jsonify(results=response)
    
    #response =  shim.read_multi(keys=[SERIES_KEY], start=start, end=end, period=resolutionstr, rollup="mean" )
    
    #print 'inFluxDB read :', response.response.successful

    
    if not response:
      #print 'inFluxDB Exception1:', response.response.successful, response.response.reason 
      return jsonify( message='No response to return 1' , status='error')


    #if not response.points:
    #  #print 'inFluxDB Exception2:', response.response.successful, response.response.reason 
    #  return jsonify( message='No data to return 2', status='error')

    print 'inFluxDB processing data headers:'
    jsondata=[]
    jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    print 'inFluxDB start processing data points:'
    #log.info("freeboard Get InfluxDB response %s", response)

    keys = response.raw.get('series',[])
    #log.info("freeboard Get InfluxDB series keys %s", keys)




    strvalue=""
    
    for series in keys:
      #log.info("freeboard Get InfluxDB series key %s", series)
      #log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
      #log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
      #log.info("freeboard Get InfluxDB series values %s ", series['values'])

      """        
      values = series['values']
      for value in values:
        log.info("freeboard Get InfluxDB series time %s", value[0])
        log.info("freeboard Get InfluxDB series mean %s", value[1])
      """

      tag = series['tags']
      log.info("freeboard Get InfluxDB series tags2 %s ", tag)

      #mydatetimestr = str(fields['time'])
      strvaluekey = {'Series': series['tags'], 'start': startepoch,  'end': endepoch}
      jsonkey.append(strvaluekey)        

      log.info("freeboard Get InfluxDB series tags3 %s ", tag['deviceid'])

      
      for point in series['values']:
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val
          
        log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields['records'])
        
        if fields['records'] != None:

          devicename = ""
          deviceid = tag['deviceid']
          for record in records:
            #log.info("get_dbstats deviceid %s - devicename %s", record[0], record[1])    
            if deviceid == record[0]:
              devicename = record[1]
          
          strvalue = {'epoch': fields['time'], 'source':tag['deviceid'], 'name':devicename, 'value': fields['records']}
          jsondata.append(strvalue)





    jsondata = sorted(jsondata,key=itemgetter('value'), reverse=True)

    total = 0

    for stat in jsondata:
      if stat['value'] != None:
        total = total + float(stat['value'])

    if len(jsondata) > 0:
      mydatetimestr = str(jsondata[0]['epoch'])
      stat0 = str(jsondata[0]['source']) + ":" + str(jsondata[0]['name']) + " = " +  str(jsondata[0]['value'])

    if len(jsondata) > 1:
      stat1 = str(jsondata[1]['source']) + ":" + str(jsondata[1]['name']) + " = " +  str(jsondata[1]['value'])       

    if len(jsondata) > 2:
      stat2 = str(jsondata[2]['source']) + ":" + str(jsondata[2]['name']) + " = " +  str(jsondata[2]['value'])       

    if len(jsondata) > 3:
      stat3 = str(jsondata[3]['source']) + ":" + str(jsondata[3]['name']) + " = " +  str(jsondata[3]['value'])       

    if len(jsondata) > 4:
      stat4 = str(jsondata[4]['source']) + ":" + str(jsondata[4]['name']) + " = " +  str(jsondata[4]['value'])       

    if len(jsondata) > 5:
      stat5 = str(jsondata[5]['source']) + ":" + str(jsondata[5]['name']) + " = " +  str(jsondata[5]['value'])       

    if len(jsondata) > 6:
      stat6 = str(jsondata[6]['source']) + ":" + str(jsondata[6]['name']) + " = " +  str(jsondata[6]['value'])       

    if len(jsondata) > 7:
      stat7 = str(jsondata[7]['source']) + ":" + str(jsondata[7]['name']) + " = " +  str(jsondata[7]['value'])       

    if len(jsondata) > 8:
      stat8 = str(jsondata[8]['source']) + ":" + str(jsondata[8]['name']) + " = " +  str(jsondata[8]['value'])       

    if len(jsondata) > 9:
      stat9 = str(jsondata[9]['source']) + ":" + str(jsondata[9]['name']) + " = " +  str(jsondata[9]['value'])       

    if len(jsondata) > 10:
      stat10 = str(jsondata[10]['source']) + ":" + str(jsondata[10]['name']) + " = " +  str(jsondata[10]['value'])            

    if len(jsondata) > 11:
      stat11 = str(jsondata[11]['source']) + ":" + str(jsondata[11]['name']) + " = " +  str(jsondata[11]['value'])       

    if len(jsondata) > 12:
      stat12 = str(jsondata[12]['source']) + ":" + str(jsondata[12]['name']) + " = " +  str(jsondata[12]['value'])       

    if len(jsondata) > 13:
      stat13 = str(jsondata[13]['source']) + ":" + str(jsondata[13]['name']) + " = " +  str(jsondata[13]['value'])       

    if len(jsondata) > 14:
      stat14 = str(jsondata[14]['source']) + ":" + str(jsondata[14]['name']) + " = " +  str(jsondata[14]['value'])       

    if len(jsondata) > 15:
      stat15 = str(jsondata[15]['source']) + ":" + str(jsondata[15]['name']) + " = " +  str(jsondata[15]['value'])       

    if len(jsondata) > 16:
      stat16 = str(jsondata[16]['source']) + ":" + str(jsondata[16]['name']) + " = " +  str(jsondata[16]['value'])       

    mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

    #log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', stat1,stat2)            

    callback = request.args.get('callback')
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


    #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
    return '{0}({1})'.format(callback, {'date_time':myjsondate, 'Interval':str(Interval),'update':'True','total':int(total),'stat0':stat0,'stat1':stat1,'stat2':stat2,'stat3':stat3,'stat4':stat4,'stat5':stat5,'stat6':stat6,'stat7':stat7,'stat8':stat8,'stat9':stat9,'stat10':stat10,'stat11':stat11,'stat12':stat12,'stat13':stat13,'stat14':stat14,'stat15':stat15,'stat16':stat16})



  except TypeError, e:
      log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ' % str(e))
          
  except KeyError, e:
      log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ' % str(e))

  except NameError, e:
      log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ' % str(e))
          
  except IndexError, e:
      log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Index Error in InfluxDB mydata append %s:  ' % str(e))  

  except ValueError, e:
    log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
    log.info('get_influxdbcloud_data: Value Error in InfluxDB  %s:  ' % str(e))

  except AttributeError, e:
    log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
    log.info('get_influxdbcloud_data: AttributeError in InfluxDB  %s:  ' % str(e))     

  except InfluxDBClientError, e:
    log.info('get_influxdbcloud_data: Exception Error in InfluxDB  %s:  ' % str(e))     
  
  except:
    log.info('get_influxdbcloud_data: Error in geting freeboard response %s:  ', strvalue)
    e = sys.exc_info()[0]
    log.info('get_influxdbcloud_data: Error in geting freeboard ststs %s:  ' % e)
    return jsonify( message='error processing data 3' , status='error')        

  callback = request.args.get('callback')
  return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })


@app.route('/get_dbstats_html')
@cross_origin()
def get_dbstats_html():

  deviceapikey = request.args.get('apikey','')
  Interval = request.args.get('interval',"12hour")
  rollup = request.args.get('rollup',"sum")

  response = None

  period = 1
  
  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]
  
  log.info("freeboard get_dbstats_html deviceapikey %s", deviceapikey)
  useremail = getuseremail(deviceapikey)
    
  log.info("freeboard get_dbstats_html useremail %s", useremail)

    

  response = None
  
  measurement = "HelmSmartDB"
  stat0 = '---'
  stat1 = '---'
  stat2 = '---'
  stat3 = '---'
  stat4 = '---'
  stat5 = '---'
  stat6 = '---'
  stat7 = '---'
  stat8 = '---'
  stat9 = '---'
  stat10 = '---'
  stat11 = '---'
  stat12 = '---'
  stat13 = '---'
  stat14 = '---'
  stat15 = '---'
  stat16 = '---'


  conn = db_pool.getconn()

  cursor = conn.cursor()
  #cursor.execute("select deviceid, devicename from user_devices where useremail = ")
  #query = "select deviceid, devicename from user_devices where useremail = %s "
  #cursor.execute(query,useremail)
  cursor.execute("select deviceid, devicename from user_devices where useremail = %s" , (useremail,))
  
  records = cursor.fetchall()

  db_pool.putconn(conn)   



  try:
   

    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'


    db = InfluxDBCloud(host, port, username, password, database,  ssl=True)
     

    
    start = datetime.datetime.fromtimestamp(float(startepoch))
    

    end = datetime.datetime.fromtimestamp(float(endepoch))


    resolution = 3600
    if Interval == "1hour":
      resolution = 300
    elif Interval == "2hour":
      resolution = 600
    elif Interval == "1day":
      resolution = 7200

      
    resolutionstr = "PT" + str(resolution) + "S"

    #rollup = "mean"

 

    query = ('select {}(records) AS records FROM {} '
                     'where time > {}s and time < {}s '
                     'group by *, time({}s) ') \
                .format(rollup,  measurement, 
                        startepoch, endepoch,
                        resolution) 

    #query =(' select records as records from HelmSmartDB')      
      
    
    log.info("inFlux-cloud Query %s", query)
    

    try:
      response= db.query(query)
    except:
      e = sys.exc_info()[0]
      log.info('inFluxDB: Error in geting inFluxDB data %s:  ' % e)
        
      return jsonify( message='Error in inFluxDB query 2', status='error')
      #raise

    
    #return jsonify(results=response)
    
    #response =  shim.read_multi(keys=[SERIES_KEY], start=start, end=end, period=resolutionstr, rollup="mean" )
    
    #print 'inFluxDB read :', response.response.successful

    
    if not response:
      #print 'inFluxDB Exception1:', response.response.successful, response.response.reason 
      return jsonify( message='No response to return 1' , status='error')


    #if not response.points:
    #  #print 'inFluxDB Exception2:', response.response.successful, response.response.reason 
    #  return jsonify( message='No data to return 2', status='error')

    print 'inFluxDB processing data headers:'
    jsondata=[]
    jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    print 'inFluxDB start processing data points:'
    #log.info("freeboard Get InfluxDB response %s", response)

    keys = response.raw.get('series',[])
    #log.info("freeboard Get InfluxDB series keys %s", keys)




    strvalue=""
    
    for series in keys:
      #log.info("freeboard Get InfluxDB series key %s", series)
      #log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
      #log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
      #log.info("freeboard Get InfluxDB series values %s ", series['values'])

      """        
      values = series['values']
      for value in values:
        log.info("freeboard Get InfluxDB series time %s", value[0])
        log.info("freeboard Get InfluxDB series mean %s", value[1])
      """

      tag = series['tags']
      devicename = ""
      deviceid = tag['deviceid']
      for record in records:
        #log.info("get_dbstats deviceid %s - devicename %s", record[0], record[1])    
        if deviceid == record[0]:
          devicename = record[1]
              
      #log.info("get_dbstats deviceid %s - devicename %s", deviceid, devicename)


      #mydatetimestr = str(fields['time'])
      #strvaluekey = {'Series': series['tags'], 'start': startepoch,  'end': endepoch}
      #jsonkey.append(strvaluekey)        

      #log.info("freeboard Get InfluxDB series tags3 %s ", tag['deviceid'])
      #log.info("freeboard Get InfluxDB series series['values'] %s ", series['values'])
      values=[]
      for point in reversed(series['values']):
        fields = {}
        for key, val in zip(series['columns'], point):
          fields[key] = val
          
        #log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields['records'])
        
        if fields['records'] != None:
          values.append( fields['records'])
        else:
          values.append("---")
          
      strvalue = {'epoch': fields['time'], 'source':tag['deviceid'], 'name':devicename, 'value':values}
      jsondata.append(strvalue)
      #log.info("get_dbstats jsondata %s ", strvalue)

    #return jsonify( message=jsondata)


    #jsondata = sorted(jsondata,key=itemgetter('value'), reverse=True)
    totals=[]
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)   
    totals.append(0)
    totals.append(0)
    totals.append(0)
    totals.append(0)
    
    total = 0
    stathtml = '<table border="0" cellspacing="5" cellpadding="5" style="width:100%; display: block">'
    
    stathtml = stathtml + "<tr> <td>" + "DeviceID" + "</td><td>" + "Device Name" + "</td>"
    stathtml = stathtml + "<td>" + "now" + "</td>"

    #log.info("get_dbstats header1 %s ", stathtml)
    units = "hr"
    period = 1
    
    if Interval == "1hour":
      period = 5
      units = "min"

    elif Interval == "2hour":
      period = 10
      units = "min"
      
    elif Interval == "1day":
      period = 2
      units = "hr"
      
    stathtml = stathtml + "<td>" +  str(int(period) * 1) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 2) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 3) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 4) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 5) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 6) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 7) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 8) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 9) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 10) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 11) +units + "</td>"
    stathtml = stathtml + "<td>" +  str(int(period) * 12) +units + "</td>"

    stathtml = stathtml + "</tr>"

    
    #log.info("get_dbstats header2 %s ", stathtml)

    
    for statdata in jsondata:
      stathtml = stathtml + "<tr> <td>" +  str(statdata['source']) + "</td><td>" + str(statdata['name']) + " </td>"

      tindex=0
      values = statdata['value']
      for value in values:
        
        if value != "---":
          stathtml = stathtml + "<td>" +  str(float("{0:.1f}".format(int(value) * 0.001) )) + "</td>"
          total = total + int(value)
          totals[tindex]=int(totals[tindex]) + int(value)
          
        else:
          stathtml = stathtml + "<td>" +  "---"  + "</td>"
          
        tindex = tindex + 1
      #log.info("get_dbstats deviceid %s - tindex %s", statdata['source'], tindex)
        
      stathtml = stathtml + "  </tr>"

    
    stathtml = stathtml + "<tr> <td>" + "" + "</td><td>" + "Totals" + "</td>"
    try:
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[0]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[1]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[2]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[3]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[4]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[5]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[6]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[7]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[8]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[9]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[10]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[11]) * 0.001) ))  + "</td>"
      stathtml = stathtml + "<td>" +    str(float("{0:.1f}".format(int(totals[12]) * 0.001) ))  + "</td>"
    except:
      pass
    
    stathtml = stathtml + "</tr>"      
    
    stathtml = stathtml + "</table>"

    #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

    #log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', stat1,stat2)            

    callback = request.args.get('callback')
    #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

    mydatetime = datetime.datetime.now()
    myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")    
    #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
    #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'Interval':str(Interval),'update':'True','total':int(total),'stat0':stat0,'stat1':stat1,'stat2':stat2,'stat3':stat3,'stat4':stat4,'stat5':stat5,'stat6':stat6,'stat7':stat7,'stat8':stat8,'stat9':stat9,'stat10':stat10,'stat11':stat11,'stat12':stat12,'stat13':stat13,'stat14':stat14,'stat15':stat15,'stat16':stat16})
    return '{0}({1})'.format(callback, {'date_time':myjsondate, 'Interval':str(Interval),'update':'True','total':int(total),'stats':stathtml})

 

  except TypeError, e:
      log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ' % str(e))
          
  except KeyError, e:
      log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ' % str(e))

  except NameError, e:
      log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ' % str(e))
          
  except IndexError, e:
      #log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Index Error in InfluxDB mydata append %s:  ' % str(e))
      pass

  except ValueError, e:
    log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
    log.info('get_influxdbcloud_data: Value Error in InfluxDB  %s:  ' % str(e))

  except AttributeError, e:
    log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
    log.info('get_influxdbcloud_data: AttributeError in InfluxDB  %s:  ' % str(e))     

  except InfluxDBClientError, e:
    log.info('get_influxdbcloud_data: Exception Error in InfluxDB  %s:  ' % str(e))     
  
  except:
    log.info('get_influxdbcloud_data: Error in geting freeboard response %s:  ', strvalue)
    e = sys.exc_info()[0]
    log.info('get_influxdbcloud_data: Error in geting freeboard ststs %s:  ' % e)
    return jsonify( message='error processing data 3' , status='error')        

  callback = request.args.get('callback')
  return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  

@app.route('/get_influxdbcloud_data')
@cross_origin()
def get_influxdbcloud_data():
  conn = db_pool.getconn()



  pgnnumber = request.args.get('pgnnumber', '000000')
  userid = request.args.get('userid', '4d231fb3a164c5eeb1a8634d34c578eb')
  deviceid = request.args.get('deviceid', 'HelmSmart')
  startepoch = request.args.get('startepoch', 0)
  endepoch = request.args.get('endepoch', 0)
  resolution = request.args.get('resolution', 60)
  SERIES_KEY = request.args.get('serieskey', 0)

  response = None
  
  measurement = "HelmSmart"
  measurement = 'HS_' + str(deviceid)
    
  query = "select devicename from user_devices where userid = %s AND deviceid = %s"
  sqlstr = 'select * from getpgn' + pgnnumber + '(%s,%s,%s,%s,%s,%s,%s);'


  try:
    ## first check db to see if user id is matched to device id
    cursor = conn.cursor()
    #cursor.execute(query, (userid, deviceid))
    #i = cursor.fetchone()
    ## if not then just exit
    #if cursor.rowcount == 0:
    #    return jsonify( message='No Userid = deviceid match', status='error')
        
    ## else run the query
  

    # Modify these with your settings found at: http://tempo-db.com/manage/
    #API_KEY = '7be1d82569414dceaa82fd93fadd7940'
    #API_SECRET = '0447ec319c3148cb98d96bfc96c787e1'
    #SERIES_KEY = '4775fc8040fa4378841570d73ff853ab'
    #SERIES_KEY = 'interval:6sec.series:2.' 
    #SERIES_KEY = 'instance:0.PGN:127488.Parameter:2.Source:0.'
    #SERIES_KEY = 'deviceid:000000000000.source:0.PGN:127488.instance:0.Parameter:3.HelmSmart'
    # SeaDream Enviromentail outside temperature
    #SERIES_KEY = 'd0a36adb1b834860b1bd24bf3a341891'
    #SERIES_KEY = 'deviceid:00204ac0e9ba.sensor:environmental_data.source:0D.instance:0.type:Outside Temperature.parameter:temperature.HelmSmart'
    #SERIES_KEY = 'deviceid:00204ac0e9ba.sensor:environmental_data.source:0D.instance:0.type:Outside Temperature.parameter:temperature.HelmSmart'
    #SERIES_KEY = 'deviceid:00204ac0e9ba.sensor:environmental_data.source:0D.instance:0.type:Outside Temperature.parameter:temperature.HelmSmart'

    #API_KEY = '7be1d82569414dceaa82fd93fadd7940'
    #API_SECRET = '0447ec319c3148cb98d96bfc96c787e1'
    #client = Client(API_KEY, API_KEY, API_SECRET)


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'




  
    #db = influxdb.InfluxDBClient(host, port, username, password, database)
    db = InfluxDBCloud(host, port, username, password, database,  ssl=True)
     
    #shim = Shim(host, port, username, password, database)
    
    #start = datetime.date(2014, 2, 24)
    #start = datetime.date(startepoch)
    #start = datetime.datetime.utcfromtimestamp(float(startepoch))

    #startepoch = 1393257600
    #endepoch = 1393804800
    #resolution="60"
    
    start = datetime.datetime.fromtimestamp(float(startepoch))
    

    end = datetime.datetime.fromtimestamp(float(endepoch))
    resolutionstr = "PT" + resolution + "S"

    rollup = "mean"

    #print 'inFlux Series Key:', SERIES_KEY
    log.info("inFlux SERIES_KEY %s", SERIES_KEY)
    #attrs = key_to_attributes(SERIES_KEY)  
    #name = "{}.{}.{}.{}.{}".format(attrs['deviceid'], attrs['sensor'], attrs['instance'], attrs['type'], attrs['parameter'])
    
    #query = 'select MEAN(value) from "001EC0B415BF.environmental_data.0.Outside Temperature.temperature" where time > now() - 1d group by time(10m);'

    if SERIES_KEY.find(".*.") > 0:  
        SERIES_KEY = SERIES_KEY.replace(".*.","*.")

    seriesname = SERIES_KEY
    seriestags = seriesname.split(".")

    seriesdeviceidtag = seriestags[0]
    seriesdeviceid = seriesdeviceidtag.split(":")

    seriessensortag = seriestags[1]
    seriessensor = seriessensortag.split(":")
    
    seriessourcetag = seriestags[2]
    seriessource = seriessourcetag.split(":")

    seriesinstancetag = seriestags[3]
    seriesinstance = seriesinstancetag.split(":")

    seriestypetag = seriestags[4]
    seriestype = seriestypetag.split(":")

    seriesparametertag = seriestags[5]
    seriesparameter = seriesparametertag.split(":")    
    parameter = seriesparameter[1]

    if seriessource[1] == "*":
      serieskeys=" deviceid='"
      serieskeys= serieskeys + seriesdeviceid[1] + "' AND "
      serieskeys= serieskeys +  " sensor='" +  seriessensor[1] + "'  AND "
      serieskeys= serieskeys +  " instance='" +  seriesinstance[1] + "'  AND "
      serieskeys= serieskeys +  " type='" +  seriestype[1] + "'  AND "
      serieskeys= serieskeys +  " parameter='" +  seriesparameter[1] + "'   "
      
    else:
      serieskeys=" deviceid='"
      serieskeys= serieskeys + seriesdeviceid[1] + "' AND "
      serieskeys= serieskeys +  " sensor='" +  seriessensor[1] + "'  AND "
      serieskeys= serieskeys +  " source='" +  seriessource[1] + "'  AND "
      serieskeys= serieskeys +  " instance='" +  seriesinstance[1] + "'  AND "
      serieskeys= serieskeys +  " type='" +  seriestype[1] + "'  AND "
      serieskeys= serieskeys +  " parameter='" +  seriesparameter[1] + "'   "
      


    log.info("inFlux-cloud serieskeys %s", serieskeys)


    query = ('select {}({}) AS {} FROM {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by *, time({}s)') \
                .format(rollup, parameter, parameter, measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 

      
      
    
    log.info("inFlux-cloud Query %s", query)
    

    try:
      response= db.query(query)
    except:
      e = sys.exc_info()[0]
      log.info('inFluxDB: Error in geting inFluxDB data %s:  ' % e)
        
      return jsonify( message='Error in inFluxDB query 2', status='error')
      #raise

    
    #return jsonify(results=response)
    
    #response =  shim.read_multi(keys=[SERIES_KEY], start=start, end=end, period=resolutionstr, rollup="mean" )
    
    #print 'inFluxDB read :', response.response.successful

    
    if not response:
      #print 'inFluxDB Exception1:', response.response.successful, response.response.reason 
      return jsonify( message='No response to return 1' , status='error')

    try:
  
      #if not response.points:
      #  #print 'inFluxDB Exception2:', response.response.successful, response.response.reason 
      #  return jsonify( message='No data to return 2', status='error')

      print 'inFluxDB processing data headers:'
      jsondata=[]
      jsonkey=[]
      #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
      #jsonkey.append(strvaluekey)
      print 'inFluxDB start processing data points:'
      #log.info("freeboard Get InfluxDB response %s", response)

      keys = response.raw.get('series',[])
      #log.info("freeboard Get InfluxDB series keys %s", keys)




      strvalue=""
      
      for series in keys:
        #log.info("freeboard Get InfluxDB series key %s", series)
        #log.info("freeboard Get InfluxDB series tags %s ", series['tags'])
        #log.info("freeboard Get InfluxDB series columns %s ", series['columns'])
        #log.info("freeboard Get InfluxDB series values %s ", series['values'])

        """        
        values = series['values']
        for value in values:
          log.info("freeboard Get InfluxDB series time %s", value[0])
          log.info("freeboard Get InfluxDB series mean %s", value[1])
        """

        tag = series['tags']
        log.info("freeboard Get InfluxDB series tags2 %s ", tag)

        #mydatetimestr = str(fields['time'])
        strvaluekey = {'Series': series['tags'], 'start': startepoch,  'end': endepoch, 'resolution': resolution}
        jsonkey.append(strvaluekey)        

        log.info("freeboard Get InfluxDB series tags3 %s ", tag['source'])

        
        for point in series['values']:
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val
            
          log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields[parameter])
          strvalue = {'epoch': fields['time'], 'source':tag['source'], 'value': fields[parameter]}
          
          jsondata.append(strvalue)





      jsondata = sorted(jsondata,key=itemgetter('epoch'))
      print 'inFluxDB returning data points:'
      #return jsonify( results = jsondata)      
      return jsonify(serieskey = jsonkey, results = jsondata)
      #result = json.dumps(data.data, cls=DateEncoder)
    
      #response = make_response(result) 
      
      #response.headers['content-type'] = "application/json"
      #return response

    except TypeError, e:
        log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
        log.info('get_influxdbcloud_data: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', response)
      log.info('get_influxdbcloud_data: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('get_influxdbcloud_data: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
      log.info('get_influxdbcloud_data: Error in geting freeboard response %s:  ', strvalue)
      e = sys.exc_info()[0]
      log.info('get_influxdbcloud_data: Error in geting freeboard ststs %s:  ' % e)
      return jsonify( message='error processing data 3' , status='error')        
  
    

    #return jsonify(result = data.data)
    #return datasets[0].data
  finally:
    db_pool.putconn(conn)




# Gets GPS lat and lng with data overlay
@app.route('/getgpsseriesbydeviceid')
@cross_origin()
def getgpsseriesbydeviceid():
  conn = db_pool.getconn()

  devicekey = request.args.get('devicekey', '4d231fb3a164c5eeb1a8634d34c578eb')
  deviceid = request.args.get('deviceid', '')
  startepoch = request.args.get('startepoch', 0)
  endepoch = request.args.get('endepoch', 0)
  resolution = request.args.get('resolution', 60)
  SERIES_KEY1 = request.args.get('serieskey1', '')
  SERIES_KEY2 = request.args.get('serieskey2', '')

  dataformat = request.args.get('format', 'json')
  minthreshold = request.args.get('min', '0')
  maxthreshold = request.args.get('max', '1000000')
  maxinterval = request.args.get('maxinterval', '1440')
  
  query = "select deviceid from user_devices where deviceapikey = %s"

  response = None
  
  measurement = "HelmSmart"
  measurement = 'HS_' + str(deviceid)

  try:
  #if dataformat == 'json':
      # first check db to see if deviceapikey is matched to device id
      if deviceid == "":
        cursor = conn.cursor()
        cursor.execute(query, (devicekey,))
        i = cursor.fetchone()
        # if not then just exit
        if cursor.rowcount == 0:
            return jsonify( message='No device key found', status='error')
        else:
            deviceid = str(i[0]) 
  

      # Modify these with your settings found at: http://tempo-db.com/manage/
      API_KEY = '7be1d82569414dceaa82fd93fadd7940'
      API_SECRET = '0447ec319c3148cb98d96bfc96c787e1'

      host = 'hilldale-670d9ee3.influxcloud.net' 
      port = 8086
      username = 'helmsmart'
      password = 'Salm0n16'
      database = 'pushsmart-cloud'


      db = InfluxDBCloud(host, port, username, password, database,  ssl=True)    


      #rollup = "mean"
      rollup = "median"

      #print 'TempoDB Series Key:', SERIES_KEY

      if SERIES_KEY1.find(".*.") > 0:  
        SERIES_KEY1 = SERIES_KEY1.replace(".*.","*.")

      if SERIES_KEY2.find(".*.") > 0:  
        SERIES_KEY2 = SERIES_KEY2.replace(".*.","*.")        
      
      gpskey =SERIES_KEY1

      overlaykey =SERIES_KEY2




      seriesname = SERIES_KEY1
      seriestags = seriesname.split(".")

      seriesdeviceidtag = seriestags[0]
      seriesdeviceid = seriesdeviceidtag.split(":")

      seriessensortag = seriestags[1]
      seriessensor = seriessensortag.split(":")

      seriessourcetag = seriestags[2]
      seriessource = seriessourcetag.split(":")

      seriesinstancetag = seriestags[3]
      seriesinstance = seriesinstancetag.split(":")

      seriestypetag = seriestags[4]
      seriestype = seriestypetag.split(":")

      seriesparametertag = seriestags[5]
      seriesparameter = seriesparametertag.split(":")    
      parameter = seriesparameter[1]

      if parameter == 'latlng':
        serieskeys="( deviceid='"
        serieskeys= serieskeys + seriesdeviceid[1] 
        serieskeys= serieskeys +  "' AND sensor='" +  seriessensor[1]
        if seriessource[1] != "*":
          serieskeys= serieskeys +  "' AND source='" +  seriessource[1] 
        serieskeys= serieskeys +  "' AND instance='" +  seriesinstance[1] 
        serieskeys= serieskeys +  "' AND type='" +  seriestype[1] 
        serieskeys= serieskeys +  "'  ) " 

 

                
      else:
        serieskeys="( deviceid='"
        serieskeys= serieskeys + seriesdeviceid[1] 
        serieskeys= serieskeys +  "' AND sensor='" +  seriessensor[1]
        if seriessource[1] != "*":
          serieskeys= serieskeys +  "' AND source='" +  seriessource[1] 
        serieskeys= serieskeys +  "' AND instance='" +  seriesinstance[1] 
        serieskeys= serieskeys +  "' AND type='" +  seriestype[1] 
        serieskeys= serieskeys +  "' AND parameter='" +  seriesparameter[1] + "'   )"

        


      log.info("inFlux-cloud serieskeys %s", serieskeys)


 

      

      if SERIES_KEY2 == "":
      # Just get lat/lng

        query = ('select median(lat) as lat, median(lng) as lng from {} '
                        'where {} AND time > {}s and time < {}s '
                       'group by *, time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)

        """
        query = ('select median(lat) as lat, median(lng) as lng from {} '
                        'where {} AND time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)
        """
        
        log.info("inFlux-cloud gps: Position Query %s", query)
        
      else:
      # get lat/lng plus overlay series

        overlayname = SERIES_KEY2
        log.info("inFlux-cloud gps: overlayname Query %s", overlayname)
        
        overlaytags = overlayname.split(".")
        log.info("inFlux-cloud gps: overlaytags Query %s", overlaytags)
        
        overlaydeviceidtag = overlaytags[0]
        overlaydeviceid = overlaydeviceidtag.split(":")

        overlaysensortag = overlaytags[1]
        overlaysensor =overlaysensortag.split(":")

        overlaysourcetag = overlaytags[2]
        overlaysource = overlaysourcetag.split(":")

        overlayinstancetag = overlaytags[3]
        overlayinstance = overlayinstancetag.split(":")

        overlaytypetag = overlaytags[4]
        overlaytype = overlaytypetag.split(":")

        overlayparametertag = overlaytags[5]
        overlayparameter = overlayparametertag.split(":")    

        log.info("inFlux-cloud gps: overlayparameter Query %s", overlayparameter)
        
        overlaykey="( deviceid='"
        overlaykey= overlaykey + overlaydeviceid[1] 
        overlaykey= overlaykey +  "' AND sensor='" +  overlaysensor[1]
        if overlaysource[1] != "*":
          overlaykey= overlaykey +  "' AND source='" +  overlaysource[1] 
        overlaykey= overlaykey +  "' AND instance='" +  overlayinstance[1] 
        overlaykey= overlaykey +  "' AND type='" +  overlaytype[1] 
        overlaykey= overlaykey +  "' AND parameter='" +  overlayparameter[1] + "'   )"

        log.info("inFlux-cloud gps: overlaykey Query %s", overlaykey)

        serieskeys   =    serieskeys  + " OR " +   overlaykey
        log.info("inFlux-cloud gps: serieskeys Query %s", serieskeys)
      
        query = ('select median(lat) as lat, median(lng) as lng, mean({}) as {} from {} '
                        'where {} AND time > {}s and time < {}s '
                       'group by *, time({}s)') \
                  .format( overlayparameter[1], overlayparameter[1], measurement, serieskeys,
                          startepoch, endepoch,
                          resolution)

   
        log.info("inFlux gps: Overlay Query %s", query)

        

      try:
        data= db.query(query)
        
      except TypeError, e:
        log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ' % str(e))
              
      except KeyError, e:
        log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ' % str(e))

      except NameError, e:
        log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ' % str(e))
              
      except IndexError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', query)
        log.info('get_influxdbcloud_data: Index Error in InfluxDB mydata append %s:  ' % str(e))  

      except ValueError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', query)
        log.info('get_influxdbcloud_data: Value Error in InfluxDB  %s:  ' % str(e))

      except AttributeError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', query)
        log.info('get_influxdbcloud_data: AttributeError in InfluxDB  %s:  ' % str(e))     

      except InfluxDBClientError, e:
        log.info('get_influxdbcloud_data: Exception Error in InfluxDB  %s:  ' % str(e))     
        
      except:
        #log.info('Telemetrypost: Error in geting Telemetry parameters %s:  ', posttype)
        e = sys.exc_info()[0]
        log.info('inFluxDB gps: Error in geting inFluxDB data %s:  ' % e)
        
        return jsonify( message='Error in inFluxDB query 2', status='error')
        #raise
      
      #return jsonify(results=data)
      #log.info('getgpsseriesbydeviceid: datad %s:  ', data)  

      if not data:
        return jsonify( message='No data object to return 1', status='error')

      #return jsonify( message='data object to return 1', status='success')
      # return csv formated data
      try:
        jsondata=[]
        jsonkey=[]
        strvaluekey = {'Series1': SERIES_KEY1, 'Series2': SERIES_KEY2,'start': startepoch,  'end': endepoch, 'resolution': resolution}
        jsonkey.append(strvaluekey)
        jsondataarray=[]

        #if overlaykey == "":
        # Just get lat/lng
        keys = data.raw.get('series',[])
        jsondata=[]
        for series in keys:
          #log.info("influxdb results..%s", series )
          #log.info("influxdb results..%s", series )
          strvalue ={}


          #name = series['name']
          name = series['tags']            
          #log.info("inFluxDB_GPS_JSON name %s", name )
          seriesname = series['tags'] 
          #seriestags = seriesname.split(".")
          #seriessourcetag = seriestags[2]
          #seriessource = seriessourcetag.split(":")
          source= seriesname['source']
          parameter = seriesname['parameter']
          #log.info("inFluxDB_GPS_JSON values %s", series['values'] )
          
          for point in  series['values']:
            fields = {}
            fields[parameter] = None
            for key, val in zip(series['columns'], point):
              fields[key] = val
              
            #strvalue = {'epoch': fields['time'], 'tag':seriesname, 'lat': fields['lat'], 'lng': fields['lng']}
            #log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields[parameter])

            mydatetimestr = str(fields['time'])

            #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
            mydatetime =  int(time.mktime(time.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')))
            
            #strvalue = {'epoch': fields['time'], 'source':tag['source'], 'value': fields[parameter]}
            if fields[parameter] != None:
              #strvalues = []
              strvalue = {'epoch': mydatetime, 'tag':seriesname, 'value': fields[parameter]}
              strvalues = (mydatetime, source,  parameter, fields[parameter] )

              
              jsondata.append(strvalues)


            
        # here we have an array of seperated lat and lng values taged with epoch times and series tags
        # Like 
        #'(u'HelmSmart', {u'instance': u'0', u'parameter': u'lat', u'deviceid': u'001EC010AD69', u'source': u'06', u'sensor': u'position_rapid', u'type': u'NULL'})':
        # [{u'time': u'2016-08-18T11:00:00Z', u'lng': None, u'lat': 42.012865}],
        # '(u'HelmSmart', {u'instance': u'0', u'parameter': u'lng', u'deviceid': u'001EC010AD69', u'source': u'06', u'sensor': u'position_rapid', u'type': u'NULL'})':
        # [{u'time': u'2016-08-18T11:00:00Z', u'lng': -124.13088, u'lat': None}],
        #
        # We need to reorder this into joined lat and lng based on same epoch times

        #jsondata = sorted(jsondata,key=itemgetter('epoch'))
        # sort based on epoch times
        jsondata = sorted(jsondata, key=lambda latlng: latlng[0])
        #log.info("freeboard  jsondata   %s",jsondata)
        #return jsonify( message=jsondata, status='success')

      
        # group lat and lng values based on epoch times and get rid of repeated epoch times
        for key, latlnggroup in groupby(jsondata, lambda x: x[0]):

          valuelat = None
          valuelng = None
          valueoverlay = None
          
          for latlng_values in latlnggroup:
            if latlng_values[2] == 'lat':
              valuelat = latlng_values[3]
              valuesource = latlng_values[1]
              
              
            elif latlng_values[2] == 'lng':
              valuelng = latlng_values[3]

            elif latlng_values[2] != None:
              valueoverlay = latlng_values[3]              
              

            
          #strvalues=  {'epoch': key, 'source':thing[1], 'value': thing[3]}

          # if we have valid lat and lng - make a json array
          if  valuelat != None and valuelng != None and valueoverlay != None:
            strvalues=  {'epoch': key, 'source':valuesource, 'lat': valuelat, 'lng': valuelng,  'overlay':valueoverlay}
            jsondataarray.append(strvalues)
            
          elif  valuelat != None and valuelng != None:
            strvalues=  {'epoch': key, 'source':valuesource, 'lat': valuelat, 'lng': valuelng}
            jsondataarray.append(strvalues)
            
            #log.info("freeboard  jsondata group   %s",strvalues)


          
        #return jsonify( message=jsondataarray, status='success')
      except:
        #log.info('Telemetrypost: Error in geting Telemetry parameters %s:  ', posttype)
        e = sys.exc_info()[0]
        log.info('get_influxdbcloud_gpsdata: Error in geting gps data parsing %s:  ' % e)
      
        return jsonify( message='Error in inFluxDB_GPS  parsing', status='error')

      
      
      if dataformat == 'csv':
        try:
          #def generate():
          #if overlaykey == "":
          # Just get lat/lng
          # create header row
          strvalue ='TimeStamp, serieskey1: ' + SERIES_KEY1 + ', serieskey2: ' + SERIES_KEY2 +', start: ' + startepoch + ', end: ' + endepoch +  ', resolution: ' + resolution  + ' \r\n'

          # create header row
          if SERIES_KEY2 != "":      
            strvalue = strvalue + 'epoch, time, source, lat, lng, seg distance, speed, delta time, ' + overlayparameter[1] + ' \r\n'
          else:
            strvalue = strvalue + 'epoch, time, source, lat, lng, seg distance, speed, delta time \r\n'

       
          #get all other rows
          #for dataset in data:
          jsondata = jsondataarray

          list_length = len(jsondata)
          for i in range(list_length-1):
            oldvector = (jsondata[i]['lat'], jsondata[i]['lng'])
            oldsource = jsondata[i]['source']
            newvector = (jsondata[i+1]['lat'], jsondata[i+1]['lng'])
            newsource = jsondata[i+1]['source']
            
            if (newsource == oldsource) and (newvector != oldvector):
              oldtime = jsondata[i]['epoch']
              newtime = jsondata[i+1]['epoch']

              deltatime = abs(newtime - oldtime)
              
              delta = vincenty(oldvector, newvector).miles
              if deltatime == 0:
                speed = float(0)
              else:
                speed = float((delta/(float(deltatime)))*60*60)

              mytime = datetime.datetime.fromtimestamp(float(jsondata[i]['epoch'])).strftime('%Y-%m-%d %H:%M:%SZ')
                
              if SERIES_KEY2 == "":                
                strvalue = strvalue + str(jsondata[i]['epoch'])+ ', ' + str(mytime) + ', ' + str(jsondata[i]['source']) + ', ' + str(jsondata[i]['lat']) + ', ' + str(jsondata[i]['lng']) + ', ' + str(delta)+ ', ' + str(speed)+ ', ' + str(deltatime) + ' \r\n'
              else:
                strvalue = strvalue + str(jsondata[i]['epoch'])+ ', ' + str(mytime) + ', ' + str(jsondata[i]['source']) + ', ' + str(jsondata[i]['lat']) + ', ' + str(jsondata[i]['lng']) + ', ' + str(delta)+ ', ' + str(speed)+ ', ' + str(deltatime) + ', ' + str(jsondata[i]['overlay'])+ ' \r\n'

          response = make_response(strvalue)
          response.headers['Content-Type'] = 'text/csv'
          response.headers["Content-Disposition"] = "attachment; filename=HelmSmart.csv"
          return response

        
        except:
          #log.info('Telemetrypost: Error in geting Telemetry parameters %s:  ', posttype)
          e = sys.exc_info()[0]
          log.info('inFluxDB_GPS: Error in geting inFluxDB CSV data %s:  ' % e)
      
          return jsonify( message='Error in inFluxDB_GPS CSV parsing', status='error')

      elif dataformat == 'gpx':
        try:
          #def generate():
          # create header row
          #strvalue ='TimeStamp, serieskey1: ' + SERIES_KEY1 + ', serieskey2: ' + SERIES_KEY2 +', start: ' + startepoch + ', end: ' + endepoch +  ', resolution: ' + resolution  + ' \r\n'
          gpxpoints=[]
          # create header row
          #strvalue = strvalue + 'time, value1, value2, value3, value4 \r\n'
          strvalue = ""
          strvalue = '<?xml version="1.0" encoding="UTF-8"?>' + '\r\n'
          strvalue = strvalue + '<gpx creator="HelmSmart Visualizer http://www.helmsmart.com/" '
          strvalue = strvalue + 'version="1.1" xmlns="http://www.topografix.com/GPX/1/1" '
          strvalue = strvalue + 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
          strvalue = strvalue + 'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">' + '\r\n'
          strvalue = strvalue + '<trk>' + '\r\n'
          strvalue = strvalue + '<name>Track001</name>' + '\r\n'
          strvalue = strvalue + '<trkseg>' + '\r\n'
          #get all other rows
          gpxpoints = jsondataarray


          #Next go through array and calculate the distance and speed vectors.
          list_length = len(gpxpoints)
          for i in range(list_length-1):
            
              oldvector = (gpxpoints[i]['lat'], gpxpoints[i]['lng'])
              newvector = (gpxpoints[i+1]['lat'], gpxpoints[i+1]['lng'])

              if newvector != oldvector:

                oldtime = gpxpoints[i]['epoch']
                newtime = gpxpoints[i+1]['epoch']

                deltatime = abs(newtime - oldtime)
                
                delta = vincenty(oldvector, newvector).miles

                if deltatime == 0:
                  speed = float(0)
     
                else:
                  speed = float((delta/(float(deltatime)))*60*60)

                # if speed vector less then threshold add to GPX file
                if speed < float(maxthreshold)/100:
                  mytime = datetime.datetime.fromtimestamp(float(gpxpoints[i]['epoch'])).strftime('%Y-%m-%dT%H:%M:%SZ')
                  strvalue = strvalue + '<trkpt lat="' + str(gpxpoints[i]['lat']) + '" lon="' + str(gpxpoints[i]['lng']) + '"> \r\n'
                  strvalue = strvalue + '<time>' + str(mytime) + '</time> \r\n'
                  strvalue = strvalue + '</trkpt> \r\n'

          #close out GPX file with footer
          strvalue = strvalue + '</trkseg> \r\n'
          strvalue = strvalue + '</trk> \r\n'
          strvalue = strvalue + '<extensions> \r\n'
          strvalue = strvalue + '</extensions> \r\n'
          strvalue = strvalue + '</gpx> \r\n'
          
          response = make_response(strvalue)
          response.headers['Content-Type'] = 'text/plain'
          response.headers["Content-Disposition"] = "attachment; filename=HelmSmart.gpx"
          return response
        except:
          #log.info('Telemetrypost: Error in geting Telemetry parameters %s:  ', posttype)
          e = sys.exc_info()[0]
          log.info('inFluxDB_GPS: Error in geting inFluxDB GPX data %s:  ' % e)
      
          return jsonify( message='Error in inFluxDB_GPS GPX parsing', status='error')

      elif dataformat == 'jsonf':
        try:
          jsondata=[]
          jsonkey=[]
          strvaluekey = {'Series1': SERIES_KEY1, 'Series2': SERIES_KEY2,'start': startepoch,  'end': endepoch, 'resolution': resolution}
          jsonkey.append(strvaluekey)

          gpsdata=[]
          jsondata=[]
          #for jsondata in jsondataarray:


          jsondata = jsondataarray


          list_length = len(jsondata)
          for i in range(list_length-1):
            oldvector = (jsondata[i]['lat'], jsondata[i]['lng'])
            oldsource = jsondata[i]['source']
            newvector = (jsondata[i+1]['lat'], jsondata[i+1]['lng'])
            newsource = jsondata[i+1]['source']
            
            if (newsource == oldsource) and (newvector != oldvector):
              oldtime = jsondata[i]['epoch']
              newtime = jsondata[i+1]['epoch']

              deltatime = abs(newtime - oldtime)
              
              delta = vincenty(oldvector, newvector).miles
              if deltatime == 0:
                speed = float(0)
              else:
                speed = float((delta/(float(deltatime)))*60*60)

              if SERIES_KEY2 == "":
                gpsjson = {'epoch': jsondata[i]['epoch'], 'source':jsondata[i]['source'], 'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng'], 'distance':delta, 'speed':speed, 'interval':deltatime}
              else:
                gpsjson = {'epoch': jsondata[i]['epoch'],  'source':jsondata[i]['source'],'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng'], 'distance':delta, 'speed':speed, 'overlay': jsondata[i]['overlay']}

              #mininterval
              if deltatime <  float(maxinterval) * 60:
                if speed < float(maxthreshold)/100:
                  gpsdata.append(gpsjson)
          
          print 'inFluxDB_GPS JSONF returning data points:'

          #return jsonify(serieskey = jsonkey, results = jsondata)
          response = make_response(json.dumps(gpsdata))
          response.headers['Content-Type'] = "application/json"
          response.headers["Content-Disposition"] = "attachment; filename=HelmSmart.json"
          return response

        
        except:
          #log.info('Telemetrypost: Error in geting Telemetry parameters %s:  ', posttype)
          e = sys.exc_info()[0]
          log.info('inFluxDB_GPS: Error in geting inFluxDB JSONF data %s:  ' % e)
      
          return jsonify( message='Error in inFluxDB_GPS JSONF parsing', status='error')
        

      
      elif dataformat == 'json':
        try:


         
          gpsdata=[]
          jsondata=[]
          #for jsondata in jsondataarray:


          jsondata = jsondataarray
          #log.info("freeboard  jsondata  %s:  %s",len(jsondata),  jsondata)
          
          list_length = len(jsondata)
          for i in range(list_length-1):
            oldvector = (jsondata[i]['lat'], jsondata[i]['lng'])
            oldsource = jsondata[i]['source']
            newvector = (jsondata[i+1]['lat'], jsondata[i+1]['lng'])
            newsource = jsondata[i+1]['source']
            
            if (newsource == oldsource) and (newvector != oldvector):

              oldtime = jsondata[i]['epoch']
              newtime = jsondata[i+1]['epoch']

              deltatime = abs(newtime - oldtime)
              
              delta = vincenty(oldvector, newvector).miles
              #print 'GetGPSJSON processing dalta points:', delta

              #speed = {'speed':float(delta/(float(deltatime)*60*60))} 
              if deltatime == 0:
                speed = float(0)
   
              else:
                speed = float((delta/(float(deltatime)))*60*60)
              #distance = {'distance':delta}

              if SERIES_KEY2 == "":
                gpsjson = {'epoch': jsondata[i]['epoch'], 'source':jsondata[i]['source'], 'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng'], 'distance':delta, 'speed':speed, 'interval':deltatime}
              else:
                gpsjson = {'epoch': jsondata[i]['epoch'], 'source':jsondata[i]['source'], 'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng'], 'distance':delta, 'speed':speed, 'overlay': jsondata[i]['overlay']}
              
              #if delta < float(maxthreshold)/1000:
              if deltatime <  float(maxinterval) * 60:
                if speed < float(maxthreshold)/100:
                  gpsdata.append(gpsjson)
                
          #except:
          #  e = sys.exc_info()[0]
          #  log.info('inFluxDB_GPS: Error in geting inFluxDB JSON data %s:  ' % e)

          gpsdata = sorted(gpsdata,key=itemgetter('epoch'))
          print 'GetGPSJSON returning data points:'
          log.info('GetGPSJSON: returning JSON data:  ' )

          
          return jsonify(serieskey = jsonkey, results = gpsdata)
        
        except AttributeError, e:
          log.info('inFluxDB_GPS: AttributeError in convert_influxdb_gpsjson %s:  ', data)
          #e = sys.exc_info()[0]

          log.info('inFluxDB_GPS: AttributeError in convert_influxdb_gpsjson %s:  ' % str(e))
          
        except TypeError, e:
          log.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', data)
          #e = sys.exc_info()[0]

          log.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ' % str(e))
          
        except ValueError, e:
          log.info('inFluxDB_GPS: ValueError in convert_influxdb_gpsjson %s:  ', data)
          #e = sys.exc_info()[0]

          log.info('inFluxDB_GPS: ValueError in convert_influxdb_gpsjson %s:  ' % str(e))            
          
        except NameError, e:
          log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', data)
          #e = sys.exc_info()[0]

          log.info('Sync: NameError in convert_influxdb_gpsjson %s:  ' % str(e))          
        except:
          e = sys.exc_info()[0]
          log.info('inFluxDB_GPS: Error in geting inFluxDB JSON data %s:  ' % e)
      
          return jsonify( message='Error in inFluxDB_GPS JSON parsing', status='error')
        
      else:
        result = json.dumps(data.data, cls=DateEncoder)
  
        response = make_response(result) 
    
        response.headers['content-type'] = "application/json"
        return response
  
  except AttributeError, e:
    log.info('inFluxDB_GPS: AttributeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
    #e = sys.exc_info()[0]

    log.info('inFluxDB_GPS: AttributeError in convert_influxdb_gpsjson %s:  ' % str(e))
    
  except TypeError, e:
    log.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
    #e = sys.exc_info()[0]

    log.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ' % str(e))
    
  except ValueError, e:
    log.info('inFluxDB_GPS: ValueError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
    #e = sys.exc_info()[0]

    log.info('inFluxDB_GPS: ValueError in convert_influxdb_gpsjson %s:  ' % str(e))            
    
  except NameError, e:
    log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
    #e = sys.exc_info()[0]

  except IndexError, e:
    log.info('inFluxDB_GPS: IndexError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
    #e = sys.exc_info()[0]


  except:
    e = sys.exc_info()[0]
    log.info('inFluxDB_GPS: Error read_data exception data.points %s:  ' % e)
    return jsonify( message='gps_influxdb read_data exception data.points', status='error')
  

  finally:
    db_pool.putconn(conn)

#@app.route('/devices/<device_id>/PushCache/<partition>', methods=['POST'])
#@cross_origin()
#def events_endpoint(device_id, partition):

@app.route('/freeboard_tcp/<apikey>', methods=['GET','POST'])
@cross_origin()
def freeboard_tcp(apikey):

    deviceapikey =apikey
    Interval = "1min"
     
    #deviceapikey = request.args.get('apikey','')
    #serieskey = request.args.get('datakey','')
    #Interval = request.args.get('Interval',"1min")

    #return jsonify(result="OK")
    
    response = None

    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]


    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })
      return "invalid deviceid"


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='tcp'  "
    #serieskeys= serieskeys +  " (type='True') " 

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



      
    query = ('select  DISTINCT(raw) AS raw  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by *, time({}s) LIMIT 1') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard data Query %s", query)
    #return jsonify(result="OK")

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return 'error - no data'


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return 'error - no data'
      
    #return jsonify(result="OK")
    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    PGNValues=""
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      for series in keys:
        #log.info("influxdb results..%s", series )
        #log.info("influxdb results..%s", series )
        strvalue ={}
 
        #points = list(response.get_points())

        #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

        #name = series['name']
        name = series['tags']            
        #log.info("inFluxDB_GPS_JSON name %s", name )
        seriesname = series['tags'] 
        #seriestags = seriesname.split(".")
        #seriessourcetag = seriestags[2]
        #seriessource = seriessourcetag.split(":")
        source= seriesname['source']
        PGN= seriesname['type']
        parameter = seriesname['parameter']
        #log.info("inFluxDB_GPS_JSON values %s", series['values'] )
        #pgnpoints = series['values']
        for point in  series['values']:
          #pgnpoints = point['raw']
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val
            
        PGNValues= PGNValues + fields['raw'] + '\r\n'        
        """
        for point in  series['values']:
          fields = {}
          fields[parameter] = None
          for key, val in zip(series['columns'], point):
            fields[key] = val
            
          #strvalue = {'epoch': fields['time'], 'tag':seriesname, 'lat': fields['lat'], 'lng': fields['lng']}
          #log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields[parameter])

          mydatetimestr = str(fields['time'])

          #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
          mydatetime =  int(time.mktime(time.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')))
          
          #strvalue = {'epoch': fields['time'], 'source':tag['source'], 'value': fields[parameter]}
          if fields[parameter] != None:
            #strvalues = []
            strvalue = {'epoch': mydatetime, 'tag':seriesname, 'PGN':PGN, 'value': fields[parameter]}
            strvalues = (mydatetime, PGN,  parameter, fields[parameter] )

            
        jsondata.append(strvalues)
        """
        #PGNValues= PGNValues + pgnpoints['raw'] + "\r\n"

        """
        for point in points:
          log.info('freeboard:  InfluxDB-Cloud point%s:', point)
          if point['raw'] is not None: 
            value1 = point['raw']
            

         
          mydatetimestr = str(point['time'])

          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

        log.info('freeboard: freeboard returning data values tcp:%s,   ', value1)            
        """
      #callback = request.args.get('callback')
      #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','raw':value1})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','raw':jsondata})
      #response = make_response(PGNValues)
      #response.headers['Content-Type'] = 'text/txt'
      #return response
      #return jsonify(result="OK", PGNValues='$PCDIN,01F010,69BEO231,06,C6F09D42309D3926*5F\r\n$PCDIN,01F112,69BEO22M,06,EAE2090000390AFD*2A\r\n$PCDIN,01F119,69BEO23E,06,C1FF7FE9FE3BFEFF*25\r\n$PCDIN,01F11A,69BEO23D,06,C1F59D42390AFFFF*53\r\n$PCDIN,01F801,69BEO22K,06,20A80A191C2103B6*20\r\n$PCDIN,01F802,69BEO22L,06,C6FCD8BC0A00FFFF*5C\r\n')
      #return jsonify(result="OK", PGNValues=PGNValues[0:1024])
      return PGNValues[0:3072]
      #return jsonify(results = PGNValues)

    except TypeError, e:
      #log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
      #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
      #log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))          
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })
        return 'error'

  
    #return jsonify(status='error', update=False )
    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })
    return 'error'



@app.route('/freeboard_raw')
@cross_origin()
def freeboard_raw():

    #deviceapikey =apikey
    #Interval = "1min"
     
    devicekey = request.args.get('devicekey', '')
    #deviceid = request.args.get('deviceid', '')
    startepoch = request.args.get('startepoch', 0)
    endepoch = request.args.get('endepoch', 0)

    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")

    
    starttime = 0

    if startepoch == 0:
      epochtimes = getepochtimes(Interval)
      startepoch = epochtimes[0]
      endepoch = epochtimes[1]
      if resolution == "":
        resolution = epochtimes[2]
    
    response = None



    deviceid = getedeviceid(devicekey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })
      return "invalid deviceid"


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    #    database = 'pushsmart-cloud'
    database = 'pushsmart-raw'

    
    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid) + '_raw'




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='tcp'  "
    #serieskeys= serieskeys +  " (type='True') " 

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)



    """      
    query = ('select  DISTINCT(raw) AS raw  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by *, time({}s) LIMIT 1') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
    """     
      
    query = ('select  DISTINCT(raw) AS raw  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s) ') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard data Query %s", query)
    #return jsonify(result="OK")

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))


            
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', response)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        pass

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return 'error - no data'


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return 'error - no data'
      
    #return jsonify(result="OK")
    #log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    #log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    PGNValues=""
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'

      for series in keys:
        #log.info("influxdb results..%s", series )
        #log.info("influxdb results..%s", series )
        strvalue ={}
 
        #points = list(response.get_points())

        #log.info('freeboard:  InfluxDB-Cloud points%s:', points)

        #name = series['name']
        #name = series['tags']            
        #log.info("inFluxDB_GPS_JSON name %s", name )
        #seriesname = series['tags'] 
        #seriestags = seriesname.split(".")
        #seriessourcetag = seriestags[2]
        #seriessource = seriessourcetag.split(":")
        #source= seriesname['source']
        #PGN= seriesname['type']
        #parameter = seriesname['parameter']
        #log.info("inFluxDB_GPS_JSON values %s", series['values'] )
        #pgnpoints = series['values']
        for point in  series['values']:
          #pgnpoints = point['raw']
          fields = {}
          for key, val in zip(series['columns'], point):
            fields[key] = val

          log.info("influxdb results..%s",  fields['raw'] ) 
          PGNValues= PGNValues + fields['raw'] + '\r\n'        
        """
        for point in  series['values']:
          fields = {}
          fields[parameter] = None
          for key, val in zip(series['columns'], point):
            fields[key] = val
            
          #strvalue = {'epoch': fields['time'], 'tag':seriesname, 'lat': fields['lat'], 'lng': fields['lng']}
          #log.info("freeboard Get InfluxDB series points %s , %s", fields['time'], fields[parameter])

          mydatetimestr = str(fields['time'])

          #mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
          mydatetime =  int(time.mktime(time.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')))
          
          #strvalue = {'epoch': fields['time'], 'source':tag['source'], 'value': fields[parameter]}
          if fields[parameter] != None:
            #strvalues = []
            strvalue = {'epoch': mydatetime, 'tag':seriesname, 'PGN':PGN, 'value': fields[parameter]}
            strvalues = (mydatetime, PGN,  parameter, fields[parameter] )

            
        jsondata.append(strvalues)
        """
        #PGNValues= PGNValues + pgnpoints['raw'] + "\r\n"

        """
        for point in points:
          log.info('freeboard:  InfluxDB-Cloud point%s:', point)
          if point['raw'] is not None: 
            value1 = point['raw']
            

         
          mydatetimestr = str(point['time'])

          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

        log.info('freeboard: freeboard returning data values tcp:%s,   ', value1)            
        """
      #callback = request.args.get('callback')
      #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','raw':value1})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','raw':jsondata})
      #response = make_response(PGNValues)
      #response.headers['Content-Type'] = 'text/txt'
      #return response
      #return jsonify(result="OK", PGNValues='$PCDIN,01F010,69BEO231,06,C6F09D42309D3926*5F\r\n$PCDIN,01F112,69BEO22M,06,EAE2090000390AFD*2A\r\n$PCDIN,01F119,69BEO23E,06,C1FF7FE9FE3BFEFF*25\r\n$PCDIN,01F11A,69BEO23D,06,C1F59D42390AFFFF*53\r\n$PCDIN,01F801,69BEO22K,06,20A80A191C2103B6*20\r\n$PCDIN,01F802,69BEO22L,06,C6FCD8BC0A00FFFF*5C\r\n')
      #return jsonify(result="OK", PGNValues=PGNValues[0:1024])
      return PGNValues[0:5072]
      #return jsonify(results = PGNValues)

    except TypeError, e:
      #log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
      #log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
      #log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))          
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        #callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })
        return 'error'

  
    #return jsonify(status='error', update=False )
    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })
    return 'error'


@app.route('/freeboard_chart_test')
@cross_origin()
def freeboard_chart_test():

  values=[]
  
  value = 1.1
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  
  value = 2.3
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  
  value = 3.4
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  
  value = 2.8
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  
  value = 3.8
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  
  value = 1.6
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  
  value = 1.1
  values.append({"thing": "SEASWITCH_ENETG2_A17",
      "created": "2016-11-25T19:56:20.796Z",
      "content": {"amps":1.0, "volts":value}})
  

  #log.info('freeboard: freeboard_chart_test returning data values %s:%s  ', value1, point['volts'])    
  #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
  callback = request.args.get('callback')
  #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
  #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'volts':value1, 'amps':value2, 'power':value3, 'energy':value4})
  #return '{0}({1})'.format(callback, {'values':values})
  #return '{0}({1})'.format(callback, values)
  #return jsonify({  "this": "succeeded", "by": "getting", "the": "dweets","with":values})
  #return jsonify({"values":[{"volt":1},{"volt":2},{"volt":3},{"volt":4},{"volt":5},{"volt":6}]})
  return jsonify({  "values":values})



@app.route('/freeboard_ac_status_array')
@cross_origin()
def freeboard_ac_status_array():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"1hour")
    Instance = request.args.get('instance','0')
    actype = request.args.get('type','GEN')
    mytimezone = request.args.get('timezone',"UTC")

    
    response = None
    
    starttime = 0

    epochtimes = getepochtimes(Interval)
    startepoch = epochtimes[0]
    endepoch = epochtimes[1]
    resolution = epochtimes[2]
    resolution = 60

    deviceid = getedeviceid(deviceapikey)
    
    log.info("freeboard deviceid %s", deviceid)

    if deviceid == "":
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })


    host = 'hilldale-670d9ee3.influxcloud.net' 
    port = 8086
    username = 'helmsmart'
    password = 'Salm0n16'
    database = 'pushsmart-cloud'

    measurement = "HelmSmart"
    measurement = 'HS_' + str(deviceid)




    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    #serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='fluid_level') AND "
    serieskeys= serieskeys +  " (sensor='ac_basic' OR sensor='ac_watthours'  ) "
    serieskeys= serieskeys +  "  AND type = '" + actype + "' AND "
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    query = ('select  mean(ac_line_neutral_volts) AS volts, mean(ac_amps) AS  amps, mean(ac_watts) AS power, mean(ac_kwatthours) AS energy FROM {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution) 
 


    log.info("freeboard data Query %s", query)

    try:
        response= dbc.query(query)
        
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', query)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))

    except UnboundLocalError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))  

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))


    except InfluxDBServerError, e:
      log.info('freeboard_createInfluxDB: Exception Client Error in InfluxDB  %s:  ' % str(e))

      
    except:
        log.info('freeboard: Error in InfluxDB mydata append %s:', query)
        e = sys.exc_info()[0]
        log.info("freeboard: Error: %s" % e)
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    log.info('freeboard:  InfluxDB-Cloud response  %s:', response)

    keys = response.raw.get('series',[])
    #keys = result.keys()
    log.info("freeboard Get InfluxDB series keys %s", keys)


    #callback = request.args.get('callback')
    #return '{0}({1})'.format(callback, {'update':'False', 'status':'success' })
     
    jsondata=[]
    #jsonkey=[]
    #strvaluekey = {'Series': SERIES_KEY, 'start': start,  'end': end, 'resolution': resolution}
    #jsonkey.append(strvaluekey)
    #print 'freeboard start processing data points:'
    
    #log.info("freeboard jsonkey..%s", jsonkey )
    try:
    
      strvalue = ""
      value1 = '---'
      value2 = '---'
      value3 = '---'
      value4 = '---'
      value5 = '---'
      value6 = '---'
      value7 = '---'
      value8 = '---'

      ac_points = []
      volts=[]
      amps=[]
      power=[]
      energy=[]
      
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['time'] is not None:
          mydatetimestr = str(point['time'])
          mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

          mydatetime_utctz = mydatetime.replace(tzinfo=timezone('UTC'))
          mydatetimetz = mydatetime_utctz.astimezone(timezone(mytimezone))

          #dtt = mydatetime.timetuple()       
          dtt = mydatetimetz.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['volts'] is not None:
          value = convertfbunits( point['volts'], 40)
          volts.append({'epoch':ts, 'value':value})
        
        if point['amps'] is not None:
          value = convertfbunits( point['amps'], 40)
          amps.append({'epoch':ts, 'value':value})
        
        if point['power'] is not None:
          value = convertfbunits( point['power'], 40)
          power.append({'epoch':ts, 'value':value})
        
        if point['energy'] is not None:
          value = convertfbunits( point['energy'], 40)
          energy.append({'epoch':ts, 'value':value})






        


        
      #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      #ac_points.append({'epoch':ts, 'date_time':myjsondate, 'update':'True', 'volts':value1, 'amps':value2, 'power':value3, 'energy':value4})
      #ac_points.append({'epoch':ts, 'date_time':myjsondate, 'update':'True', 'volts':value1, 'amps':value2, 'power':value3, 'energy':value4})
        
      #log.info('freeboard: freeboard_engine returning data values %s:%s  ', value1, point['volts'])    
      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      #myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'volts':value1, 'amps':value2, 'power':value3, 'energy':value4})
      #return '{0}({1})'.format(callback, {'ac_points':ac_points})
      return '{0}({1})'.format(callback, {'volts':volts, 'amps':amps, 'power':power, 'energy':energy})
    
    except TypeError, e:
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Type Error in InfluxDB mydata append %s:  ' % str(e))
            
    except KeyError, e:
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Key Error in InfluxDB mydata append %s:  ' % str(e))

    except NameError, e:
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Name Error in InfluxDB mydata append %s:  ' % str(e))
            
    except IndexError, e:
        log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
        log.info('freeboard: Index Error in InfluxDB mydata append %s:  ' % str(e))  

    except ValueError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: Value Error in InfluxDB  %s:  ' % str(e))

    except AttributeError, e:
      #log.info('freeboard: Index error in InfluxDB mydata append %s:  ', response)
      log.info('freeboard_createInfluxDB: AttributeError in InfluxDB  %s:  ' % str(e))     

    except InfluxDBClientError, e:
      log.info('freeboard_createInfluxDB: Exception Error in InfluxDB  %s:  ' % str(e))     
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        #return jsonify(update=False, status='missing' )
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })

  
    #return jsonify(status='error', update=False )
    callback = request.args.get('callback')
    return '{0}({1})'.format(callback, {'update':'False', 'status':'error' })



@app.route('/setswitchapi')
@cross_origin()
def setswitchapi():
  deviceapikey = request.args.get('deviceapikey', '000000000000')
  switchid = request.args.get('switchid', "0")
  switchvalue = request.args.get('switchvalue', "3")
  instance = request.args.get('instance', "0")


  deviceid = getedeviceid(deviceapikey)
    
  log.info("sendswitchapi deviceid %s", deviceid)
  #log.info("sendswitchapi switchpgn %s", switchpgn)
  
  if deviceid == "":
    return jsonify(result="Error", switch=switchpgn)

  # Create an client object
  #cache = IronCache()
  switchitem=""
  """
  try:
    log.info("setswitchapi - IronCache  get key %s", "switch_"+str(instance))
    switchitem = cache.get(cache=deviceid, key="switch_"+str(instance))

  except NameError, e:
      log.info('setswitchapi - IronCache NameError %s:  ' % str(e))

    
  except:
    switchitem = ""
    log.info('setswitchapi - IronCache error  %s:  ', switchitem)
    e = sys.exc_info()[0]
    log.info('setswitchapi - IronCache error %s:  ' % e)
  """

  try:
    switchitem = mc.get(deviceid + '_switch_'+str(instance))

    log.info('setswitchapi - MemCache   deviceid %s payload %s:  ', deviceid, switchitem)

  except NameError, e:
    log.info('setswitchapi - MemCache NameError %s:  ' % str(e))

    
  except:
    switchitem = ""
    log.info('setswitchapi - MemCache error  deviceid %s payload %s:  ', deviceid, switchitem)
    e = sys.exc_info()[0]
    log.info('setswitchapi - MemCache error %s:  ' % e)


  newswitchitem=[]      
  if switchitem != "" and switchitem != "" and switchitem is not None:
    log.info("setswitchapi - IronCache  key exists %s", switchitem.value)
    jsondata = json.loads(switchitem.value)
    for item in jsondata:
      newswitchitem.append(item)
    
  switchpgn = {'instance':instance, 'switchid':switchid, 'switchvalue':switchvalue}
  newswitchitem.append(switchpgn)
  log.info("setswitchapi - IronCache  new key  %s",json.dumps(newswitchitem))

   
  # Put an item
  #cache.put(cache="001EC0B415BF", key="switch", value="$PCDIN,01F20E,00000000,00,0055000000FFFFFF*23")
  #cache.put(cache="001EC0B415BF", key="switch", value=switchpgn )
  #switchpgn = {'instance':instance, 'switchid':switchid, 'switchvalue':switchvalue}
  log.info("Cache put switch key %s", newswitchitem)
  log.info("setswitchapi - Cache  put key %s", "switch_"+str(instance))
  #item=cache.put(cache=deviceid, key="switch_"+str(instance), value=newswitchitem )
  #log.info("IronCache response key %s", item)

  try:
    mc.set(deviceid + "switch_"+str(instance) , newswitchitem, time=600)
    log.info('setswitchapi - MemCache  set deviceid %s payload %s:  ', deviceid, newswitchitem)

  except NameError, e:
    log.info('setswitchapi - MemCache set NameError %s:  ' % str(e))

    
  except:
    newswitchitem = ""
    log.info('setswitchapi - MemCache set error  deviceid %s payload %s:  ', deviceid, newswitchitem)
    e = sys.exc_info()[0]
    log.info('setswitchapi - MemCache set error %s:  ' % e)


  
  return jsonify(result="OK", switch=newswitchitem)

# set the secret key.  keep this really secret:
app.secret_key = 'H0Zr27j/3yX R~CDI!jmN]CDI/,?RT'


