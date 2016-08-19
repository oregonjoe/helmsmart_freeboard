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


import urlparse

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
                return float("{0:.2f}".formatvalue )

   
            
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
            #case 21: //="21">Gallons</option>
            #case 22: //="22">CubicMeter</option>
            #case 23: //="23">- - -</option>
            #case 24: //="24">RPM</option>
              
            elif units == 24: #//="24">RPM</option>
                return float("{0:.0f}".format(value *1.0))
            
              
            #case 25: //="25">RPS</option>   
              
            elif units == 26: #//="26">%</option>
                return float("{0:.0f}".format(value *1.0))
            

              
            elif units == 27: #//="27">Volts</option>
                return float("{0:.2f}".format(value *0.10))
            
            # case 26: //="26">%</option>
      
            elif units == 30: #//="30">Meters</option>
                return float("{0:.2f}".format(value * 1.0))
          
            
            elif units == 31: #//="31">Feet</option>
                return float("{0:.2f}".format(value * 3.28084)) 
      
            
            elif units == 32: #//="32">Fathoms</option>
                return float("{0:.2f}".format(value * 0.546806649))
  
            elif units == 37: #//="37">Time</option>
                #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))
                return (datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))

            elif units == 38: #//="38">Date/time</option>
                #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
                return (datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
            
            
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
                return float("{0:.2f}".formatvalue )

   
            
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
                return float("{0:.2f}".format(value *0.10))
            
            # case 26: //="26">%</option>
      
            elif units == 30: #//="30">Meters</option>
                return float("{0:.2f}".format(value * 1.0))
          
            
            elif units == 31: #//="31">Feet</option>
                return float("{0:.2f}".format(value * 3.28084)) 
      
            
            elif units == 32: #//="32">Fathoms</option>
                return float("{0:.2f}".format(value * 0.546806649))
  
            elif units == 37: #//="37">Time</option>
                #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))
                return (datetime.datetime.fromtimestamp(int(value)).strftime('%H:%M:%S'))

            elif units == 38: #//="38">Date/time</option>
                #log.info('HeartBeat time %s:', datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
                return (datetime.datetime.fromtimestamp(int(value)).strftime('%m/%d/%Y %H:%M:%S'))
            
            
            else:
                return float("{0:.2f}".formatvalue)

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

  
    query = "select deviceid from user_devices where deviceapikey = %s"

    try:
    # first check db to see if deviceapikey is matched to device id

        cursor = conn.cursor()
        cursor.execute(query, (deviceapikey,))
        i = cursor.fetchone()
            
        # see we got any matches
        if cursor.rowcount == 0:
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



@app.route('/')
@cross_origin()
def index():

    response = make_response(render_template('index.html', features = []))
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
  serieskey = request.args.get('datakey','')
  Interval = request.args.get('Interval',"1day")
  Instance = request.args.get('instance','0')
  Repeat = int(request.args.get('repeat','1'))
  Sensor = request.args.get('sensor','environmental_data')

  response = None
    
  starttime = 0

  epochtimes = getepochtimes(Interval)
  startepoch = epochtimes[0]
  endepoch = epochtimes[1]
  resolution = epochtimes[2]
  
  resolution = 60*60*24
  qresolution = 60
  resolution = 60*60*24
  endepoch =  int(time.time())
  startepoch = endepoch - (resolution * 1)   

  deviceid = getedeviceid(deviceapikey)
  
  log.info("freeboard deviceid %s", deviceid)

  if deviceid == "":
      #return jsonify(update=False, status='missing' )
      callback = request.args.get('callback')
      return '{0}({1})'.format(callback, {'update':'False', 'status':'deviceid error' })

  
  dchost = 'hilldale-670d9ee3.influxcloud.net' 
  dcport = 8086
  dcusername = 'helmsmart'
  dcpassword = 'Salm0n16'
  dcdatabase = 'pushsmart-cloud'


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

  days = 0

  while (days < Repeat):

    #serieskeys = 'deviceid:' + deviceid + '.sensor:environmental_data.source:*.instance:*.type:*.parameter:*.HelmSmart'
    serieskeys = 'deviceid:' + deviceid + '.sensor:' + Sensor + '.source:*.instance:*.type:*.parameter:*.HelmSmart'
        
    if serieskeys.find("*") > 0:
        serieskeys = serieskeys.replace("*", ".*")

        query = ('select mean(value) from /{}/ '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        qresolution)
    else:
        query = ('select mean(value) from "{}" '
                     'where time > {}s and time < {}s '
                     'group by time({}s)') \
                .format( serieskeys,
                        startepoch, endepoch,
                        qresolution)


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

        myjsonkeys = { 'deviceid':tag0[1], 'sensor':tag1[1], 'source':tag2[1], 'instance':tag3[1], 'type':tag4[1], 'parameter':tag5[1]}
        #log.info('freeboard: convert_influxdbcloud_json tagpairs %s:  ', myjsonkeys)

        #values = {'value':value}
        values = {tag5[1]:float(fields['mean'])}

        ifluxjson ={"measurement":tagpairs[6], "time": ts, "tags":myjsonkeys, "fields": values}
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

    endepoch = startepoch
    startepoch = endepoch - (resolution * 1)   

  return jsonify(count = days,  status='success')

  query = ("select mean(speed) as speed from HelmSmart where deviceid='001EC010AD69' and sensor='engine_parameters_rapid_update' and time > {}s and time < {}s group by time(60s)") \
        .format( startepoch, endepoch)
    

  log.info("freeboard Get InfluxDB query %s", query)

    
  result = dbc.query(query)

  log.info("freeboard Get InfluxDB results %s", result)



  return jsonify(series = keys,  status='success')

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


    
    query = ("select  * from HelmSmart "
           "where deviceid='{}'  AND  time > {}s AND  time < {}s group by * limit 1") \
        .format(deviceid,
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
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })
      

    if not response:
        log.info('freeboard: InfluxDB Query has no data ')
        callback = request.args.get('callback')
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })

    log.info('freeboard:  InfluxDB-Cloud response  %s:', response)
    
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
        if point['temperature'] is not None: 
          value1 = convertfbunits(point['temperature'], 0)
        if point['atmospheric_pressure'] is not None:         
          value2 = convertfbunits(point['atmospheric_pressure'], 10)
        if point['humidity'] is not None:         
          value3 = convertfbunits(point['humidity'], 26)

          
        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      log.info('freeboard: freeboard returning data values temperature:%s, baro:%s, humidity:%s  ', value1,value2,value3)            

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

