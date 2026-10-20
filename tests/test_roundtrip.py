"""Rebuild every vector sample with src/rldwriter.py and compare to the original.
Bytes RDWorks fills with leftover memory are masked. Run:  python3 tests/test_roundtrip.py"""
import copy, glob, os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "src"), os.path.join(ROOT, "tools")]
import rldwriter as W, rld_parse as P

VECTOR = ["b00", "b01", "b02", "b03", "b04", "b05", "b06", "b07", "b08", "b10", "b11", "b12",
          "b21", "b22", "b23", "b24", "b26", "b27", "b29"]

def mask(b, shapes):
    b = bytearray(b)
    for sh in shapes:
        p = sh["start"] + 53
        for i, (k, _) in enumerate(sh["segs"]):
            q = p + i * 74
            b[q + 2:q + 6] = bytes(4)
            if k == "L":
                b[q + 38:q + 70] = bytes(32)
    return bytes(b)

def rebuild(path, tpl):
    b = open(path, "rb").read()
    sec = 0x449C3 + (b[0xFE] - 1)
    L, S, _ = P.parse(b)
    pal = [next(i for i in range(256) if b[0x191 + i * W.REC:0x195 + i * W.REC].hex() == g["color"]) for g in L]
    t = copy.copy(tpl); t.prefix = bytearray(b[:sec])
    layers = [dict(palette=p, speed=g["speed"], min=g["min"], max=g["max"], mode=g["mode"],
                   output=g["output"], air=g["air"], bidir=g["bidir"], interval=g["interval"],
                   min2=struct.unpack_from("<d", b, 0x191 + p * W.REC + 0x20)[0],
                   max2=struct.unpack_from("<d", b, 0x191 + p * W.REC + 0x28)[0]) for g, p in zip(L, pal)]
    pos = {g["color"]: i for i, g in enumerate(L)}
    out = W.build(t, layers, [(pos[s["color"]], s["segs"], bool(s["a"])) for s in S])
    return out == b, mask(out, P.parse(out)[1]) == mask(b, S)

if __name__ == "__main__":
    tpl = W.Template(os.path.join(ROOT, "samples/batch1/t1.rld"),
                     glob.glob(os.path.join(ROOT, "samples/batch2/b00_*.rld"))[0])
    files = {os.path.basename(p).split("_")[0].removesuffix(".rld"): p for p in glob.glob(os.path.join(ROOT, "samples/batch*/*.rld"))}
    fails = 0
    for k in VECTOR + ["t2", "t3", "t4", "t5", "t6"]:
        exact, masked = rebuild(files[k], tpl)
        fails += not masked
        print(f"{k:4} exact={exact!s:5} masked={masked}")
    print("FAIL" if fails else "PASS")
    sys.exit(1 if fails else 0)
