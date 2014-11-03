import math as mt
import time
from itertools import izip

import graph_tool.all as gt
from imposm.parser import OSMParser
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
import bike_routing.models as model
from bike_routing.pathcompleter import completePath

__all__ = ['Graphmap']

class Visitor(gt.AStarVisitor):
    
    def __init__(self, target):
        self.target = target
     
    def edge_relaxed(self, e):
        if e.target() == self.target:
            raise gt.StopSearch()
 
class Distance:
    
    euclidean = 0
    effort = 0
    
    def __init__(self, euclidean = 0, effort = 0):
        self.euclidean = euclidean
        self.effort = effort
        
    def __iadd__(self, other):
        self.euclidean += other.euclidean
        self.effort += other.effort
        return self
        
class Graphmap:
    
    __LOG = "console"
    __EFFORT_CONST = 15
    __start = time.time()
    
    def __init__(self,osmMapFileName, elevationFileName):
        self.osmMapFileName = osmMapFileName
        self.elevationFileName = elevationFileName
        self.visitedNodes = dict()
        self.gr = gt.Graph() # the graph that model the map
        self.graphFileName = 'data/my_graph.xml.gz'
        self.errorLogFilName = 'errors.log'
        
    def __log(self,string, logTime = True):
        if self.__LOG == "console" :
            timeString = ""
            if logTime:
                interval = time.time()- self.__start
                timeString = " in %.3f seconds" %interval
                self.__start = time.time()
            print("[Graphmap] " + string + timeString)
    
    @staticmethod
    def __euclidean_dist(start_lat, start_long, end_lat, end_long):
        start_lat = mt.radians(start_lat) 
        start_long = mt.radians(start_long)    
        end_lat = mt.radians(end_lat)
        end_long = mt.radians(end_long)
        d_latt = end_lat - start_lat
        d_long = end_long - start_long
        a = mt.sin(d_latt/2)**2 + mt.cos(start_lat) * mt.cos(end_lat) * mt.sin(d_long/2)**2  
        c = 2 * mt.asin(mt.sqrt(a)) 
        return 6372795 * c

    def __get_distance(self, latSrc, lonSrc, elevSrc,latDst, lonDst, elevDst):
        "Return a Distance object of the two points src and dst"
        euclideanDist = Graphmap.__euclidean_dist(latSrc, lonSrc,latDst, lonDst)
        if euclideanDist == 0:
            return Distance(0,0)
        
        deltah = (elevDst - elevSrc)
        if deltah > euclideanDist:
            deltah = euclideanDist
            
        euclideanDist = mt.sqrt(euclideanDist**2 + deltah**2)
        if deltah <= 0:
            effortDist = euclideanDist 
        else:
            effortDist = euclideanDist + deltah*self.__EFFORT_CONST
            
        return Distance(euclideanDist, effortDist)

    def __osmid2graphid(self, osmid):
        return self.visitedNodes[osmid]
    def __is_visited(self, osmid):
        return osmid in self.visitedNodes
    def __set_visited(self, osmid, graphid):
        self.visitedNodes[osmid] = graphid
    
    def __ways_cb(self, ways):
        # callback method for waysToSave
        for wayid, tags, osmidsInTheWay in ways:
            if not 'highway' in tags:
                continue
            if tags["highway"] == 'platform':
                continue
            if "bicycle" in tags and tags["bicycle"] != "yes":
                continue
            if "motorroad" in tags and tags["motorroad"] != "no":
                continue
            if 'name' not in tags:
                tags['name'] = "Unknown"
            way = model.Way(id = wayid, name = tags['name'])
            self.waysToSave.append(way)
            for i, osmid in enumerate(osmidsInTheWay):
                if not self.__is_visited(osmid):
                    #save the new node into the graph  
                    newGraphid = int(self.gr.add_vertex())
                    self.__set_visited(osmid, newGraphid)
                node = model.Node(id = osmid)
                self.relationToSave.append(model.NodeWayRelation(node = node, way = way, position = i))
               
            for osmidSrc, osmidDst in izip(osmidsInTheWay,osmidsInTheWay[1:]):
                vertexSrc = self.gr.vertex(self.__osmid2graphid(osmidSrc))
                vertexDst = self.gr.vertex(self.__osmid2graphid(osmidDst))
                self.gr.add_edge(vertexSrc, vertexDst)
                self.gr.add_edge(vertexDst, vertexSrc)
        
    @transaction.commit_manually
    def __update_graphids(self,osmidProp):
        for vert in self.gr.vertices():
            model.Node.objects.filter(id=osmidProp[vert]).update(graphid = self.gr.vertex_index[vert]) 
        transaction.commit()
     
    def __get_cross(self, startingNode, nodeWayList,
                  outDist=Distance(), inDist=Distance()):
        oldlat, oldlon, oldElev = startingNode.latitude, startingNode.longitude, startingNode.elevation
        for nodeWay in nodeWayList:
            node = nodeWay.node
            outDist += self.__get_distance(oldlat, oldlon, oldElev, node.latitude, node.longitude, node.elevation)
            inDist += self.__get_distance(node.latitude, node.longitude, node.elevation, oldlat, oldlon, oldElev)
            oldlat, oldlon, oldElev = node.latitude, node.longitude, node.elevation
            if node.graphid != None:
                return node, outDist, inDist
        newNodeWay, newNodeWay2 = model.NodeWayRelation.objects.filter(node = nodeWayList[-1].node)
        if newNodeWay.way == nodeWayList[0].way:
            newNodeWay = newNodeWay2
        newNodeWayList = list(model.NodeWayRelation.objects.select_related('Node').filter(way=newNodeWay.way))
        return self.__get_cross(nodeWayList[-1].node,newNodeWayList, outDist, inDist)          
     
    def __insert_vertex(self, start):
        startNodeWayList = model.NodeWayRelation.objects.filter(node=start)
         
        if len(startNodeWayList) == 1:
            nodeWayList = list(model.NodeWayRelation.objects.select_related('Node').filter(way=startNodeWayList[0].way)) 
             
            startPos = startNodeWayList[0].position
            startNode = nodeWayList[startPos].node
                
            leftNodeWayList = list(reversed(nodeWayList[:startPos]))
            rightNodeWayList = nodeWayList[startPos + 1:]
        else:
            leftNodeWayList = list(model.NodeWayRelation.objects.select_related('Node').filter(way=startNodeWayList[0].way))
            rightNodeWayList = list(model.NodeWayRelation.objects.select_related('Node').filter(way=startNodeWayList[1].way))
            
            leftStartPos = startNodeWayList[0].position
            rightStartPos = startNodeWayList[1].position
            startNode = leftNodeWayList[leftStartPos].node
            
            if leftStartPos != 0: #because it is  either in 0 or in the last position
                leftNodeWayList.reverse()
            leftNodeWayList = leftNodeWayList[1:]
            if rightStartPos != 0:
                rightNodeWayList.reverse()
            rightNodeWayList = rightNodeWayList[1:]
        leftCross, leftOutDist, leftInDist = self.__get_cross(startNode, leftNodeWayList)
        rightCross, rightOutDist, rightInDist = self.__get_cross(startNode, rightNodeWayList)
        
        leftVertex = self.gr.vertex(leftCross.graphid) 
        rightVertex = self.gr.vertex(rightCross.graphid)
          
        newVertex = self.gr.add_vertex()
        self.gr.vertex_properties['osmid'][newVertex] = startNode.id
        
        rightOutEdge = self.gr.add_edge(newVertex,rightVertex)
        self.gr.edge_properties['euclidean'][rightOutEdge] = rightOutDist.euclidean
        self.gr.edge_properties['effort'][rightOutEdge] = rightOutDist.effort
        
        rightInEdge = self.gr.add_edge(rightVertex,newVertex)
        self.gr.edge_properties['euclidean'][rightInEdge] = rightInDist.euclidean
        self.gr.edge_properties['effort'][rightOutEdge] = rightOutDist.effort
         
        leftOutEdge = self.gr.add_edge(newVertex,leftVertex)
        self.gr.edge_properties['euclidean'][leftOutEdge] = leftOutDist.euclidean
        self.gr.edge_properties['effort'][rightOutEdge] = rightOutDist.effort
         
        leftInEdge = self.gr.add_edge(leftVertex,newVertex)
        self.gr.edge_properties['euclidean'][leftInEdge] = leftInDist.euclidean
        self.gr.edge_properties['effort'][rightOutEdge] = rightOutDist.effort
        return newVertex

    def __heuristic(self, v, target, euclidean):
        distance = self.__get_distance(
                            self.gr.vertex_properties['latitude'][v],
                            self.gr.vertex_properties['longitude'][v],
                            self.gr.vertex_properties['elevation'][v],
                            self.gr.vertex_properties['latitude'][target],
                            self.gr.vertex_properties['longitude'][target],
                            self.gr.vertex_properties['elevation'][target])
        if euclidean:
            return distance.euclidean
        return distance.effort
    
    def __getNode(self, lat, lon):
        try:
            return model.Node.objects.get(latitude=lat, longitude=lon)
        except ObjectDoesNotExist:
            
            delta = 0.0008
            nodes = model.Node.objects.filter(latitude__range = (lat - delta, lat + delta), 
                                              longitude__range = (lon - delta, lon + delta))
                
            def distance(n):
                d = self.__euclidean_dist(n.latitude, n.longitude, lat, lon)
                print "Distance of %s: %s" %(str(n.id), str(d))
                return d
                
            node = min([n for n in nodes], key=distance)
            return node

        
    def make_graph(self):
        self.__log("Start make_graph")
