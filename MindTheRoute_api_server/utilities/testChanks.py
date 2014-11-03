from itertools import izip

for n in range(0,24):
    filein = open("chunks/data_%02d.tsv" %n)
    fileout = open("elevs/elev_%02d.tsv" %n)
    for i,(inline, outline) in enumerate(izip(filein,fileout)):
        idin = inline.strip().split()[:6]
        idout = outline.strip().split()[:6]
        if idin != idout:
            print("file %d corrupted from line %d" % (n,i+1))
            fileout.seek(0)
            fileoutLines = fileout.readlines()[:i]
            open("elevs/elev_%02d.tsv" %n,"w").writelines(fileoutLines)
            break
        