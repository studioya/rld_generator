# Batch 3 — test files to save from RDWorks

Same rule as batch 2: start each file from its baseline, make **one** change,
then Save As. Where a field takes a number, use the odd value given. Odd values are
easy to find as doubles in the file; round numbers like 0, 1 and 30 appear everywhere.

## G. Generated files: does RDWorks accept them? (most important)

For each file in `generated/`:
1. Open it in RDWorks. Note anything odd: an error, wrong shape, wrong place, or
   wrong layer settings in the layer list.
2. Without changing anything, **Save As** `gNN_resaved.rld`.

| File | What it should show |
|---|---|
| `g01_rect_like_b00` | One 20 × 10 rectangle at display X=100 Y=50 (center), black layer, cut 100 mm/s 15/20% |
| `g02_curves_open` | Ø20 circle, an open L shape, an open S-curve; all on the black layer |
| `g03_four_layers` | Four 20 mm squares in a row on 4 layers. Settings: black cut 37 mm/s 11/13%; blue scan 333 mm/s 21/23%, interval 0.07, unidirectional; red dot 44 mm/s 31/33%; green cut 55 mm/s 41/43%, **output off, air off** |
| `g04_palette40` | One 30 × 15 rectangle on palette color #41 (40 counting from 0), cut 66 mm/s 12/14% |
| `g05_200_squares` | 200 squares, 8 mm, in a 20 × 10 grid |
| `g06_orientation_check` | "TOP F" + arrow pointing RIGHT, top-right corner of the bed |

Also: run **Simulate** on g02 and note whether the open shapes stay open.

## H. Remaining layer fields (start from b00)

| File | Change |
|---|---|
| `c01_seal_0.123` | Seal 0.060 → 0.123 |
| `c02_open_delay_4.5` | Open Delay → 4.5 |
| `c03_close_delay_6.5` | Close Delay → 6.5 |
| `c04_through_mode_off` | Untick Laser through mode |
| `c05_through_power1_7.7` | Through power 1 → 7.7 |
| `c06_power2_on` | Tick power 2, set min 11.5 / max 12.5 |
| `c07_speed_default_ticked` | Tick "Default" next to speed |
| `c08_power_default_ticked` | Tick "Default" next to power |
| `c09_seal_advance_…` | Open the **Advance…** next to Seal: screenshot it, then one file per field changed |
| `c10_mode_advance_…` | Open the **Advance…** next to Processing Mode (cut mode): screenshot it, then one file per field |
| `c11_scan_advance_…` | Same as c10 with the layer in **Scan** mode (its Advance… is probably different) |

## I. Bitmap layers (start from b31: gradient bitmap)

| File | Change |
|---|---|
| `c20_bitmap_speed_123` | Bitmap layer speed → 123 |
| `c21_bitmap_power_17_19` | Bitmap layer min/max → 17 / 19 |
| `c22_bitmap_plus_rect` | Add a vector rectangle on another layer (black) |
| `c23_bitmap_dither_…` | Change the bitmap's dither or processing mode, one file per option. Screenshot the bitmap layer dialog. |
| `c24_bitmap_moved` | Move the bitmap to display X=200 |
| `c25_two_bitmaps` | Import `i8_checker` as well (second bitmap) |

## J. Text (TrueType)

| File | Change |
|---|---|
| `c30_text_arial_AB` | New project, text tool, `AB`, **Arial**, height 10 |
| `c31_text_arial_ABC` | Same, `ABC` |
| `c32_text_arial_h20` | Same as c30, height 20 |
| `c33_text_times_AB` | Same as c30, Times New Roman |
| `c34_text_then_deleted` | c30, then delete the text and add a plain rectangle. Shows what text leaves in the header. |

## K. Objects and document

| File | Change |
|---|---|
| `c40_group_two_rects` | b00 + a second rectangle, both grouped |
| `c41_nested_group` | c40 grouped again with a circle |
| `c42_rect_reversed` | b00, reverse the path direction (if RDWorks has the tool) |
| `c43_rect_start_point` | b00, change the cut start point (if available) |
| `c44_off_bed` | b00 moved partly outside the bed (display X=−5) |
| `c45_star_tool` | Polygon/star tool, any |
| `c46_doc_setting_…` | Any document-level setting you know of (cut optimisation, laser head position, output selection…). One file each. |

## Also
- Screenshots of every Advance… dialog you open, and the bitmap layer dialog.
