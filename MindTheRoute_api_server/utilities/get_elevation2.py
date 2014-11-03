'''
Created on 14/feb/2014

@author: Francesca Delfino
'''
import simplejson
import time
import urllib2
import sys, fcntl

maxTimeout = 7
n = 1
proxyFileName = "prox.txt"

def getProxy():
    ips = open(proxyFileName,"r").readlines()
    if not ips or ips[0] == "":
        print("no ips")
        sys.exit()
    open(proxyFileName,"w").writelines(ips[1:])
    return ips[0].strip()
changeProxy = True
while True:
    if n == 80:
        print "COMPLETE!!!"
        break
    out = 'elevs/elev_%02d.tsv' %n
    try:
        fileout = open(out, 'r+')
    except:
        fileout = open(out, 'w+')
    try:
        fcntl.flock(fileout,fcntl.LOCK_EX| fcntl.LOCK_NB)
    except IOError:
        print("File %s already in processing"%out)
        n +=1
        continue
    
    fileinName = "chunks/data_%02d.tsv" %n
    filein = open(fileinName, 'r')
    complete = False
    while not complete:
        complete = True
        if changeProxy:
            proxy_support = urllib2.ProxyHandler({"http":getProxy()})
            opener = urllib2.build_opener(proxy_support)
            filein.seek(0)
            fileout.seek(0)
        changeProxy = False
 
        for i, line in enumerate(filein):
            datas = line.strip().split('\t')
            # print datas[1]
            if fileout.readline():
                continue
            lat = datas[3]
            lon = datas[5]
            print "parsing linea %d del file %s" %(i,fileinName)
            url = 'http://maps.googleapis.com/maps/api/elevation/json?locations=%s,%s&sensor=true' %(lat, lon)
#             print url
            time.sleep(0.1)
            timeout = True
            num = 0
            while timeout and num < maxTimeout:
                try:
                    response = simplejson.load(opener.open(url, timeout=2))
                    timeout = False
                except:
                    num += 1
                    print("riprovo - %d" %num)
                    time.sleep(0.2)
            if num == maxTimeout:
                print "Timeout exceeded -- set a new proxy" 
                complete = False
                changeProxy = True
                break
            if response['status'] != 'OK':
                print response['status']
                complete = False
                changeProxy = True
                break
            else:
                for res in response['results']:
                    s = 'id\t%s\tlat\t%s\tlon\t%s\telev\t%s\tresol\t%s\n' %(datas[1].replace('L', ''), lat, lon, str(res['elevation']), str(res['resolution']))
                    fileout.write(s)
            #go to for
        #go to while
    filein.close()
    fileout.close()
    print('File %s complete!'%out)
    n += 1
    # while complete end
#while true end
