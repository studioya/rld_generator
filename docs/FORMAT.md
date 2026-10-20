# RDWorks `.rld` project file format (V8): reverse-engineering notes

Decoded from samples saved by **RDWorks V8.01.24** (`RDFILEVER8.0.01`) on a
Ruida-controlled 150 W CO2 laser (1300 × 900 mm bed) at Bezalel Academy's
modelling center.

Confidence tags:
- **[confirmed]**: `src/rldwriter.py` rebuilds RDWorks' own files from this description, or RDWorks accepts files written this way
- **[observed]**: consistent across samples, but not written by the writer
- **[guess]**: inferred, unverified

## Status

| Area | State |
|---|---|
| Layer table, used-layer blocks, main layer fields | confirmed |
| Paths: lines, cubic Béziers, open/closed | confirmed |
| Bitmaps (8-bit gray, 1-bit) | confirmed |
| Groups, text | observed: parsed fully, not written |
| RDWorks accepts writer output | **confirmed**: 6 generated files opened and re-saved byte-identical (batch 3) |

All 66 samples parse completely. 44 rebuild from their parsed contents: 33 byte-for-byte,
11 differing only in bytes RDWorks fills with leftover memory, or in the last bit of a float.
Run `python3 tests/test_roundtrip.py`.

## General

- Little-endian. Numbers are IEEE-754 `double` (mm, mm/s, %, ms). Counts are `uint32`.
  Strings are Pascal strings (1-byte length, no terminator), in the Windows ANSI code page. [confirmed]
- Not compressed or encrypted. [confirmed]
- Saving an unchanged project gives a byte-identical file. [confirmed]

### Coordinates [confirmed]

Stored coordinates use ordinary math axes: **x right, y up, origin at the bed's
bottom-left corner**. RDWorks displays positions from the top-right machine origin,
measured to the object's centre:

```
X_display = bed_width  - x_centre
Y_display = bed_height - y_centre
```

Objects may lie outside the bed; nothing is clamped (c44: x up to 1315 on a 1300 bed).
The "laser head position" setting is **not** stored in the project (c46 is identical to b00).

### Memory junk [observed]

RDWorks writes some fixed-size fields without initialising them:
- the 4-byte tag in every segment record
- the unused 32 bytes of a line segment
- the row padding inside embedded 1-bit bitmaps

Their values vary between RDWorks sessions, and RDWorks ignores them.

## File layout

| Offset | Size | Content |
|---|---|---|
| `0x000` | variable | Header, including the text tool's settings block |
| `0x191 + s` | 257 × 619 | Layer table [confirmed] |
| … | … | Unknown region, constant in all samples [observed] |
| `0x449C3 + s` | 4 | `N`: number of used-layer blocks [confirmed] |
| … | variable | N used-layer blocks [confirmed] |
| … | 4 | `M`: number of top-level objects [confirmed] |
| … | variable | M objects [confirmed] |
| end − 48 | 48 | Fixed trailer [confirmed] |

`s` is the header shift: how much the three header strings differ in length from
the reference layout (`"í"`, `Narkisim`, `FS.SHX`):

```
t = b[0xFE];  f = b[0x129 + t];  x = b[0x12A + t + f]
s = (t − 1) + (f − 8) + (x − 6)
```
[confirmed on all 66 samples]

### Header (partial)

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | pstring | `RDFILEVER8.0.01` |
| `0x14` | double | bed width, mm [confirmed] |
| `0x1C` | double | bed height, mm [confirmed] |
| `0x72` | pstring | system font name, GBK (`宋体`) [observed] |
| `0x77` | pstring | `FS.SHX` [observed] |
| `0xFE` | text-settings block | the text tool's last-used settings: same layout as a text object, see type 5 [confirmed] |

## Layer table

257 records of 619 bytes, from `0x191 + s`.
- Records 0–255 are the palette colors. RDWorks shows only the first 20 in its color picker, but files using
  higher indices (index 40 in g04) open and re-save unchanged.
- Record 256 holds the **bitmap layer** settings.

The table remembers every color's last settings, so an empty project carries the
machine's whole layer history. Moving a shape onto a color brings in that slot's
stored settings, including *Is Output* (b04).

### Layer record fields

Offsets are relative to the record start (its COLORREF). Field names follow the
RDWorks Layer Parameter dialog (`docs/img/layer_parameter_dialog.png`).

| Rel. | Type | Field | Source |
|---|---|---|---|
| `+0x000` | COLORREF | Layer color: R, G, B, 0 | confirmed |
| `+0x004` | byte | Is Output: 1 yes / 0 no | b11 |
| `+0x008` | double | Speed (mm/s) | t3 |
| `+0x010` | double | Min Power 1 (%) | t4 |
| `+0x018` | double | Max Power 1 (%) | t4 |
| `+0x020` | double | Min Power 2 (%) | c06 |
| `+0x028` | double | Max Power 2 (%) | c06 |
| `+0x030` | byte | If Blowing: 1 yes / 0 no | b12 |
| `+0x064` | byte | Power 2 enabled (tick box) | c06 |
| `+0x068` | byte | Speed "Default" tick box | c07 |
| `+0x06C` | byte | Power "Default" tick box | c08 |
| `+0x124` | byte | Processing Mode: 0 scan / 1 cut / 2 dot | b06, b10 |
| `+0x134` | byte | Scan: 1 bidirectional ("x swing") / 0 one-way | b08 |
| `+0x135` | double | Scan interval (mm) | b07 |
| `+0x18D` | double | Seal (mm) | c01 |
| `+0x195` | double | Close Delay (ms) | c03 |
| `+0x19D` | double | Open Delay (ms) | c02 |
| `+0x1A5` | byte | Advance… (next to Seal) → Enable sew compensation | c09 |
| `+0x1B3` | byte | Laser through mode | c04 |
| `+0x1B7` | double | Through power 1 (%) | c05 |

