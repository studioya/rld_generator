def hexdump(b, start, n, base=0):
    for o in range(start, min(start+n, len(b)), 16):
        ch=b[o:o+16]
        print(f"{o+base:06x}  " + " ".join(f"{x:02x}" for x in ch).ljust(48) + "  " + "".join(chr(x) if 32<=x<127 else "." for x in ch))
def diffs(a, b):
    out=[]; i=0; n=min(len(a),len(b))
    while i<n:
        if a[i]!=b[i]:
            j=i
            while j<n and (a[j]!=b[j] or (j+1<n and a[j+1]!=b[j+1]) or (j+2<n and a[j+2]!=b[j+2])): j+=1
            out.append((i,j)); i=j
        else: i+=1
    return out
