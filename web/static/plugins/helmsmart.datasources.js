// ┌────────────────────────────────────────────────────────────────────┐ \\
// │ F R E E B O A R D                                                  │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Copyright © 2013 Jim Heising (https://github.com/jheising)         │ \\
// │ Copyright © 2013 Bug Labs, Inc. (http://buglabs.net)               │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Licensed under the MIT license.                                    │ \\
// └────────────────────────────────────────────────────────────────────┘ \\

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
			var hsapikey = currentSettings.apikey;
			var hsinterval = currentSettings.span;
			var hsresolution = currentSettings.resolution;

			var hsinstance = currentSettings.instance;
			var hstype = currentSettings.type;
			if(hstype == "")			
				var requestURL= hsurl + "?apikey=" + hsapikey + "&interval=" + hsinterval + "&resolution=" + hsresolution + "&instance=" + hsinterval ;
			else
				var requestURL= hsurl + "?apikey=" + hsapikey + "&interval=" + hsinterval + "&resolution=" + hsresolution + "&instance=" + hsinterval + "&type=" + hstype;
						
						
						
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
						name: "Wind Data",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_environmental"
					},					
					
					{
						name: "AC Status",
						value: "https://helmsmart-freeboard.herokuapp.com/freeboard_ac_status"
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
				name: "instance",
				display_name: "Instance",
				type: "option",
				options: [
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
						name: "UTIL",
						value: "UTIL"
					},					
					{
						name: "GEN",
						value: "GEN"
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