#         self.__resetDB()
#         self.__log("DB Reseted")
        # Property maps:
        latitudePM = self.gr.new_vertex_property('double')
        longitudePM = self.gr.new_vertex_property('double')
        elevationPM = self.gr.new_vertex_property('double')
        osmidPM = self.gr.new_vertex_property('long')
        effortPM = self.gr.new_edge_property('double')
        euclidPM = self.gr.new_edge_property('double')
        
        self.waysToSave = list()
        self.relationToSave = list()
        p = OSMParser( ways_callback=self.__ways_cb)
        p.parse(self.osmMapFileName)
        self.__log("Osm parsed")

        elevationFile = open(self.elevationFileName,'r')
        nodesToSave = list()
        for line in elevationFile:
            dataLine = line.strip().split('\t')
            osmid = int(dataLine[1])
            if not self.__is_visited(osmid): #this node isn't for bicycle traffic 
                continue
            lat = float(dataLine[3])
            lon = float(dataLine[5])
            elev = float(dataLine[7])
            nodesToSave.append(model.Node(id = osmid,latitude = lat,
                                          longitude = lon, elevation = elev))
            vertex = self.gr.vertex(self.__osmid2graphid(osmid))
            osmidPM[vertex] = osmid
            latitudePM[vertex] = lat
            longitudePM[vertex] = lon
            elevationPM[vertex] = elev
        self.__log("Elevation parsed")
        
        model.Way.objects.bulk_create(self.waysToSave)  
        model.Node.objects.bulk_create(nodesToSave)
        model.NodeWayRelation.objects.bulk_create(self.relationToSave)
        
        if len(self.visitedNodes) != len(nodesToSave):
            errorLogFile = open(self.errorLogFilName,'w')
            print("-------------  error!  -------------")
            errorLogFile.write("# of visitedNode %d, # of nodesToSave %d" %(len(self.visitedNodes), len(nodesToSave)))
            errorLogFile.write("Nodes in osmfile but not in elevation\n")
            for osmid in self.visitedNodes:
                if not model.Node.objects.filter(id=osmid).exists():
                    errorLogFile.write(str(osmid) + "\n")
            errorLogFile.close()
            

        del(nodesToSave)
        del(self.waysToSave)
        del(self.relationToSave)
        del(self.visitedNodes)
        self.__log("Data saved in the DB")

        # add the weight at each edge
        for (src,dst) in self.gr.edges():
            distance = self.__get_distance(
                latitudePM[src], longitudePM[src], elevationPM[src], 
                latitudePM[dst], longitudePM[dst], elevationPM[dst])
            effortPM[self.gr.edge(src,dst)] = distance.effort
            euclidPM[self.gr.edge(src,dst)] = distance.euclidean
            


        self.__log("Weights added at each edge")
        numVertBefore = self.gr.num_vertices()
        self.__log("Nodes before deleting: %d" %numVertBefore, logTime=False)
        toDeleteVertex = self.gr.new_vertex_property("bool")
        self.gr.set_vertex_filter(toDeleteVertex, inverted=True)
          
        for vert in self.gr.vertices():
            if vert.out_degree() == 2:
                if vert.in_degree() != 2:
                    self.__log("The graph is corrupted", logTime=False)
                ngb1, ngb2 = vert.out_neighbours()
                if not self.gr.edge(ngb1,ngb2):
                    edge1V = self.gr.edge(ngb1, vert)
                    edge2V = self.gr.edge(ngb2, vert)
                    edgeV1 = self.gr.edge(vert, ngb1)
                    edgeV2 = self.gr.edge(vert, ngb2)
                    
                    edge12 = self.gr.add_edge(ngb1, ngb2)
                    edge21 = self.gr.add_edge(ngb2, ngb1)
                    euclidPM[edge12] = euclidPM[edge1V] + euclidPM[edgeV2]
                    euclidPM[edge21] = euclidPM[edge2V] + euclidPM[edgeV1]
                    effortPM[edge12] = effortPM[edge1V] + effortPM[edgeV2]
                    effortPM[edge21] = effortPM[edge2V] + effortPM[edgeV1]
                    toDeleteVertex[vert] = True
                        
        self.__log("Nodes to delete selected")
        self.gr.purge_vertices()
        numVertAfter = self.gr.num_vertices()
        self.__log("%d nodes deleted" %(numVertBefore - numVertAfter))
        self.__log("Nodes after deleting: %d" %numVertAfter, logTime=False)
        self.__update_graphids(osmidPM)        
        self.__log("Ids of the graph updated in the DB")
        
        self.gr.edge_properties['euclidean'] = euclidPM
        self.gr.edge_properties['effort'] = effortPM
        self.gr.vertex_properties['osmid'] = osmidPM
        self.gr.vertex_properties['latitude'] = latitudePM
        self.gr.vertex_properties['longitude'] = longitudePM
        self.gr.vertex_properties['elevation'] = elevationPM      
        self.gr.save(self.graphFileName)
        self.__log("Graph Saved")

    def find_path(self, startLat, startLon, endLat, endLon, mode):
        self.__log("Find path request! ")
        if self.gr.num_vertices() == 0:
            self.gr.load(self.graphFileName)
            self.__log("Graph loaded")
        else:
            self.__log("Graph already in memory")
        
        start = self.__getNode(startLat,startLon)
        end = self.__getNode(endLat,endLon)
        
