# render-chart.py

Purpose: render the cumulative category matrix produced by `analyze.py` as a compact ASCII chart.

Primary callers: `analyze.py` imports `render-chart.py` from the same scripts directory.

Invariants: accept TSV matrix input, use one single-letter legend key per category, preserve deterministic output, and use `*` when multiple series collide in the same cell.

Makefile wiring: none; this is a dev-only local skill helper.

Test harness: `python3 -c "import ast; ast.parse(open('.claude/skills/analyze-issues/scripts/render-chart.py').read())"`.

Edit in sync: update this contract and `analyze.py` whenever the chart input format or rendering semantics change.
