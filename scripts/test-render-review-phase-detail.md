# test-render-review-phase-detail.sh

Offline harness for `scripts/render-review-phase-detail.sh`.

The harness validates the shared Review Phase Detail table, cost attribution,
top-reviewer attribution, failed-slot attribution, stdout mode, usage errors,
plain fenced ASCII reviewer timing charts, and `--no-gantt` suppression.

## ASCII chart coverage

The harness validates plain fenced ASCII charts instead of generated Mermaid.
It checks absolute TSV sort order, tab-delimited sorting for label-first TSV
rows, unfiltered round-window aggregation, vendor overlap selection without
skill filtering, best-effort renderer failure handling under `set -e`, renderer
launch from outside the repo root, chart title `m:ss` formatting, and axis
placement.

For rendered charts it checks these invariants:

- Left edges align.
- Right edges align.
- Track glyphs are only space or `█`.
- Bars contain no embedded spaces.

## Invocation

Run directly:

```bash
bash scripts/test-render-review-phase-detail.sh
```

The Makefile target is `make test-render-review-phase-detail`.