@app.route('/freeboard_winddata')
@cross_origin()
def freeboard_winddata():

    deviceapikey = request.args.get('apikey','')
    serieskey = request.args.get('datakey','')
    Interval = request.args.get('Interval',"5min")
    windtype = request.args.get('type',"true")

    response = None


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
        return '{0}({1})'.format(callback, {'update':'False', 'status':'missing' })


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
        if point['wind_speed'] is not None:       
          value1 = convertfbunits(point['wind_speed'], 4)
        if point['wind_direction'] is not None:       
          value2 = convertfbunits(point['wind_direction'], 16)

        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', value1,value2)            

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")

      
      if  windtype =="apparent":
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','apparentwindspeed':value1, 'apparentwinddirection':value2,})
      else:
        return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','truewindspeed':value1, 'truewinddir':value2,})
      

     
    
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
        value1 = convertfbunits(point['wind_speed'], 4)
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
            truewindspeed =  convertfbunits(fields['mean'],4)
            strvalue = strvalue + ':' + str(truewindspeed)
            
        elif tag['type'] == 'Apparent Wind' and tag['parameter'] == 'wind_speed':
            appwindspeed =  convertfbunits(fields['mean'], 4)
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
    serieskeys= serieskeys +  " sensor='position_rapid' "
 

    log.info("freeboard Query InfluxDB-Cloud:%s", serieskeys)
    log.info("freeboard Create InfluxDB %s", database)


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
 
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        if point['lat'] is not None:
          if point['lng'] is not None:          
            value1 = convertfbunits(point['lat'], 15)
            value2 = convertfbunits(point['lng'], 15)

        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      log.info('freeboard: freeboard returning data values lat:%s, lng:%s  ', value1,value2)            

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
        

     
    
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
 
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        if point['cog'] is not None: 
          value1 = convertfbunits(point['cog'], 16)
          
        if point['sog'] is not None:         
          value2 = convertfbunits(point['sog'], 4)
          
        if point['heading'] is not None:         
          value3 = convertfbunits(point['heading'], 16)
       
        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      log.info('freeboard: freeboard returning data values wind_speed:%s, wind_direction:%s  ', value1,value2)            

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','cog':value1, 'sog':value2, 'heading_true':value3, 'heading_mag':value4})
        

     
    
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
    Interval = request.args.get('Interval',"5min")
    Instance = request.args.get('instance','0')

    response = None
    
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
 
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        if point['voltage'] is not None: 
          value1 = convertfbunits(point['voltage'], 27)
          
        if point['current'] is not None:         
          value2 = convertfbunits(point['current'], 28)
          
        if point['temperature'] is not None:         
          value3 = convertfbunits(point['temperature'], 0)
       
        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')

      log.info('freeboard: freeboard returning data values voltage:%s, current:%s  ', value1,value2)            

      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")


      #return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','lat':value1, 'lng':value2,})
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True','voltage':value1, 'current':value2, 'temperature':value3})
        

     
    
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
    Interval = request.args.get('Interval',"5min")
    Instance = request.args.get('instance','0')

    response = None
    
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

       
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)
        
        if point['speed'] is not None:
          value1 = convertfbunits( point['speed'], 24)
        
        if point['engine_temp'] is not None:
          value2 =  convertfbunits(point['engine_temp'], 0)
        
        if point['oil_pressure'] is not None:
          value3=  convertfbunits(point['oil_pressure'], 8)
        
        if point['alternator_potential'] is not None:
          value4 =  convertfbunits(point['alternator_potential'], 27)
        
        if point['fuel_rate'] is not None:
          value6 =  convertfbunits(point['fuel_rate'], 18)
        
        if point['level'] is not None:
          value7=  convertfbunits(point['level'], 26)
        
        if point['total_engine_hours'] is not None:
          value8 = convertfbunits(point['total_engine_hours'], 37)

        
        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
        
      log.info('freeboard: freeboard_engine returning data values %s:%s  ', value1, point['speed'])    
      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'rpm':value1, 'eng_temp':value2, 'oil_pressure':value3, 'alternator':value4, 'tripfuel':value5, 'fuel_rate':value6, 'fuel_level':value7, 'eng_hours':value8})

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
    Interval = request.args.get('Interval',"5min")
    Instance = request.args.get('instance','0')

    response = None

    
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
      status12=False
      status13=False
      status14=False
      status15=False
       
      points = list(response.get_points())

      log.info('freeboard:  InfluxDB-Cloud points%s:', points)

      for point in points:
        log.info('freeboard:  InfluxDB-Cloud point%s:', point)

        if point['bank0'] is not None:
          value1 =  point['bank0']

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


        if point['bank1'] is not None:
          value2 =  point['bank1']
            
          if value2 != '---':
            if value2 & 0x1 == 0x01:
              status8 = True

            if value2 & 0x2 == 0x02:
              status9 = True

            if value2 & 0x4 == 0x04:
              status10 = True

            if value2 & 0x8 == 0x08:
              status11 = True

            if value2 & 0x10 == 0x10:
              status12 = True

            if value2 & 0x20 == 0x20:
              status13 = True

            if value2 & 0x40 == 0x40:
              status14 = True

            if value2 & 0x80 == 0x80:
              status15 = True           
 

        
        mydatetimestr = str(point['time'])

        mydatetime = datetime.datetime.strptime(mydatetimestr, '%Y-%m-%dT%H:%M:%SZ')
        
      log.info('freeboard: freeboard_engine returning data values %s:%s  ', value1, point['bank0'])    
      #return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
      callback = request.args.get('callback')
      myjsondate = mydatetime.strftime("%B %d, %Y %H:%M:%S")
      return '{0}({1})'.format(callback, {'date_time':myjsondate, 'update':'True', 'bank0':value1, 'status0':status0, 'status1':status1, 'status2':status2, 'status3':status3, 'status4':status4, 'status5':status5, 'status6':status6, 'status7':status7, 'status8':status8, 'status9':status9, 'status10':status10, 'status11':status11, 'status12':status12, 'status13':status13, 'status14':status14, 'status15':status15})

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



