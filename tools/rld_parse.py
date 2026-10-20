"""
RDWorks V8 .rld parser — layers and all known object types
(1 path, 2 bitmap, 4 group, 5 text). See docs/FORMAT.md.

    python3 tools/rld_parse.py file.rld [...]      # summary
    python3 tools/rld_parse.py -v file.rld          # with layers and objects
"""
import struct, sys

TABLE_OFF, REC, GROUP, SEG, SEC0 = 0x191, 0x26B, 0x26D, 74, 0x449C3
BITMAP_BLOCK = 479
MODES = {0: "scan", 1: "cut", 2: "dot"}


def d(b, o, n=1):
    return struct.unpack_from("<%dd" % n, b, o)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def header_shift(b):
    t = b[0xFE]; fo = 0x129 + t; f = b[fo]; s = b[fo + 1 + f]
    return (t - 1) + (f - 8) + (s - 6)


def layer_fields(r):
    """r: bytes of a layer record starting at its COLORREF."""
    return dict(color=r[0:4].hex(), output=r[0x04], speed=d(r, 0x08)[0], min=d(r, 0x10)[0],
                max=d(r, 0x18)[0], min2=d(r, 0x20)[0], max2=d(r, 0x28)[0], air=r[0x30],
                power2_on=r[0x64], speed_default=r[0x68], power_default=r[0x6C],
                mode=MODES.get(r[0x124], r[0x124]), bidir=r[0x134], interval=d(r, 0x135)[0],
                seal=d(r, 0x18C)[0], close_delay=d(r, 0x195)[0], open_delay=d(r, 0x19D)[0],
                sew_comp=r[0x1A5], through_mode=r[0x1B3], through_power1=d(r, 0x1B7)[0])


def pstr(b, o):
    n = b[o]
    return b[o + 1:o + 1 + n], o + 1 + n


def parse_object(b, o):
    t = struct.unpack_from("<H", b, o)[0]
    if t == 5:                                    # text: settings block + children
        text, _ = pstr(b, o + 2)
        height = d(b, o + 3 + len(text))[0]
        # same layout as the header block at 0xFE: font pstring sits 0x2B + len(text)
        # bytes after the text pstring; SHX pstring follows it directly
        tl = len(text)
        font, p = pstr(b, o + 2 + 0x2B + tl)
        shx, p = pstr(b, p)
        end = o + 177 + (tl - 2) + (len(font) - 5) + (len(shx) - 6)   # 177 = block length for "AB", Arial, FS.SHX
        n = u32(b, end)
        q = end + 4; kids = []
        for _ in range(n):
            k, q = parse_object(b, q); kids.append(k)
        return dict(type="text", text=text.decode("latin-1"), font=font.decode("latin-1"),
                    shx=shx.decode("latin-1"), height=height, children=kids), q
    head = dict(seq=u32(b, o + 5), color=b[o + 9:o + 13].hex(), bbox=d(b, o + 13, 4))
    if t == 1:
        closed, ns = struct.unpack_from("<II", b, o + 45)
        p = o + 53; segs = []
        for _ in range(ns):
            ty = struct.unpack_from("<H", b, p)[0]
            if ty == 0: segs.append(("L", d(b, p + 6, 4)))
            elif ty == 3: segs.append(("C", d(b, p + 6, 8)))
            else: segs.append(("?%d" % ty, b[p:p + SEG].hex()))
            p += SEG
        return dict(type="path", closed=closed, segs=segs, start=o, **head), p + 188
    if t == 2:
        bm = o + 45
        size = u32(b, bm + 2)
        w, h = struct.unpack_from("<ii", b, bm + 18)
        bpp = struct.unpack_from("<H", b, bm + 28)[0]
        center = d(b, bm + size, 2)
        return dict(type="bitmap", px=(w, h), bpp=bpp, bmp=b[bm:bm + size], center=center, **head), bm + size + 20
    if t == 4:
        n = u32(b, o + 45); q = o + 49; kids = []
        for _ in range(n):
            k, q = parse_object(b, q); kids.append(k)
        return dict(type="group", children=kids, **head), q
    raise ValueError("unknown object type %d at %#x" % (t, o))


def parse(b):
    assert b[1:16] == b"RDFILEVER8.0.01", "not an RDWorks V8 file"
    sh = header_shift(b)
    table = TABLE_OFF + sh
    sec = SEC0 + sh
    hdr = dict(shift=sh, bed=d(b, 0x14, 2), table=table, sec=sec)
    n = u32(b, sec); o = sec + 4; layers = []
    for _ in range(n):
        pre = b[o:o + 4]
        bitmap = pre == b"\x01\x00\x01\x00"
        L = layer_fields(b[o + 4:o + 4 + REC] + bytes(REC))
        L["bitmap"] = bitmap
        layers.append(L)
        o += BITMAP_BLOCK if bitmap else GROUP
    m = u32(b, o); o += 4; objs = []
    for _ in range(m):
        ob, o = parse_object(b, o); objs.append(ob)
    return hdr, layers, objs, len(b) - o


def summary(path, verbose=False):
    hdr, layers, objs, rest = parse(open(path, "rb").read())
    kinds = {}
    def count(ob):
        kinds[ob["type"]] = kinds.get(ob["type"], 0) + 1
        for k in ob.get("children", []): count(k)
    for ob in objs: count(ob)
    print(f"{path}: layers {len(layers)} objects {len(objs)} {kinds} trailer {rest}{'' if rest == 48 else '  <-- UNEXPECTED'}")
    if verbose:
        for L in layers:
            print("   layer", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in L.items()})
        for ob in objs:
            print("   ", {k: v for k, v in ob.items() if k not in ("segs", "bmp", "children")})


if __name__ == "__main__":
    v = "-v" in sys.argv
    for p in [a for a in sys.argv[1:] if a != "-v"]:
        summary(p, v)
