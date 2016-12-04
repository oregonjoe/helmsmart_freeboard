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
	
	// Java-0, Light Green-1,Bittersweet-2, Wild Blue Yonder-3, Pale Turquoise-4,Razzmatazz-5, Plum-6, Apple-7, Valencia-8, Neptune-9, Saffron-10, Default-11
	var gaugeColors = ["#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232","#edebeb"];
	var gaugeFillColors = ["#EB9D07", "#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232","#edebeb"];
	var gaugePointerColors = ["#8e8e93","#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232"];
	var LOADING_INDICATOR_DELAY = 1000;	
	
	
    var gaugeID = 0;
	freeboard.addStyle('.gauge-widget-wrapper', "width: 100%;text-align: center;");
	//freeboard.addStyle('.gauge-widget', "width:200px;height:260px;display:inline-block;");
	freeboard.addStyle('.gauge-widget', "width:75%;75%;display:inline-block;");

    var hsgaugeWidget = function (settings) {
        var self = this;
		var fillcolor = [];
		//var myheight = 60 * this.getHeight();
		
        var thisGaugeID = "gauge-" + gaugeID++;
        var titleElement = $('<h2 class="section-title"></h2>');
       // var gaugeElement = $('<div class="gauge-widget" id="' + thisGaugeID + '" height:'+ myheight + 'px; "></div>');
		var gaugeElement = $('<div class="gauge-widget" id="' + thisGaugeID + '"></div>');
        var gaugeObject;
        var rendered = false;

        var currentSettings = settings;
		
		var fillindex = _.isUndefined(currentSettings.gaugeFillColor) ? 0 : currentSettings.gaugeFillColor;
		
		if(parseInt(fillindex) == 0)
		{
			fillcolor.push('#85A137');	
			fillcolor.push('#85A137');	
			fillcolor.push('#85A137');	
			fillcolor.push('#FFC414'); 	
			fillcolor.push('#FFC414'); 	
			fillcolor.push('#D0532A'); 				
			fillcolor.push('#CE1B21');



		}
		else
		 fillcolor.push(gaugeFillColors[parseInt(fillindex)]);

        function createGauge() {
            if (!rendered) {
                return;
            }
			var myheight = 60 * self.getHeight();
			
			var enableCompass = false;
			var enablefullCircle= false;
			
			if(currentSettings.gaugeStyle == "half")
			{
				enableCompass = false;
				enablefullCircle= false;
			}
			else if(currentSettings.gaugeStyle == "full")
			{
				enableCompass = false;
				enablefullCircle= true;
			}
			else if(currentSettings.gaugeStyle == "compass")
				{
				enableCompass = true;
				enablefullCircle= true;
				currentSettings.min_value = 0;
				currentSettings.max_value = 360;
			}
			
            gaugeElement.empty();

            gaugeObject = new JustGage({
                id: thisGaugeID,
                value: (_.isUndefined(currentSettings.min_value) ? 0 : currentSettings.min_value),
                min: (_.isUndefined(currentSettings.min_value) ? 0 : currentSettings.min_value),
                max: (_.isUndefined(currentSettings.max_value) ? 0 : currentSettings.max_value),
				relativeGaugeSize: true,
				
				//symbol: "NW",

				//gaugeColor: '#F1C232',
				gaugeColor: gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11 : currentSettings.gaugeBackColor],
				
				//levelColors: ['#F1C232',],
				//levelColors: [gaugeFillColors[_.isUndefined(currentSettings.gaugeFillColor) ? 0 : currentSettings.gaugeFillColor],],
				
				levelColors: fillcolor,
				
                label: currentSettings.units,
                //showInnerShadow: false,
		
					//showInnerShadow: true,
					showInnerShadow: currentSettings.dropshadow,
					
					shadowOpacity: 1,
					shadowSize: 2,
					shadowVerticalOffset: 2,
	
				
				
                valueFontColor: "#d3d4d4",
				
			
				donut: enablefullCircle,
				compass: enableCompass,
				
				pointer: true,
				gaugeWidthScale: 0.5,
				
				 textRenderer: function(val) {
					if (val == 99999) 
						return '---';
					else
						return val;
					
				},

				//
				//pointerOptions: {
				//  toplength: -15,
				//  bottomlength: 10,
				//  bottomwidth: 12,
				//  color: '#8e8e93',
				//  stroke: '#ffffff',
				//  stroke_width: 2,
				//  stroke_linecap: 'round'
				//},
				
				    pointerOptions: {
				  toplength: 10,
				  bottomlength: 10,
				  bottomwidth: 8,
				  //color: '#8e8e93'
				   color: gaugePointerColors[_.isUndefined(currentSettings.gaugePointerColor) ? 0 : currentSettings.gaugePointerColor],
				},
						
				
				
				counter: true
            });
        }

        this.render = function (element) {
            rendered = true;
            $(element).append(titleElement).append($('<div class="gauge-widget-wrapper"></div>').append(gaugeElement));
            createGauge();
        }

        this.onSettingsChanged = function (newSettings) {
            if (newSettings.gaugeStyle != currentSettings.gaugeStyle || newSettings.min_value != currentSettings.min_value || newSettings.max_value != currentSettings.max_value || newSettings.units != currentSettings.units || newSettings.units != currentSettings.units) {
				
				if(newSettings.gaugeStyle == "compass")
				{
			
					currentSettings.min_value = 0;
					currentSettings.max_value = 360;
					newSettings.min_value = 0;
					newSettings.max_value = 360;
				}
			
                currentSettings = newSettings;
                createGauge();
            }
            else 
			{
				if(newSettings.gaugeStyle == "compass")
				{
			
					currentSettings.min_value = 0;
					currentSettings.max_value = 360;
					newSettings.min_value = 0;
					newSettings.max_value = 360;
				}
				
                currentSettings = newSettings;
            }

            titleElement.html(newSettings.title);
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (!_.isUndefined(gaugeObject)) {
				
				var datavalue;
					
					if( newValue.constructor === Array)
					{
						if(newValue.length)
						{
							//gaugeObject.label = "NE";
							//gaugeObject.symbol = "NE";
							gaugeObject.refresh(Number(newValue[0].value));
							
						}
						else
							gaugeObject.refresh(Number(99999));
					}
            }
			
        }

        this.onDispose = function () {
        }

        this.getHeight = function () { 
          // return 3;
			return currentSettings.blocks;
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "gauge",
        display_name: "HelmSmart Array Gauge",
		description: "Gauge - uses HelmSmart Data source to grab selected array span - plots only first point in array",
        "external_scripts" : [
            //"plugins/thirdparty/raphael.2.1.0.min.js",
            //"plugins/thirdparty/justgage.1.0.1.js"
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/raphael.2.1.4.min.js",
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/justgage.1.2.9.js"
        ],
        settings: [
            {
                name: "title",
                display_name: "Title",
                type: "text"
            },
            {
                name: "value",
                display_name: "Value",
                type: "calculated"
            },
            {
                name: "units",
                display_name: "Units",
                type: "text"
            },
            {
                name: "min_value",
                display_name: "Minimum",
                type: "text",
                default_value: 0
            },
            {
                name: "max_value",
                display_name: "Maximum",
                type: "text",
                default_value: 100
            },
			
			//
			//{
             //   name: "fullcircle",
             //   display_name: "Full Circle Gauge",
			//	description: "Enable for compass style pointer gauge",
             //   type: "boolean",
             //   default_value: false
            //},
			
			{
			"name": "gaugeStyle",
			"display_name": "Gauge Style",
			"type": "option",
			"options": [
				{
					"name": "Half Circle",
					"value": "half"
				},
				{
					"name": "Full Circle",
					"value": "full"
				},
				{
					"name": "Compass",
					"value": "compass"
				},
				]
			},

			
			{
                name: "dropshadow",
                display_name: "Drop Shadow",
                type: "boolean",
                default_value: true
            },
			
			{
			name: "blocks",
			display_name: "Height (No. Blocks)",
			type: "text",
			default_value: 4
			}, 
			
			// Java-0, Light Green-1,Bittersweet-2, Wild Blue Yonder-3, Pale Turquoise-4,Razzmatazz-5, Plum-6, Apple-7, Valencia-8, Neptune-9, Saffron-10, Default-11
			{
			"name": "gaugeBackColor",
			"display_name": "Gauge BackGround Color",
			"type": "option",
			"options": [
				{
					"name": "Default",
					"value": "11"
				},
				{
					"name": "Java",
					"value": "0"
				}, 
				{
					"name": "Light Green",
					"value": "1"
				},
						{
					"name": "Bittersweet",
					"value": "2"
				}, 
				{
					"name": "Wild Blue Yonder",
					"value": "3"
				},
						{
					"name": "Pale Turquoise",
					"value": "4"
				}, 
				{
					"name": "Razzmatazz",
					"value": "5"
				},
						{
					"name": "Plum",
					"value": "6"
				}, 
				{
					"name": "Apple",
					"value": "7"
				},
						{
					"name": "Valencia",
					"value": "8"
				}, 
				{
					"name": "Neptune",
					"value": "9"
				},
				{
					"name": "Saffron",
					"value": "10"
				}
				]
			} ,
						{
			"name": "gaugeFillColor",
			"display_name": "Gauge Fill Color",
			"type": "option",
			"options": [
				{
					"name": "Default",
					"value": "0"
				}, 	
			
				{
					"name": "Java",
					"value": "1"
				}, 
				{
					"name": "Light Green",
					"value": "2"
				},
						{
					"name": "Bittersweet",
					"value": "3"
				}, 
				{
					"name": "Wild Blue Yonder",
					"value": "4"
				},
						{
					"name": "Pale Turquoise",
					"value": "5"
				}, 
				{
					"name": "Razzmatazz",
					"value": "6"
				},
						{
					"name": "Plum",
					"value": "7"
				}, 
				{
					"name": "Apple",
					"value": "8"
				},
						{
					"name": "Valencia",
					"value": "9"
				}, 
				{
					"name": "Neptune",
					"value": "10"
				},
				{
					"name": "Saffron",
					"value": "11"
				}
				]
			} ,
			// Default-0, Java-1, Light Green-2,Bittersweet-3, Wild Blue Yonder-4, Pale Turquoise-5,Razzmatazz-6, Plum-7, Apple-8, Valencia-9, Neptune-10, Saffron-11, 
						{
			"name": "gaugePointerColor",
			"display_name": "Gauge Pointer Color",
			"type": "option",
			"options": [
				{
					"name": "Default",
					"value": "0"
				}, 
				{
					"name": "Java",
					"value": "1"
				}, 
				{
					"name": "Light Green",
					"value": "2"
				},
						{
					"name": "Bittersweet",
					"value": "3"
				}, 
				{
					"name": "Wild Blue Yonder",
					"value": "4"
				},
						{
					"name": "Pale Turquoise",
					"value": "5"
				}, 
				{
					"name": "Razzmatazz",
					"value": "6"
				},
						{
					"name": "Plum",
					"value": "7"
				}, 
				{
					"name": "Apple",
					"value": "8"
				},
						{
					"name": "Valencia",
					"value": "9"
				}, 
				{
					"name": "Neptune",
					"value": "10"
				},
				{
					"name": "Saffron",
					"value": "11"
				}
				]
			} 
			
			
			
			
			
			
			
			
			
			
			
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new hsgaugeWidget(settings));
        }
    });
	
	}());