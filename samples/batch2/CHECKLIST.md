# Batch 2 — test files to save from RDWorks

**Rule:** build `b00` once. Make every other file by opening `b00`, making only the
change listed, and using **Save As**. Don't chain edits from one file to the next.

Note any value RDWorks shows that you didn't set (e.g. the default interval).

## A. Baseline and repeatability
| File | What to do |
|---|---|
| `b00_base` | New project. Rectangle on the **black** layer, set to **20 wide × 10 tall** in the size boxes and **X=100, Y=50** in the position boxes. Note which anchor point in the 9-dot grid is active. Cut mode. |
| `b01_resave` | Open b00 and Save As without changing anything. Shows which bytes change on every save. |

## B. Position and axis direction
| File | Change from b00 |
|---|---|
| `b02_x200` | Position X → 200 (Y stays 50) |
| `b03_y150` | Position Y → 150 (X stays 100) |

## C. Layer references and order
| File | Change from b00 |
|---|---|
| `b04_layer_far` | Move the rectangle to a color far down the palette (e.g. the 10th or 20th). Note which number or color. |
| `b05_two_layers_reordered` | Add a second rectangle on **red**, then move red **above** black in the layer list. |

## D. Layer parameters (black layer)
| File | Change from b00 |
|---|---|
| `b06_scan` | Mode → Scan, nothing else |
| `b07_scan_interval005` | Mode → Scan, interval → 0.05 |
| `b08_scan_bidir_toggled` | Mode → Scan, toggle bidirectional (note whether it was on or off) |
| `b09_scan_cut` | Mode → Scan+Cut (or whatever the combined mode is called) |
| `b10_dot` | Mode → Dot |
| `b11_output_off` | Output / enable unchecked |
| `b12_air_toggled` | Blowing / air toggled |
| `b13_…` onward | Every other field in the layer dialog: one change per file, file named after the field, e.g. `b13_open_delay_5`. |

## E. Geometry
| File | Change from b00 (delete the rectangle first, except b29) |
|---|---|
| `b20_circle_tool` | Circle tool, Ø20 |
| `b21_ellipse_tool` | Ellipse tool, 30 × 15 |
| `b22_import_circle` | Import `i1_circle_r10_at_100_50.dxf` |
| `b23_import_arc` | Import `i2_arc_r10_0to90.dxf` |
| `b24_import_poly_arc` | Import `i3_polyline_with_arc_segment.dxf` |
| `b25_import_spline` | Import `i4_spline.dxf` |
| `b26_import_open_L` | Import `i5_open_L_polyline.dxf` |
| `b27_import_hole` | Import `i6_square_with_hole.dxf` |
| `b28_text_ttf` | Text tool: `AB`, Arial (any TrueType font), height 10 |
| `b29_rotated30` | Keep the rectangle, rotate it 30° |
| `b30_grouped` | Rectangle + Ø20 circle, grouped |
| `b31_bitmap_gray` | Import `i7_gradient_200x100px.png`, size 20 × 10 mm |
| `b32_bitmap_1bit` | Import `i8_checker_40x20px.png`, size 20 × 10 mm |
| `b33_text_shx` | Text tool: `AB` with the SHX font option, height 10 |

## Also
- Screenshots of the layer-parameter dialog for b00, all tabs or sections. These map field names to offsets.
- RDWorks version from Help → About.
