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
import datetime
import time
from time import mktime

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

#Convert Units used for freeboard numerical displays
def convertfbunits(value, units):
            units = int(units)

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


            #case 20: //="20">Liters</option>
            #case 21: //="21">Gallons</option>
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
def index():

    response = make_response(render_template('index.html', features = []))
    #response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response





@app.route('/freeboard_location')
def freeboard_location():

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
         return jsonify(update=False, status='deviceid error' )



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
        return jsonify(status = 'DB Query error', update=False)

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
        return jsonify(date_time=mydatetime, update=True, lat=lat, lng=lng)
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        return jsonify(update=False )




  

    #jasondata = {'datatime':nowtime}

    #log.info('freeboard_io:  keys %s:%s  ', deviceapikey, serieskey)

  
    return jsonify(status='error', update=False )


@app.route('/freeboard_winddata')
def freeboard_winddata():

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
         return jsonify(status="deviceid error", update=False )



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
        return jsonify(update=False )

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

        callback = request.args.get('callback')
        log.info('freeboard: callback %s:  ', callback)  

        
    try:
        log.info('freeboard: freeboard returning data values %s:  ', strvalue)    
        return jsonify(date_time=mydatetime, update=True, truewindspeed=truewindspeed, appwindspeed=appwindspeed, truewinddir=truewinddir, appwinddir=appwinddir)
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        return jsonify( update=False )


  
    return jsonify(update=False)


@app.route('/freeboard_environmental')
def freeboard_environmental():

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
         return jsonify(update=False, status='deviceid error' )



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
        return jsonify(update=False, status='missing' )

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
        return jsonify(date_time=mydatetime, update=True, temperature=value1, baro=value2, humidity=value3)
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        return jsonify(status='error' , update=False)


  
    return jsonify(status='error',  update=False )


@app.route('/freeboard_nav')
def freeboard_nav():

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
         return jsonify(update=False, status='deviceid error' )



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
        return jsonify(update=False, status='missing' )

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
        return jsonify(date_time=mydatetime, update=True, cog=value1, sog=value2, heading_true=value3, heading_mag=value4)
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        return jsonify(status='error' , update=False)


  
    return jsonify(status='error',  update=False )

@app.route('/freeboard_battery')
def freeboard_battery():

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
         return jsonify(update=False, status='deviceid error' )



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
        return jsonify(update=False, status='missing' )

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
        return jsonify(date_time=mydatetime, update=True, voltage=value1, current=value2, temperature=value3)
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        return jsonify(status='error' , update=False)


  
    return jsonify(status='error',  update=False )

@app.route('/freeboard_engine')
def freeboard_engine():

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
         return jsonify(update=False, status='deviceid error' )



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
    SERIES_KEY5 = 'deviceid:' + deviceid + '.sensor:engine_parameters_rapid_update.source:*.instance:' + Instance + '.type:NULL.parameter:boost_pressure.HelmSmart'
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
        return jsonify(date_time=mydatetime, update=False, status='missing', rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)

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
        return jsonify(date_time=mydatetime, update=True, rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
    
    except:
        log.info('freeboard: Error in geting freeboard_engine  %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard_engine  %s:  ' % e)
        #return jsonify(status='error' , update=False)
        mydatetime = datetime.datetime.now()
        return jsonify(date_time=mydatetime, update=False, status='error', rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)


    mydatetime = datetime.datetime.now()
    return jsonify(date_time=mydatetime, update=False, status='error', rpm=value1, eng_temp=value2, oil_pressure=value3, alternator=value4, boost=value5, fuel_rate=value6, fuel_level=value7, eng_hours=value8)
  
    #return jsonify(status='error',  update=False )

@app.route('/freeboard_status')
def freeboard_status():

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
         return jsonify(update=False, status='deviceid error' )



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
        return jsonify(update=False, status='missing' )

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
        return jsonify(date_time=mydatetime, update=True, bank0=value1, status0=status0, status1=status1, status2=status2, status3=status3, status4=status4, status5=status5, status6=status6, status7=status7, status8=status8, status9=status9, status10=status10, status11=status11)
    
    except:
        log.info('freeboard: Error in geting freeboard response %s:  ', strvalue)
        e = sys.exc_info()[0]
        log.info('freeboard: Error in geting freeboard ststs %s:  ' % e)
        return jsonify(status='error' , update=False)


  
    return jsonify(status='error',  update=False )