Not yet located:
- Sew width
- Through power 2–6
- Power 3–6
- Everything in "Other layer parameters" (pen up/down, U axis, dot interval, IO1–4, laser frequency); see `docs/img/other_layer_params_*.png`

Palette (first entries): 0 black, 1 blue, 2 red, 3 green, 5 yellow. [observed]

## Used-layer blocks

One block per layer that has objects, in **layer-list order**, which is the run order (b05). [confirmed]

| Kind | Size | Content |
|---|---|---|
| vector layer | 621 | `00 00 00 00` + first 617 bytes of the color's table record |
| bitmap layer | 479 | `01 00 01 00` + first 475 bytes of table record **256** |

A bitmap and a vector shape on the same color get two separate blocks (c22).

Objects are **not** linked to blocks by index. A path joins a layer by its COLORREF.
A bitmap joins the bitmap layer.

## Objects

Every object starts with a type (`uint16`). Types 1, 2 and 4 then share a 45-byte header:

| Size | Field |
|---|---|
| 2 | type |
| 2 | type repeated |
| 1 | `00` |
| 4 | `uint32` sequence number, 1-based in file order. *Not* a layer reference (b05, b27) |
| 4 | COLORREF: assigns the object to its layer. Groups use `ff ff ff 00` |
| 32 | bbox: xmin, xmax, ymin, ymax |

### Type 1: path [confirmed]

| Size | Field |
|---|---|
| 45 | header |
| 4 | `uint32` closed flag: 1 closed / 0 open (open paths stay open in Simulate) |
| 4 | `uint32` nseg |
| nseg × 74 | segment records |
| 188 | constant path trailer (contains 5.0, 45.0, 10.0, 45.0; meaning unknown) |

A closed path still lists its closing segment.

**Segment record (74 bytes):**

| Offset | Size | Line (type 0) | Cubic Bézier (type 3) |
|---|---|---|---|
| 0 | 2 | `00 00` | `03 00` |
| 2 | 4 | memory junk | memory junk |
| 6 | 64 | x1, y1, x2, y2 + 32 junk bytes | P0, P3, C1, C2: start, end, control 1, control 2 |
| 70 | 2 | 0 | 2 if joined to a previous Bézier, else 0 |
| 72 | 2 | 0 | 2 if joined to a following Bézier, else 0 |

Circles, ellipses, arcs and splines are stored as cubic Béziers. A circle is 4 segments;
a 90° arc is 5. The bbox is the hull of all points, control points included.

### Type 2: bitmap [confirmed]

| Size | Field |
|---|---|
| 45 | header (COLORREF = the bitmap layer's color) |
| var | complete `.bmp` file: `BM` file header, BITMAPINFOHEADER, palette, rows bottom-up padded to 4 bytes. Length is in the `BM` header |
| 16 | centre x, y (doubles) |
| 4 | `00 00 00 00` |

- Size on the bed = pixels ÷ the BMP's pixels-per-metre field, so 10 000 px/m gives 254 dpi.
- RDWorks writes `biClrImportant = 0`.
- Seen formats:
  - 8-bit grayscale with a 256-entry palette (b31)
  - 1-bit with a 2-entry palette (b32, c25)
- The bitmap-processing dialog (brightness, contrast, dither) wasn't exercised. The pixels may be stored already processed.

### Type 4: group [observed]

| Size | Field |
|---|---|
| 45 | header, color `ff ff ff 00` |
| 4 | `uint32` child count |
| var | children: complete objects, recursively |

Grouping a group with another object (c41) produced one flat group of 3 children,
in which two children had the same sequence number.

### Type 5: text [observed]

| Size | Field |
|---|---|
| 2 | `05 00` |
| var | text-settings block (same layout as the header at `0xFE`) |
| 4 | `uint32` child count: number of glyph contours ("AB" in Arial = 5) |
| var | children: path objects with the rendered outlines |

Text-settings block, relative to its start:

| Offset | Field |
|---|---|
| `+0` | pstring text |
| `+1+len` | double height, mm (c32: 10 → 20) |
| `+9+len` | double, 100.0 (probably width %) |
| `+0x2B+len` | pstring TrueType font name |
| next | pstring SHX font name |
| … | pstrings `0000`, `0000`, `9999` and more fields |

The block is 177 bytes for "AB" / Arial / FS.SHX and changes length with the three strings.
A flag byte before the font name is `01` when the SHX font is selected (b33). [observed]

## Open questions

1. Remaining layer fields: sew width and the "Other layer
   parameters" dialog. (Power rows 2–6 and through power 2–6 are out of scope: they apply to multi-tube machines.)
2. Bitmap layers on colors other than black. Is slot 256 the only bitmap slot?
3. Bitmap processing settings: brightness, contrast, dither, output resolution.
4. The 188-byte path trailer and the region between the layer table and `N`.
5. Writing text objects. Text written as outlines already works.
