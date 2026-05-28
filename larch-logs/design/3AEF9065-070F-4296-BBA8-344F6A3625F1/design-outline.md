## Proposed Design Outline

### Goals
- Close all 6 acceptance items from #3091 (combined #3087 + #3080): A1 escape-aware double-quoted literals, A2 broader pin routing, A3 BASH_COMPAT=3.2 invocation case, A4 sketch-variant exact-line counting, B5 per-step placement, B6 shared TSV manifest.
- Keep changes surgical: edit `check-contains-pins.sh`, `relevant-checks.sh`, `lint-readability-preamble.sh` and the two harnesses; add one new TSV. No new lint scripts.

### Non-goals
- No rewrite of `readability-style.md`, `lint-foreground-markers.sh`, or any unrelated lint surface.
- No JSON/YAML config; manifest stays a TSV consumable by Bash 3.2 `while IFS=$'\t' read`.
- No changes to the 52 existing single-quoted `contains` assertions; A1 only touches the parser to admit escape-bearing double-quoted literals.

### Approach sketch
- A1: extend the awk dispatcher's double-quoted-literal branch to unescape `\$`, `\"`, `\\` instead of bailing on any `$`. Reuse the existing CHECK/SKIP emit shape.
- A2: append `check-contains-pins.sh|test-check-contains-pins.sh|test-design-structure.sh|test-parse-codex-usage.sh` cases to `relevant-checks.sh`; broaden the design-skill arm to `skills/*/SKILL.md|skills/*/references/*.md`.
- A3: one new test section in `test-check-contains-pins.sh` that re-runs an existing happy-path fixture under `BASH_COMPAT=3.2 bash`.
- A4 + B5 + B6: extract manifest rows to `scripts/lint-readability-preamble.tsv` (+ sibling `.md`); enrich rows with optional `step_markers` column for B5; rework `lint-readability-preamble.sh` to source the TSV and switch sketch variant to `grep -Fxc` against an exact-line template; B5 adds a proximity check (≤80 lines below each `<!-- step:N -->` marker named in `step_markers`); test harness sources the same TSV instead of duplicating fixture path lists.

### Surfaces in scope
- `scripts/check-contains-pins.sh`, `scripts/check-contains-pins.md`, `scripts/test-check-contains-pins.sh`
- `scripts/relevant-checks.sh`, `scripts/relevant-checks.md`
- `scripts/lint-readability-preamble.sh`, `scripts/lint-readability-preamble.md`, `scripts/test-lint-readability-preamble.sh`, `scripts/test-lint-readability-preamble.md`
- NEW: `scripts/lint-readability-preamble.tsv` + sibling `.md`
- `scripts/test-design-structure.sh` may need an added assertion verifying the A1 unescape (the line 44 case already covers it but a new test pin in test-check-contains-pins.sh exercises the parser directly)

### Open questions
- None.
