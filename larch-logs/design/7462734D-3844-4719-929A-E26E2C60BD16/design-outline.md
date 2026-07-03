## Proposed Design Outline

### Goals
- Remove prose in `approval-gates.md` that duplicates what `design_gate_render.py` now owns (renderer internals, cap-computation restatement).
- Compress renderer-contract and per-gate instruction prose without changing gate behavior or routing.
- Bank a measurable eager-closure reduction (ballpark 1k+ tokens) and lower the `design` baseline in `python/skill-closure-baseline.json` if the live measurement drops.

### Non-goals
- No change to `design_gate_render.py` or any other Python renderer logic — rendered strings stay byte-identical.
- No change to gate semantics, control flow, or routing (Gate A/B/C behavior unchanged).
- No edits to other conditional reference files (`settle-rc-dispatch.md`, `step2b5-rc-handling.md`, `brainstorm.md`, etc.) or to `approval-gates-explicit.md`.

### Approach sketch
- Treat `scripts/test-design-structure.sh` and `skills/design/scripts/test-gate-b-apply-mode.sh` literal-string pins on `approval-gates.md` as hard constraints; verify every pinned string survives verbatim.
- Trim the "Review-round cap" section's restatement of the cap-computation algorithm (already implemented in `_review_count`/`_gate_c_options`) down to a short "trust the rendered `REVIEW_ROUND_CAP` and option rows" pointer.
- Tighten repeated "the renderer relabels/emits/omits X" asides across Gate A/B/C into terser forms that state the contract once.
- Densify wordy Behavior/Prompt/Presentation prose elsewhere in the file, preserving every operational instruction (routing, safety brakes, invariants).
- Re-measure with `python3 python/cli.py skill-closure report` before/after; run `python3 python/cli.py lint skill-closure-growth --write` only if the design closure total drops.

### Surfaces in scope
- `skills/design/references/approval-gates.md`
- `python/skill-closure-baseline.json` (lower only, if closure drops)

### Open questions
- None.
