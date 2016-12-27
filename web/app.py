import os
import sys
import json
#import csv
import requests
from requests.exceptions import HTTPError
#import nmea
import urlparse
import urllib
import md5
import base64
from operator import itemgetter
import numpy as np
from geopy.distance import vincenty
import datetime
import time
from time import mktime
#from datetime import datetime
from itertools import groupby
import pyonep
from pyonep import onep
import urlparse
from iron_cache import *
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



#import db

def connection_from(url):
  config = urlparse.urlparse(url)
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
  

@app.route('/')
@cross_origin()
def index():

    response = make_response(render_template('index.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response
  
@app.route('/freeboard')
@cross_origin()
def freeboard():

    response = make_response(render_template('freeboard.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
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
    #Interval = request.args.get('interval',"1hour")
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")

    
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

        query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  mean(temperature) AS temperature, mean(atmospheric_pressure) AS  atmospheric_pressure, mean(humidity) AS humidity from {} '
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
      humidity=[]

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
          dtt = mydatetime.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['temperature'] is not None: 
          value1 = convertfbunits(point['temperature'],  convertunittype('temperature', units))
        temperature.append({'epoch':ts, 'value':value1})
          
        if point['atmospheric_pressure'] is not None:         
          value2 = convertfbunits(point['atmospheric_pressure'], 10)
        atmospheric_pressure.append({'epoch':ts, 'value':value2})
                    
        if point['humidity'] is not None:         
          value3 = convertfbunits(point['humidity'], 26)
        humidity.append({'epoch':ts, 'value':value3})

          
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")        
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':value1, 'baro':value2, 'humidity':value3})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','temperature':list(reversed(temperature)), 'atmospheric_pressure':list(reversed(atmospheric_pressure)), 'humidity':list(reversed(humidity))})     

    except AttributeError, e:
      #log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: AttributeError in freeboard_environmental %s:  ' % str(e))
      
    except TypeError, e:
      l#og.info('inFluxDB_GPS: TypeError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: TypeError in freeboard_environmental %s:  ' % str(e))
      
    except ValueError, e:
      #log.info('inFluxDB_GPS: ValueError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]

      log.info('inFluxDB_GPS: ValueError in freeboard_environmental %s:  ' % str(e))            
      
    except NameError, e:
      #log.info('inFluxDB_GPS: NameError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('inFluxDB_GPS: ValueError in freeboard_environmental %s:  ' % str(e))           

    except IndexError, e:
      #log.info('inFluxDB_GPS: IndexError in convert_influxdb_gpsjson %s:  ', SERIES_KEY1)
      #e = sys.exc_info()[0]
      log.info('inFluxDB_GPS: ValueError in freeboard_environmental %s:  ' % str(e))
      
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

@app.route('/freeboard_winddata')
@cross_origin()
def freeboard_winddata():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    resolution = request.args.get('resolution',"")
    windtype = request.args.get('type',"true")
    units= request.args.get('units',"US")

    
    response = None


    wind_speed=[]
    wind_direction=[]
    
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
      serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND type='Apparent Wind' "
    else  :
      serieskeys=" deviceid='"
      serieskeys= serieskeys + deviceid + "' AND "
      serieskeys= serieskeys +  " sensor='wind_data' AND instance='0' AND type='TWIND True North' "
  
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
          dtt = mydatetime.timetuple()
          ts = int(mktime(dtt)*1000)

        if point['wind_speed'] is not None:       
          value1 = convertfbunits(point['wind_speed'],  convertunittype('speed', units))
        wind_speed.append({'epoch':ts, 'value':value1})
          
        if point['wind_direction'] is not None:       
          value2 = convertfbunits(point['wind_direction'], 16)
        wind_direction.append({'epoch':ts, 'value':value2})
       

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

      
      if  windtype =="apparent":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','apparentwindspeed':list(reversed(wind_speed)), 'apparentwinddirection':list(reversed(wind_direction))})
      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'status':'success','truewindspeed':list(reversed(wind_speed)), 'truewinddir':list(reversed(wind_direction))})
   

      

     
    
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
    response = None
    log.info("freeboard_location deviceapikey %s", deviceapikey)
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
    #serieskeys={'deviceid'=deviceid, 'sensor'='environmental_data', 'instance'='0', 'type'='Outside_Temperature'}

    serieskeys=" deviceid='"
    serieskeys= serieskeys + deviceid + "' AND "
    serieskeys= serieskeys +  " sensor='position_rapid' "
 

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    #log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


      

    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select  mean(lat) AS lat, mean(lng) AS  lng  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      query = ('select  mean(lat) AS lat, mean(lng) AS  lng  from {} '
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
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

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
          dtt = mydatetime.timetuple()
          ts = int(mktime(dtt)*1000)

        
        if point['lat'] is not None:
          if point['lng'] is not None:          
            value1 = convertfbunits(point['lat'], 15)
            lat.append({'epoch':ts, 'value':value1})
            
            value2 = convertfbunits(point['lng'], 15)
            lng.append({'epoch':ts, 'value':value2})

            position.append({'epoch':ts, 'lat':value1, 'lng':value2})
 
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':list(reversed(lat)), 'lng':list(reversed(lng)), 'position':list(reversed(position))})     
        

     
    
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

      query = ('select  mean(course_over_ground) AS cog, mean(speed_over_ground) AS  sog, mean(heading) AS heading  from {} '
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
          dtt = mydatetime.timetuple()
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


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
    serieskeys= serieskeys +  " (sensor='water_depth' )  "



    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)


    if serieskeys.find("*") > 0:
      serieskeys = serieskeys.replace("*", ".*")

      
      #query = ('select  mean(depth) AS depth, mean(waterspeed) AS  waterspeed, mean(groundspeed) AS groundspeed, mean(groundspeed) AS groundspeed  from {} '
      query = ('select  mean(depth) AS depth  from {} '
                     'where {} AND time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( measurement, serieskeys,
                        startepoch, endepoch,
                        resolution)
    else:
      
      #query = ('select  mean(course_over_ground) AS cog, mean(speed_over_ground) AS  sog, mean(heading) AS heading  from {} '
      query = ('select  mean(depth) AS depth  from {} '            
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
      speed=[]
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
          dtt = mydatetime.timetuple()
          ts = int(mktime(dtt)*1000)

        
        if point['depth'] is not None: 
          value1 = convertfbunits(point['depth'], 32)
        depth.append({'epoch':ts, 'value':value1})
        csvout = csvout + str(ts) + ', '+ str(value1)  + '\r\n'
        """          
        if point['speed'] is not None:         
          value2 = convertfbunits(point['speed'], convertunittype('speed', units))
        speed.append({'epoch':ts, 'value':value2})
          
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


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





@app.route('/freeboard_battery')
@cross_origin()
def freeboard_battery():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    units= request.args.get('units',"US")
    
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

      
    query = ('select  mean(voltage) AS voltage, mean(current) AS  current, mean(temperature) AS temperature  from {} '
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
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing', 'update':'False', 'voltage':list(reversed(voltage)), 'current':list(reversed(current)), 'temperature':list(reversed(temperature))})     


    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        #return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
        return '{0}({1})'.format(callback, {'date_time':myjsondate,  'status':'missing', 'update':'False', 'voltage':list(reversed(voltage)), 'current':list(reversed(current)), 'temperature':list(reversed(temperature))})     

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
      
      voltage=[]
      current=[]
      temperature=[]

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
          dtt = mydatetime.timetuple()
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
               

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':value1, 'current':value2, 'temperature':value3})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':list(reversed(voltage)), 'current':list(reversed(current)), 'temperature':list(reversed(temperature))})     
        

     
    
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


    boost_presure=[]
    coolant_pressure=[]
    fuel_pressure=[]
    oil_temp=[]
    egt_temperature=[]
    fuel_rate_average=[]
    instantaneous_fuel_economy=[]
    tilt_or_trim=[]

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
    serieskeys= serieskeys +  " (sensor='engine_parameters_rapid_update' OR sensor='engine_parameters_dynamic'  OR  sensor='temperature'  OR  sensor='trip_parameters_engine') AND "
    if Instance == 1:
      serieskeys= serieskeys +  " (type='NULL' OR type='Reserved 134')  AND "
    else:
      serieskeys= serieskeys +  " (type='NULL' OR type='Reserved 135')  AND "
      
    serieskeys= serieskeys +  " (instance='" + Instance + "') "





    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


    dbc = InfluxDBCloud(host, port, username, password, database,  ssl=True)

      
    query = ('select  mean(tilt_or_trim) AS tilt_or_trim, mean(boost_presure) AS  boost_presure, mean(coolant_pressure) AS coolant_pressure, mean(fuel_pressure) AS fuel_pressure, mean(oil_temp) AS oil_temp ,  mean(actual_temperature) AS egt_temperature , mean(fuel_rate_average) AS fuel_rate_average  , mean(instantaneous_fuel_economy) AS instantaneous_fuel_economy from {} '
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
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','boost_presure':list(reversed(boost_presure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)), 'tilt_or_trim':list(reversed(tilt_or_trim))})     

    if response is None:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','boost_presure':list(reversed(boost_presure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)), 'tilt_or_trim':list(reversed(tilt_or_trim))})     

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'missing','update':'False','boost_presure':list(reversed(boost_presure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)), 'tilt_or_trim':list(reversed(tilt_or_trim))})     

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


      boost_presure=[]
      coolant_pressure=[]
      fuel_pressure=[]
      oil_temp=[]
      egt_temperature=[]
      fuel_rate_average=[]
      instantaneous_fuel_economy=[]
      tilt_or_trim=[]

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
          dtt = mydatetime.timetuple()
          ts = int(mktime(dtt)*1000)
          
        if point['boost_presure'] is not None:
          value1 = convertfbunits( point['boost_presure'], convertunittype('pressure', units))
          boost_presure.append({'epoch':ts, 'value':value1})
          
        
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
        egt_temperature.append({'epoch':ts, 'value':value6})
          
       
        if point['fuel_rate_average'] is not None:
          value6=  convertfbunits(point['fuel_rate_average'], convertunittype('flow', units))
        fuel_rate_average.append({'epoch':ts, 'value':value7})
          
        
        if point['instantaneous_fuel_economy'] is not None:
          value7 = convertfbunits(point['instantaneous_fuel_economy'],convertunittype('flow', units))
        instantaneous_fuel_economy.append({'epoch':ts, 'value':value8})

          
        
        if point['tilt_or_trim'] is not None:
          value8 = convertfbunits(point['tilt_or_trim'], convertunittype('%', units))
        tilt_or_trim.append({'epoch':ts, 'value':value8})
          
          

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','rpm':list(reversed(speed)), 'eng_temp':list(reversed(engine_temp)), 'oil_pressure':list(reversed(oil_pressure)),'alternator':list(reversed(alternator_potential)), 'tripfuel':list(reversed(tripfuel)), 'fuel_rate':list(reversed(fuel_rate)), 'fuel_level':list(reversed(level)), 'eng_hours':list(reversed(total_engine_hours))})     
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'status':'success','update':'True','boost_presure':list(reversed(boost_presure)), 'coolant_pressure':list(reversed(coolant_pressure)), 'fuel_pressure':list(reversed(fuel_pressure)),'oil_temp':list(reversed(oil_temp)), 'egt_temperature':list(reversed(egt_temperature)), 'fuel_rate_average':list(reversed(fuel_rate_average)), 'instantaneous_fuel_economy':list(reversed(instantaneous_fuel_economy)), 'tilt_or_trim':list(reversed(tilt_or_trim))})     



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
          dtt = mydatetime.timetuple()
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
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



@app.route('/freeboard_ac_status')
@cross_origin()
def freeboard_ac_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
    actype = request.args.get('type','GEN')
    
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
          dtt = mydatetime.timetuple()
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
          
        

      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'volts':value1, 'amps':value2, 'power':value3, 'energy':value4})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','volts':list(reversed(volts)), 'amps':list(reversed(amps)), 'power':list(reversed(power)), 'energy':list(reversed(energy)), 'energy_interval':list(reversed(energy_caluculated))})     

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
          dtt = mydatetime.timetuple()
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
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




@app.route('/freeboard_switch_bank_status')
@cross_origin()
def freeboard_switch_bank_status():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('interval',"5min")
    Instance = request.args.get('instance','0')
    resolution = request.args.get('resolution',"")
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
          dtt = mydatetime.timetuple()
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
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
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


  Interval = request.args.get('Interval',"5min")
  rollup = request.args.get('rollup',"sum")

  response = None

  
  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]



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


  Interval = request.args.get('Interval',"5min")
  rollup = request.args.get('rollup',"sum")

  response = None

  
  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]



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
    stathtml = "<table>"


    for stat in jsondata:
      if stat['value'] != None:
        total = total + float(stat['value'])

    if len(jsondata) > 0:
      mydatetimestr = str(jsondata[0]['epoch'])

    for statdata in jsondata:
      stathtml = stathtml + "<tr> <td>" +  str(statdata['source']) + "</td><td>" + str(statdata['name']) + " </td><td>" +  str(statdata['value']) + "</td></tr>"

    stathtml = stathtml + "</table>"

    mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

    #log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', stat1,stat2)            

    callback = request.args.get('callback')
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
          dtt = mydatetime.timetuple()
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
  cache = IronCache()
  switchitem=""
  
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

  newswitchitem=[]      
  if switchitem != "":
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
  log.info("IronCache put switch key %s", newswitchitem)
  log.info("setswitchapi - IronCache  put key %s", "switch_"+str(instance))
  item=cache.put(cache=deviceid, key="switch_"+str(instance), value=newswitchitem )
  #item=cache.put(cache=deviceid, key="switch", value=switchpgn )
  log.info("IronCache response key %s", item)
  return jsonify(result="OK", switch=newswitchitem)


