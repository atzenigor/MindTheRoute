from bike_routing.models import Node, NodeWayRelation, Way
  
# function that return an ordered list containing all node positions from a to b 
def rangeList(a, b):
    if a < b:
        return range(a, b+1)
    else:
        return range(a, b-1, -1)

def getRightDirection(relations, dst):
    res = list()
    relations = list(relations)
    if len(relations) == 0:
        return None
    for rel in relations:
        if rel.node.id == dst:
            res.append(rel)
            return res
        elif rel.node.graphid != None:
            return None
        else:
            res.append(rel)
            lastNode = rel
    relOfLastNode = NodeWayRelation.objects.filter(node = lastNode.node.id)
    for wayOfLastNode in relOfLastNode:
        if wayOfLastNode.way.id == lastNode.way.id:
            continue
        else:
            nodesInWay = NodeWayRelation.objects.filter(way = wayOfLastNode.way.id)
            lastNodePos = nodesInWay.get(node = lastNode.node.id).position
            nodesInWay = list(nodesInWay)
            
            if lastNodePos == 0:
                again = getRightDirection(nodesInWay, dst)
            else:
                again = getRightDirection(reversed(nodesInWay), dst)
            
            if again == None:
                return None
            else:
                return res + again

def completePath(path):
    print "[PathCompleter] Start improving path"
    comps = list()
    allrelations = NodeWayRelation.objects
    prev = set() # set containing the previous incident street
    src_id = '' # id of the previous node
    
    for dst_id in path:
        print "From %s to %s" %(str(src_id), str(dst_id))
        actual = set()
        d_isinways = allrelations.filter(node = dst_id) # object containing all relations in which dst_id appears
        for w in d_isinways:
            actual.add(w.way.id) #set containing all ids of the ways in which dst_is appears   
        if len(prev) == 0:
            prev = actual
            src_id = dst_id
            
        else:
            intersection = prev.intersection(actual)
            
            if not intersection:
                print "No intersections"
                # For every way of src_id search shared nodes with a way of dst_id
                s_isinways = allrelations.filter(node = src_id) # object containing all relations in which src_id appears
                for ws in s_isinways:
                    nds = allrelations.filter(way = ws.way.id) # object containing all relations in which ws appears
                    src_pos = nds.get(node = src_id).position
                    ndsList = list(nds)
                    nodesInChoosenWay1 = getRightDirection(ndsList[src_pos+1:], dst_id)
                    if nodesInChoosenWay1 != None:
                        comps += nodesInChoosenWay1
                        break
                    nodesInChoosenWay2 = getRightDirection(reversed(ndsList[:src_pos]), dst_id)
                    if nodesInChoosenWay2 != None:
                        comps += nodesInChoosenWay2
                        break
            else:
                allIntersections = list() # list containing all possible intersections
                chooseWay = list() # list containing a possible intersection
                for rel in intersection:
                    way = allrelations.filter(way = rel)
                    totNodeInWay = way.count() 
                    # If the street is circular (same node at both starting and ending point)
                    # search the direction with less nodes inside
                    if way.get(position = 0).node.id == way.get(position = totNodeInWay - 1).node.id:
                        allIntersections = list() # list containing all possible intersections
                        chooseWay = list() # list containing a possible intersection
                        print("Circular way found")
                        a = way.filter(node = src_id).first().position
                        b = way.filter(node = dst_id).first().position
                        chooseWay = [way.get(position = i) for i in rangeList(a, b)]
                        allIntersections.append(chooseWay)
                        chooseWay = [way.get(position = i) for i in rangeList(a, totNodeInWay - 1)] + [way.get(position = i) for i in rangeList(0, b)]
                        allIntersections.append(chooseWay)
                    else:
                        # Creation of a node for each component of a street
                        a = way.filter(node = src_id).first().position
                        b = way.filter(node = dst_id).first().position
                        chooseWay = [way.get(position = i) for i in rangeList(a, b)]
                        allIntersections.append(chooseWay)
                comps += min(allIntersections, key = len)
            prev = actual
            src_id = dst_id
            
    print "[PathCompleter]Finish improving path"
    return [(n.node, n.way) for n in comps]