#         start = self.__getNode(41.8880107, 12.5219164)
#         end = self.__getNode(41.8887613, 12.5203503)
        
        if start.graphid != None:
            startAddedToGraph = False
            startVertex = self.gr.vertex(start.graphid)
        else: 
            startAddedToGraph= True
            startVertex = self.__insert_vertex(start)
         
        if end.graphid != None:
            endAddedToGraph = False
            endVertex = self.gr.vertex(end.graphid)
        else: 
            endAddedToGraph = True
            endVertex = self.__insert_vertex(end)           
        self.__log("Start = %d, end = %d  founds" %(start.id,end.id))
           
        if mode == "shortest":
            weightPropToUse = self.gr.edge_properties['euclidean']
            euclidean = True
        elif mode == "less_effort":
            weightPropToUse = self.gr.edge_properties['effort']
            euclidean = False
        else:
            self.__log("Mode unknown", logTime=False)
            return
            

        _, pred = gt.astar_search(self.gr, startVertex, 
                weightPropToUse,
                Visitor(endVertex),
                heuristic=lambda v: self.__heuristic(v, endVertex, euclidean))
        self.__log("A* terminated")
            
        if pred[endVertex] == int(endVertex):
            self.__log("Failed!!", logTime=False)
            return
        
        v = endVertex
        path = [self.gr.vertex_properties['osmid'][v]]
        while v != startVertex:
            v = self.gr.vertex(pred[v])
            path.append(self.gr.vertex_properties['osmid'][v])
        path = list(reversed(path))
        print path
        path = completePath(path)
        self.__log("Path completed")
        if endAddedToGraph:
            self.gr.clear_vertex(endVertex)
            self.gr.remove_vertex(endVertex)
        if startAddedToGraph:
            self.gr.clear_vertex(startVertex)
            self.gr.remove_vertex(startVertex)
        return path