// ┌────────────────────────────────────────────────────────────────────┐ \\
// │ F R E E B O A R D                                                  │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Copyright © 2013 Jim Heising (https://github.com/jheising)         │ \\
// │ Copyright © 2013 Bug Labs, Inc. (http://buglabs.net)               │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Licensed under the MIT license.                                    │ \\
// └────────────────────────────────────────────────────────────────────┘ \\

	var MAX_NUM_ZONES = 3;

(function () {
	var SPARKLINE_HISTORY_LENGTH = 100;
	var SPARKLINE_COLORS = ["#FF9900", "#FFFFFF", "#B3B4B4", "#6B6B6B", "#28DE28", "#13F7F9", "#E6EE18", "#C41204", "#CA3CB8", "#0B1CFB"];
	
	// Java-0, Light Green-1,Bittersweet-2, Wild Blue Yonder-3, Pale Turquoise-4,Razzmatazz-5, Plum-6, Apple-7, Valencia-8, Neptune-9, Saffron-10, Default-11
	var gaugeColors = ["#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232","#edebeb"];
	var gaugeFillColors = ["#EB9D07", "#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232","#edebeb"];
	var gaugePointerColors = ["#8e8e93","#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee", "#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232"];
	var LOADING_INDICATOR_DELAY = 1000;	
	var myStrokeColors = 
  ['#41137B', '#47137B','#4F127B','#58107B','#630F7B','#6D0E7B', '#780C7B','#840A7B','#90097B','#9C087B',
  '#A7067B', '#B3047B','#BE047B','#C7027B','#D1017B','#D9007B', '#DF007A','#E20078','#E20076','#E20075',
  '#E20072', '#E20070','#E2006D','#E2006B','#E20068','#E20064', '#E20061','#E2005E','#E2005A','#E20057',
  '#E20053', '#E2004F','#E2004C','#E20049','#E20045','#E20042', '#E2003F','#E1003B','#E00238','#E00436',
  '#DF0733', '#DF0B31','#DF0E2E','#DF122C','#E0182A','#E11F28', '#E22726','#E42F25','#E63922','#E84320',
  '#EB4F1F', '#EE5A1D','#F1661C','#F3721A','#F37D19','#F38A19', '#F39618','#F3A216','#F3AD16','#F3B815',
  '#F3C315', '#F3CC15','#F3D515','#F3DE15','#F3E415','#F3E915', '#F3EE15','#EFEF15','#E7EF16','#DEEF17',
  '#D3EF18', '#C8ED19','#BAE91A','#ADE31C','#9EDD1D','#8FD71F', '#7ED021','#6FC924','#5FC127','#51BA29',
  '#42B32C', '#34AC30','#27A633','#1BA137','#109D3C','#089A41', '#009847','#00984C','#009852','#009859',
  '#009961', '#009C69','#009E72','#00A07A','#00A384','#00A68D', '#00AA97','#00ADA1','#00B1A9','#00B4B3',
  '#00B8BC', '#00BCC5','#00BECD','#00C2D5','#01C5DC','#02C7E3', '#04CAE9','#04CBED','#04CCF0','#04CCF0',
  '#04CCF0', '#04CCF0','#04CCF0','#04CCF0','#04CCF0','#04CCF0', '#04CCF0','#04CCF0','#04CCF0','#04CCF0'];
					
    function easeTransitionText(newValue, textElement, duration) {

		var currentValue = $(textElement).text();

        if (currentValue === newValue)
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

	function addSparklineLegend(element, legend) {
		var legendElt = $("<div class='sparkline-legend'></div>");
		for(var i=0; i<legend.length; i++) {
			var color = SPARKLINE_COLORS[i % SPARKLINE_COLORS.length];
			var label = legend[i];
			legendElt.append("<div class='sparkline-legend-value'><span style='color:" +
							 color + "'>&#9679;</span>" + label + "</div>");
		}
		element.empty().append(legendElt);

		freeboard.addStyle('.sparkline-legend', "margin:5px;");
		freeboard.addStyle('.sparkline-legend-value',
			'color:white; font:10px arial,san serif; float:left; overflow:hidden; width:50%;');
		freeboard.addStyle('.sparkline-legend-value span',
			'font-weight:bold; padding-right:5px;');
	}

	function addValueToSparkline(element, value, legend) {
		var values = $(element).data().values;
		var valueMin = $(element).data().valueMin;
		var valueMax = $(element).data().valueMax;
		if (!values) {
			values = [];
			valueMin = undefined;
			valueMax = undefined;
		}

		var collateValues = function(val, plotIndex) {
			if(!values[plotIndex]) {
				values[plotIndex] = [];
			}
			if (values[plotIndex].length >= SPARKLINE_HISTORY_LENGTH) {
				values[plotIndex].shift();
			}
			values[plotIndex].push(Number(val));

			if(valueMin === undefined || val < valueMin) {
				valueMin = val;
			}
			if(valueMax === undefined || val > valueMax) {
				valueMax = val;
			}
		}

		if(_.isArray(value)) {
			_.each(value, collateValues);
		} else {
			collateValues(value, 0);
		}
		$(element).data().values = values;
		$(element).data().valueMin = valueMin;
		$(element).data().valueMax = valueMax;

		var tooltipHTML = '<span style="color: {{color}}">&#9679;</span> {{y}}';

		var composite = false;
		_.each(values, function(valueArray, valueIndex) {
			$(element).sparkline(valueArray, {
				type: "line",
				composite: composite,
				height: "100%",
				width: "100%",
				fillColor: false,
				lineColor: SPARKLINE_COLORS[valueIndex % SPARKLINE_COLORS.length],
				lineWidth: 2,
				spotRadius: 3,
				spotColor: false,
				minSpotColor: "#78AB49",
				maxSpotColor: "#78AB49",
				highlightSpotColor: "#9D3926",
				highlightLineColor: "#9D3926",
				chartRangeMin: valueMin,
				chartRangeMax: valueMax,
				tooltipFormat: (legend && legend[valueIndex])?tooltipHTML + ' (' + legend[valueIndex] + ')':tooltipHTML
			});
			composite = true;
		});
	}

	var valueStyle = freeboard.getStyleString("values");

	freeboard.addStyle('.widget-big-text', valueStyle + "font-size:75px;");
	freeboard.addStyle('.widget-huge-text', valueStyle + "font-size:150px;");
	
	freeboard.addStyle('.pwidget-big-text', valueStyle + "font-size:75px;");

	freeboard.addStyle('.hstw-display', 'width: 100%; height:100%; display:table; table-layout:fixed;');

	freeboard.addStyle('.hstw-tr', 'display:table-row;');

	freeboard.addStyle('.hstw-tg',
		'display:table-row-group;');

	freeboard.addStyle('.hstw-tc',
		'display:table-caption;');

	freeboard.addStyle('.hstw-td',
		'display:table-cell;');

	freeboard.addStyle('.hstw-value',
		valueStyle +
		'overflow: hidden;' +
		'display: inline-block;' +
		'text-overflow: ellipsis;');

	freeboard.addStyle('.hstw-unit',
		'display: inline-block;' +
		'padding-left: 10px;' +
		'padding-bottom: 1.1em;' +
		'vertical-align: bottom;');

	freeboard.addStyle('.hstw-value-wrapper',
		'position: relative;' +
		'vertical-align: middle;' +
		'height:100%;');

	freeboard.addStyle('.hstw-sparkline',
		'height:20px;');

    var hstextWidget = function (settings) {

        var self = this;

        var currentSettings = settings;
		var displayElement = $('<div class="hstw-display"></div>');
		var titleElement = $('<h2 class="section-title hstw-title hstw-td"></h2>');
        var valueElement = $('<div class="hstw-value"></div>');
        var unitsElement = $('<div class="hstw-unit"></div>');
        var sparklineElement = $('<div class="hstw-sparkline hstw-td"></div>');

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
				.append($('<div class="hstw-tr"></div>').append(titleElement))
				.append($('<div class="hstw-tr"></div>').append($('<div class="hstw-value-wrapper hstw-td"></div>').append(valueElement).append(unitsElement)))
				.append($('<div class="hstw-tr"></div>').append(sparklineElement));

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
				titleElement.html((_.isUndefined(newSettings.title) ? "": newSettings.title));
				titleElement.attr("style", null);
			}
			else
			{
				titleElement.empty();
				titleElement.hide();
			}

			if(shouldDisplayUnits)
			{
				unitsElement.html((_.isUndefined(newSettings.units) ? "": newSettings.units));
				unitsElement.attr("style", null);
			}
			else
			{
				unitsElement.empty();
				unitsElement.hide();
			}

			var valueFontSize = 30;
			if(newSettings.size == "small")
			{
				valueFontSize = 20;
			}
			if(newSettings.size == "big")
			{
				valueFontSize = 75;

				if(newSettings.sparkline)
				{
					valueFontSize = 60;
				}
			}
			else if(newSettings.size == "huge")
			{
				valueFontSize = 150;

				if(newSettings.sparkline)
				{
					valueFontSize = 125;
				}
			}

			valueElement.css({"font-size": valueFontSize + "px"});

			updateValueSizing();
        }

		this.onSizeChanged = function()
		{
			updateValueSizing();
		}

        this.onCalculatedValueChanged = function (settingName, newValue) {
			if (settingName == "value") 
			{
				var value;
				
				//if(Array.isArray(newValue[0]) && newValue[0].length)
					
				if( newValue.constructor === Array)
				{
					if(newValue.length)
					{
						value = "---";
						//j=0;
						for(i=0; i< newValue.length; i++)
						//for(i=newValue.length-1; i>0; i--)
						{
							if(newValue[i].value != "---")
							{
								value = newValue[i].value;
								
								break;
							}
						}
						
						if (currentSettings.sparkline) {
							for(i=0; i< newValue.length; i++)
							//for(i=newValue.length-1; i>0; i--)
							{
								
								if(newValue[i].value != "---")
									addValueToSparkline(sparklineElement, newValue[i].value);
							}
						}
					}
					else
						value = "---";
					
				}
				else 
				{
					value = newValue;
					
					if (currentSettings.sparkline) {
                    addValueToSparkline(sparklineElement, value);
					}
				}
				
				
				
                if (currentSettings.animate && !isNaN(value)) {
					
                    easeTransitionText(value, valueElement, 500);
                }
                else {
                    valueElement.text(value);
					//unitsElement.css({"color": "blue !important"});
					//valueElement.css({"color": "blue !important"});
                }

			
            }
        }

        this.onDispose = function () {

        }

        this.getHeight = function () {
			 if (currentSettings.size == "huge" ) {
                return 4;
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
        type_name: "hstext_widget",
        display_name: "HelmSmart Array Text",
		description: "Text Box - uses HelmSmart Data source to grab selected array span - plots first point in array",
        "external_scripts": [
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
                        name: "Small",
                        value: "small"
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
            newInstanceCallback(new hstextWidget(settings));
        }
    });
	
	

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
		
		var fillindex = _.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor;
		
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
                value: (_.isUndefined(currentSettings.min_value) ? 0: currentSettings.min_value),
                min: (_.isUndefined(currentSettings.min_value) ? 0: currentSettings.min_value),
                max: (_.isUndefined(currentSettings.max_value) ? 0: currentSettings.max_value),
				relativeGaugeSize: true,
				
				//symbol: "NW",

				//gaugeColor: '#F1C232',
				gaugeColor: gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor],
				
				//levelColors: ['#F1C232',],
				//levelColors: [gaugeFillColors[_.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor],],
				
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
				   color: gaugePointerColors[_.isUndefined(currentSettings.gaugePointerColor) ? 0: currentSettings.gaugePointerColor],
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
							var gaugevalue = Number(99999);
							
							for(i=0; i< newValue.length; i++)
							{
								if(newValue[i].value != "---")
								{
									gaugevalue = Number(newValue[i].value);
									break;
								}
								
							}
							gaugeObject.refresh(gaugevalue);
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
        "external_scripts": [
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

	
	
	/*
    var compassID = 0;
	freeboard.addStyle('.compass-widget-wrapper', "width: 100%;text-align: center;");
	//freeboard.addStyle('.compass-widget', "width:200px;height:260px;display:inline-block;");
	freeboard.addStyle('.compass-widget', "width:75%;75%;display:inline-block;");

    var hscompassWidget = function (settings) {
        var self = this;
		var fillcolor = [];
		//var myheight = 60 * this.getHeight();
		
        var thisCompassID = "compass-" + compassID++;
        var titleElement = $('<h2 class="section-title"></h2>');
       // var gaugeElement = $('<div class="compass-widget" id="' + thisGaugeID + '" height:'+ myheight + 'px; "></div>');
		var compassElement = $('<div class="compass-widget" id="' + thisCompassID + '"></div>');
        var compassObject;
        var rendered = false;

        var currentSettings = settings;
		
		var fillindex = _.isUndefined(currentSettings.compassFillColor) ? 0: currentSettings.compassFillColor;
		
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

        function createCompass() {
            if (!rendered) {
                return;
            }
			var myheight = 60 * self.getHeight();
            compassElement.empty();

            compassObject = new JustGage({
                id: thisCompassID,
                value: (_.isUndefined(currentSettings.min_value) ? 0: currentSettings.min_value),
                min: (_.isUndefined(currentSettings.min_value) ? 0: currentSettings.min_value),
                max: (_.isUndefined(currentSettings.max_value) ? 0: currentSettings.max_value),
				relativeGaugeSize: true,

				//gaugeColor: '#F1C232',
				gaugeColor: gaugeColors[_.isUndefined(currentSettings.compassBackColor) ? 11: currentSettings.compassBackColor],
				
				//levelColors: ['#F1C232',],
				//levelColors: [gaugeFillColors[_.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor],],
				
				levelColors: fillcolor,
				
                label: currentSettings.units,
                //showInnerShadow: false,
		
					//showInnerShadow: true,
					showInnerShadow: currentSettings.dropshadow,
					
					shadowOpacity: 1,
					shadowSize: 2,
					shadowVerticalOffset: 2,
	
				
				
                valueFontColor: "#d3d4d4",
				
			
				donut: currentSettings.fullcircle,
				
				
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
				//
				    pointerOptions: {
				  toplength: 10,
				  bottomlength: 10,
				  bottomwidth: 8,
				  //color: '#8e8e93'
				   color: gaugePointerColors[_.isUndefined(currentSettings.compassPointerColor) ? 0: currentSettings.compassPointerColor],
				},
						
				
				
				counter: true
            });
        }

        this.render = function (element) {
            rendered = true;
            $(element).append(titleElement).append($('<div class="gauge-widget-wrapper"></div>').append(compassElement));
            createCompass();
        }

        this.onSettingsChanged = function (newSettings) {
            if (newSettings.min_value != currentSettings.min_value || newSettings.max_value != currentSettings.max_value || newSettings.units != currentSettings.units) {
                currentSettings = newSettings;
                createCompass();
            }
            else {
                currentSettings = newSettings;
            }

            titleElement.html(newSettings.title);
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (!_.isUndefined(compassObject)) {
				
				var datavalue;
					
					if( newValue.constructor === Array)
					{
						if(newValue.length)
						{
							compassObject.refresh(Number(newValue[0].value));
						}
						else
							compassObject.refresh(Number(99999));
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
        type_name: "compass",
        display_name: "HelmSmart Array Compass",
		description: "Compass - uses HelmSmart Data source to grab selected array span - plots only first point in array",
        "external_scripts": [
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
			
			
			{
                name: "fullcircle",
                display_name: "Full Circle Gauge",
				description: "Enable for compass style pointer gauge",
                type: "boolean",
                default_value: true
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
			"name": "compassBackColor",
			"display_name": "Compass BackGround Color",
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
			"name": "compassFillColor",
			"display_name": "Compass Fill Color",
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
			"name": "compassPointerColor",
			"display_name": "Compass Pointer Color",
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

	
	*/
	
	
	freeboard.addStyle('.sparkline', "width:100%;height: 75px;");
    var sparklineWidget = function (settings) {
        var self = this;

        var titleElement = $('<h2 class="section-title"></h2>');
        var sparklineElement = $('<div class="sparkline"></div>');
		var sparklineLegend = $('<div></div>');
		var currentSettings = settings;
		var arrayvalues = [];

        this.render = function (element) {
            $(element).append(titleElement).append(sparklineElement).append(sparklineLegend);
        }

        this.onSettingsChanged = function (newSettings) {
			currentSettings = newSettings;
            titleElement.html((_.isUndefined(newSettings.title) ? "": newSettings.title));

			if(newSettings.include_legend) {
				addSparklineLegend(sparklineLegend,  newSettings.legend.split(","));
			}
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
			//if (settingName == "value") 
			{
				// newValue is an array of arrays
				// each sub arry is a series of data points
				// there is an arry for each sparkline
				//if( newValue.constructor === Array)
				{
						

					if(Array.isArray(newValue[0]) && newValue[0].length)
					{
						
						// get number of points to plot for the series
					// assume all series have the saem number of points ??
					length=newValue[0].length;			
						for(i=0; i< length; i++)
						{
							// empty the series points
							arrayvalues = [];
							
							// add a point from each series
							for(j=0; j< newValue.length; j++)
							{
								if(newValue[j][i].value != "---")
									arrayvalues.push(newValue[j][i].value);
							}
								
								// now pass the serries of points into the plot routine 
								if (currentSettings.legend)
								{
								
									addValueToSparkline(sparklineElement,  arrayvalues, currentSettings.legend.split(","));
								} else 
								{
									
										addValueToSparkline(sparklineElement, arrayvalues);
									
								}
						}
					}
					else
					{
						// now pass the serries of points into the plot routine 
								if (currentSettings.legend)
								{
								
									addValueToSparkline(sparklineElement,  newValue, currentSettings.legend.split(","));
								} else 
								{
									
										addValueToSparkline(sparklineElement, newValue);
									
								}
						
					}
				}
				
			}
        }

        this.onDispose = function () {
        }

        this.getHeight = function () {
			var legendHeight = 0;
			if (currentSettings.include_legend && currentSettings.legend) {
				var legendLength = currentSettings.legend.split(",").length;
				if (legendLength > 4) {
					legendHeight = Math.floor((legendLength-1) / 4) * 0.5;
				} else if (legendLength) {
					legendHeight = 0.5;
				}
			}
			return 2 + legendHeight;
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "sparkline",
        display_name: "HelmSmart Array Sparkline",
		description: "Historical Sparkline- uses HelmSmart Data source to grab selected array span - plots all points in array",
        "external_scripts": [
            //"plugins/thirdparty/jquery.sparkline.min.js"
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/jquery.sparkline.min.js"
			//"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/raphael.2.1.0.min.js",
			//"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/justgage.1.0.1.js"
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
                type: "calculated",
				multi_input: "true"
            },
			{
				name: "include_legend",
				display_name: "Include Legend",
				type: "boolean"
			},
			{
				name: "legend",
				display_name: "Legend",
				type: "text",
				description: "Comma-separated for multiple sparklines"
			}
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new sparklineWidget(settings));
        }
    });
	/*
	var pgaugeID = 0;
	freeboard.addStyle('.pgauge-widget-wrapper', "width: 100%;text-align: center;");
	freeboard.addStyle('.pgauge-widget', "width:150px;height:200px;display:inline-block;");

	freeboard.addStyle('div.pointer-value', "position:absolute;height:160px;margin: auto;top: 0px;bottom: 0px;width: 100%;text-align:center;");
    var pointerWidget = function (settings) {
        var self = this;
        var paper;
        var strokeWidth = 3;
        var triangle;
        var width, height;
        var currentValue = 0;
        var valueDiv = $('<div class="pwidget-big-text"></div>');
        var unitsDiv = $('<div></div>');
		var thisGaugeID = "gauge-" + pgaugeID++;
        var titleElement = $('<h2 class="section-title"></h2>');
        var gaugeElement = $('<div class="pgauge-widget" id="' + thisGaugeID + '"></div>');

		
		

        function polygonPath(points) {
            if (!points || points.length < 2)
                return [];
            var path = []; //will use path object type
            path.push(['m', points[0], points[1]]);
            for (var i = 2; i < points.length; i += 2) {
                path.push(['l', points[i], points[i + 1]]);
            }
            path.push(['z']);
            return path;
        }

        this.render = function (element) {

			
			 $(element).append($('<div class="pointer-value"></div>').append(valueDiv).append(unitsDiv).append(gaugeElement));
			
            width = $(element).width();
            height = $(element).height();
			 height = gaugeElement.height();
			//height = 160;

            var radius = Math.min(width, height) / 2 - strokeWidth * 2;

            paper = Raphael($(element).get()[0], width, height);
            var circle = paper.circle(width / 2, height / 2, radius);
            circle.attr("stroke", "#FF9900");
            circle.attr("stroke-width", strokeWidth);

            triangle = paper.path(polygonPath([width / 2, (height / 2) - radius + strokeWidth, 15, 20, -30, 0]));
            triangle.attr("stroke-width", 0);
            triangle.attr("fill", "#fff");

            $(element).append($('<div class="pointer-value"></div>').append(valueDiv).append(unitsDiv));
        }

        this.onSettingsChanged = function (newSettings) {
            unitsDiv.html(newSettings.units);
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
			var datavalue = newValue[0].value;
			
			if (!isNaN(datavalue))
			{
				if (settingName == "direction") {
					if (!_.isUndefined(triangle)) {
						var direction = "r";

						var oppositeCurrent = currentValue + 180;

						if (oppositeCurrent < datavalue) {
							//direction = "l";
						}

						triangle.animate({transform: "r" + datavalue + "," + (width / 2) + "," + (height / 2)}, 250, "bounce");
					}

					currentValue = datavalue;
				}
				else if (settingName == "value_text") {
					valueDiv.html(datavalue);
				}
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
        type_name: "pointer",
        display_name: "HelmSmart Array Pointer",
		description: "Radial Pointer Gauge - uses HelmSmart Data source to grab selected array span - plots only first point in array",
        "external_scripts": [
            //"plugins/thirdparty/raphael.2.1.0.min.js"
						//"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/jquery.sparkline.min.js"
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/raphael.2.1.0.min.js",
			//"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/justgage.1.0.1.js"
        ],
        settings: [
            {
                name: "direction",
                display_name: "Direction",
                type: "calculated",
                description: "In degrees"
            },
            {
                name: "value_text",
                display_name: "Value Text",
                type: "calculated"
            },
            {
                name: "units",
                display_name: "Units",
                type: "text"
            }
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new pointerWidget(settings));
        }
    });
*/
 var vgaugeID = 0;
	freeboard.addStyle('.vgauge-widget-wrapper', "width: 100%;text-align: center;");
	//freeboard.addStyle('.vgauge-widget', "width:240px;height:160px;display:inline-block;");
	freeboard.addStyle('.vgauge-widget', "width:100%;height:100%;display:inline-block;");
	
 var verticalgaugeWidget = function (settings) {
       // var titleElement = $('<h2 class="section-title"></h2>');
       // var gaugeElement = $('<div></div>');
		

        //var gaugeElement = $('<div></div>');

		var thisGaugeID = "vgauge-" + vgaugeID++;
        var titleElement = $('<h2 class="section-title"></h2>');
        var gaugeElement = $('<div class="vgauge-widget" id="' + thisGaugeID + '"></div>');
		
		
		
        var self = this;
        var paper = null;
        var gaugeFill = null;
        var rect;
        var width, height;
        var valueText, unitsText;
        var minValueLabel, maxValueLabel;
		var calculatedHeight=0;
		
        //var currentValue = 0;
        //var colors = ["#a9d70b", "#f9c802", "#ff0000"];

        var currentSettings = settings;

		
		var fillindex = _.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor;
		

	
		
		
		
		
        // get the color for a fill percentage
        //   these colors match the justGage library for radial guagues //
        function getColor(fillPercent) {
            // mix colors
            // green rgb(169,215,11) #a9d70b
            // yellow rgb(249,200,2) #f9c802
            // red rgb(255,0,0) #ff0000

            if (fillPercent >= 0.5 ) {
                fillPercent = 2 * fillPercent - 1;
                var R = fillPercent * 255 + (1 - fillPercent) * 249;
                var G = fillPercent * 0 + (1 - fillPercent) * 200;
                var B = fillPercent * 0 + (1 - fillPercent) * 2;
            }
            else {
                fillPercent = 2 * fillPercent;
                var R = fillPercent * 249 + (1 - fillPercent) * 169;
                var G = fillPercent * 200 + (1 - fillPercent) * 215;
                var B = fillPercent * 2 + (1 - fillPercent) * 11;
            }

            return "rgb(" + Math.round(R) + "," + Math.round(G) + "," + Math.round(B) + ")"
        }
		       
		function createvGauge()
		{
			
			width = gaugeElement.width();
            height = 160;
			var myheight = 60 * self.getHeight();
			height = myheight;
			
			//calculatedHeight = 120;
			//calculatedHeight = myheight/2 - 20;
			calculatedHeight = myheight * 0.75;
			var gaugeTop = height*0.10
			
            var gaugeWidth = 30;
            var gaugeHeight = calculatedHeight;

			
			fillindex = _.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor;

			
			
			// get full container space
            paper = Raphael(gaugeElement.get()[0], width, height);
			// clear widget
            paper.clear();

			//rect = paper.rec(x pos, y pos, width, height, radius)
            //rect = paper.rect(width / 3 - gaugeWidth / 2, height / 2 - gaugeHeight / 2, gaugeWidth, gaugeHeight);
			// set vBar top to 10% of the space
			rect = paper.rect(width / 4 - gaugeWidth / 2, gaugeTop, gaugeWidth, gaugeHeight);
			
            rect.attr({
              //  "fill": "#edebeb",
				"fill":	gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor],
                "stroke": "#A6A3A3"
            });

            // place min and max labels
           // minValueLabel = paper.text(width / 3, height / 2 + gaugeHeight / 2 + 14, currentSettings.min_value);
           // maxValueLabel = paper.text(width / 3, height / 2 - gaugeHeight / 2 - 14, currentSettings.max_value);
			
			minValueLabel = paper.text(width / 4 + gaugeWidth, gaugeTop + gaugeHeight - 10, currentSettings.min_value);
            maxValueLabel = paper.text(width / 4 + gaugeWidth, gaugeTop + 10, currentSettings.max_value);

            minValueLabel.attr({
                "font-family": "arial",
                "font-size": "10",
                "fill": "#b3b3b3",
                "text-anchor": "middle"
            });

            maxValueLabel.attr({
                "font-family": "arial",
                "font-size": "10",
                "fill": "#b3b3b3",
                "text-anchor": "middle"
            });

            // place units and value
            var units = _.isUndefined(currentSettings.units) ? "": currentSettings.units;

            valueText = paper.text(width * 3 / 4, height / 2 - 20, "");
            unitsText = paper.text(width * 3 / 4, height / 2 + 20, units);

            valueText.attr({
                "font-family": "arial",
                "font-size": "45",
                "font-weight": "bold",
                "fill": "#d3d4d4",
                "text-anchor": "middle"
            });

            unitsText.attr({
                "font-family": "arial",
                "font-size": "15",
                "font-weight": "normal",
                "fill": "#b3b3b3",
                "text-anchor": "middle"
            });

            // fill to 0 percent
		
			// set vBar top to 10% of the space

            //gaugeFill = paper.rect(width / 3 - gaugeWidth / 2, height / 2 - gaugeHeight / 2, gaugeWidth, 0);
			gaugeFill = paper.rect(width / 4 - gaugeWidth / 2, gaugeTop, gaugeWidth, 0);
            gaugeFill.attr({
               // "fill": "#edebeb",
				"fill":	gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor],
                "stroke":  "#A6A3A3"
            });
			
		}
		

        self.render = function (element) {
            $(element).append(titleElement.html(currentSettings.title)).append(gaugeElement);
			
			createvGauge();

        }

        self.onSettingsChanged = function (newSettings) {
            if (newSettings.units != currentSettings.units || newSettings.min_value != currentSettings.min_value || newSettings.max_value != currentSettings.max_value) {
                currentSettings = newSettings;
                var units = _.isUndefined(currentSettings.units) ? "": currentSettings.units;
                var min = _.isUndefined(currentSettings.min_value) ? 0: currentSettings.min_value;
                var max = _.isUndefined(currentSettings.max_value) ? 0: currentSettings.max_value;

                unitsText.attr({"text": units});
                minValueLabel.attr({"text": min});
                maxValueLabel.attr({"text": max});
            }
            else {
                currentSettings = newSettings;
            }

            titleElement.html(newSettings.title);
			
			createvGauge();
        }

        self.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName === "value") {
                if (!_.isUndefined(gaugeFill) && !_.isUndefined(valueText)) {

                    newValue = _.isUndefined(newValue) ? 0: newValue;
					
					var datavalue;
					
					if( newValue.constructor === Array)
					{
						if(newValue.length)
						{
							
							
							datavalue = "---";
							
							for(i=0; i< newValue.length; i++)
							{
								if(newValue[i].value != "---")
								{
									datavalue = newValue[i].value;
									
									break;
								}
							}
						

							if(datavalue != "---")
							{
					
								var fillVal = calculatedHeight * (datavalue - currentSettings.min_value)/(currentSettings.max_value - currentSettings.min_value);

								fillVal = fillVal > calculatedHeight ? calculatedHeight: fillVal;
								fillVal = fillVal < 0 ? 0: fillVal;

								var backfill = gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor];
								
								if(parseInt(fillindex) == 0)
									var fillColor = getColor(fillVal / calculatedHeight);
								else					
									var fillColor = gaugeFillColors[parseInt(fillindex)];	
								 
								 


								// animate like radial gauges
								//gaugeFill.animate({"height": 120 - fillVal, "fill": "#edebeb", "stroke": "#A6A3A3"}, 500, ">");
								gaugeFill.animate({"height": calculatedHeight - fillVal, "fill": backfill, "stroke": "#A6A3A3"}, 500, ">");
								rect.animate({"fill": fillColor, "stroke":  "#A6A3A3" });

								valueText.attr({"text": datavalue});
							}
							else
								valueText.attr({"text": "---"});
						}
						else
							valueText.attr({"text": "---"});
					}
					else
						valueText.attr({"text": newValue});
                }
            }
        }

        self.onDispose = function () {
        }

        self.getHeight = function () {
            //return 3;
			return currentSettings.blocks;
        }

    };

    freeboard.loadWidgetPlugin({
        type_name: "vertical-linear-gauge",
        display_name: "HelmSmart Array Vertical Gauge",
        "external_scripts": [
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/raphael.2.1.0.min.js",
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/colormix.2.0.0.min.js"
            //"plugins/thirdparty/raphael.2.1.0-custom.js",
            //"plugins/thirdparty/colormix.2.0.0.min.js"
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
                type: "number",
                default_value: 0
            },
            {
                name: "max_value",
                display_name: "Maximum",
                type: "number",
                default_value: 100
            },
			
			{
			name: "blocks",
			display_name: "Height (No. Blocks)",
			type: "text",
			default_value: 3
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
			},
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
			} 			
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new verticalgaugeWidget(settings));
        }
    });	
	
	
	var hgaugeID = 0;
	freeboard.addStyle('.hgauge-widget-wrapper', "width: 100%;text-align: center;");
	freeboard.addStyle('.hgauge-widget', "width:260px;height:80px;display:inline-block;");
		freeboard.addStyle('.hgauge-widget', "width:100%;100%;display:inline-block;");
	
   var horzinalgaugeWidget = function (settings) {
       //var titleElement = $('<h2 class="section-title"></h2>');
        //var gaugeElement = $('<div></div>');
		
		var thisGaugeID = "hgauge-" + hgaugeID++;
        var titleElement = $('<h2 class="section-title"></h2>');
        var gaugeElement = $('<div class="hgauge-widget" id="' + thisGaugeID + '"></div>');

        var self = this;
        var paper = null;
        var gaugeFill = null;
        var width, height;
        var valueText, unitsText;
        var minValueLabel, maxValueLabel;
		var calculatedWidth=160;
		var calculatedHeight=160;
				
        //var currentValue = 0;
        //var colors = ["#a9d70b", "#f9c802", "#ff0000"];

        var currentSettings = settings;
		var fillindex = _.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor;
		var backfill = gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor];
        /* get the color for a fill percentage
           these colors match the justGage library for radial guagues */
        function getColor(fillPercent) {
            // mix colors
            // green rgb(169,215,11) #a9d70b
            // yellow rgb(249,200,2) #f9c802
            // red rgb(255,0,0) #ff0000

            if (fillPercent >= 0.5 ) {
                fillPercent = 2 * fillPercent - 1;
                var R = fillPercent * 255 + (1 - fillPercent) * 249;
                var G = fillPercent * 0 + (1 - fillPercent) * 200;
                var B = fillPercent * 0 + (1 - fillPercent) * 2;
            }
            else {
                fillPercent = 2 * fillPercent;
                var R = fillPercent * 249 + (1 - fillPercent) * 169;
                var G = fillPercent * 200 + (1 - fillPercent) * 215;
                var B = fillPercent * 2 + (1 - fillPercent) * 11;
            }

            return "rgb(" + Math.round(R) + "," + Math.round(G) + "," + Math.round(B) + ")"
        }

		function createhGauge()
		{
			width = gaugeElement.width();
            height = 160;
			height = 60 * self.getHeight();
			calculatedWidth = width * 0.60;
			
            var gaugeWidth = calculatedWidth;
            var gaugeHeight = height * 0.40;
			
			var gaugeTop = height * 0.10;
			
			fillindex = _.isUndefined(currentSettings.gaugeFillColor) ? 0: currentSettings.gaugeFillColor;
					
			backfill = gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor];

            paper = Raphael(gaugeElement.get()[0], width, height);
            paper.clear();
			
           //rect = paper.rec(x pos, y pos, width, height, radius)
            //var rect = paper.rect( 10, height / 3 - gaugeHeight / 2, gaugeWidth, gaugeHeight);
			var rect = paper.rect( 10, gaugeTop, gaugeWidth, gaugeHeight);
            rect.attr({
                "fill": backfill,
                "stroke": "#A6A3A3"
            });

            // place min and max labels
           // minValueLabel = paper.text(width / 2 - gaugeWidth / 2 - 8, height / 3, currentSettings.min_value);
          //  maxValueLabel = paper.text(width / 2 + gaugeWidth / 2 + 8, height / 3, currentSettings.max_value);
            minValueLabel = paper.text(10 + 10, gaugeTop + gaugeHeight + 10, currentSettings.min_value);
            maxValueLabel = paper.text( 10 + gaugeWidth - 10, gaugeTop + gaugeHeight + 10, currentSettings.max_value);

            minValueLabel.attr({
                "font-family": "arial",
                "font-size": "10",
                "fill": "#b3b3b3",
                "text-anchor": "end"
            });

            maxValueLabel.attr({
                "font-family": "arial",
                "font-size": "10",
                "fill": "#b3b3b3",
                "text-anchor": "start"
            });

            // place units and value
            var units = _.isUndefined(currentSettings.units) ? "": currentSettings.units;

            //valueText = paper.text(width / 2, height * 2 / 3, "");
            //unitsText = paper.text(width / 2, height * 2 / 3 + 20, units);

			//valueText = paper.text(gaugeWidth +50  , height  / 3, "");
            //unitsText = paper.text(gaugeWidth +50 ,  height  / 3 + 20, units);
			//valueText = paper.text(width -30  , height  / 3, "");
            //unitsText = paper.text(width -30 ,  height  / 3 + 20, units);	
			valueText = paper.text(width -35  , height  * 0.3 , "");
            unitsText = paper.text(width -35 ,  height  * 0.3 + 20, units);	
			
            valueText.attr({
                "font-family": "arial",
                "font-size": "25",
                "font-weight": "bold",
                "fill": "#d3d4d4",
				"text-align": "right",
                "text-anchor": "right"
            });

            unitsText.attr({
                "font-family": "arial",
                "font-size": "10",
                "font-weight": "normal",
                "fill": "#b3b3b3",
				"text-align": "right",
                "text-anchor": "right"
            });

            // fill to 0 percent
            //gaugeFill = paper.rect(width / 2 - gaugeWidth / 2, height / 3 - gaugeHeight / 2, 0, gaugeHeight);
			//gaugeFill = paper.rect(10, height / 3 - gaugeHeight / 2, 0, gaugeHeight);
			gaugeFill = paper.rect(10, gaugeTop, 0, gaugeHeight);
			
			gaugeFill.attr({
               // "fill": "#edebeb",
				"fill": backfill,
                "stroke":  "#A6A3A3"
            });
		}
		
        self.render = function (element) {
            $(element).append(titleElement.html(currentSettings.title)).append(gaugeElement);

           createhGauge();
        }

        self.onSettingsChanged = function (newSettings) {
            if (newSettings.units != currentSettings.units || newSettings.min_value != currentSettings.min_value || newSettings.max_value != currentSettings.max_value) {
                currentSettings = newSettings;
                var units = _.isUndefined(currentSettings.units) ? "": currentSettings.units;
                var min = _.isUndefined(currentSettings.min_value) ? 0: currentSettings.min_value;
                var max = _.isUndefined(currentSettings.max_value) ? 0: currentSettings.max_value;

                unitsText.attr({"text": units});
                minValueLabel.attr({"text": min});
                maxValueLabel.attr({"text": max});
            }
            else {
                currentSettings = newSettings;
            }

            titleElement.html(newSettings.title);
			
			 createhGauge();
        }

        self.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName === "value") {
                if (!_.isUndefined(gaugeFill) && !_.isUndefined(valueText)) {

                    newValue = _.isUndefined(newValue) ? 0: newValue;
					//var datavalue = newValue[0].value;
					var datavalue;
					
					if( newValue.constructor === Array)
					{
						if(newValue.length)
						{
							//datavalue = newValue[0].value;
							
							datavalue = "---";
							
							for(i=0; i< newValue.length; i++)
							{
								if(newValue[i].value != "---")
								{
									datavalue = newValue[i].value;
									
									break;
								}
							}
						

							if(datavalue != "---")
							{
					
								var fillVal = calculatedWidth * (datavalue - currentSettings.min_value)/(currentSettings.max_value - currentSettings.min_value);

								fillVal = fillVal > calculatedWidth ? calculatedWidth: fillVal;
								fillVal = fillVal < 0 ? 0: fillVal;
								
								var backfill = gaugeColors[_.isUndefined(currentSettings.gaugeBackColor) ? 11: currentSettings.gaugeBackColor];
								
								if(parseInt(fillindex) == 0)
									var fillColor = getColor(fillVal / calculatedHeight);
								else					
									var fillColor = gaugeFillColors[parseInt(fillindex)];	

								//gaugeFill.animate({"width": fillVal, "fill": fillColor, "stroke": fillColor}, 500, ">");
								gaugeFill.animate({"width": fillVal, "fill": fillColor, "stroke": "#A6A3A3"}, 500, ">");
								valueText.attr({"text": datavalue});
							}						
							else
								valueText.attr({"text": "---"});
						}
						else
							valueText.attr({"text": "---"});
					}
					else
						valueText.attr({"text": newValue});
                }
            }
        }

        self.onDispose = function () {
        }

        self.getHeight = function () {
          //  return 2;
		    return currentSettings.blocks;
        }

    };

    freeboard.loadWidgetPlugin({
        type_name: "horizontal-linear-gauge",
        display_name: "HelmSmart Horizontal Gauge",
        "external_scripts": [
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/raphael.2.1.0.min.js",
			"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/colormix.2.0.0.min.js"
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
                type: "number",
                default_value: 0
            },
            {
                name: "max_value",
                display_name: "Maximum",
                type: "number",
                default_value: 100
            },
			{
			name: "blocks",
			display_name: "Height (No. Blocks)",
			type: "text",
			default_value: 3
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
			} 
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new horzinalgaugeWidget(settings));
        }
    });	
	
	var gIndicatorID=0;
	
	freeboard.addStyle('@keyframes blink {   50% { border-color: #ff0000; } }');
    freeboard.addStyle('.indicator-light.interactive:hover', "box-shadow: 0px 0px 15px #FF9900; cursor: pointer;");
	freeboard.addStyle('.indicator-light', "border-radius:50%;width:22px;height:22px;border:2px solid #3d3d3d;margin-top:5px;float:left;background-color:#222;margin-right:10px;");

	freeboard.addStyle('.indicator-light.on', "background-color:#FFC773;box-shadow: 0px 0px 15px #FF9900;border-color:#FDF1DF; ");
	//freeboard.addStyle('.indicator-light.off', "background-color:#222;box-shadow: 0px 0px 15px #FF9900;border-color:#FDF1DF; ");
	freeboard.addStyle('.indicator-light.off', "background-color:#553607;box-shadow: 0px 0px 15px #D4840B;border-color:#CA9E5D; ");
	//freeboard.addStyle('.indicator-light.wait', "background-color:#FFC773;box-shadow: 0px 0px 15px #FF9900;border-color:#FDF1DF; animation: blink .5s step-end infinite alternate;");
	freeboard.addStyle('.indicator-light.wait', "border-color:#FDF1DF; animation: blink .5s step-end infinite alternate;");
	//freeboard.addStyle('.indicator-light.wait', "background-color:#DF5353;box-shadow: 0px 0px 15px #FF9900;border-color:#FDF1DF;");
	
	//freeboard.addStyle('.indicator-light.wait', "background-color:#DF5353;box-shadow: 0px 0px 15px #FF9900;border-color:#FDF1DF;");
	
	
	freeboard.addStyle('.indicator-text', "margin-top:10px;");
    var indicatorWidget = function (settings) {
        var self = this;
		
		var thisIndicatorID = "indicator-" + gIndicatorID++;
        var titleElement = $('<h2 class="section-title"></h2>');
        var stateElement = $('<div class="indicator-text"></div>');
        //var indicatorElement = $('<div class="indicator-light"></div>');
		var indicatorElement = $('<div class="indicator-light" id="' + thisIndicatorID + '"></div>');
		var indicatortextElement = $('<div class="indicator-text" id="' + thisIndicatorID + '"></div>');
		
        var currentSettings = settings;
        var isOn = false;
        var onText;
        var offText;
		var stateWaiting = false;
		var setState = false;
		var switchStates=[];
		var switchInstance=0;
		var gdisableIndicatorClick	= false;
		//var disableIndicatorClicks = [false,false,false,false,false,false]
		/*
		function flash($element, times) {
	  var colors = ['#fff', '#000'];
	  $element.css('background-color', colors[times % colors.length]);
	  if (times === 0) return;
	  setTimeout(function () {
		flash($element, times - 1);
		  }, 500);
		}
		*/
		
		
			function toHex(d) {
				return  ("0"+(Number(d).toString(16))).slice(-2).toUpperCase()
			}
			
		
			
			
			
			
        function updateState() {
            //indicatorElement.toggleClass("on", isOn);

			
				try {	
					if(indicatorElement.hasClass('wait')){
					indicatorElement.removeClass("wait")}
				}
				catch(err) {
				console.log("error object toString():");
				console.log("\t" + err.toString());
				};	
			
			
            if (isOn) {
				if(setState == true){
					
		
									
				gdisableIndicatorClick = false;}
					
				indicatorElement.removeClass("off")
				indicatorElement.addClass("on")
                stateElement.text((_.isUndefined(onText) ? (_.isUndefined(currentSettings.on_text) ? "": currentSettings.on_text): onText));
            }
            else {
				if(setState == false){
					
					
	
				gdisableIndicatorClick = false;}
					
				indicatorElement.addClass("off")
				indicatorElement.removeClass("on")
                stateElement.text((_.isUndefined(offText) ? (_.isUndefined(currentSettings.off_text) ? "": currentSettings.off_text): offText));
            }
        }

		
		var request;
		
		// send HTTP post to URL to activate switch
		this.sendValue = function (apikey, widgettype, switchid, new_val ) {
			    // freeboard.showDialog($("<div align='center'>send switch</div>"), "Status!", "OK", null, function () {
                //});
				
			if( widgettype == "switch")	
			{
				if(new_val == false)
				{
					switchvalue=0;
					setState = false;
					
				}
				else
				{
					switchvalue=1;
					setState = true;
					
				}
			

				var url = "https://helmsmart-freeboard.herokuapp.com/setswitchapi";
				url = url + "?deviceapikey=" + currentSettings.apikey;

				url = url + "&instance=" + switchInstance ;
				url = url + "&switchid=" + switchid ;
				url = url + "&switchvalue=" + switchvalue ;
			}	
			else if( widgettype == "dimmer")	
			{

					if(new_val >= 0 && new_val <= 100)
						dimmervalue=new_val;
					else
						dimmervalue=101;
	
			

				var url = "https://helmsmart-freeboard.herokuapp.com/setdimmerapi";
				url = url + "?deviceapikey=" + currentSettings.apikey;

				url = url + "&instance=" + switchInstance ;
				url = url + "&dimmerid=" + switchid ;
				url = url + "&dimmervalue=" + dimmervalue ;
			}	
			
			
			request = new XMLHttpRequest();
            if (!request) {
                console.log('Giving up:( Cannot create an XMLHTTP instance');
                return false;
            }
            request.onreadystatechange = this.alertContents;
            request.open('GET', url, true);
            freeboard.showLoadingIndicator(true);
            request.send();
			
			stateWaiting = true;
			gdisableIndicatorClick = true;
			//disableIndicatorClicks[switchid]=true;
			indicatorElement.addClass("wait");
				
		}
		
		
		
		this.alertContents = function () {
            if (request.readyState === XMLHttpRequest.DONE) {
                if (request.status === 200) {
                    console.log(request.responseText);
                    setTimeout(function () {
                        freeboard.showLoadingIndicator(false);
                        //freeboard.showDialog($("<div align='center'>Request response 200</div>"),"Success!","OK",null,function(){});
                    }, LOADING_INDICATOR_DELAY);
                } else {
                    console.log('There was a problem with the request.');
                    setTimeout(function () {
                        freeboard.showLoadingIndicator(false);
                        freeboard.showDialog($("<div align='center'>There was a problem with the request. Code " + request.status + request.responseText + " </div>"), "Error!", "OK", null, function () {
                        });
                    }, LOADING_INDICATOR_DELAY);
                }

            }

        }
		
			// handle mouse click on button 
		this.ondDlclick = function(element) {
            element.preventDefault();
			gdisableIndicatorClick = false;
			//disableIndicatorClicks = false;
			indicatorElement.removeClass("wait");
		}
		  
		// handle mouse click on button 
		this.onClick = function(element) {
            element.preventDefault()
			
			if (currentSettings.indicatortype == "switch")
			{
				if(gdisableIndicatorClick == false)
				{
					var new_val = !isOn
					var new_val_array = []
					new_val_array.push(new_val);
					
					//this.onCalculatedValueChanged('value', new_val_array);
					var apikey =  currentSettings.apikey;
					//var switchinstance = currentSettings.instance;
					var switchid = currentSettings.switchid;
					
					
					if (_.isUndefined(apikey))
						freeboard.showDialog($("<div align='center'>apikey undefined</div>"), "Error!", "OK", null, function () {
						});
					else {
						this.sendValue(apikey, currentSettings.indicatortype, switchid, new_val);
					}
				}
			}
			else if (currentSettings.indicatortype == "dimmer")
			{
				if(gdisableIndicatorClick == false)
				{
					var new_val = currentSettings.threshold
					//var new_val = !isOn
					var new_val_array = []
					new_val_array.push(new_val);
					
					//this.onCalculatedValueChanged('value', new_val_array);
					var apikey =  currentSettings.apikey;
					//var switchinstance = currentSettings.instance;
					var switchid = currentSettings.switchid;
					
					
					if (_.isUndefined(apikey))
						freeboard.showDialog($("<div align='center'>apikey undefined</div>"), "Error!", "OK", null, function () {
						});
					else {
						this.sendValue(apikey, currentSettings.indicatortype, switchid, new_val);
					}
				}
			}
			
			
        }
		
		
        this.render = function (element) {
            $(element).append(titleElement).append(indicatorElement).append(stateElement);
			$(indicatorElement).click(this.onClick.bind(this));
			$(indicatorElement).dblclick(this.ondDlclick.bind(this));
				indicatorElement.removeClass("on");
					indicatorElement.removeClass("off");
        }

        this.onSettingsChanged = function (newSettings) {
            currentSettings = newSettings;
            titleElement.html((_.isUndefined(newSettings.title) ? "": newSettings.title));
            updateState();
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName == "value") {
				if( newValue.constructor === Array)
				{
					if(newValue.length)
					{	
						if (currentSettings.indicatortype == "indicator_value")
						{

							var threshold = currentSettings.threshold
							var switchvalue = switchvalue = "---";
													
						
							for(i=0; i< newValue.length; i++)
							{
								if(newValue[i].value != "---")
								{
									switchvalue = newValue[i].value;
									break;
								}
							}
						
						
							if (currentSettings.indicatormode == "active_high_GT")
							{
								if(switchvalue > threshold)
								{
									
									isOn = true;
									updateState();
								}
								else
								{
									
									isOn = false;
									updateState();
								}
								
							}
							else if (currentSettings.indicatormode == "active_low_GT")
							{
								if(switchvalue > threshold)
								{
									
									isOn = false;
									updateState();
								}
								else 
								{
									
									isOn = true;
									updateState();
								}
								
							}
							else if (currentSettings.indicatormode == "active_high_LT")
							{
								if(switchvalue < threshold)
								{
									
									isOn = true;
									updateState();
								}
								else
								{
									
									isOn = false;
									updateState();
								}
								
							}
							else if (currentSettings.indicatormode == "active_low_LT")
							{
								if(switchvalue < threshold)
								{
									
									isOn = false;
									updateState();
								}
								else 
								{
									
									isOn = true;
									updateState();
								}
								
							}
							
						}
						else if (currentSettings.indicatortype == "dimmer")
						{

							var threshold = currentSettings.threshold
							var switchvalue = switchvalue = "---";
													
						
							for(i=0; i< newValue.length; i++)
							{
								if(newValue[i].value != "---")
								{
									switchvalue = newValue[i].value;
									break;
								}
							}
						
						
							if (currentSettings.indicatormode == "active_high_EQ")
							{
								if(switchvalue == threshold)
								{
									
									isOn = true;
									updateState();
								}
								else
								{
									
									isOn = false;
									updateState();
								}
								
							}
							else if (currentSettings.indicatormode == "active_low_EQ")
							{
								if(switchvalue == threshold)
								{
									
									isOn = false;
									updateState();
								}
								else 
								{
									
									isOn = true;
									updateState();
								}
								
							}
						}
						else
						{
							var switchid=currentSettings.switchid;
							switchStates = newValue[0];
					
							var switchvalue = switchStates[switchid]
					 
							if(switchvalue == 0)
							{
								switchInstance = switchStates[16];
								isOn = false;
								updateState();
							}
							else if(switchvalue == 1)
							{
								switchInstance = switchStates[16];
								isOn = true;
								updateState();
							}
							else
							{	indicatorElement.removeClass("on")
								indicatorElement.removeClass("off")
								
							}
						}
					}
					else
					{
						indicatorElement.removeClass("on")
						indicatorElement.removeClass("off")
					}
				}
			}
            //if (settingName == "on_text") {
            //    onText = newValue[0].value;
            //}
            //if (settingName == "off_text") {
            //    offText = newValue[0].value;
            //}

            //updateState();
        }

        this.onDispose = function () {
        }

        this.getHeight = function () {
            return 1;
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "indicator",
        display_name: "HelmSmart Array Indicator Light",
		description: "Indicator light for HelmSmart Status - uses HelmSmart Data source to grab selected span - plots first point in array",
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
	            name: "on_text",
	            display_name: "On Text",
	            type: "calculated"
	        },
	        {
	            name: "off_text",
	            display_name: "Off Text",
	            type: "calculated"
	        },
			 {
                name: "apikey",
                display_name: "API KEY",
                type: "text"
            },
			
			{
			"name": "indicatortype",
			"display_name": "Type",
			"type": "option",
			"default_value": "indicator",	
			"options": [
				{
					"name": "Indicator Value",
					"value": "indicator_value"
				}, 
				{
					"name": "Indicator Bank",
					"value": "indicator"
				}, 
				{
					"name": "Switch Bank",
					"value": "switch"
				}, 
				{
					"name": "Dimmer Zone",
					"value": "dimmer"
				}
				]
			},
			{
			"name": "indicatormode",
			"display_name": "Mode",
			"type": "option",
			"default_value": "active_low",	
			"options": [
				{
					"name": "Active Low - Less then ",
					"value": "active_low_LT"
				}, 
				{
					"name": "Active Low - Greater then ",
					"value": "active_low_GT"
				}, 
				{
					"name": "Active High - Less then ",
					"value": "active_high_LT"
				}, 
				{
					"name": "Active High - Greater then ",
					"value": "active_high_GT"
				}, 
				{
					"name": "Active High - equal to ",
					"value": "active_high_EQ"
				}, 
				{
					"name": "Active Low - equal to ",
					"value": "active_low_EQ"
				}

				]
			},
			{
				name: "threshold",
				display_name: "Threshold Value",
				type: "number",
				suffix: "",
				default_value: 0
			},
			{
			"name": "instance",
			"display_name": "Switch Bank Instance",
			"type": "option",
			"default_value": 0,	
			"options": [
			{
				"name": "0",
				"value": "0"
			}, 
			{
				"name": "1",
				"value": "1"
			}, 
			{
				"name": "2",
				"value": "2"
			}, 
			{
				"name": "3",
				"value": "3"
			},
			{
				"name": "4",
				"value": "4"
			},
			{
				"name": "5",
				"value": "5"
			},		
			{
				"name": "6",
				"value": "6"
			},
			{
				"name": "7",
				"value": "7"
			},
			{
				"name": "8",
				"value": "8"
			}]
			}, 
		
			{
			"name": "switchid",
			"display_name": "Switch ID",
			"type": "option",
			"default_value": 0,	
			"options": [
			{
				"name": "0",
				"value": "0"
			}, 
			{
				"name": "1",
				"value": "1"
			}, 
			{
				"name": "2",
				"value": "2"
			}, 
			{
				"name": "3",
				"value": "3"
			},
			{
				"name": "4",
				"value": "4"
			},
			{
				"name": "5",
				"value": "5"
			},		
			{
				"name": "6",
				"value": "6"
			},
			{
				"name": "7",
				"value": "7"
			},
			{
				"name": "8",
				"value": "8"
			},
			{
				"name": "9",
				"value": "9"
			},
			{
				"name": "10",
				"value": "10"
			}, 
			{
				"name": "11",
				"value": "11"
			}, 
			{
				"name": "12",
				"value": "12"
			}, 
			{
				"name": "13",
				"value": "13"
			},
			{
				"name": "14",
				"value": "14"
			},
			{
				"name": "15",
				"value": "15"
			},		
			
			]
		}, 
			
		
		
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new indicatorWidget(settings));
        }
    });

    freeboard.addStyle('.gm-style-cc a', "text-shadow:none;");


    var googleMapWidget = function (settings) {
        var self = this;
        var currentSettings = settings;
        var map;
        var marker;
		var markers = new Array();
		//var infowindows = new Array();
		var infoWindows = new Array();
        var currentPosition = {};
		var currentWind = {};
		var myLatlng;
		var myOldLatlng;
		
		
		var newpoly = new Array();
		var mypolyOptions = {
		   //strokeColor: '#B40B6A',
		   strokeColor: gaugeColors[_.isUndefined(currentSettings.trailColor) ? 5: currentSettings.trailColor],
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
		
		 function updatePositions(zone) {
            if (map && markers[zone] && currentPosition.lat && currentPosition.lon) {
                var newLatLon = new google.maps.LatLng(currentPosition.lat, currentPosition.lon);
                markers[zone].setPosition(newLatLon);
				
				if(currentWind)
				{
					
						var serieno = "zone" + zone + "label";
						var title = currentSettings[serieno];
					
					//markers[zone].set('labelContent', 'wind speed =' + currentWind.speed);
					var icon = markers[zone].getIcon();
					
					icon.rotation = Math.floor(currentWind.direction);
					icon.strokeColor = myStrokeColors[Math.floor(currentWind.speed * 2) & 0x7F];
					
					markers[zone].setIcon(icon);
					
				//	var label = markers[zone].getLabel();
				//	label.text = 'wind speed =' + currentWind.speed;
				//	markers[zone].setLabel(label);
				
					var TitleString = title + '\n' +
						  'Wind Speed = ' + currentWind.speed + '\n' +
						  'Wind Direction = ' + currentWind.direction;
				
					markers[zone].setTitle(TitleString)
					
					markers[zone].snippet = currentWind.speed + "\n" + currentWind.direction
				
				}
				
				
				var bounds = new google.maps.LatLngBounds();
	//var infowindow = new google.maps.InfoWindow();
				for (i = 0; i < MAX_NUM_ZONES; i++) {
					  //extend the bounds to include each marker's position
					
					if(markers[i])
					{
						if(markers[i].position)
						{
							bounds.extend(markers[i].position);
						}
					}
				}
				
               // map.panTo(newLatLon);
				
				//now fit the map to the newly inclusive bounds
				map.fitBounds(bounds);
				
				
				//newpoly[i] = new google.maps.Polyline(mypolyOptions);
				
				
            }
        }
		

        this.render = function (element) {
            function initializeMap() {
				
				        // Create a new StyledMapType object, passing it an array of styles,
        // and the name to be displayed on the map type control.
        var styledMapType = new google.maps.StyledMapType(
            [
				
								  {
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#1d2c4d"
									  }
									]
								  },
								  {
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#8ec3b9"
									  }
									]
								  },
								  {
									"elementType": "labels.text.stroke",
									"stylers": [
									  {
										"color": "#1a3646"
									  }
									]
								  },
								  {
									"featureType": "administrative.country",
									"elementType": "geometry.stroke",
									"stylers": [
									  {
										"color": "#4b6878"
									  }
									]
								  },
								  {
									"featureType": "administrative.land_parcel",
									"elementType": "labels",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "administrative.land_parcel",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#64779e"
									  }
									]
								  },
								  {
									"featureType": "administrative.province",
									"elementType": "geometry.stroke",
									"stylers": [
									  {
										"color": "#4b6878"
									  }
									]
								  },
								  {
									"featureType": "landscape.man_made",
									"elementType": "geometry.stroke",
									"stylers": [
									  {
										"color": "#334e87"
									  }
									]
								  },
								  {
									"featureType": "landscape.natural",
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#023e58"
									  }
									]
								  },
								  {
									"featureType": "poi",
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#283d6a"
									  }
									]
								  },
								  {
									"featureType": "poi",
									"elementType": "labels.text",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "poi",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#6f9ba5"
									  }
									]
								  },
								  {
									"featureType": "poi",
									"elementType": "labels.text.stroke",
									"stylers": [
									  {
										"color": "#1d2c4d"
									  }
									]
								  },
								  {
									"featureType": "poi.business",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "poi.park",
									"elementType": "geometry.fill",
									"stylers": [
									  {
										"color": "#023e58"
									  }
									]
								  },
								  {
									"featureType": "poi.park",
									"elementType": "labels.text",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "poi.park",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#3C7680"
									  }
									]
								  },
								  {
									"featureType": "road",
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#304a7d"
									  }
									]
								  },
								  {
									"featureType": "road",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#98a5be"
									  }
									]
								  },
								  {
									"featureType": "road",
									"elementType": "labels.text.stroke",
									"stylers": [
									  {
										"color": "#1d2c4d"
									  }
									]
								  },
								  {
									"featureType": "road.arterial",
									"elementType": "labels",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "road.highway",
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#2c6675"
									  }
									]
								  },
								  {
									"featureType": "road.highway",
									"elementType": "geometry.stroke",
									"stylers": [
									  {
										"color": "#255763"
									  }
									]
								  },
								  {
									"featureType": "road.highway",
									"elementType": "labels",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "road.highway",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#b0d5ce"
									  }
									]
								  },
								  {
									"featureType": "road.highway",
									"elementType": "labels.text.stroke",
									"stylers": [
									  {
										"color": "#023e58"
									  }
									]
								  },
								  {
									"featureType": "road.local",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "road.local",
									"elementType": "labels",
									"stylers": [
									  {
										"visibility": "off"
									  }
									]
								  },
								  {
									"featureType": "transit",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#98a5be"
									  }
									]
								  },
								  {
									"featureType": "transit",
									"elementType": "labels.text.stroke",
									"stylers": [
									  {
										"color": "#1d2c4d"
									  }
									]
								  },
								  {
									"featureType": "transit.line",
									"elementType": "geometry.fill",
									"stylers": [
									  {
										"color": "#283d6a"
									  }
									]
								  },
								  {
									"featureType": "transit.station",
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#3a4762"
									  }
									]
								  },
								  {
									"featureType": "water",
									"elementType": "geometry",
									"stylers": [
									  {
										"color": "#0e1626"
									  }
									]
								  },
								  {
									"featureType": "water",
									"elementType": "labels.text.fill",
									"stylers": [
									  {
										"color": "#4e6d70"
									  }
									]
								  }
				               ], 
							   
							   
                {name: 'Night Map'});
				  
				/*
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
				   */ 
             

              //  map = new google.maps.Map(element, mapOptions);
			 // Creation of Navionics NauticalChart Layer
