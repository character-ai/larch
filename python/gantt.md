# gantt.py

`python/gantt.py` is a generic ASCII Gantt renderer. It has no larch reviewer-domain knowledge.

## Library contract

- `GanttRow(label, start_s, end_s)` carries opaque caller input.
- Labels pass through unchanged. The renderer does not sanitize or truncate them.
- `render_gantt(window_start_s, window_end_s, rows, width=56)` interprets row times and window times in the same absolute time base.
- `render_gantt()` clamps rows to the absolute window, subtracts `window_start_s` internally, then places whole-cell `█` bars.
- Rows with no positive overlap after clamping are skipped.
- `format_mss(seconds)` formats non-negative seconds as `m:ss` for chart axes and chart title spans. It is not the table duration formatter.

## CLI contract

Bash callers use:

```bash
python3 python/cli.py gantt render \
  --window-start-s N \
  --window-end-s N \
  --rows-tsv rows.tsv \
  --width 56
```

`rows.tsv` has three tab-delimited columns:

```text
label<TAB>start_s<TAB>end_s
```

`start_s` and `end_s` must use the same absolute time base as the window flags. Shell callers should pass clamped absolute overlap bounds, not round-relative offsets.

## Axis contract

- The left label is `0:00`.
- `0:00` starts under the first track cell.
- The right label is the window span as `m:ss`.
- The right label ends under the last track cell.

## Invariants

Tests should pin these checks for every chart:

- Right edges align.
- Left edges align.
- Track glyphs are only space or `█`.
- Bars contain no embedded spaces.

`/review` should reuse this module or CLI when it adds timing charts.
