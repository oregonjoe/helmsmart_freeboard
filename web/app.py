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


