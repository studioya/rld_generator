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


def header_shift(b):
    """Bytes the header has grown/shrunk relative to the reference layout.
    The header holds the text tool's defaults: pstring text at 0xFE, then 42 fixed
    bytes, then pstring TrueType font (ref. length 8) and pstring SHX font (ref. 6)."""
    t = b[0xFE]
    fo = 0x129 + t
    f = b[fo]
    sh = b[fo + 1 + f]
    return (t - 1) + (f - 8) + (sh - 6)


BITMAP_SLOT = 256      # table record used for bitmap layers
BITMAP_BLOCK = 4 + 475


class Template:
    def __init__(self, empty_path, one_rect_path):
        e = open(empty_path, "rb").read()
        r = open(one_rect_path, "rb").read()
        assert e[1:16] == b"RDFILEVER8.0.01", "not an RDWorks V8 file"
        self.shift = header_shift(e)
        self.table = TABLE_OFF + self.shift
        self.sec = 0x449C3 + self.shift
        assert struct.unpack_from("<I", e, self.sec)[0] == 0, "template must be an empty project"
        self.prefix = bytearray(e[:self.sec])
        self.trailer = e[self.sec + 8:]
        assert len(self.trailer) == 48
        self.bed = struct.unpack_from("<2d", e, 0x14)
        rsec = 0x449C3 + header_shift(r)
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
        o = self.table + idx * REC
        return bytes(self.prefix[o:o + 4])


# Optional layer fields (offset from record start, kind). Names follow the RDWorks dialog.
OPTIONAL_FIELDS = {
    "power2_on":      (0x064, "b"),   # tick "2:" power row
    "speed_default":  (0x068, "b"),   # "Default" next to speed
    "power_default":  (0x06C, "b"),   # "Default" next to power
    "seal":           (0x18D, "d"),   # Seal, mm
    "close_delay":    (0x195, "d"),   # Close Delay, ms
    "open_delay":     (0x19D, "d"),   # Open Delay, ms
    "sew_comp":       (0x1A5, "b"),   # Advance… (seal) > Enable sew compensation
    "through_mode":   (0x1B3, "b"),   # Laser through mode
    "through_power1": (0x1B7, "d"),   # Through power 1, %
}


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
    for key, (off, kind) in OPTIONAL_FIELDS.items():
        if key in L:
            if kind == "d":
                struct.pack_into("<d", buf, o + off, float(L[key]))
            else:
                buf[o + off] = 1 if L[key] else 0


def build(tpl, layers, shapes):
    """Layer membership is by color: each shape carries its layer's COLORREF.
    layers: dicts {palette, speed, min, max, mode, [output, air, bidir, interval]}
    in layer-list (= run) order.
    shapes: (layer_pos, segments, closed) where segments are
      ('L', (x1, y1, x2, y2))  or  ('C', (x0, y0, x3, y3, cx1, cy1, cx2, cy2)),
    or (layer_pos, [points], closed) for a plain polyline."""
    buf = bytearray(tpl.prefix)
    groups, colors = [], []
    for L in layers:
        if L.get("bitmap"):
            o = tpl.table + BITMAP_SLOT * REC
            _layer_patch(buf, o, dict(L, mode=L.get("mode", "scan")))
            groups.append(b"\x01\x00\x01\x00" + bytes(buf[o:o + BITMAP_BLOCK - 4]))
        else:
            o = tpl.table + L["palette"] * REC
            _layer_patch(buf, o, L)
            groups.append(b"\0\0\0\0" + bytes(buf[o:o + GROUP - 4]))
        colors.append(bytes(buf[o:o + 4]))
    out = buf
    out += struct.pack("<I", len(groups))
    for g in groups:
        out += g
    out += struct.pack("<I", len(shapes))
    for si, (lp, geom, closed) in enumerate(shapes):
        if isinstance(geom, Bitmap):
            out += b"\x02\x00\x02\x00\x00" + struct.pack("<I", si + 1) + colors[lp]
            out += struct.pack("<4d", *geom.bbox) + geom.bmp
            out += struct.pack("<2d", *geom.center) + b"\0\0\0\0"
            continue
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
        out += colors[lp]
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


class Bitmap:
    """A bitmap object. `bmp` is a complete .bmp file (bytes); its pixels-per-metre
    fields set the size on the bed. Place it by its centre (mm, y up)."""
    def __init__(self, bmp, center):
        self.bmp = bytes(bmp)
        assert self.bmp[:2] == b"BM"
        w, h = struct.unpack_from("<ii", self.bmp, 18)
        ppm_x, ppm_y = struct.unpack_from("<ii", self.bmp, 38)
        wmm, hmm = abs(w) / ppm_x * 1000, abs(h) / ppm_y * 1000
        cx, cy = center
        self.center = (cx, cy)
        self.bbox = (cx - wmm / 2, cx + wmm / 2, cy - hmm / 2, cy + hmm / 2)

    @classmethod
    def from_image(cls, img, width_mm, center):
        """Grayscale 8-bit .bmp from a PIL image, scaled by resolution (pixels kept)."""
        import io
        g = img.convert("L")
        dpi = g.width / (width_mm / 25.4)
        buf = io.BytesIO()
        g.save(buf, format="BMP", dpi=(dpi, dpi))
        b = bytearray(buf.getvalue())
        ppm = round(g.width / width_mm * 1000)
        struct.pack_into("<ii", b, 38, ppm, ppm)
        struct.pack_into("<I", b, 50, 0)          # biClrImportant = 0, as RDWorks writes
        return cls(b, center)
