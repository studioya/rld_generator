# RDWorks `.rld` project file format (V8) — reverse-engineering notes

Decoded from samples saved by **RDWorks V8.01.24** (`RDFILEVER8.0.01`) on a
Ruida-controlled 150 W CO2 laser (1300 × 900 mm bed) at Bezalel Academy's
modelling center.

Confidence tags:
- **[confirmed]**: `src/rldwriter.py` rebuilds the sample files from this description
- **[observed]**: consistent across samples, but not exercised by the writer
- **[guess]**: inferred, unverified

Status: vector paths (lines and cubic Béziers, open and closed) and the main layer
parameters are **confirmed**. 19 of 19 vector samples in batch 2 rebuild. 14 match
byte-for-byte. The other 5 differ only in bytes RDWorks fills with leftover memory
(see *Memory junk*). Text, groups and bitmaps are **observed** only.

## General

- Little-endian. Numbers are IEEE-754 `double`. Counts and indices are `uint32`. [confirmed]
- Not compressed or encrypted. Roughly 80% of the bytes are zero. [confirmed]
- Saving an unchanged project gives a byte-identical file (b00 vs b01). [confirmed]
- Units: mm, mm/s, %. [confirmed]

### Coordinates [confirmed]

Stored coordinates use ordinary math axes: **x to the right, y up, origin at the
bed's bottom-left corner**. RDWorks *displays* positions from the machine origin at
the top-right:

```
X_display = bed_width  - x
Y_display = bed_height - y
```

(b00 at display X=100, Y=50 is stored centred on (1200, 850). Moving display X +100
moves x −100 (b02). Moving display Y +100 moves y −100 (b03).)

### Memory junk [observed]

Some fixed-size fields contain uninitialised memory: the 4-byte tag in every
segment record and the unused 32 bytes of a line segment. Their values differ
between RDWorks sessions and imports. RDWorks ignores them, as far as we can tell.

## Layout

| Offset | Size | Content |
|---|---|---|
| `0x000000` | variable | Header (contains Pascal strings, see below) |
| `0x000191` | 257 × 619 | Layer table: one record per palette color [confirmed] |
| … | … | Unknown region up to the object section [observed: constant across samples] |
| `SEC` | 4 | `N`: number of layers in use [confirmed] |
| … | N × 621 | Used-layer blocks [confirmed for vector layers] |
| … | 4 | `M`: number of top-level objects [confirmed] |
| … | variable | Objects [confirmed for paths] |
| end − 48 | 48 | Fixed trailer [confirmed] |

`SEC = 0x449C3 + (header[0xFE] − 1)`, because the Pascal string at `0xFE` moves
everything after it. In every sample so far the strings before `0xFE` have the same
length, so the layer table stays at `0x191`. [confirmed]

### Header (partial)

| Offset | Type | Value seen | Meaning |
|---|---|---|---|
| `0x00` | pstring | `RDFILEVER8.0.01` | 1-byte length + version [observed] |
| `0x14` | double | 1300.0 | bed width, mm [confirmed] |
| `0x1C` | double | 900.0 | bed height, mm [confirmed] |
| `0x72` | pstring | `cb ce cc e5` | default TrueType font name, GBK (宋体 SimSun) [observed] |
| `0x77` | pstring | `FS.SHX` | default SHX font [observed] |
| `0xFE` | pstring | `"AB"` after using the text tool, else 1 byte `ed` | last text-tool string [confirmed] |

### Layer record (619 bytes in the table, at `0x191 + i × 0x26B`)

The table holds every palette color with the settings it last had. An empty project
therefore carries the machine's whole layer history. Moving a shape onto a color
brings in that slot's stored settings, including *Is Output* (b04: palette 19 came
in with output = No).

Offsets are relative to the record start (its COLORREF).

