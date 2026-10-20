#!/usr/bin/env python3
"""
Write the calibration set as RDWorks .rld projects, with every layer's speed,
power and mode already set.

    python3 make_rld.py <empty.rld> <one_rect.rld> [out_dir] [--y-down]

<empty.rld> and <one_rect.rld> are files saved from your own RDWorks (an empty
project, and one rectangle on the default layer). The machine's own header and
256-color layer table are reused, so only the layers this set uses change.

Coordinates: confirmed from batch-2 samples — x right, y up, origin bottom-left
of the bed; RDWorks shows them mirrored from the top-right machine origin.
"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_calibration as mc
from rldwriter import Template, build

MARGIN = 10.0                  # art placed this far from the top-right machine origin, mm

# Cut settings used where the SVG/DXF set says "use your grid result".
# Pre-filled from each material's grid centre (kerf) or its strongest cell
# (frame) — REPLACE with your measured values and re-run.
KERF_CUT = {3: (25, 55, 65), 4: (25, 55, 65), 5: (18, 65, 75),
            6: (9, 64, 74), 8: (6, 66, 74), 10: (4, 74, 82)}   # speed, min, max (plywood)


def frame_setting(rows_for_file):
    cells = [r for r in rows_for_file if r["purpose"].startswith("test cell")]
    if cells[0]["mode"] == "Fill":          # engrave coupons: frame = strongest cut of the wood 3-5 grid
        return 18, 75, 85
    sp = min(int(r["speed_mm_s"]) for r in cells)
    pw = max(int(r["max_power"]) for r in cells)
    return sp, max(10, pw - 10), pw


def merge_segments(items):
    """Join 2-point label strokes into polylines (fewer objects in RDWorks)."""
    out = []
    for ci, pts, closed in items:
        if (not closed and out and out[-1][0] == ci and not out[-1][2]
                and abs(out[-1][1][-1][0] - pts[0][0]) < 1e-9 and abs(out[-1][1][-1][1] - pts[0][1]) < 1e-9):
            out[-1][1].extend(pts[1:])
        else:
            out.append([ci, list(pts), closed])
    return out


def to_rld(d, rows_for_file, tpl, y_down):
    by_color = {int(r["color"][1:]): r for r in rows_for_file}
    order = sorted(d.layers, key=lambda ci: int(by_color[ci]["order"]))
    layers, pos = [], {}
    for k, ci in enumerate(order):
        r = by_color[ci]
        mode = "scan" if r["mode"] == "Fill" else "cut"
        if r["purpose"].startswith("outer frame"):
            sp, mn, mx = frame_setting(rows_for_file)
        elif d.name.startswith("09_") and ci != 0:
            sp, mn, mx = KERF_CUT[int(d.name.split("_")[-1].rstrip("m"))]
        elif d.name.startswith("09_"):
            sp, mx, mn = mc.LABEL_SET["wood"]          # label score on plywood
        else:
            sp, mn, mx = int(r["speed_mm_s"]), int(r["min_power"]), int(r["max_power"])
        L = dict(palette=k, speed=sp, min=mn, max=mx, mode=mode, output=True, air=True,
                 purpose=r["purpose"])
        if mode == "scan":
            L.update(interval=mc.FILL_INTERVAL, bidir=True)
        layers.append(L)
        pos[ci] = k
    x0, y0, x1, y1 = d.bounds()
    bw, bh = tpl.bed
    ox = bw - MARGIN - (x1 - x0)          # art's left edge
    oy = bh - MARGIN                      # art's top edge (y up)
    def tr(p):
        x = p[0] - x0 + ox
        y = (p[1] - y0 + oy - (y1 - y0)) if y_down else (oy - (p[1] - y0))
        return (round(x, 4), round(y, 4))
    shapes = [(pos[ci], [tr(p) for p in pts], closed) for ci, pts, closed in merge_segments(d.items)]
    # execution follows layer order; keep shapes grouped by layer
    shapes.sort(key=lambda s: s[0])
    return build(tpl, layers, shapes), layers


def orientation_check():
    d = mc.Drawing("00_orientation-check", "orientation")
    d.text(0, "TOP  F", 4, 14, 8.0)
    d.poly(0, [(4, 24), (40, 24)], closed=False)
    d.poly(0, [(34, 20), (40, 24), (34, 28)], closed=False)
    d.text(0, "RIGHT", 44, 27, 4.0)
    d.rect(1, 0, 0, 70, 34)
    d.layer(0, "text", "Line"); d.layer(1, "frame", "Line")
    rows = [dict(color="C00", order=1, mode="Line", speed_mm_s=400, min_power=8, max_power=10,
                 purpose="text — very light; only for checking orientation"),
            dict(color="C01", order=2, mode="Line", speed_mm_s=400, min_power=8, max_power=10,
                 purpose="frame — very light")]
    return d, rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    y_down = "--y-down" in sys.argv
    empty, one = args[0], args[1]
    out = args[2] if len(args) > 2 else "out_rld"
    os.makedirs(out, exist_ok=True)
    tpl = Template(empty, one)
    drawings, rows = mc.main(os.path.join(out, "_svgdxf_tmp"))
    jobs = [(d, [r for r in rows if r["file"] == d.name]) for d in drawings]
    jobs.insert(0, orientation_check())
    table = []
    for d, rr in jobs:
        data, layers = to_rld(d, rr, tpl, y_down)
        path = os.path.join(out, d.name + ".rld")
        open(path, "wb").write(data)
        for k, L in enumerate(layers):
            table.append(dict(file=d.name + ".rld", rdworks_layer=k, mode=L["mode"],
                              speed_mm_s=L["speed"], min_power=L["min"], max_power=L["max"],
                              purpose=L["purpose"]))
    with open(os.path.join(out, "rld_layers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader(); w.writerows(table)
    import shutil; shutil.rmtree(os.path.join(out, "_svgdxf_tmp"))
    print(f"wrote {len(jobs)} .rld files to {out}")


if __name__ == "__main__":
    main()
