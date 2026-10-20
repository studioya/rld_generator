#!/usr/bin/env python3
"""
Ruida 150W CO2 calibration file generator — Bezalel Modelling Center.

Writes color-coded SVG + DXF test files (one color = one layer setting) and a
settings CSV that maps every color to its power/speed. Edit the RANGES / KERF
sections and re-run to regenerate.

    python3 make_calibration.py [output_dir]

Colors use the LightBurn C00–C29 palette so each color lands on its own
layer when imported into LightBurn. Labels are single-stroke (Hershey) vector
text on the C00 black layer, so they score as lines — no fonts needed.
"""
import csv, math, os, sys
from xml.sax.saxutils import escape
from functools import lru_cache
import ezdxf
from ezdxf import colors as ezc
from HersheyFonts import HersheyFonts

# ---------------------------------------------------------------- palette ---
# LightBurn default layer palette C00..C29
LB = ["000000", "0000FF", "FF0000", "00E000", "D0D000", "FF8000", "00E0E0",
      "FF00FF", "B4B4B4", "0000A0", "A00000", "00A000", "A0A000", "C08000",
      "00A0FF", "A000A0", "808080", "7D87B9", "BB7784", "4A6FE3", "D33F6A",
      "8CD78C", "F0B98D", "F6C4E1", "FA9ED4", "500A78", "B45A00", "004754",
      "86FA88", "FFDB66"]