//var navionicsNauticalChartOverlay = new JNC.Views.gNavionicsOverlay({
//    navKey:'Navionics_webapi_00313',
 //   chartType: JNC.Views.gNavionicsOverlay.CHARTS.NAUTICAL,
 //   isTransparent: false
//}); 
			   // Create a map object, and include the MapTypeId to add
        // to the map type control.
        map = new google.maps.Map(element, {
          center: {lat: -124.26833, lng: 42.05038},
          zoom: 11,
          mapTypeControlOptions: {
            mapTypeIds: ['roadmap', 'satellite', 'hybrid', 'terrain',
                    'styled_map']
          }
        });

        //Associate the styled map with the MapTypeId and set it to display.
        map.mapTypes.set('styled_map', styledMapType);
		//map.mapTypes.set(JNC.Views.gNavionicsOverlay.CHARTS.NAUTICAL, navionicsNauticalChartOverlay);

        //map.setMapTypeId('styled_map');
		//map.setMapTypeId('roadmap');
		map.setMapTypeId(_.isUndefined(currentSettings.mapstyle) ? 'roadmap': currentSettings.mapstyle);
				
			//}

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
				
				for (i = 0; i < MAX_NUM_ZONES; i++) {
					
					var datasource = currentSettings['zone' + i];
					
					if (datasource) {
						var serieno = "zone" + i + "label";
						var title = currentSettings[serieno];
						
						var serieclor = "zone" + i + "color";
						var iconcolor = currentSettings[serieclor];
						
						var contentString = '<font size="1"> ' +
						  '<p>Wind Speed = 2.4 </p>' +
						  '<p> Wind Direction = 4.4</p>'+
						'</font>';						
						
						var TitleString = 'Winchuck \n' +
						  'Wind Speed = 2.4\n' +
						  'Wind Direction = 4.4';
						
						//markers[i] = new google.maps.Marker({map: map, icon: {labelOrigin: { x: 12, y: -10}}, title: title, label: {text: "label " + i, color: '#222222', fontSize: '12px'}});
						//markers[i] = new google.maps.Marker({map: map,  title: title, label: {text: "label " + i, color: '#222222', fontSize: '12px'}});
						
						//markers[i] = new google.maps.Marker({map: map, icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 10, strokeColor: '#222288' , rotation: 30 }, title: title, snippet: "wind dir 230 speed 2.3", label: {text: "label " + i, color: '#222222', fontSize: '12px'}});
						
						//markers[i] = new google.maps.Marker({map: map, icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 10, strokeColor: '#222288' , rotation: 30 }, title: title, labelContent:contentString, label: {text: "label " + i, color: '#222222', fontSize: '12px'}});
	
						markers[i] = new google.maps.Marker({map: map, icon: { path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 10, strokeColor: '#222288' , rotation: 30 }, title: title });
			
						
						
						//markers[i] = new google.maps.Marker({map: map, icon: {labelOrigin: { x: 12, y: -10}}, title: title});
						
						//infowindows[i] = new google.maps.InfoWindow({ content: "<span>any html goes here zone=" + i +" </span>" });
						


						//infoWindows[i]  = new google.maps.InfoWindow();

						//infoWindows[i].setContent(contentString);
						
						// google.maps.event.addListener(marker, 'click', function() { myinfoWindow.open(map,marker); });
						
						//google.maps.event.addListener(markers[i], 'click', function() {   infoWindows[i].open(map,markers[i]); });
						
					}
					
					
					

					//updatePositions(i);
					
				}
				
				
            }

            if (window.google && window.google.maps) {
                initializeMap();
            }
            else {
                window.gmap_initialize = initializeMap;
                //head.js("https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false&callback=gmap_initialize");
				  head.js("https://maps.googleapis.com/maps/api/js?v=3&key=AIzaSyCE0JHB4u3xqbBndHV4RFTa6oRfZrJzP8Y&callback=gmap_initialize");
            }
        }

        this.onSettingsChanged = function (newSettings) {
            currentSettings = newSettings;
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
			
			currentWind = {};
			
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
		 else if (settingName == "zone0") {
				 position = newValue[0];
				 currentPosition.lon = position.lng;
				 currentPosition.lat = position.lat;
				 
				 try {
				 currentWind.speed = position.truewindspeed;
				 currentWind.direction = position.truewinddir;
				}
				catch(err) { };
		
				updatePositions(0);
		
		}
		else if (settingName == "zone1") {
				 position = newValue[0];
				 currentPosition.lon = position.lng;
				 currentPosition.lat = position.lat;
				 
				 try {
				 currentWind.speed = position.truewindspeed;
				 currentWind.direction = position.truewinddir;
				}
				catch(err) { };
		
				updatePositions(1);
		
		}
		else if (settingName == "zone2") {
				 position = newValue[0];
				 currentPosition.lon = position.lng;
				 currentPosition.lat = position.lat;
		
				try {
				 currentWind.speed = position.truewindspeed;
				 currentWind.direction = position.truewinddir;
				}
				catch(err) { };
		
				updatePositions(2);
		
		}
		};

        this.onDispose = function () {
        }

        this.getHeight = function () {
           return 4;
			//return _.isUndefined(currentSettings.blocks) ? 4: currentSettings.blocks;
		    //return currentSettings.blocks;
       
        }

        this.onSettingsChanged(settings);
    };
	
	//create empty LatLngBounds object
	//var bounds = new google.maps.LatLngBounds();
	//var infowindow = new google.maps.InfoWindow();
	
	var GoogleMapsWidgetSettings = [
	
		{
                name: "position",
                display_name: "Position",
                type: "calculated"
        },
		
		{
			name: "blocks",
			display_name: "Height (No. Blocks)",
			type: "option",
			default_value: 4,
			options: [
			{
				"name": "0",
				"value": "1"
			}, 
			{
				"name": "1",
				"value": "1"
			}, 
			{
				"name": "2",
				"value": "2"
			}, 
			{
				"name": "3",
				"value": "3"
			},
			{
				"name": "4",
				"value": "4"
			},
			{
				"name": "5",
				"value": "5"
			},		
			{
				"name": "6",
				"value": "6"
			},
			{
				"name": "7",
				"value": "7"
			},
			{
				"name": "8",
				"value": "8"
			}]
		}, 
	{
                name: "mapstyle",
                display_name: "Map Style",
                type: "option",
                options: [
                    {
                        name: "Map",
                        value: "roadmap"
                    },
					{
                        name: "Sat",
                        value: "satellite"
                    },
                    {
                        name: "Hybrid",
                        value: "hybrid"
                    },
					{
                        name: "Terrain",
                        value: "terrain"
                    },
					{
                        name: "Night",
                        value: "styled_map"
                    }
                ]
            },
			
			// Java-0, Light Green-1,Bittersweet-2, Wild Blue Yonder-3, Pale Turquoise-4,Razzmatazz-5, Plum-6, Apple-7, Valencia-8, Neptune-9, Saffron-10, Default-11
			{
			"name": "trailColor",
			"display_name": "Trail Color",
			"type": "option",
			"options": [
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
			},
	
	
	

	
	];
	
		for (i = 0; i < MAX_NUM_ZONES; i++) {
		var dataSource = {
			"name": "zone" + i,
			"display_name": "Zone " + i + " - Datasource",
			"type": "calculated"
		};

		var xField = {
			"name": "zone" + i + "label",
			"display_name": "Zone " + i + " - Label",
			"type": "text",
		};

			// Java, Light Green,Bittersweet, Wild Blue Yonder, Pale Turquoise,Razzmatazz, Plum, Apple, Valencia, Neptune, Saffron
		var xColor = {
		"name": "zone" + i + "color",
		"display_name": "Zone " + i + " - Color",
		"type": "option",
		"options": [
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
		}; 
		
		
		
		GoogleMapsWidgetSettings.push(dataSource);
		GoogleMapsWidgetSettings.push(xField);
		GoogleMapsWidgetSettings.push(xColor);
	}
	
	
    freeboard.loadWidgetPlugin({
        type_name: "google_map",
        display_name: "HelmSmart Array Google Map",
		description: "Map with historical path from data point array - uses HelmSmart Data source to grab selected span",
        fill_size: true,

		settings: GoogleMapsWidgetSettings,
		/*
		
        settings: [

			{
                name: "position",
                display_name: "Position",
                type: "calculated"
            },

			{
			name: "blocks",
			display_name: "Height (No. Blocks)",
			type: "option",
			default_value: 4,
			options: [
			{
				"name": "0",
				"value": "1"
			}, 
			{
				"name": "1",
				"value": "1"
			}, 
			{
				"name": "2",
				"value": "2"
			}, 
			{
				"name": "3",
				"value": "3"
			},
			{
				"name": "4",
				"value": "4"
			},
			{
				"name": "5",
				"value": "5"
			},		
			{
				"name": "6",
				"value": "6"
			},
			{
				"name": "7",
				"value": "7"
			},
			{
				"name": "8",
				"value": "8"
			}]
		}, 
		// mapTypeIds: ['roadmap', 'satellite', 'hybrid', 'terrain',  'styled_map']
		 {
                name: "mapstyle",
                display_name: "Map Style",
                type: "option",
                options: [
                    {
                        name: "Map",
                        value: "roadmap"
                    },
					{
                        name: "Sat",
                        value: "satellite"
                    },
                    {
                        name: "Hybrid",
                        value: "hybrid"
                    },
					{
                        name: "Terrain",
                        value: "terrain"
                    },
					{
                        name: "Night",
                        value: "styled_map"
                    }
                ]
            },
			
					// Java-0, Light Green-1,Bittersweet-2, Wild Blue Yonder-3, Pale Turquoise-4,Razzmatazz-5, Plum-6, Apple-7, Valencia-8, Neptune-9, Saffron-10, Default-11
			{
			"name": "trailColor",
			"display_name": "Trail Color",
			"type": "option",
			"options": [
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
			},
			
        ],
		*/
		
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new googleMapWidget(settings));
        }
    });

    var pictureWidget = function(settings)
    {
        var self = this;
        var widgetElement;
        var timer;
        var imageURL;

        function stopTimer()
        {
            if(timer)
            {
                clearInterval(timer);
                timer = null;
            }
        }

        function updateImage()
        {
            if(widgetElement && imageURL)
            {
                var cacheBreakerURL = imageURL + (imageURL.indexOf("?") == -1 ? "?": "&") + Date.now();

                $(widgetElement).css({
                    "background-image":  "url(" + cacheBreakerURL + ")"
                });
            }
        }

        this.render = function(element)
        {
            $(element).css({
                width: "100%",
                height: "100%",
                "background-size": "cover",
                "background-position": "center"
            });

            widgetElement = element;
        }

        this.onSettingsChanged = function(newSettings)
        {
            stopTimer();

            if(newSettings.refresh && newSettings.refresh > 0)
            {
                timer = setInterval(updateImage, Number(newSettings.refresh) * 1000);
            }
        }

        this.onCalculatedValueChanged = function(settingName, newValue)
        {
            if(settingName == "src")
            {
				index = newValue[0].value;
				
				index = Math.floor(index/10);
			
                imageURL = "https://helmsmart-freeboard.herokuapp.com/static/plugins/images/Large_Compass_Rotating_Black_" + index +".jpg";
            }

            updateImage();
        }

        this.onDispose = function()
        {
            stopTimer();
        }

        this.getHeight = function()
        {
            return 4;
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        type_name: "hspicture",
        display_name: "HelmSmart Picture",
        fill_size: true,
        settings: [
            {
                name: "src",
                display_name: "Image URL",
                type: "calculated"
            },
            {
                "type": "number",
                "display_name": "Refresh every",
                "name": "refresh",
                "suffix": "seconds",
                "description":"Leave blank if the image doesn't need to be refreshed"
            }
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new pictureWidget(settings));
        }
    });
	
	 freeboard.addStyle('.hshtml-widget', "white-space:normal;width:100%;height:100%");

    var hshtmlWidget = function (settings) {
        var self = this;
        var htmlElement = $('<div class="hshtml-widget"></div>');
        var currentSettings = settings;

        this.render = function (element) {
            $(element).append(htmlElement);
        }

        this.onSettingsChanged = function (newSettings) {
            currentSettings = newSettings;
        }

        this.onCalculatedValueChanged = function (settingName, newValue) {
            if (settingName == "html") {
                htmlElement.html(newValue);
            }
        }

        this.onDispose = function () {
        }

        this.getHeight = function () {
            return Number(currentSettings.height);
        }

        this.onSettingsChanged(settings);
    };

    freeboard.loadWidgetPlugin({
        "type_name": "hshtml",
        "display_name": "HelmSmart HTML",
        "fill_size": true,
        "settings": [
            {
                "name": "html",
                "display_name": "HTML",
                "type": "calculated",
                "description": "Can be literal HTML, or javascript that outputs HTML."
            },
            {
                "name": "height",
                "display_name": "Height Blocks",
                "type": "number",
                "default_value": 4,
                "description": "A height block is around 60 pixels"
            }
        ],
        newInstance: function (settings, newInstanceCallback) {
            newInstanceCallback(new hshtmlWidget(settings));
        }
    });

}());