@app.route('/get_influxdbcloud_data')
@cross_origin()
def get_influxdbcloud_data():
  conn = db_pool.getconn()



  pgnnumber = request.args.get('pgnnumber', '000000')
  userid = request.args.get('userid', '4d231fb3a164c5eeb1a8634d34c578eb')
  deviceid = request.args.get('deviceid', '000000000000')
  startepoch = request.args.get('startepoch', 0)
  endepoch = request.args.get('endepoch', 0)
  resolution = request.args.get('resolution', 60)
  SERIES_KEY = request.args.get('serieskey', 0)

  response = None
  
  measurement = "HelmSmart"

    
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


      
      gpskey =SERIES_KEY1

      overlaykey =SERIES_KEY2

      if SERIES_KEY1.find(".*.") > 0:  
        SERIES_KEY1 = SERIES_KEY1.replace(".*.","*.")


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

      

      if overlaykey == "":
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
        if gpskey.find("*") > 0 or overlaykey.find("*") > 0:
          gpskey = gpskey.replace("*", ".*")
          overlaykey = overlaykey.replace("*", ".*")
          
          query = ('select median("{}.valuelat") as lat, median("{}.valuelng") as lng, {}("{}.value") as overlay from /{}/ inner join /{}/ '
                       'where time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format(gpskey,  gpskey, rollup, overlaykey,  gpskey, overlaykey,
                          startepoch, endepoch,
                          resolution)
        else:
          
          query = ('select median("{}.valuelat") as lat, median("{}.valuelng") as lng, {}("{}.value") as overlay from "{}" inner join "{}" '
                       'where time > {}s and time < {}s '
                       'group by time({}s)') \
                  .format( gpskey,  gpskey, rollup, overlaykey,  gpskey, overlaykey,
                          startepoch, endepoch,
                          resolution)
   
        log.info("inFlux gps: Overlay Query %s", query)

        

      try:
        data= db.query(query)
        
      except TypeError, e:
        log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ', data)
        log.info('get_influxdbcloud_data: Type Error in InfluxDB mydata append %s:  ' % str(e))
              
      except KeyError, e:
        log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ', data)
        log.info('get_influxdbcloud_data: Key Error in InfluxDB mydata append %s:  ' % str(e))

      except NameError, e:
        log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ', data)
        log.info('get_influxdbcloud_data: Name Error in InfluxDB mydata append %s:  ' % str(e))
              
      except IndexError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', data)
        log.info('get_influxdbcloud_data: Index Error in InfluxDB mydata append %s:  ' % str(e))  

      except ValueError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', data)
        log.info('get_influxdbcloud_data: Value Error in InfluxDB  %s:  ' % str(e))

      except AttributeError, e:
        log.info('get_influxdbcloud_data: Index error in InfluxDB mydata append %s:  ', data)
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
      
      if dataformat == 'csv':
        try:
          #def generate():
          #if overlaykey == "":
          # Just get lat/lng
          # create header row
          strvalue ='TimeStamp, serieskey1: ' + SERIES_KEY1 + ', serieskey2: ' + SERIES_KEY2 +', start: ' + startepoch + ', end: ' + endepoch +  ', resolution: ' + resolution  + ' \r\n'

          # create header row
          strvalue = strvalue + 'epoch, time, lat, lng \r\n'
       
          #get all other rows
          #for dataset in data:
          """
          for point in data.points:
                
              #strvalue = str(point.t) + "," + str(point.get(SERIES_KEY1))+ "," + str(point.get(SERIES_KEY2)) + "," + str(point.get(SERIES_KEY3)) + "," + str(point.get(SERIES_KEY4))  
              #yield strvalue + '\r\n'
              strvalue = strvalue + str(point.t) + "," + str(point.get(SERIES_KEY1))+ "," + str(point.get(SERIES_KEY2)) + "," + str(point.get(SERIES_KEY3)) + "," + str(point.get(SERIES_KEY4))   + '\r\n'
              #yield strvalue + '\r\n'

          """
          
          for series in data:
            #log.info("influxdb results..%s", series )
            for point in series['points']:
              fields = {}
              for key, val in zip(series['columns'], point):
                fields[key] = val
                
              mytime = datetime.datetime.fromtimestamp(float(fields['time'])).strftime('%Y-%m-%d %H:%M:%SZ')  
              strvalue = strvalue + str(fields['time'])+ ', ' + str(mytime) + ', ' + str(fields['lat']) + ', ' + str(fields['lng']) + ' \r\n'


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
          #for dataset in data:
          #for point in data.points:
          #First get all the points and put into a JSON array
          for series in data:
            #log.info("influxdb results..%s", series )
            for point in series['points']:
              fields = {}
              for key, val in zip(series['columns'], point):
                fields[key] = val

              #mytime = datetime.datetime.fromtimestamp(float(fields['time'])).strftime('%Y-%m-%dT%H:%M:%SZ')

              #gpxpoints.append({'epoch': jsondata[i]['epoch'], 'source':jsondata[i]['source'], 'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng']})
              gpxpoints.append({'epoch': float(fields['time']), 'lat': float(fields['lat']), 'lng': float(fields['lng'])})

          #Now sort array based on time
          gpxpoints = sorted(gpxpoints,key=itemgetter('epoch'))

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

          if overlaykey == "":
          # Just get lat/lng
            for series in data:
              #log.info("influxdb results..%s", series )
              for point in series['points']:
                fields = {}
                for key, val in zip(series['columns'], point):
                  fields[key] = val
                strvalue = {'epoch': fields['time'], 'lat': fields['lat'], 'lng': fields['lng']}
                print 'inFluxDB processing data points:', strvalue
                
                jsondata.append(strvalue)
                
          else:
          # Get lat/lng and overlay
            for series in data:
              #log.info("influxdb results..%s", series )
              for point in series['points']:
                fields = {}
                for key, val in zip(series['columns'], point):
                  fields[key] = val

                strvalue = {'epoch': fields['time'], 'lat': fields['lat'], 'lng': fields['lng'], 'overlay': fields['overlay']}
                print 'inFluxDB processing data points:', strvalue
                
                jsondata.append(strvalue)

                
          jsondata = sorted(jsondata,key=itemgetter('epoch'))

          gpsdata=[]
          list_length = len(jsondata)
          for i in range(list_length-1):
            oldvector = (jsondata[i]['lat'], jsondata[i]['lng'])
            newvector = (jsondata[i+1]['lat'], jsondata[i+1]['lng'])

            oldtime = jsondata[i]['epoch']
            newtime = jsondata[i+1]['epoch']

            deltatime = abs(newtime - oldtime)
            
            delta = vincenty(oldvector, newvector).miles
            if deltatime == 0:
              speed = float(0)
            else:
              speed = float((delta/(float(deltatime)))*60*60)

            if overlaykey == "":
              gpsjson = {'epoch': jsondata[i]['epoch'], 'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng'], 'distance':delta, 'speed':speed, 'interval':deltatime}
            else:
              gpsjson = {'epoch': jsondata[i]['epoch'], 'lat':jsondata[i]['lat'], 'lng': jsondata[i]['lng'], 'distance':delta, 'speed':speed, 'overlay': jsondata[i]['overlay']}

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
          jsondata=[]
          jsonkey=[]
          strvaluekey = {'Series1': SERIES_KEY1, 'Series2': SERIES_KEY2,'start': startepoch,  'end': endepoch, 'resolution': resolution}
          jsonkey.append(strvaluekey)
          jsondataarray=[]

          if overlaykey == "":
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

            # group lat and lng values based on epoch times and get rid of repeated epoch times
            for key, latlnggroup in groupby(jsondata, lambda x: x[0]):

              valuelat = None
              valuelng = None
              
              for latlng_values in latlnggroup:
                if latlng_values[2] == 'lat':
                  valuelat = latlng_values[3]
                  
                if latlng_values[2] == 'lng':
                  valuelng = latlng_values[3]
                  
                valuesource = latlng_values[1]
                
              #strvalues=  {'epoch': key, 'source':thing[1], 'value': thing[3]}

              # if we have valid lat and lng - make a json array
              if  valuelat != None and valuelng != None:
                strvalues=  {'epoch': key, 'source':valuesource, 'lat': valuelat, 'lng': valuelng}
                #log.info("freeboard  jsondata group   %s",strvalues)
                jsondataarray.append(strvalues)

              
            return jsonify( message=jsondataarray, status='success')

            
            series_lat_value = None
            series_lng_value = None
            
            for seriesvalues in jsondata:
              series_tag = seriesvalues['tag']
              series_epoch=seriesvalues['epoch']

              if series_tag['parameter'] == 'lat':
                  if seriesvalues['value'] != None:                     
                      series_lat_value = seriesvalues['value']

              if series_tag['parameter'] == 'lng':
                  if seriesvalues['value'] != None:                     
                      series_lng_value = seriesvalues['value']

                        
              log.info('inFluxDB_GPS_JSON latlng tag = %s:%s', series_lat_value, series_lng_value)
              
              if series_lat_value != None and series_lng_value != None:
                #distance = process_gpsdistance( "series_1", parameters,  series_lat_value, series_lng_value)
                strvalue = {'epoch':series_epoch, 'source':series_tag['source'], 'lat': series_lat_value, 'lng': series_lng_value}

                
              jsondataarray.append(strvalue)
            
            return jsonify( message=jsondataarray, status='success')
          
          else:
          # Get lat/lng and overlay
            for series in data:
              #log.info("influxdb results..%s", series )
              jsondata=[]
              name = series['name']
              log.info("inFluxDB_GPS_JSON name %s", name )
              seriesname = series['name']
              seriestags = seriesname.split(".")
              seriessourcetag = seriestags[2]
              seriessource = seriessourcetag.split(":")
              source= seriessource[1]
              log.info("inFluxDB_GPS_JSON source %s", source )
              
              for point in series['points']:
                fields = {}
                for key, val in zip(series['columns'], point):
                  fields[key] = val
                strvalue = {'epoch': fields['time'],  'source':source, 'lat': fields['lat'], 'lng': fields['lng'], 'overlay': fields['overlay']}
                #print 'GetGPSJSON processing data points with overlay:', strvalue
                
                jsondata.append(strvalue)

              jsondataarray.append(jsondata)

          gpsdata=[]
          jsondata=[]
          for jsondata in jsondataarray:
          #try:
            #jsondata = jsondataarray[0]
              
            jsondata = sorted(jsondata,key=itemgetter('epoch'))
            print 'inFluxDB returning data points:'



            list_length = len(jsondata)
            for i in range(list_length-1):
              oldvector = (jsondata[i]['lat'], jsondata[i]['lng'])
              newvector = (jsondata[i+1]['lat'], jsondata[i+1]['lng'])

              if newvector != oldvector:

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

                if overlaykey == "":
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




