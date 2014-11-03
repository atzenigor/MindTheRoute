from rest_framework.decorators import api_view, renderer_classes
from rest_framework.response import Response
from rest_framework.renderers import JSONPRenderer,JSONRenderer
from django.utils import simplejson

from bike_routing.serializers import NodeSerializer, WaySerializer
from bike_routing.graphmaker import Graphmap

graphmap = Graphmap('data/map.osm','data/map_elevations.tsv')

@api_view(['GET'])
@renderer_classes((JSONRenderer, JSONPRenderer))
def bike_api(request):
    start_lat = float(request.QUERY_PARAMS['start_lat'])
    start_lon = float(request.QUERY_PARAMS['start_lon'])
    end_lat = float(request.QUERY_PARAMS['end_lat'])
    end_lon = float(request.QUERY_PARAMS['end_lon'])
    mode = request.QUERY_PARAMS['mode']
    path = graphmap.find_path(start_lat, start_lon, end_lat, end_lon, mode)
    if path:
        nodesPath = [nodeway[0] for nodeway in path]
        nodesPathSerialized = NodeSerializer(nodesPath, many=True).data
        
        allWaysPath = [nodeway[1] for nodeway in path]
        waysPath = list()
        waysPath.append(allWaysPath[0])
        for w in allWaysPath[1:]:
            if w.name != waysPath[-1].name and w.name != "Unknown":
                waysPath.append(w)
        waysPathSerialized = WaySerializer(waysPath, many=True).data
        
        json_data = {'nodes': nodesPathSerialized, 'ways': waysPathSerialized }
        
        return Response(json_data,content_type="application/json")
    return Response()

@api_view(['GET'])
def make_graph(request):
    graphmap.make_graph()
    return Response()