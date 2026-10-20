# rld_generator: create RDWorks `.rld` files

Reverse-engineering of RDWorks project files. RDWorks is Ruida's free laser software. Its project format, `.rld`, has no public
specification. This repo documents the format and includes a Python writer that
generates `.rld` projects with layers already set: speed, power, cut/scan/dot,
output, air, scan interval, bidirectional, seal, delays and through power.
It writes vector paths (lines and Béziers) and bitmaps.

- **Format spec:** [`docs/FORMAT.md`](docs/FORMAT.md)
- **Writer:** [`src/rldwriter.py`](src/rldwriter.py): vector paths (lines, cubic Béziers) and bitmaps
- **Parser:** [`tools/rld_parse.py`](tools/rld_parse.py): layers and all known object types (path, bitmap, group, text)
- **Samples:** [`samples/`](samples/), saved from RDWorks V8.01.24, with the test checklist for each batch
- **Round-trip test:** `python3 tests/test_roundtrip.py` rebuilds every vector sample
  and compares it byte-for-byte (only bytes RDWorks fills with leftover memory are masked)

## Method

Controlled samples: save a baseline project from RDWorks, change one thing, Save As,
then diff. Each finding in the spec is tagged *confirmed* (the writer reproduces it),
*observed*, or *guess*.

## Use

```python
from rldwriter import Template, build
tpl = Template("empty.rld", "one_rect.rld")      # both saved from YOUR RDWorks
layers = [dict(palette=0, speed=20, min=55, max=65, mode="cut")]
shapes = [(0, [(100, 100), (120, 100), (120, 110), (100, 110)], True)]   # mm, y up
# bitmaps: layers.append(dict(bitmap=True, speed=300, min=10, max=20))
#          shapes.append((1, Bitmap.from_image(pil_image, width_mm=40, center=(200, 150)), True))
open("out.rld", "wb").write(build(tpl, layers, shapes))
```

The writer reuses your own empty project as its template, so the header and the
256-color layer table come from your machine. Coordinates are in mm, with the origin
at the bed's bottom-left and y up. RDWorks displays them from the top-right machine
origin.

## Status

- RDWorks V8.01.24 opens files from the writer, and re-saving them changes nothing
  (6 test files, including curves, open paths, 4 layers and 200 shapes).
- All 66 samples parse completely. The writer rebuilds 42 of them byte-for-byte, apart
  from bytes RDWorks fills with leftover memory.
- Groups and text are parsed but not written. Text can be written as outlines.
- Open questions are listed at the end of the spec.

## Note on samples

An empty `.rld` contains the saving machine's full layer table: every palette color
with its last-used speed and power settings.
