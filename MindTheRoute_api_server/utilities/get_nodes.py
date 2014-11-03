'''
Created on 14/feb/2014

@author: Francesca Delfino
'''
from collections import defaultdict

from imposm.parser import OSMParser


def nodes_cb(nodes):
    print('Sono nella nodes_cb')
    for nid, lon, lat in nodes:
        if nid in data:
            print nid
            print type(nid)
            data[nid] = {'id': nid, 'lat': lat, 'lon': lon}

def ways_cb(ways):
    print('Sono nella ways_cb')
    for wid, tags, refs in ways:
        if 'highway' in tags:
            for ref in refs:
                if ref not in data:
                    data[ref] = 'ok'

if __name__ == '__main__':
    #osmFile = 'data/Pigneto-highways.osm'
    osmFile = './../../data/map.osm'
    data = defaultdict(dict)
    
    fdata = open('data.tsv', 'w')
    p = OSMParser(concurrency = 1, ways_callback = ways_cb)
    p.parse(osmFile)
    p = OSMParser(concurrency = 1, coords_callback = nodes_cb)
    p.parse(osmFile)
    
    print("Start writing on file")
    i = 0
    for k in data:
        i += 1
        v = data[k]
        if v == 'ok':
            s = 'id\t%s\tok\n' %(repr(k))
            fdata.write(s)
        else:
            r = 'id\t%s\tlat\t%s\tlon\t%s\n' %(str(k), str(v['lat']), str(v['lon']))
            fdata.write(r)
    fdata.close()
    print(i)
    print("Finished with %d nodes" %(i)) #197665 Nodes
    