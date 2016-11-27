// ┌────────────────────────────────────────────────────────────────────┐ \\
// │ F R E E B O A R D                                                  │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Copyright © 2013 Jim Heising (https://github.com/jheising)         │ \\
// │ Copyright © 2013 Bug Labs, Inc. (http://buglabs.net)               │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Licensed under the MIT license.                                    │ \\
// └────────────────────────────────────────────────────────────────────┘ \\

(function () {
	var SPARKLINE_HISTORY_LENGTH = 100;
	var SPARKLINE_COLORS = ["#FF9900", "#FFFFFF", "#B3B4B4", "#6B6B6B", "#28DE28", "#13F7F9", "#E6EE18", "#C41204", "#CA3CB8", "#0B1CFB"];

    function easeTransitionText(newValue, textElement, duration) {

		var currentValue = $(textElement).text();

        if (currentValue == newValue)
            return;

        if ($.isNumeric(newValue) && $.isNumeric(currentValue)) {
            var numParts = newValue.toString().split('.');
            var endingPrecision = 0;

            if (numParts.length > 1) {
                endingPrecision = numParts[1].length;
            }

            numParts = currentValue.toString().split('.');
            var startingPrecision = 0;

            if (numParts.length > 1) {
                startingPrecision = numParts[1].length;
            }

            jQuery({transitionValue: Number(currentValue), precisionValue: startingPrecision}).animate({transitionValue: Number(newValue), precisionValue: endingPrecision}, {
                duration: duration,
                step: function () {
                    $(textElement).text(this.transitionValue.toFixed(this.precisionValue));
                },
                done: function () {
                    $(textElement).text(newValue);
                }
            });
        }
        else {
            $(textElement).text(newValue);
        }
    }


    freeboard.addStyle('.gm-style-cc a', "text-shadow:none;");

    var googleMapWidget = function (settings) {
        var self = this;
        var currentSettings = settings;
        var map;
        var marker;
        var currentPosition = {};
		var myLatlng;
		var myOldLatlng;
		
		
		var newpoly = new Array();
		var mypolyOptions = {
		   strokeColor: '#B40B6A',
		   strokeOpacity: 1.0,
		   strokeWeight: 5,
		   visible:true
		   }

        function updatePosition() {
            if (map && marker && currentPosition.lat && currentPosition.lon) {
                var newLatLon = new google.maps.LatLng(currentPosition.lat, currentPosition.lon);
                marker.setPosition(newLatLon);
                map.panTo(newLatLon);
				
				
				
				
				//newpoly[i] = new google.maps.Polyline(mypolyOptions);
				
				
            }
        }

        this.render = function (element) {
            function initializeMap() {
                var mapOptions = {
                    zoom: 13,
                    center: new google.maps.LatLng(37.235, -115.811111),
                    disableDefaultUI: false,
                    draggable: true,
                    styles: [
                        {"featureType": "water", "elementType": "geometry", "stylers": [
                            {"color": "#052C84"}
                        ]},
                        {"featureType": "landscape", "elementType": "geometry", "stylers": [
                            {"color": "#046753"},
                            {"lightness": 20}
                        ]},
                        {"featureType": "road.highway", "elementType": "geometry.fill", "stylers": [
                            {"color": "#000000"},
                            {"lightness": 17}
                        ]},
                        {"featureType": "road.highway", "elementType": "geometry.stroke", "stylers": [
                            {"color": "#535207"},
                            {"lightness": 29},
                            {"weight": 0.2}
                        ]},
                        {"featureType": "road.arterial", "elementType": "geometry", "stylers": [
                            {"color": "#000000"},
                            {"lightness": 18}
                        ]},
                        {"featureType": "road.local", "elementType": "geometry", "stylers": [
                            {"color": "#000000"},
                            {"lightness": 16}
                        ]},
                        {"featureType": "poi", "elementType": "geometry", "stylers": [
                            {"color": "#027533"},
                            {"lightness": 21}
                        ]},
                        {"elementType": "labels.text.stroke", "stylers": [
                            {"visibility": "on"},
                            {"color": "#000000"},
                            {"lightness": 16}
                        ]},
                        {"elementType": "labels.text.fill", "stylers": [
                            {"saturation": 36},
                            {"color": "#000000"},
                            {"lightness": 40}
                        ]},
                        {"elementType": "labels.icon", "stylers": [
                            {"visibility": "off"}
                        ]},
                        {"featureType": "transit", "elementType": "geometry", "stylers": [
                            {"color": "#000000"},
                            {"lightness": 19}
                        ]},
                        {"featureType": "administrative", "elementType": "geometry.fill", "stylers": [
                            {"color": "#027533"},
                            {"lightness": 20}
                        ]},
                        {"featureType": "administrative", "elementType": "geometry.stroke", "stylers": [
                            {"color": "#000000"},
                            {"lightness": 17},
                            {"weight": 1.2}
                        ]}
                    ]
                };

                map = new google.maps.Map(element, mapOptions);

                google.maps.event.addDomListener(element, 'mouseenter', function (e) {
                    e.cancelBubble = true;
                    if (!map.hover) {
                        map.hover = true;
                        map.setOptions({zoomControl: true});
                    }
                });

                google.maps.event.addDomListener(element, 'mouseleave', function (e) {
                    if (map.hover) {
                        map.setOptions({zoomControl: false});
                        map.hover = false;
                    }
                });

                marker = new google.maps.Marker({map: map});

                updatePosition();
            }

            if (window.google && window.google.maps) {
                initializeMap();
            }
            else {
                window.gmap_initialize = initializeMap;
                head.js("https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false&callback=gmap_initialize");
            }
        }

        this.onSettingsChanged = function (newSettings) {
            currentSettings = newSettings;
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName == "lat") {
               // currentPosition.lat = newValue;
            }
            else if (settingName == "lon") {
               // currentPosition.lon = newValue;
            }
			 else if (settingName == "position") {
				 position = newValue[0];
				 currentPosition.lon = position.lng;
				 currentPosition.lat = position.lat;
				 
				 for(i=0; i< newpoly.length; i++)
				{
					newpoly[i].setMap(null)
				}
				 newpoly=[];
									
				 for(i=0; i< newValue.length; i++)
					{
	
						position = newValue[i];
	
						 
						if((typeof newpoly[i] === 'undefined') || newpoly[i].Show != false)
						{
    
							myLatlng = new google.maps.LatLng(position.lat, position.lng);
						 
						 newpoly[i] = new google.maps.Polyline(mypolyOptions);
					
							
							
						         var path = newpoly[i].getPath();

					 // Because path is an MVCArray, we can simply append a new coordinate
					// and it will automatically appear
						 if(myOldLatlng != null)
						   polyLineCount = path.push(myOldLatlng);
						 
						  polyLineCount = path.push(myLatlng);
						  newpoly[i].setMap(map); 
											 
						 // marker.setPosition(myLatlng);
											  
						 myOldLatlng = myLatlng;	
							
							
					}
            }

            updatePosition();
        }
		}

        this.onDispose = function () {
        }

        this.getHeight = function () {
            return 4;
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "google_map",
        display_name: "HelmSmart Google Map",
        fill_size: true,
        settings: [
            {
                name: "lat",
                display_name: "Latitude",
                type: "calculated"
            },
            {
                name: "lon",
                display_name: "Longitude",
                type: "calculated"
            },
			{
                name: "position",
                display_name: "Position",
                type: "calculated"
            }
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new googleMapWidget(settings));
        }
    });

	var valueStyle = freeboard.getStyleString("values");

	freeboard.addStyle('.widget-big-text', valueStyle + "font-size:75px;");

	freeboard.addStyle('.tw-display', 'width: 100%; height:100%; display:table; table-layout:fixed;');

	freeboard.addStyle('.tw-tr',
		'display:table-row;');

	freeboard.addStyle('.tw-tg',
		'display:table-row-group;');

	freeboard.addStyle('.tw-tc',
		'display:table-caption;');

	freeboard.addStyle('.tw-td',
		'display:table-cell;');

	freeboard.addStyle('.tw-value',
		valueStyle +
		'overflow: hidden;' +
		'display: inline-block;' +
		'text-overflow: ellipsis;');

	freeboard.addStyle('.tw-unit',
		'display: inline-block;' +
		'padding-left: 10px;' +
		'padding-bottom: 1.1em;' +
		'vertical-align: bottom;');

	freeboard.addStyle('.tw-value-wrapper',
		'position: relative;' +
		'vertical-align: middle;' +
		'height:100%;');

	freeboard.addStyle('.tw-sparkline',
		'height:20px;');
		
 var textWidget = function (settings) {

        var self = this;

        var currentSettings = settings;
		var displayElement = $('<div class="tw-display"></div>');
		var titleElement = $('<h2 class="section-title tw-title tw-td"></h2>');
        var valueElement = $('<div class="tw-value"></div>');
        var unitsElement = $('<div class="tw-unit"></div>');
        var sparklineElement = $('<div class="tw-sparkline tw-td"></div>');

		function updateValueSizing()
		{
			if(!_.isUndefined(currentSettings.units) && currentSettings.units != "") // If we're displaying our units
			{
				valueElement.css("max-width", (displayElement.innerWidth() - unitsElement.outerWidth(true)) + "px");
			}
			else
			{
				valueElement.css("max-width", "100%");
			}
		}

        this.render = function (element) {
			$(element).empty();

			$(displayElement)
				.append($('<div class="tw-tr"></div>').append(titleElement))
				.append($('<div class="tw-tr"></div>').append($('<div class="tw-value-wrapper tw-td"></div>').append(valueElement).append(unitsElement)))
				.append($('<div class="tw-tr"></div>').append(sparklineElement));

			$(element).append(displayElement);

			updateValueSizing();
        }

        this.onSettingsChanged = function (newSettings) {
            currentSettings = newSettings;

			var shouldDisplayTitle = (!_.isUndefined(newSettings.title) && newSettings.title != "");
			var shouldDisplayUnits = (!_.isUndefined(newSettings.units) && newSettings.units != "");

			if(newSettings.sparkline)
			{
				sparklineElement.attr("style", null);
			}
			else
			{
				delete sparklineElement.data().values;
				sparklineElement.empty();
				sparklineElement.hide();
			}

			if(shouldDisplayTitle)
			{
				titleElement.html((_.isUndefined(newSettings.title) ? "" : newSettings.title));
				titleElement.attr("style", null);
			}
			else
			{
				titleElement.empty();
				titleElement.hide();
			}

			if(shouldDisplayUnits)
			{
				unitsElement.html((_.isUndefined(newSettings.units) ? "" : newSettings.units));
				unitsElement.attr("style", null);
			}
			else
			{
				unitsElement.empty();
				unitsElement.hide();
			}

			var valueFontSize = 30;

			if(newSettings.size == "big")
			{
				valueFontSize = 75;

				
			}
			else if(newSettings.size == "huge")
			{
				valueFontSize = 125;

				
			}

			valueElement.css({"font-size" : valueFontSize + "px"});

			updateValueSizing();
        }

		this.onSizeChanged = function()
		{
			updateValueSizing();
		}

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName == "value") {

                if (currentSettings.animate) {
                    easeTransitionText(newValue, valueElement, 500);
                }
                else {
                    valueElement.text(newValue);
                }

                //if (currentSettings.sparkline) {
                //    addValueToSparkline(sparklineElement, newValue);
                //}
            }
        }

        this.onDispose = function () {

        }

        this.getHeight = function () {
			if (currentSettings.size == "huge" ) {
                return 3;
            }
            else if (currentSettings.size == "big" ) {
                return 2;
            }
            else {
                return 1;
            }
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "text_widget",
        display_name: "Huge Text",
        "external_scripts" : [
            //"plugins/thirdparty/jquery.sparkline.min.js"
			   "https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/jquery.sparkline.min.js"
        ],
        settings: [
            {
                name: "title",
                display_name: "Title",
                type: "text"
            },
            {
                name: "size",
                display_name: "Size",
                type: "option",
                options: [
                    {
                        name: "Regular",
                        value: "regular"
                    },
                    {
                        name: "Big",
                        value: "big"
                    },
					{
                        name: "Huge",
                        value: "huge"
                    }
                ]
            },
            {
                name: "value",
                display_name: "Value",
                type: "calculated"
            },
            {
                name: "sparkline",
                display_name: "Include Sparkline",
                type: "boolean"
            },
            {
                name: "animate",
                display_name: "Animate Value Changes",
                type: "boolean",
                default_value: true
            },
            {
                name: "units",
                display_name: "Units",
                type: "text"
            }
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new textWidget(settings));
        }
    });		
		
		
