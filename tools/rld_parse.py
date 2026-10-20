"""Generic .rld parser (V8) — walks layer blocks and shapes. Unknown shape kinds are
reported with their raw bytes rather than guessed."""
import struct, sys
SEC=0x449C3; G=0x26D; SEG=74
def d(b,o,n=1): return struct.unpack_from('<%dd'%n,b,o)
def parse(b, shape_tail=188, verbose=False):
    n=struct.unpack_from('<I',b,SEC)[0]; o=SEC+4
    layers=[]
    for i in range(n):
        g=b[o:o+G]; layers.append(dict(color=g[4:8].hex(), output=g[8], speed=d(g,12)[0], min=d(g,20)[0], max=d(g,28)[0],
             air=g[4+0x30], mode={0:'scan',1:'cut',2:'dot'}.get(g[4+0x124],g[4+0x124]), bidir=g[4+0x134], interval=d(g,4+0x135)[0]))
        o+=G
    m=struct.unpack_from('<I',b,o)[0]; o+=4
    shapes=[]
    for i in range(m):
        st=o; head=b[o:o+5]; lay=struct.unpack_from('<I',b,o+5)[0]; col=b[o+9:o+13].hex()
        bbox=d(b,o+13,4); a,ns=struct.unpack_from('<II',b,o+45); p=o+53
        segs=[]
        for k in range(ns):
            t=struct.unpack_from('<H',b,p)[0]
            if t==0: segs.append(('L',d(b,p+6,4)))
            elif t==3: segs.append(('C',d(b,p+6,8)))
            else: segs.append(('?%d'%t,b[p:p+SEG].hex()))
            p+=SEG
        shapes.append(dict(start=st,head=head.hex(),layer=lay,color=col,bbox=bbox,a=a,segs=segs,seg_end=p))
        o=p+shape_tail
    return layers,shapes,len(b)-o
if __name__=='__main__':
    for path in sys.argv[1:]:
        L,S,rest=parse(open(path,'rb').read())
        print(path, 'layers',len(L),'shapes',len(S),'rest',rest)
