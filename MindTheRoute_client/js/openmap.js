/* OpenMap script */
//var bikeip = '10.16.2.7:8000'; // ip dipartimento
//var bikeip = '192.168.1.129:8000'; // ip casa Igor
var bikeip = 'localhost:8000';
var zoom = 18;
var lat = "";
var lon = "";
var currentPos = "";

// The map object
var map = new OpenLayers.Map("map", {
	controls:[
	          new OpenLayers.Control.Navigation(),
	          new OpenLayers.Control.Attribution()
	          ],
	numZoomLevels: 19,
	units: 'm',
	projection: new OpenLayers.Projection("EPSG:3857"),
	displayProjection: new OpenLayers.Projection("EPSG:4326")
});

// The map layers
var mapnik = new OpenLayers.Layer.OSM("OpenStreetMap (Mapnik)");
map.addLayer(mapnik);
var layerMarkers = new OpenLayers.Layer.Markers( "Markers" );
var layerMarkersPath = new OpenLayers.Layer.Markers( "Markers" );
map.addLayer(layerMarkers);
map.addLayer(layerMarkersPath);

//Geolocalization of start position for the map
var output = document.getElementById("out");

if (!navigator.geolocation){
	output.innerHTML = "<p>Geolocation is not supported by your browser</p>";
}

function success(position) {
	lat = lat + position.coords.latitude;
	lon = lon + position.coords.longitude;
	var lonlat = new OpenLayers.LonLat(lon, lat)
	.transform(
			new OpenLayers.Projection("EPSG:4326"), // transform from WGS 1984
			map.getProjectionObject() // to Spherical Mercator Projection
		);
	map.setCenter(lonlat, zoom);
	
	var size = new OpenLayers.Size(21,25);
	var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
	var icon = new OpenLayers.Icon('img/pin.png',size,offset);
	layerMarkers.addMarker(new OpenLayers.Marker(lonlat,icon));
	
	// Searching for the street name of actual position
	uripos = "http://open.mapquestapi.com/nominatim/v1/reverse.php?format=json&lat="+lat+"&lon="+lon;
	$.getJSON(uripos, function(response) {
		$('#from').val(response.address.road);
		currentPos = currentPos + response.address.road;
	});
};
    
function error() {
    output.innerHTML = "Unable to retrieve your location";
};

navigator.geolocation.getCurrentPosition(success, error);
// Invert event
$('#invert').click(function() {
	from = $('#from').val();
	to = $('#to').val();
	$('#from').val(to);
	$('#to').val(from);
});

// Search submit event
var vector_layer = new OpenLayers.Layer.Vector("Route Layer");
$('#button_search').click(function() {
	var result = document.getElementById("result");
	result.innerHTML = "Addresses translation...";
		
	// Step 1: searching coordinates of the "from" address
	var a = $('#from').val().replace(/ /gi, "+");
	var uria = "http://maps.google.com/maps/api/geocode/json?address="+ a +"+roma&sensor=false";
	console.log(uria);
	
	$.ajax({
		url: uria,
		dataType: 'json',
		async: false,
		success: function(response) {
			if (response.results.length != 0) {
				for (var i = 0; i < response.results.length; i++) {
					if (response.results[i].address_components[2].long_name == "Roma") {
						if ($('#from').val() == currentPos) {
							fromLat = lat;
							fromLon = lon;
						}
						else {
							fromLat = response.results[i].geometry.location.lat;
							fromLon = response.results[i].geometry.location.lng;
						}
						break;
					}
				}
				// Step 2: searching coordinates of the "to" address
				var b = $('#to').val().replace(/ /gi, "+");
				var urib = "http://maps.google.com/maps/api/geocode/json?address="+ b +"+roma&sensor=false";
				console.log(urib);
				$.ajax({
					url: urib,
					dataType: 'json',
					async: false,
					success: function(response) {
						if (response.results.length != 0) {
							for (var i = 0; i < response.results.length; i++) {
								if (response.results[i].address_components[2].long_name == "Roma") {
									toLat = response.results[i].geometry.location.lat;
									toLon = response.results[i].geometry.location.lng;
									break;
								}
							}
							// Step 3: sending the request to calculate the route
							var mode = $('input[name=mode]:checked').val();
							var requri = 'http://'+bikeip+'/bike_api?format=jsonp&callback=?&start_lat='+fromLat+'&start_lon='+fromLon+'&end_lat='+toLat+'&end_lon='+toLon+'&mode='+mode;
							console.log(requri);
							result.innerHTML = "Route search...<br><img src = 'img/ajax-loader.gif'></img>";
							
							$.ajax({
								url: requri,
								type:'GET',
								dataType: 'jsonp',
								async: false,
								statusCode: {
									404: function() {
										result.innerHTML = 'Could not contact server.';
									},
									500: function() {
										result.innerHTML = 'A server-side error has occurred.';
									}
								},
								success: function(response) {
									l = [];
									ids = [];
									if (response != null) {
										for (var i = 0; i < response.nodes.length; i++) {
											l[i] = new OpenLayers.Geometry.Point(
													response.nodes[i].longitude,
													response.nodes[i].latitude).transform(
													new OpenLayers.Projection(
															"EPSG:4326"),
													map.getProjectionObject());
										}
										
										layerMarkersPath.clearMarkers();
										var startlonlat = new OpenLayers.LonLat(response.nodes[0].longitude,response.nodes[0].latitude)
													.transform(new OpenLayers.Projection("EPSG:4326"), // transform from WGS 1984
													map.getProjectionObject() // to Spherical Mercator Projection
										);
										var size = new OpenLayers.Size(20,34);
										var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
										var icon = new OpenLayers.Icon('img/dd-start.png',size,offset);
										layerMarkersPath.addMarker(new OpenLayers.Marker(startlonlat,icon));
										
										var endlonlat = new OpenLayers.LonLat(response.nodes[response.nodes.length-1].longitude,response.nodes[response.nodes.length-1].latitude)
										.transform(new OpenLayers.Projection("EPSG:4326"), // transform from WGS 1984
													map.getProjectionObject() // to Spherical Mercator Projection
										);
										var size = new OpenLayers.Size(20,34);
										var offset = new OpenLayers.Pixel(-(size.w/2), -size.h);
										var icon = new OpenLayers.Icon('img/dd-end.png',size,offset);
										layerMarkersPath.addMarker(new OpenLayers.Marker(endlonlat,icon));
										
										var style = {
											strokeColor : "green",
											strokeWidth : 5,
											strokeOpacity : 0.5
										};
										var line = new OpenLayers.Geometry.LineString(l);
										var lineFeature = new OpenLayers.Feature.Vector(line, null, style);
										vector_layer.destroyFeatures();
										vector_layer.addFeatures([lineFeature]);
										map.addLayer(vector_layer);
										map.panTo(startlonlat);
										
										// Adding source and destination names
										names = "<p>From " +$('#from').val()+ " go to:</p>";
										for (var i = 0; i < response.ways.length; i++) {
											ids[i] = response.ways[i].name;
											names = "<p>"+ names +(i+1)+". "+ response.ways[i].name +"</p>";
										}
										names = names + "<p>Finally you are arrived at " + $('#to').val()+"!</p>";
										result.innerHTML = names;
									}
									else result.innerHTML = "Nothing found... Try again!";
								}
							});
						}
						else {
							alert("Invalid destination address!");
						}
						
					}
				});
			}
			else {
				alert("Invalid source address!");
			}
			
		}
	});
	
});