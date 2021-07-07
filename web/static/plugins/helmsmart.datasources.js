// ┌────────────────────────────────────────────────────────────────────┐ \\
// │ F R E E B O A R D                                                  │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Copyright © 2013 Jim Heising (https://github.com/jheising)         │ \\
// │ Copyright © 2013 Bug Labs, Inc. (http://buglabs.net)               │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Licensed under the MIT license.                                    │ \\
// └────────────────────────────────────────────────────────────────────┘ \\

		var sourceoptions = new Array ();
		var sourceoptionsjson = {}
		
		sourceoptionsjson = { "name": "---", "value": "" };
		sourceoptions.push(sourceoptionsjson);
		
		for (i=0; i < 255; i++)
		{
			sourceoptionsjson = { "name":  ('00' + (parseInt(i)).toString(16).toUpperCase()).slice(-2), "value": i };
			sourceoptions.push(sourceoptionsjson);
		}
		
		


(function () {
	var jsonDatasource = function (settings, updateCallback) {
		var self = this;
		var updateTimer = null;
		var currentSettings = settings;
		var errorStage = 0; 	// 0 = try standard request
		// 1 = try JSONP
		// 2 = try thingproxy.freeboard.io
		var lockErrorStage = false;
		var use_thingproxy = true;
		


		function updateRefresh(refreshTime) {
			if (updateTimer) {
				clearInterval(updateTimer);
			}

			updateTimer = setInterval(function () {
				self.updateNow();
			}, refreshTime);
		}

		updateRefresh(currentSettings.refresh * 1000);

		this.updateNow = function () {
			if ((errorStage > 1 && !use_thingproxy) || errorStage > 2) // We've tried everything, let's quit
			{
				return; // TODO: Report an error
			}

			var hsurl = currentSettings.url;
			
			var hsapikey = currentSettings.apikey.split(':');
			
			
			var requestURL = hsurl + "?apikey=" + hsapikey[0];
			
			if ( hsapikey.length == 3)
			{	
				requestURL = requestURL + "&wunstation=" + hsapikey[1];
				
				requestURL = requestURL + "&wunpw=" + hsapikey[2];
			}
			
			
			
			
			var hsinterval =  _.isUndefined(currentSettings.span) ? 600 : currentSettings.span;
			if(hsinterval != "")
				requestURL = requestURL + "&interval=" + hsinterval;
			
			var hsresolution =  _.isUndefined(currentSettings.resolution) ? 60 : currentSettings.resolution;
			if(hsresolution != "")
				requestURL = requestURL + "&resolution=" + hsresolution;	

			
			
			var hsinstance = _.isUndefined(currentSettings.instance) ? 0 : currentSettings.instance;
			if(hsinstance != "")
				requestURL = requestURL + "&instance=" + hsinstance;
			 
			var hssource = _.isUndefined(currentSettings.source) ? 0 : currentSettings.source;
			if(hssource != "")
				requestURL = requestURL + "&source=" + ('00' + (parseInt(hssource)).toString(16).toUpperCase()).slice(-2);	
				//requestURL = requestURL + "&source=" + (hssource).toString.padStart(2, '0');			
			
			var hsindex = _.isUndefined(currentSettings.index) ? 0 : currentSettings.index;
			if(hsindex != "")
				requestURL = requestURL + "&indicator=" + hsindex;			
			
			
			
			var hstype = _.isUndefined(currentSettings.type) ? "" : currentSettings.type;
			if(hstype != "")			
				requestURL = requestURL + "&type=" + hstype;	


	
		

			var hstimezone =  _.isUndefined(currentSettings.timezone) ? 'UTC' : currentSettings.timezone;
			if(hstimezone != "")			
				requestURL = requestURL + "&timezone=" + hstimezone;

			var hsunits =  _.isUndefined(currentSettings.units) ? 'US' : currentSettings.units;
			if(hsunits != "")			
				requestURL = requestURL + "&units=" + hsunits;	

			var hsmode =  _.isUndefined(currentSettings.mode) ? 'median' : currentSettings.mode;
			if(hsmode != "")			
				requestURL = requestURL + "&mode=" + hsmode;				
						
			if (errorStage == 2 && use_thingproxy) {
				requestURL = (location.protocol == "https:" ? "https:" : "http:") + "//thingproxy.freeboard.io/fetch/" + encodeURI(currentSettings.url);
			}

			//var body = currentSettings.body;
			var body = "";
			// Can the body be converted to JSON?
			/*
			if (body) {
				try {
					body = JSON.parse(body);
				}
				catch (e) {
				}
			}
			*/
			$.ajax({
				url: requestURL,
				dataType: (errorStage == 1) ? "JSONP" : "JSON",
				//type: currentSettings.method || "GET",
				type: "GET",
				data: body,
				/*
				beforeSend: function (xhr) {
					try {
						_.each(currentSettings.headers, function (header) {
							var name = header.name;
							var value = header.value;

							if (!_.isUndefined(name) && !_.isUndefined(value)) {
								xhr.setRequestHeader(name, value);
							}
						});
					}
					catch (e) {
					}
				},
				*/
				success: function (data) {
					lockErrorStage = true;
					updateCallback(data);
				},
				error: function (xhr, status, error) {
					if (!lockErrorStage) {
						// TODO: Figure out a way to intercept CORS errors only. The error message for CORS errors seems to be a standard 404.
						errorStage++;
						self.updateNow();
					}
				}
			});
		}

		this.onDispose = function () {
			clearInterval(updateTimer);
			updateTimer = null;
		}

		this.onSettingsChanged = function (newSettings) {
			lockErrorStage = false;
			errorStage = 0;

			currentSettings = newSettings;
			updateRefresh(currentSettings.refresh * 1000);
			self.updateNow();
		}
	};

	freeboard.loadDatasourcePlugin({
		type_name: "JSON",
		display_name: "HelmSmart JSON",
		settings: [

			{
				name: "url",
				display_name: "URL",
				type: "option",
				options: [
					{
						name: "Environmental",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_environmental"
					},
					
					{
						name: "Environmental Calculated",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_environmental_calculated"
					},
					
					
					{ 
						name: "Wind Data",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_winddata"
					},					
					
					
					{
						name: "Weather WUN",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_weather_wung"
					},		
					
					
					{
						name: "GPS Location",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_location"
					},
					
					{
						name: "GPS Location and Wind",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_location_wind"
					},	

					{
						name: "Rain Gauge",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_rain_gauge"
					},	
					
					
					{
						name: "Navigation",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_nav"
					},
					{
						name: "Attitude",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_attitude"
					},
					{
						name: "Engine Status",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_engine"
					},	
					{
						name: "Engine Status Extended",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_engine_aux"
					},	
					{
						name: "Fluid Levels",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_fluidlevels"
					},						
					{
						name: "DC Status",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_battery"
					},					
					
					{
						name: "AC Status",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_ac_status"
					},
					
					{
						name: "Water Depth",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_water_depth"
					},

					{
						name: "Indicator Bank",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_status"
					},
					
					{
						name: "Indicator",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_indicator_status"
					},
					
					{
						name: "Indicator Runtime",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_indicator_runtime"
					},
					
					{
						name: "Dimmer",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_dimmer_status"
					},
					{
						name: "Dimmer Values",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_dimmer_values"
					},
					{
						name: "Switches",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_switch_bank_status"
					},
					{
						name: "Stats",
						value: "https://helmsmart-freeboard.herokuapp.com/get_dbstats_html"
					}

				]
			},	
			
			
			
			{
				name: "apikey",
				display_name: "API KEY",
				type: "text"
			},	
			
			/*
			
					{
				name: "url",
				display_name: "URL",
				type: "text"
			},	
			
			
			{
				name: "use_thingproxy",
				display_name: "Try thingproxy",
				description: 'A direct JSON connection will be tried first, if that fails, a JSONP connection will be tried. If that fails, you can use thingproxy, which can solve many connection problems to APIs. <a href="https://github.com/Freeboard/thingproxy" target="_blank">More information</a>.',
				type: "boolean",
				default_value: true
			},
			*/
			
			
			{
				name: "refresh",
				display_name: "Refresh Every",
				type: "number",
				suffix: "seconds",
				default_value: 5
			},
			
			{
				name: "span",
				display_name: "Span",
				type: "option",
				options: [
					{
						name: "1 min",
						value: "1min"
					},
					{
						name: "2 min",
						value: "2min"
					},
					{
						name: "5 min",
						value: "5min"
					},
					{
						name: "10 min",
						value: "10min"
					},
					{
						name: "15 min",
						value: "15min"
					},
					{
						name: "30 min",
						value: "30min"
					},
					{
						name: "1 hour",
						value: "1hour"
					},
					{
						name: "2 hour",
						value: "2hour"
					},
										{
						name: "3 hour",
						value: "3hour"
					},
										{
						name: "4 hour",
						value: "4hour"
					},
					{
						name: "6 hour",
						value: "6hour"
					},
					{
						name: "8 hour",
						value: "8hour"
					},
					{
						name: "12 hour",
						value: "12hour"
					},
					{
						name: "1 day",
						value: "1day"
					},
					{
						name: "2 day",
						value: "2day"
					},
					{
						name: "1 week",
						value: "7day"
					},
					{
						name: "1 month",
						value: "1month"
					}
				]
			},
			
				{
				name: "resolution",
				display_name: "Resolution",
				type: "option",
				options: [
					{
						name: "---",
						value: ""
					},
					{
						name: "1 min",
						value: "60"
					},
					{
						name: "2 min",
						value: "120"
					},
					{
						name: "5 min",
						value: "300"
					},
					{
						name: "10 min",
						value: "600"
					},
					{
						name: "15 min",
						value: "900"
					},
					{
						name: "30 min",
						value: "1200"
					},
					{
						name: "1 hour",
						value: "3600"
					},
					{
						name: "4 hour",
						value: "14400"
					},
					{
						name: "6 hour",
						value: "21600"
					},
					{
						name: "8 hour",
						value: "28800"
					},
					{
						name: "12 hour",
						value: "43200"
					},
					{
						name: "1 day",
						value: "86400"
					},
					{
						name: "2 day",
						value: "172800"
					},
					{
						name: "1 week",
						value: "604800"
					},
					{
						name: "1 month",
						value: "2419200"
					}
				]
			},
			
						{
				name: "source",
				display_name: "Source",
				type: "option",
				options: sourceoptions,
					
						
			},
			
			{
				name: "instance",
				display_name: "Instance",
				type: "option",
				options: [
					{
						name: "---",
						value: ""
					},
					{
						name: "0",
						value: "0"
					},
					{
						name: "1",
						value: "1"
					},
					{
						name: "2",
						value: "2"
					},					
					{
						name: "3",
						value: "3"
					},					
					{
						name: "4",
						value: "4"
					},					
					{
						name: "5",
						value: "5"
					},					
					{
						name: "6",
						value: "6"
					},					
					{
						name: "7",
						value: "7"
					},					
					{
						name: "8",
						value: "8"
					},					
					{
						name: "9",
						value: "9"
					},
					{
						name: "10",
						value: "10"
					},
					{
						name: "11",
						value: "11"
					},
					{
						name: "12",
						value: "12"
					},					
					{
						name: "13",
						value: "13"
					},					
					{
						name: "14",
						value: "14"
					},					
					{
						name: "15",
						value: "15"
					},					
					{
						name: "16",
						value: "16"
					},					
					{
						name: "17",
						value: "17"
					},					
					{
						name: "18",
						value: "18"
					},					
					{
						name: "19",
						value: "19"
					},
					{
						name: "20",
						value: "20"
					},
					{
						name: "21",
						value: "21"
					},
					{
						name: "22",
						value: "22"
					},					
					{
						name: "23",
						value: "23"
					},
					{
						name: "24",
						value: "24"
					}					
				]
			},
			
			
			
			
			
			
			{
				name: "index",
				display_name: "Value Index",
				type: "option",
				options: [
					{
						name: "---",
						value: ""
					},
					{
						name: "0",
						value: "0"
					},
					{
						name: "1",
						value: "1"
					},
					{
						name: "2",
						value: "2"
					},					
					{
						name: "3",
						value: "3"
					},					
					{
						name: "4",
						value: "4"
					},					
					{
						name: "5",
						value: "5"
					},					
					{
						name: "6",
						value: "6"
					},					
					{
						name: "7",
						value: "7"
					},					
					{
						name: "8",
						value: "8"
					},					
					{
						name: "9",
						value: "9"
					}
				]
			},
			{
				name: "type",
				display_name: "Type",
				type: "option",
				options: [
					{
						name: "---",
						value: ""
					},
					{
						name: "Apparent Direction",
						value: "apparent"
					},
					{
						name: "True Direction",
						value: "true"
					},
					{
						name: "Inside",
						value: "inside"
					},
					{
						name: "Inside Mesh",
						value: "inside mesh"
					},
					
					{
						name: "Outside",
						value: "outside"
					},
					{
						name: "Sea",
						value: "sea"
					},
					{
						name: "UTIL",
						value: "UTIL"
					},	
					{
						name: "UTIL2",
						value: "UTIL2"
					},		

					
					{
						name: "GEN",
						value: "GEN"
					},
					{
						name: "LIGHTS",
						value: "LIGHTS"
					},
										{
						name: "LIGHTS2",
						value: "LIGHTS2"
					},
					
					{
						name: "HEAT",
						value: "HEAT"
					},
					{
						name: "OUTDOOR",
						value: "OUTDOOR"
					},
					{
						name: "APPLIANCE",
						value: "APPLIANCE"
					},
					{
						name: "no GPS",
						value: "no GPS"
					},
					{
						name: "GNSS fix",
						value: "GNSS fix"
					},
					{
						name: "DGNSS fix",
						value: "DGNSS fix"
					},					
					{
						name: "Precise GNSS",
						value: "Precise GNSS"
					},
					{
						name: "LED 4 Channel Hub",
						value: "hub"
					},
					{
						name: "LED 1 Channel Mesh",
						value: "mesh"
					},
					{
						name: "RGB 1 Channel Hub",
						value: "rgbhub"
					},
					{
						name: "NULL",
						value: "NULL"
					}
					
					
					
					
					
					
				]
			},
			
				{
				name: "timezone",
				display_name: "Timezone",
				description: "Timezone for device data ",
				type: "option",
				default_value: "UTC",
				options: [
					{
						name: "UTC",
						value: "UTC"
					},
					{
						name: "Eastern",
						value: "US%2FEastern"
					},
					{
						name: "Central",
						value: "US%2FCentral"
					},
					{
						name: "Mountain",
						value: "US%2FMountain"
					},
					{
						name: "Pacific",
						value: "US%2FPacific"
					},
					{
						name: "Hawaii",
						value: "US%2FHawaii"
					}
				]
			},		
					
			{
				name: "units",
				display_name: "Units",
				description: "Units for temperature, pressure, speed, flow, distance, and volume",
				type: "option",
				default_value: "US",
				options: [
					{
						name: "US",
						value: "US"
					},
					{
						name: "Metric",
						value: "metric"
					},
					{
						name: "Scientific",
						value: "si"
					},
					{
						name: "Nautical",
						value: "nautical"
					}
				]
			},		
					
			{
				name: "mode",
				display_name: "Mode",
				description: "method for averaging between points",
				type: "option",
				default_value: "median",
				options: [
					{
						name: "Mean",
						value: "mean"
					},
					{
						name: "Median",
						value: "median"
					},
					{
						name: "Max",
						value: "max"
					},
					{
						name: "Min",
						value: "min"
					}
					
				]
			}
			/*
			{
				name: "method",
				display_name: "Method",
				type: "option",
				options: [
					{
						name: "GET",
						value: "GET"
					},
					{
						name: "POST",
						value: "POST"
					},
					{
						name: "PUT",
						value: "PUT"
					},
					{
						name: "DELETE",
						value: "DELETE"
					}
				]
			},
			{
				name: "body",
				display_name: "Body",
				type: "text",
				description: "The body of the request. Normally only used if method is POST"
			},
			{
				name: "headers",
				display_name: "Headers",
				type: "array",
				settings: [
					{
						name: "name",
						display_name: "Name",
						type: "text"
					},
					{
						name: "value",
						display_name: "Value",
						type: "text"
					}
				]
			}
			*/
		],
		newInstance: function (settings, newInstanceCallback, updateCallback) {
			newInstanceCallback(new jsonDatasource(settings, updateCallback));
		}
	});





}());
