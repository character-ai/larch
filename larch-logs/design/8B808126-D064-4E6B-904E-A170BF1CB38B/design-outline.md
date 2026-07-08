## Proposed Design Outline

### Goals
- Append four pre-written guideline entries (G-Py-15, G-Cfg-3, G-Orch-5, G-Obs-5) to `ARCHITECTURAL_GUIDELINES.md`.
- Place each entry byte-exact at its named anchor: end of its target section, before the next `##` heading.
- Raise the coverage indexer's guidelines count by exactly 4.

### Non-goals
- Do not change any other line of `ARCHITECTURAL_GUIDELINES.md`.
- Do not restyle, repunctuate, or renumber the supplied entry text; target IDs are already free.
- Do not touch code, scripts, or CLI wiring; verification only reads `learn_from_bugs.py`.

### Approach sketch
- One file edit: four surgical insertions into `ARCHITECTURAL_GUIDELINES.md`.
- Per entry: blank line, `### <heading>`, bullet lines directly below, one blank line before the next `##`.
- Anchors confirmed in Step 0c: after G-Py-14 (L66), G-Cfg-2 (L76), G-Orch-4 (L168), G-Obs-4 (L187).
- Verify new headings match `_GUIDELINE_ID_RE`; confirm `coverage_index_main` reports +4.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md`: the only edited file.
- `python/larch/issue/learn_from_bugs.py`: read-only, for `_GUIDELINE_ID_RE` and `coverage_index_main`.

### Open questions
- None.
