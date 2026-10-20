"""
RDWorks V8 .rld writer (vector paths only).

Builds on two files saved by the target RDWorks install:
  empty.rld      an empty project            -> header + 256-color layer table
  one_rect.rld   one rectangle, default layer -> shape-block constants

Supports: lines and cubic Béziers, open/closed paths, per-layer speed, power,
mode (cut / scan / dot), output on/off, air on/off, scan interval, bidirectional.
See docs/FORMAT.md for the layout.

Coordinates: mm, x to the right, y UP, origin at the bed's bottom-left corner.
RDWorks displays them mirrored from the top-right machine origin:
    X_display = bed_w - x,  Y_display = bed_h - y
"""
import struct

TABLE_OFF = 0x191
REC = 0x26B            # layer table record
GROUP = 0x26D          # used-layer block (vector layers)
SEG = 74
MODES = {"scan": 0, "cut": 1, "dot": 2}

# offsets inside a layer record (from its COLORREF)
F_OUTPUT, F_SPEED, F_AIR, F_MODE, F_BIDIR, F_INTERVAL = 0x04, 0x08, 0x30, 0x124, 0x134, 0x135


class Template:
    def __init__(self, empty_path, one_rect_path):
        e = open(empty_path, "rb").read()
        r = open(one_rect_path, "rb").read()
        assert e[1:16] == b"RDFILEVER8.0.01", "not an RDWorks V8 file"
        self.sec = 0x449C3 + (e[0xFE] - 1)          # header holds a Pascal string at 0xFE
        assert struct.unpack_from("<I", e, self.sec)[0] == 0, "template must be an empty project"
        self.prefix = bytearray(e[:self.sec])
        self.trailer = e[self.sec + 8:]
        assert len(self.trailer) == 48
        self.bed = struct.unpack_from("<2d", e, 0x14)
        rsec = 0x449C3 + (r[0xFE] - 1)
        ob = rsec + 4 + GROUP + 4
        self.shape_head = r[ob:ob + 5]
        seg0 = ob + 53
        assert struct.unpack_from("<H", r, seg0)[0] == 0, "one_rect sample must be a plain rectangle"
        self.line_tag = r[seg0 + 2:seg0 + 6]
        self.line_junk = r[seg0 + 38:seg0 + 70]
        self.line_end = r[seg0 + 70:seg0 + 74]
        self.shape_tail = r[seg0 + 4 * SEG:len(r) - 48]
        assert len(self.shape_tail) == 188
        self.curve_tag = b"\x19\x00\x0c\x62"      # constant in all curve samples so far

    def color(self, idx):
        o = TABLE_OFF + idx * REC
        return bytes(self.prefix[o:o + 4])


def _layer_patch(buf, o, L):
    buf[o + F_OUTPUT] = 1 if L.get("output", True) else 0
    struct.pack_into("<5d", buf, o + F_SPEED, float(L["speed"]), float(L["min"]), float(L["max"]),
                     float(L.get("min2", 30)), float(L.get("max2", 30)))
    buf[o + F_AIR] = 1 if L.get("air", True) else 0
    buf[o + F_MODE] = MODES[L["mode"]]
    if "bidir" in L:
        buf[o + F_BIDIR] = 1 if L["bidir"] else 0
    if "interval" in L:
        struct.pack_into("<d", buf, o + F_INTERVAL, float(L["interval"]))


def build(tpl, layers, shapes):
    """Layer membership is by color: each shape carries its layer's COLORREF.
    layers: dicts {palette, speed, min, max, mode, [output, air, bidir, interval]}
    in layer-list (= run) order.
    shapes: (layer_pos, segments, closed) where segments are
      ('L', (x1, y1, x2, y2))  or  ('C', (x0, y0, x3, y3, cx1, cy1, cx2, cy2)),
    or (layer_pos, [points], closed) for a plain polyline."""
    buf = bytearray(tpl.prefix)
    groups = []
    for L in layers:
        o = TABLE_OFF + L["palette"] * REC
        _layer_patch(buf, o, L)
        groups.append(b"\0\0\0\0" + bytes(buf[o:o + GROUP - 4]))
    out = buf
    out += struct.pack("<I", len(groups))
    for g in groups:
        out += g
    out += struct.pack("<I", len(shapes))
    for si, (lp, geom, closed) in enumerate(shapes):
        if geom and isinstance(geom[0][0], str):
            segs = list(geom)
        else:
            pts = list(geom)
            if closed and pts[0] == pts[-1]:
                pts = pts[:-1]
            segs = [("L", (*a, *b)) for a, b in zip(pts, pts[1:])]
            if closed:
                segs.append(("L", (*pts[-1], *pts[0])))
        xs, ys = [], []
        for kind, v in segs:
            xs += v[0::2]; ys += v[1::2]
        out += tpl.shape_head
        out += struct.pack("<I", si + 1)          # shape sequence number (not a layer ref)
        out += tpl.color(layers[lp]["palette"])
        out += struct.pack("<4d", min(xs), max(xs), min(ys), max(ys))
        out += struct.pack("<II", 1 if closed else 0, len(segs))
        n = len(segs)
        for i, (kind, v) in enumerate(segs):
            if kind == "L":
                out += b"\0\0" + tpl.line_tag + struct.pack("<4d", *v) + tpl.line_junk + tpl.line_end
            elif kind == "C":
                has_prev = i > 0 or closed
                has_next = i < n - 1 or closed
                fp = 2 if has_prev and segs[(i - 1) % n][0] == "C" else 0
                fn = 2 if has_next and segs[(i + 1) % n][0] == "C" else 0
                out += b"\x03\x00" + tpl.curve_tag + struct.pack("<8d", *v) + struct.pack("<HH", fp, fn)
            else:
                raise ValueError(kind)
        out += tpl.shape_tail
    out += tpl.trailer
    return bytes(out)