| Rel. | Type | Dialog field | Values |
|---|---|---|---|
| `+0x000` | COLORREF | Layer (color) | R, G, B, 0 [confirmed] |
| `+0x004` | byte | Is Output | 1 yes / 0 no [confirmed, b11] |
| `+0x008` | double | Speed (mm/s) | [confirmed] |
| `+0x010` | double | Min Power 1 (%) | [confirmed] |
| `+0x018` | double | Max Power 1 (%) | [confirmed] |
| `+0x020` | double | Min Power 2 (%) | [observed] |
| `+0x028` | double | Max Power 2 (%) | [observed] |
| `+0x030` | byte | If Blowing (air) | 1 yes / 0 no [confirmed, b12] |
| `+0x124` | byte | Processing Mode | 0 scan / 1 cut / 2 dot [confirmed, b06 b10] |
| `+0x134` | byte | Scan: bidirectional ("x swing") | 1 swing / 0 unilateral [confirmed, b08] |
| `+0x135` | double | Scan: interval (mm) | default 0.2 here [confirmed, b07] |
| ? | | Seal, Open/Close Delay, Laser through mode, Through power 1–6, power 3–6 enables | not yet located |

Palette: index 0 black, 1 blue, 2 red, 3 green, 5 yellow; 256 entries. [observed]

### Used-layer block (621 bytes, vector layers)

`00 00 00 00` + the first 617 bytes of that color's table record. Blocks are
written in **layer-list order** (b05: red moved above black is written first).
This order is the run order. [confirmed]

When the layer holds a bitmap, the first 4 bytes are `01 00 01 00` and the block is
shorter (478 bytes in b31/b32), with a different internal layout. **Open question.**

## Objects

Every object starts with a 45-byte common header:

| Size | Field |
|---|---|
| 2 | object type: `1` path, `2` bitmap, `4` group, `5` text [observed] |
| 2 | repeat of type [observed] |
| 1 | `00` |
| 4 | uint32 **sequence number**, 1-based, in file order. *Not* a layer index [confirmed, b05 b27] |
| 4 | COLORREF: **this is what assigns the object to a layer** [confirmed] |
| 32 | bbox: xmin, xmax, ymin, ymax [confirmed] |

### Type 1: path [confirmed]

| Size | Field |
|---|---|
| 45 | common header |
| 4 | uint32 closed flag: 1 closed, 0 open |
| 4 | uint32 `nseg` |
| nseg × 74 | segment records |
| 188 | constant path trailer (contains 5.0, 45.0, 10.0, 45.0 twice; meaning unknown) |

A closed path still lists its closing segment explicitly.

**Segment record (74 bytes):**

| Offset | Size | Line (type 0) | Cubic Bézier (type 3) |
|---|---|---|---|
| 0 | 2 | `00 00` | `03 00` |
| 2 | 4 | memory junk | memory junk |
| 6 | 64 | x1, y1, x2, y2 + 32 junk bytes | P0, P3, C1, C2 (start, end, control 1, control 2) |
| 70 | 2 | 0 | 2 if joined to a previous Bézier, else 0 |
| 72 | 2 | 0 | 2 if joined to a following Bézier, else 0 |

Arcs, circles, ellipses and splines all become cubic Béziers:
- circle: 4 segments
- 90° arc: 5 segments
- DXF bulge arc: split into several

The bbox is the hull of all points, control points included.

### Type 4: group [observed]

Common header with color `ff ff ff 00`, then a uint32 child count, then the
children as complete objects (b30).

### Type 5: text [observed]

Stores the text string (pstring), font name (pstring, e.g. `Narkisim`), SHX font name,
several parameter strings (`0000`, `9999`), sizes, then the rendered glyph
outlines as child paths. A TrueType text sample (b28) also changed the header,
which the current parser doesn't handle yet. Writing text as plain paths works and is
what `make_rld.py` does.

### Type 2: bitmap [observed]

Common header, then a **complete embedded `.bmp` file** (`BM` header, BITMAPINFOHEADER,
palette, rows padded to 4 bytes; the padding bytes are memory junk), then the
centre point (2 doubles) and 4 bytes.
- 8-bit gray: 256-entry palette, 200 × 100 px stored as 20 000 bytes (b31)
- 1-bit: 2-entry palette (b32)

## Open questions

1. Bitmap layer block (478 bytes, prefix `01 00 01 00`).
2. Remaining layer fields: seal, open/close delay, laser through mode, through
   power 1–6, power 3–6 enables, the dialog's "Advance…" sections, the "Default" checkboxes.
3. Text and group objects in full, and the TrueType-text header change.
4. The meaning of the constant 188-byte path trailer and the region between the
   layer table and the object section.
5. Whether a writer-generated file opens in RDWorks (pending first real test).
