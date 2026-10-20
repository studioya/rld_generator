# Batch 4 — test files to save from RDWorks

Same rule as before: start from the named baseline, make **one** change, Save As.
Use the odd values given; they're easy to find in the file.

## G. Generated files (open, check, Save As `gNN_resaved.rld`)

| File | What it should show |
|---|---|
| `g07_bitmap_plus_rect` | The gradient bitmap (20 × 10 mm) with a 20 × 10 rectangle below it. Bitmap layer: 123 mm/s, 17 / 19 %. Black layer: cut, 100 mm/s, 15 / 20 % |
| `g08_layer_fields` | One rectangle. Black layer: Seal **0.321**, Open Delay **2.5**, Close Delay **3.5**, sew compensation **ticked** (Advance… next to Seal), laser through mode **unticked** |

Note anything that looks wrong, and check the layer dialog values for g08.

## L. Other layer parameters (start from b00; Advance… next to Processing Mode)

| File | Change |
|---|---|
| `d01_pen_enable` | Tick "Enable pen up and down" |
| `d02_pen_down_1.11` | Enable pen, tick Pen down, value 1.11 |
| `d03_pen_up_2.22` | Enable pen, tick Pen up, value 2.22 |
| `d04_pen_speed_33` | Enable pen, Speed → 33 |
| `d05_u_axis_4.44` | Tick U axis moving, value 4.44 |
| `d06_dot_interval_0.55` | Dot interval → 0.55 |
| `d07_io1` | Tick IO1 |
| `d08_io3` | Tick IO3 |
| `d09_laser1_freq_21.5` | Tick Laser1 freq, value 21.5 |
| `d10_sew_width_0.17` | Advance… next to Seal: tick sew compensation, width 0.17 |

## M. Bitmap processing (start from b31, gradient bitmap; open the Bitmap handle dialog)

Make the change, click **Apply to source**, then **Ok**.

| File | Change |
|---|---|
| `d20_dither_on` | Tick Dither (leave the default mode) |
| `d21_dither_net_freq7` | Dither → Net graphic, frequency 7 |
| `d22_dither_dot` | Dither → Dot graphic |
| `d23_dither_bw` | Dither → Black And White |
| `d24_dither_sharpen` | Dither → Sharpen |
| `d25_brightness_23` | Brightness → about +23 % |
| `d26_contrast_17` | Contrast → about +17 % |
| `d27_invert` | Tick Invert color |
| `d28_resolution_300` | Output resolution → 300 |
| `d29_dither_view_only` | Same as d20 but click **Apply to view** instead of Apply to source |

## N. Bitmap layer color (start from b31)

| File | Change |
|---|---|
| `d30_bitmap_on_red` | Move the bitmap to the red layer |
| `d31_bitmap_red_and_black` | d30 + import `i8_checker` and leave it on black |

## O. Per-object cut settings (start from b00)

The constant 188 bytes at the end of every path contain 5.0, 45.0, 10.0 and 45.0.
They could be lead-in/lead-out settings (length 5 mm, 45°…) or something similar.

| File | Change |
|---|---|
| `d40_…` | Any per-object cut option you can find (lead-in/out lines, cut direction, start point, overcut, kerf/offset), one file each, named after the option |
| `d41_two_rects_order_swapped` | Two rectangles; then swap their cutting order (if RDWorks lets you set order manually) |

## Also
Screenshot any dialog you used in section O.
