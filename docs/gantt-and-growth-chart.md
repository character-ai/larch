# `gantt render` and `analyze-issues render-chart` contracts

Both verbs are Rust-owned. `larch_core::report::gantt` holds the ASCII Gantt
renderer and `larch_core::report::growth_chart` holds the cumulative-growth
chart. Issue #8092 retired the Python implementations.

## `gantt render`

A generic ASCII Gantt renderer with no reviewer-domain knowledge.

```bash
scripts/larch.sh gantt render \
  --window-start-s N \
  --window-end-s N \
  --rows-tsv rows.tsv \
  [--width 56]
```

`rows.tsv` carries three tab-delimited columns:

```text
label<TAB>start_s<TAB>end_s
```

`start_s` and `end_s` use the same absolute time base as the window flags. Shell
callers pass clamped absolute overlap bounds, not round-relative offsets.

### Library contract

- Labels pass through unchanged. The renderer neither sanitizes nor truncates them.
- Rows are clamped to the absolute window, then placed as whole-cell `█` bars.
- A row with no positive overlap after clamping is skipped, and a chart with no
  surviving row renders as empty output with exit 0.
- Absent `--width` selects 56 and narrows the track to fit long labels. An
  explicit `--width` is used as given.
- `format_mss` renders non-negative seconds as `m:ss` for axes and title spans.
  It is not the table duration formatter.

### Axis contract

- The left label is `0:00` and starts under the first track cell.
- The right label is the window span as `m:ss` and ends under the last track cell.

### Invariants

Every chart holds these:

- Right edges align, and left edges align.
- Track glyphs are only space or `█`.
- Bars contain no embedded spaces.

### Exit codes

`0` on success. `2` for a usage error, a `--width` below 1 or above 10000, an
unreadable rows TSV, or a malformed row.

## `analyze-issues render-chart`

```bash
scripts/larch.sh analyze-issues render-chart [path]
```

Without `path`, the TSV is read from stdin. The first line is the header, whose
columns from the third onward name the buckets. Each later line is
`key<TAB>label<TAB>value...`; a line with fewer than three columns is skipped and
an empty bucket cell reads as `0`. A key is arbitrary text, so a multi-character
key widens its own canvas row.

Exit codes: `0` on success, `2` for a usage error, and `1` for an unreadable
path, non-UTF-8 bytes, or a non-integer bucket value.
