// ┌────────────────────────────────────────────────────────────────────┐ \\
// │ freeboard-dynamic-highcharts-plugin                                │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ http://blog.onlinux.fr/dynamic-highcharts-plugin-for-freeboard-io/ │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Licensed under the MIT license.                                    │ \\
// ├────────────────────────────────────────────────────────────────────┤ \\
// │ Freeboard widget plugin for Highcharts.                            │ \\
// └────────────────────────────────────────────────────────────────────┘ \\
(function() {

	//
	// DECLARATIONS
	//
	var HIGHCHARTS_ID = 0;
	var ONE_SECOND_IN_MILIS = 1000;
	var MAX_NUM_SERIES = 3;

	//
	// HELPERS
	//

	// Get coordinates of point
	function xy(obj, x, y) {
		return [obj[x], obj[y]]
	}

	function isNumber(n) {
		return !isNaN(parseFloat(n)) && isFinite(n);
	}
	//
	// TIME SERIES CHARTS
	//
	var highchartsLineWidgetSettings = [
	{
                name: "showledgen",
                display_name: "Show Ledgen",
                type: "boolean",
                default_value: false
         },
		{
		"name": "blocks",
		"display_name": "Height (No. Blocks)",
		"type": "option",
		"default_value": 4,
		
		"options": [
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
		"name": "chartType",
		"display_name": "Chart Type",
		"type": "option",
		"options": [{
			"name": "Area",
			"value": "area"
		}, 
		{
			"name": "Stacked Area",
			"value": "stackedarea"
		}, 
		{
			"name": "Spline",
			"value": "spline"
		}]
	}, 
	
	{
		"name": "title",
		"display_name": "Title",
		"type": "text"
	}, {
		"name": "xaxis",
		"display_name": "X-Axis",
		"type": "calculated",
		"default_value": "{\"title\":{\"text\" : \"Time\"}, \"type\": \"datetime\", \"floor\":0}"
	}, {
		"name": "yaxis",
		"display_name": "Y-Axis",
		"type": "calculated",
		"default_value": "{\"title\":{\"text\" : \"Values\"}, \"minorTickInterval\":\"auto\", \"floor\":0}"
	}];

	for (i = 1; i <= MAX_NUM_SERIES; i++) {
		var dataSource = {
			"name": "series" + i,
			"display_name": "Series " + i + " - Datasource",
			"type": "calculated"
		};

		var xField = {
			"name": "series" + i + "label",
			"display_name": "Series " + i + " - Label",
			"type": "text",
		};

			// Java, Light Green,Bittersweet, Wild Blue Yonder, Pale Turquoise,Razzmatazz, Plum, Apple, Valencia, Neptune, Saffron
		var xColor = {
		"name": "series" + i + "color",
		"display_name": "Series " + i + " - Color",
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
		
		
		
		highchartsLineWidgetSettings.push(dataSource);
		highchartsLineWidgetSettings.push(xField);
		highchartsLineWidgetSettings.push(xColor);
	}

	freeboard
		.loadWidgetPlugin({
			"type_name": "highcharts-timeseries",
			"display_name": "HelmSmart Array HighChart",
			"description": "Time series charts using array of data points - uses HelmSmart Data source to grab selected span",
			"external_scripts": [
				//"https://code.highcharts.com/highcharts.js",
				//"https://code.highcharts.com/modules/exporting.js"
				//"plugins/thirdparty/highcharts.js",
				//"plugins/thirdparty/exporting.js"
				"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/highcharts.js",
				"https://helmsmart-freeboard.herokuapp.com/static/plugins/thirdparty/exporting.js"
			],
			"fill_size": true,
			"settings": highchartsLineWidgetSettings,
			newInstance: function(settings, newInstanceCallback) {
				newInstanceCallback(new highchartsTimeseriesWidgetPlugin(
					settings));
			}
		});

	var highchartsTimeseriesWidgetPlugin = function(settings) {

		var self = this;
		var currentSettings = settings;

		var thisWidgetId = "highcharts-widget-timeseries-" + HIGHCHARTS_ID++;
		var thisWidgetContainer = $('<div class="highcharts-widget" id="' + thisWidgetId + '"></div>');

		
		// Java, Light Green,Bittersweet, Wild Blue Yonder, Pale Turquoise,Razzmatazz, Plum, Apple, Valencia, Neptune, Saffron
		
		
		function createWidget() {

			Highcharts.theme = {
				global: {
					useUTC: true
				},
				colors: ["#2b908f", "#90ee7e", "#f45b5b", "#7798BF", "#aaeeee",
					"#ff0066", "#eeaaee", "#55BF3B", "#DF5353", "#76A5AF", "#F1C232"
				],
				chart: {
					backgroundColor: null,
					style: {
						fontFamily: "'Open Sans', sans-serif"
					},
					plotBorderColor: '#606063'
				},
				title: {
					style: {
						color: '#E0E0E3',
						fontSize: '20px'
					}
				},
				subtitle: {
					style: {
						color: '#E0E0E3',
						textTransform: 'uppercase'
					}
				},
				xAxis: {
					gridLineColor: '#707073',
					labels: {
						style: {
							color: '#E0E0E3'
						}
					},
					lineColor: '#707073',
					minorGridLineColor: '#505053',
					tickColor: '#707073',
					title: {
						style: {
							color: '#A0A0A3'

						}
					}
				},
				yAxis: {
					gridLineColor: '#707073',
					labels: {
						style: {
							color: '#E0E0E3'
						}
					},
					lineColor: '#707073',
					minorGridLineColor: '#505053',
					tickColor: '#707073',
					tickWidth: 1,
					title: {
						style: {
							color: '#A0A0A3'
						}
					}
				},
				tooltip: {
					backgroundColor: 'rgba(0, 0, 0, 0.85)',
					style: {
						color: '#F0F0F0'
					}
				},
				plotOptions: {
					series: {
						dataLabels: {
							color: '#B0B0B3'
						},
						marker: {
							lineColor: '#333'
						}
					},
					 
					boxplot: {
						fillColor: '#505053'
					},
					candlestick: {
						lineColor: 'white'
					},
					errorbar: {
						color: 'white'
					}
				},
				legend: {
					enabled: currentSettings.showledgen,
					itemStyle: {
						color: '#E0E0E3'
					},
					itemHoverStyle: {
						color: '#FFF'
					},
					itemHiddenStyle: {
						color: '#606063'
					}
				},
				credits: {
					style: {
						color: '#666'
					}
				},
				labels: {
					style: {
						color: '#707073'
					}
				},

				drilldown: {
					activeAxisLabelStyle: {
						color: '#F0F0F3'
					},
					activeDataLabelStyle: {
						color: '#F0F0F3'
					}
				},

				navigation: {
					buttonOptions: {
						symbolStroke: '#DDDDDD',
						theme: {
							fill: '#505053'
						}
					}
				},

				// scroll charts
				rangeSelector: {
					buttonTheme: {
						fill: '#505053',
						stroke: '#000000',
						style: {
							color: '#CCC'
						},
						states: {
							hover: {
								fill: '#707073',
								stroke: '#000000',
								style: {
									color: 'white'
								}
							},
							select: {
								fill: '#000003',
								stroke: '#000000',
								style: {
									color: 'white'
								}
							}
						}
					},
					inputBoxBorderColor: '#505053',
					inputStyle: {
						backgroundColor: '#333',
						color: 'silver'
					},
					labelStyle: {
						color: 'silver'
					}
				},

				navigator: {
					handles: {
						backgroundColor: '#666',
						borderColor: '#AAA'
					},
					outlineColor: '#CCC',
					maskFill: 'rgba(255,255,255,0.1)',
					series: {
						color: '#7798BF',
						lineColor: '#A6C7ED'
					},
					xAxis: {
						gridLineColor: '#505053'
					}
				},

				scrollbar: {
					barBackgroundColor: '#808083',
					barBorderColor: '#808083',
					buttonArrowColor: '#CCC',
					buttonBackgroundColor: '#606063',
					buttonBorderColor: '#606063',
					rifleColor: '#FFF',
					trackBackgroundColor: '#404043',
					trackBorderColor: '#404043'
				},

				// special colors for some of the
				legendBackgroundColor: 'rgba(0, 0, 0, 0.5)',
				background2: '#505053',
				dataLabelsColor: '#B0B0B3',
				textColor: '#C0C0C0',
				contrastTextColor: '#F0F0F3',
				maskColor: 'rgba(255,255,255,0.3)'
			};

			Highcharts.setOptions(Highcharts.theme);

			// Get widget configurations
			var thisWidgetXAxis = JSON.parse(currentSettings.xaxis);
			var thisWidgetYAxis = JSON.parse(currentSettings.yaxis);
			var thisWidgetTitle = currentSettings.title;
			var thisWidgetChartType = currentSettings.chartType;
			var thisWidgetChartStackedStyle = null;
			//console.log('chartType:' + currentSettings.chartType + ' ' + thisWidgetChartType);
			var thisWidgetSeries = [];
			
			if(thisWidgetChartType == "stackedarea")
			{
				thisWidgetChartType = "area";
				thisWidgetChartStackedStyle ="normal";
			}
			

			for (i = 1; i <= MAX_NUM_SERIES; i++) {
				var datasource = currentSettings['series' + i];
				
				if (datasource) {
					var serieno = "series" + i + "label";
					var label = currentSettings[serieno];
					console.log('label: ', label);
					var serieclor = "series" + i + "color";
					var chartcolor =parseInt(currentSettings[serieclor]);
					if(isNaN(chartcolor))
						chartcolor = 0
					
					var newSeries = {
						id: 'series' + i,
						name: label,
						lineColor : Highcharts.getOptions().colors[chartcolor],
						fillColor: {
							linearGradient: {
								x1: 0,
								y1: 0,
								x2: 0,
								y2: 1
							},
							stops: [
								//[0, Highcharts.getOptions().colors[chartcolor]],
								[0, Highcharts.Color(Highcharts.getOptions().colors[chartcolor]).setOpacity(90).get('rgba')],
								[1, Highcharts.Color(Highcharts.getOptions().colors[chartcolor]).setOpacity(0).get('rgba')]
							]
						},
						marker: {
							fillColor :Highcharts.Color(Highcharts.getOptions().colors[chartcolor]).setOpacity(80).get('rgba'),
						},

						data: [],
						connectNulls: true
					};
					
					thisWidgetSeries.push(newSeries);
				}
			}

			// Create widget
			thisWidgetContainer
				.css('height', 60 * self.getHeight() - 10 + 'px');
			thisWidgetContainer.css('width', '100%');

			thisWidgetContainer.highcharts({
				chart: {
					type: thisWidgetChartType,
					animation: Highcharts.svg,
					marginRight: 20
				},
				title: {
					text: thisWidgetTitle
				},
				xAxis: thisWidgetXAxis,
				yAxis: thisWidgetYAxis,

				plotOptions: {
					area: {
						stacking: thisWidgetChartStackedStyle,
						marker: {
							enabled: false,
							symbol: 'circle',
							radius: 2,
							hover: {
								enabled: true
							}
						},
						lineWidth: 2,
						states: {
							hover: {
								lineWidth: 2
							}
						},
						threshold: null
					}
				},

				tooltip: {
					formatter: function() {
						return '<b>' + this.series.name + '</b><br/>' + Highcharts.dateFormat('%Y-%m-%d %H:%M:%S',
							this.x) + '<br/>' + Highcharts.numberFormat(this.y, 1);
					}
				},
				series: thisWidgetSeries
			});
		}

		self.render = function(containerElement) {
			$(containerElement).append(thisWidgetContainer);
			createWidget();
		}

		self.getHeight = function() {
			return currentSettings.blocks;
		}

		self.onSettingsChanged = function(newSettings) {
			currentSettings = newSettings;
			createWidget();
		}

		self.onCalculatedValueChanged = function(settingName, newarrayValue) {
			// console.log(settingName, 'newValue:', newValue);
			var myDataArray =[];
			if( newarrayValue.constructor === Array)
			{
				if(newarrayValue.length)
				{
			
					
					// sort by value
						newarrayValue.sort(function (a, b) {
						  if (a.epoch > b.epoch) {
							return 1;
						  }
						  if (a.epoch < b.epoch) {
							return -1;
						  }
						  // a must be equal to b
						  return 0;
						});
					
					
					
					for(i=0; i< newarrayValue.length; i++)
					{
						myvalues=newarrayValue[i];
						// myvalue = myvalues.content
						 myvalue = myvalues.value;

						
						if (isNumber(myvalue)) { //check if it is a real number and not text
						var x = (new Date()).getTime();
						// console.log('addPoint:', x,currentSettings[seriesno], Number(newValue));
						var plotMqtt = [ myvalues.epoch, Number(myvalue)]; //create the array+ "Y"
						//myDataArray[i] = plotMqtt;
						myDataArray.push(plotMqtt);
						}
					}
				}
				
			}

			var chart = thisWidgetContainer.highcharts();
			var series = chart.get(settingName);
			if (series) {
				//var timeframeMS = currentSettings.timeframe * ONE_SECOND_IN_MILIS;
				//var seriesno = settingName;
				//var len = series.data.length;
				//var shift = false;

				/*
				// Check if it should shift the series
				if (series.data.length > 1) {

					var first = series.data[0].x;
					//var last = series.data[series.data.length-1].x;
					var last = new Date().getTime();
					// Check if time frame is complete
					var diff = last - first;
					//                                         console.log('last :', last);
					//                                         console.log('first:', first);
					//                                         console.log('diff :', diff);

					if (last - first > timeframeMS) {
						shift = true;
					}
				}

				if (isNumber(newValue)) { //check if it is a real number and not text
					var x = (new Date()).getTime();
					// console.log('addPoint:', x,currentSettings[seriesno], Number(newValue));
					var plotMqtt = [x, Number(newValue)]; //create the array+ "Y"
					series.addPoint(plotMqtt, true, shift);
				};
				*/
				
				series.setData(myDataArray);
				
				
				
			}
		}

		self.onDispose = function() {
			return;
		}
	}

}());