def rgb(hexs):
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def _d2(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _nearest_lb(c):
    return min(range(len(LB)), key=lambda i: _d2(rgb(LB[i]), c))


@lru_cache(maxsize=None)
def nearest_aci(hexs):
    """Closest AutoCAD index color that still maps back to this same palette
    entry — so programs that ignore DXF true color keep the layers separate."""
    target = rgb(hexs)
    me = LB.index(hexs)
    cands = [i for i in range(1, 256) if _nearest_lb(tuple(ezc.aci2rgb(i))) == me]
    pool = cands or range(1, 256)
    return min(pool, key=lambda i: _d2(tuple(ezc.aci2rgb(i)), target))


# ------------------------------------------------------------ text helper ---
_font = HersheyFonts()
_font.load_default_font("futural")


def text_lines(s, x, y, h, anchor="left"):
    """Single-stroke text, cap height h (mm), baseline at y (y-down coords)."""
    _font.normalize_rendering(h / 0.75)          # futural caps ≈ 75% of em
    segs = list(_font.lines_for_text(s))
    if not segs:
        return []
    base = h / 0.75 * 0.25                        # baseline offset in em
    xs = [p[0] for seg in segs for p in seg]
    w = max(xs) - min(xs)
    dx = {"left": 0, "center": -w / 2, "right": -w}[anchor] - min(xs)
    out = []
    for (x1, y1), (x2, y2) in segs:
        out.append([(x + x1 + dx, y - (y1 - base)), (x + x2 + dx, y - (y2 - base))])
    return out


# --------------------------------------------------------------- drawing ----
class Drawing:
    def __init__(self, name, title):
        self.name, self.title = name, title
        self.layers = {}     # color index -> dict(name, mode, settings...)
        self.items = []      # (color index, points, closed)

    def layer(self, ci, label, mode, **settings):
        self.layers[ci] = dict(label=label, mode=mode, **settings)

    def poly(self, ci, pts, closed=True):
        self.items.append((ci, pts, closed))

    def rect(self, ci, x, y, w, h):
        self.poly(ci, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

    def circle(self, ci, cx, cy, r, n=72):
        self.poly(ci, [(cx + r * math.cos(2 * math.pi * k / n),
                        cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)])

    def text(self, ci, s, x, y, h, anchor="left"):
        for seg in text_lines(s, x, y, h, anchor):
            self.poly(ci, seg, closed=False)

    def bounds(self):
        xs = [p[0] for _, pts, _ in self.items for p in pts]
        ys = [p[1] for _, pts, _ in self.items for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    # ---- writers
    def write_svg(self, path):
        x0, y0, x1, y1 = self.bounds()
        m = 2
        W, H = x1 - x0 + 2 * m, y1 - y0 + 2 * m
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" '
               f'viewBox="{x0 - m:.3f} {y0 - m:.3f} {W:.3f} {H:.3f}">',
               f'<title>{escape(self.title)}</title>']
        for ci in sorted(self.layers):
            L = self.layers[ci]
            col = "#" + LB[ci]
            fill = col if L["mode"] == "Fill" else "none"
            out.append(f'<g id="C{ci:02d}" data-setting="{escape(L["label"])}" stroke="{col}" '
                       f'stroke-width="0.1" fill="{fill}" fill-rule="evenodd">')
            for c, pts, closed in self.items:
                if c != ci:
                    continue
                d = "M" + " L".join(f"{px:.3f},{py:.3f}" for px, py in pts) + (" Z" if closed else "")
                out.append(f'<path d="{d}"/>')
            out.append("</g>")
        out.append("</svg>")
        with open(path, "w") as f:
            f.write("\n".join(out))

    def write_dxf(self, path):
        doc = ezdxf.new("R2010", setup=False)
        doc.units = ezdxf.units.MM
        doc.header["$INSUNITS"] = 4
        msp = doc.modelspace()
        for ci, L in self.layers.items():
            lname = f"C{ci:02d}_{L['label']}".replace("/", "-").replace(" ", "_")[:60]
            lay = doc.layers.add(lname)
            lay.color = nearest_aci(LB[ci])
            lay.rgb = rgb(LB[ci])
            L["_dxf"] = lname
        for ci, pts, closed in self.items:
            L = self.layers[ci]
            e = msp.add_lwpolyline([(px, -py) for px, py in pts], close=closed,
                                   dxfattribs={"layer": L["_dxf"]})
            e.dxf.color = nearest_aci(LB[ci])
            e.rgb = rgb(LB[ci])
        doc.saveas(path)


# ------------------------------------------------------- shared settings ----
LABEL = 0                 # C00 black: labels (score)
FRAME = 29                # C29: outer frame (cut out the coupon)
TEST_COLORS = [c for c in range(1, 27) if c != 21]   # 5x5 matrix; C21 skipped (no clean DXF index-color match)

# label (score) settings per family: (speed mm/s, max%, min%)
LABEL_SET = {
    "thin":      (400, 10, 10),
    "cardboard": (300, 12, 10),
    "wood":      (200, 18, 12),
    "acrylic":   (200, 16, 12),
}

# ---------------------------------------------------------------- RANGES ----
# name, title, family, mode, powers (rows, %), speeds (cols, mm/s), cell
GRIDS = [
    ("01_cut_paper-textile-veneer", "CUT  paper / textile / veneer  <=1mm", "thin", "Line",
     [12, 15, 18, 22, 26], [100, 200, 300, 400, 500]),
    ("02_cut_cardboard", "CUT  cardboard / greyboard  1-4mm", "cardboard", "Line",
     [15, 20, 26, 33, 40], [30, 50, 80, 120, 180]),
    ("03_cut_wood_3-5mm", "CUT  plywood / MDF / solid wood  3-5mm", "wood", "Line",
     [45, 55, 65, 75, 85], [12, 18, 25, 32, 40]),
    ("04_cut_wood_6-10mm", "CUT  plywood 6-8mm / solid wood 6-10mm", "wood", "Line",
     [58, 66, 74, 82, 90], [4, 6, 9, 12, 16]),
    ("05_cut_acrylic_3-5mm", "CUT  cast acrylic  3-5mm", "acrylic", "Line",
     [45, 55, 65, 75, 85], [8, 12, 16, 22, 30]),
    ("06_cut_acrylic_6-8mm", "CUT  cast acrylic  6-8mm", "acrylic", "Line",
     [58, 66, 74, 82, 90], [3, 5, 7, 9, 12]),
    ("07_engrave_wood-acrylic-cardboard", "ENGRAVE  wood / ply / acrylic / cardboard", "wood", "Fill",
     [12, 18, 25, 35, 50], [150, 250, 350, 450, 550]),
    ("08_engrave_paper-textile-veneer", "ENGRAVE  paper / textile / veneer", "thin", "Fill",
     [10, 12, 15, 18, 22], [200, 300, 400, 500, 600]),
]

FILL_INTERVAL = 0.1       # mm line interval for Fill layers (254 DPI)


def min_power(p, mode):
    if mode == "Fill":
        return p
    return max(10, p - 10)


def make_grid(name, title, family, mode, powers, speeds, rows_out):
    d = Drawing(name, title)
    pitch, cell = 22.0, (12.0 if mode == "Line" else 16.0)
    left, top = 26.0, 30.0
    n = len(powers)
    W = left + pitch * len(speeds) + 4
    H = top + pitch * n + 10

    d.text(LABEL, title, 4, 9, 4.0)
    d.text(LABEL, "RUIDA 150W  BEZALEL", 4, 16, 2.5)
    d.text(LABEL, "SPEED mm/s", left + pitch * len(speeds) / 2, 22, 2.5, "center")
    d.text(LABEL, "PWR%", 4, top + 2, 2.5)
    for j, s in enumerate(speeds):
        d.text(LABEL, str(s), left + pitch * j + pitch / 2, top - 2, 3.0, "center")
    k = 0
    for i, p in enumerate(powers):
        y = top + pitch * i
        d.text(LABEL, str(p), left - 4, y + pitch / 2 + 1.5, 3.0, "right")
        for j, s in enumerate(speeds):
            ci = TEST_COLORS[k]; k += 1
            x = left + pitch * j + (pitch - cell) / 2
            d.rect(ci, x, y + (pitch - cell) / 2, cell, cell)
            d.layer(ci, f"P{p}_S{s}", mode, power=p, speed=s)
            rows_out.append(dict(file=name, color=f"C{ci:02d}", hex="#" + LB[ci], mode=mode,
                                 speed_mm_s=s, max_power=p, min_power=min_power(p, mode),
                                 interval_mm=FILL_INTERVAL if mode == "Fill" else "",
                                 bidirectional="yes" if mode == "Fill" else "",
                                 purpose=f"test cell  row P{p} / col S{s}", order=k + 1))
    ls, lmax, lmin = LABEL_SET[family]
    d.layer(LABEL, "labels_score", "Line", power=lmax, speed=ls)
    rows_out.append(dict(file=name, color="C00", hex="#000000", mode="Line", speed_mm_s=ls,
                         max_power=lmax, min_power=lmin, interval_mm="", bidirectional="",
                         purpose="labels — score; run FIRST", order=1))
    d.rect(FRAME, 0, 0, W, H)
    d.layer(FRAME, "frame_cut_last", "Line")
    rows_out.append(dict(file=name, color=f"C{FRAME:02d}", hex="#" + LB[FRAME], mode="Line",
                         speed_mm_s="known-good cut", max_power="known-good cut", min_power="",
                         interval_mm="", bidirectional="",
                         purpose="outer frame — your current cut setting; run LAST (optional)",
                         order=27))
    return d


# ------------------------------------------------------------- KERF / FIT ---
KERF_THICKNESSES = [3, 4, 5, 6, 8, 10]          # nominal sheet thickness, mm
SLOT_DELTAS = [-0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3]
KERF_SQUARE = 20.0


def make_kerf(t, rows_out):
    name = f"09_kerf-fit_{t}mm"
    d = Drawing(name, f"KERF + FIT  t={t}mm")
    INNER, OUTER = 2, 1                              # C02 red inner, C01 blue outer
    depth = max(10.0, 2 * t)
    gap = 8.0                                        # tooth width between slots
    widths = [t + dl for dl in SLOT_DELTAS]
    body_h = 42.0
    x = gap
    pts = [(0, 0)]
    slot_x = []
    for w in widths:
        pts += [(x, 0), (x, depth), (x + w, depth), (x + w, 0)]
        slot_x.append(x + w / 2)
        x += w + gap
    L = x
    pts += [(L, 0), (L, depth + body_h), (0, depth + body_h)]
    d.poly(OUTER, pts)
    # labels above each slot, inside the body
    for sx, dl in zip(slot_x, SLOT_DELTAS):
        d.text(LABEL, f"{dl:+.1f}".replace("+0.0", "0"), sx, depth + 6.5, 2.5, "center")
    d.text(LABEL, f"KERF + FIT   t={t}mm   slot = t + label", 4, depth + 14, 3.0)
    # kerf square (inner) with its labels
    sx0 = L - KERF_SQUARE - 6
    sy0 = depth + body_h - KERF_SQUARE - 4
    d.rect(INNER, sx0, sy0, KERF_SQUARE, KERF_SQUARE)
    d.text(LABEL, f"{KERF_SQUARE:.0f}", sx0 + KERF_SQUARE / 2, sy0 + KERF_SQUARE / 2 + 1.5,
           3.0, "center")
    d.text(LABEL, "kerf = (hole - square) / 2", 4, depth + 22, 2.5)
    d.text(LABEL, "slide strip into slots; tightest", 4, depth + 28, 2.5)
    d.text(LABEL, "slot that fits = your offset", 4, depth + 33, 2.5)
    # test strip (outer), below the comb
    sy = depth + body_h + 6
    d.rect(OUTER, 0, sy, 70, max(12.0, 2 * t))
    d.text(LABEL, f"TEST STRIP t={t}", 4, sy + max(12.0, 2 * t) / 2 + 1.5, 3.0)

    d.layer(LABEL, "labels_score", "Line")
    d.layer(INNER, "inner_cut_first", "Line")
    d.layer(OUTER, "outer_cut_last", "Line")
    for ci, mode, purpose, order in [(0, "Line", "labels — score; run FIRST", 1),
                                     (INNER, "Line", "kerf square — your cut setting; run SECOND", 2),
                                     (OUTER, "Line", "comb + strip outlines — same cut setting; run LAST", 3)]:
        rows_out.append(dict(file=name, color=f"C{ci:02d}", hex="#" + LB[ci], mode=mode,
                             speed_mm_s="from grid result" if ci else "light score",
                             max_power="from grid result" if ci else "see grid label",
                             min_power="", interval_mm="", bidirectional="",
                             purpose=purpose, order=order))
    return d


# ------------------------------------------------------------ SCAN OFFSET ---
SCAN_SPEEDS = [100, 150, 200, 250, 300, 350, 400, 450, 500, 600, 700]
SCAN_POWER = 20


def make_scan(rows_out):
    name = "10_scan-offset"
    d = Drawing(name, "SCAN OFFSET  bidirectional engrave")
    d.text(LABEL, "SCAN OFFSET  bidirectional fill", 4, 9, 4.0)
    d.text(LABEL, "look for doubled / jagged vertical edges", 4, 16, 2.5)
    top, rowh = 24.0, 14.0
    for i, s in enumerate(SCAN_SPEEDS):
        ci = i + 1
        y = top + i * rowh
        d.text(LABEL, f"{s}", 18, y + 7, 3.0, "right")
        # 6 vertical bars, 0.6mm .. 3mm wide, separated by 2mm gaps, + a wide block
        x = 22.0
        for w in [0.6, 1.0, 1.5, 2.0, 3.0]:
            d.rect(ci, x, y, w, 9)
            x += w + 2.0
        d.rect(ci, x + 1, y, 20, 9)
        # diamond — shows offset on diagonal edges
        cx = x + 32
        d.poly(ci, [(cx, y), (cx + 4.5, y + 4.5), (cx, y + 9), (cx - 4.5, y + 4.5)])
        d.layer(ci, f"scan_S{s}", "Fill", speed=s, power=SCAN_POWER)
        rows_out.append(dict(file=name, color=f"C{ci:02d}", hex="#" + LB[ci], mode="Fill",
                             speed_mm_s=s, max_power=SCAN_POWER, min_power=SCAN_POWER,
                             interval_mm=FILL_INTERVAL, bidirectional="yes",
                             purpose=f"scan row @ {s} mm/s — record offset in controller table",
                             order=ci + 1))
    d.text(LABEL, "mm/s", 18, top - 3, 2.5, "right")
    d.layer(LABEL, "labels_score", "Line")
    rows_out.append(dict(file=name, color="C00", hex="#000000", mode="Line", speed_mm_s=200,
                         max_power=16, min_power=12, interval_mm="", bidirectional="",
                         purpose="labels — score; run FIRST (any engrave-able scrap)", order=1))
    return d


# ------------------------------------------------------------------- main ---
def main(out):
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    os.makedirs(os.path.join(out, "dxf"), exist_ok=True)
    rows, drawings = [], []
    for g in GRIDS:
        drawings.append(make_grid(*g, rows))
    for t in KERF_THICKNESSES:
        drawings.append(make_kerf(t, rows))
    drawings.append(make_scan(rows))
    for d in drawings:
        d.write_svg(os.path.join(out, "svg", d.name + ".svg"))
        d.write_dxf(os.path.join(out, "dxf", d.name + ".dxf"))
    fields = ["file", "order", "color", "hex", "mode", "speed_mm_s", "max_power", "min_power",
              "interval_mm", "bidirectional", "purpose"]
    rows.sort(key=lambda r: (r["file"], r["order"]))
    with open(os.path.join(out, "layer_settings.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    return drawings, rows


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
