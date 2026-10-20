# rld_generator: create RDWorks `.rld` files

Reverse-engineering of RDWorks project files. RDWorks is Ruida's free laser software. Its project format, `.rld`, has no public
specification. This repo documents the format and includes a Python writer that
generates `.rld` projects with layers already set: speed, power, cut/scan/dot,
output, air, scan interval and bidirectional.

- **Format spec:** [`docs/FORMAT.md`](docs/FORMAT.md)
- **Writer:** [`src/rldwriter.py`](src/rldwriter.py) (vector paths: lines and cubic Béziers)
- **Parser:** [`tools/rld_parse.py`](tools/rld_parse.py)
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
open("out.rld", "wb").write(build(tpl, layers, shapes))
```

The writer reuses your own empty project as its template, so the header and the
256-color layer table come from your machine. Coordinates are in mm, with the origin
at the bed's bottom-left and y up. RDWorks displays them from the top-right machine
origin.

## Status

Vector files are confirmed against RDWorks' own output. **Generated files haven't
been opened in RDWorks yet.** Text, groups and bitmaps are documented but not written.
See *Open questions* in the spec.

## Note on samples

An empty `.rld` contains the saving machine's full layer table: every palette color
with its last-used speed and power settings.