/*
    var textWidget = function (settings) {

        var self = this;

        var currentSettings = settings;
		var displayElement = $('<div class="tw-display"></div>');
		var titleElement = $('<h2 class="section-title tw-title tw-td"></h2>');
        var valueElement = $('<div class="tw-value"></div>');
        var unitsElement = $('<div class="tw-unit"></div>');
 

		function updateValueSizing()
		{
			if(!_.isUndefined(currentSettings.units) && currentSettings.units != "") // If we're displaying our units
			{
				valueElement.css("max-width", (displayElement.innerWidth() - unitsElement.outerWidth(true)) + "px");
			}
			else
			{
				valueElement.css("max-width", "100%");
			}
		}

        this.render = function (element) {
			$(element).empty();

			$(displayElement)
				.append($('<div class="tw-tr"></div>').append(titleElement))
				.append($('<div class="tw-tr"></div>').append($('<div class="tw-value-wrapper tw-td"></div>').append(valueElement).append(unitsElement)))
	

			$(element).append(displayElement);

			updateValueSizing();
        }

        this.onSettingsChanged = function (newSettings) {
            currentSettings = newSettings;

			var shouldDisplayTitle = (!_.isUndefined(newSettings.title) && newSettings.title != "");
			var shouldDisplayUnits = (!_.isUndefined(newSettings.units) && newSettings.units != "");



			if(shouldDisplayTitle)
			{
				titleElement.html((_.isUndefined(newSettings.title) ? "" : newSettings.title));
				titleElement.attr("style", null);
			}
			else
			{
				titleElement.empty();
				titleElement.hide();
			}

			if(shouldDisplayUnits)
			{
				unitsElement.html((_.isUndefined(newSettings.units) ? "" : newSettings.units));
				unitsElement.attr("style", null);
			}
			else
			{
				unitsElement.empty();
				unitsElement.hide();
			}

			var valueFontSize = 30;

			if(newSettings.size == "big")
			{
				valueFontSize = 75;


			}
			else if(newSettings.size == "huge")
			{
				valueFontSize = 125;


			}

			valueElement.css({"font-size" : valueFontSize + "px"});

			updateValueSizing();
        }

		this.onSizeChanged = function()
		{
			updateValueSizing();
		}

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName == "value") {

                if (currentSettings.animate) {
                    easeTransitionText(newValue, valueElement, 500);
                }
                else {
                    valueElement.text(newValue);
                }

               
            }
        }

        this.onDispose = function () {

        }

        this.getHeight = function () {
			if (currentSettings.size == "huge" ) {
                return 3;
            }
            if (currentSettings.size == "big" ) {
                return 2;
            }
            else {
                return 1;
            }
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "text_widget",
        display_name: "Huge Text",
        "external_scripts" : [
            //"plugins/thirdparty/jquery.sparkline.min.js"
        ],
        settings: [
            {
                name: "title",
                display_name: "Title",
                type: "text"
            },
            {
                name: "size",
                display_name: "Size",
                type: "option",
                options: [
                    {
                        name: "Regular",
                        value: "regular"
                    },
                    {
                        name: "Big",
                        value: "big"
                    },
					{
                        name: "Huge",
                        value: "huge"
                    }
                ]
            },
            {
                name: "value",
                display_name: "Value",
                type: "calculated"
            },
            
            {
                name: "animate",
                display_name: "Animate Value Changes",
                type: "boolean",
                default_value: true
            },
            {
                name: "units",
                display_name: "Units",
                type: "text"
            }
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new textWidget(settings));
        }
    });

*/

}());
