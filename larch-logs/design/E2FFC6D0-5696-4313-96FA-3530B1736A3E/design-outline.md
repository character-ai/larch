## Proposed Design Outline

### Goals
- Reduce always-loaded `/design` Step 3/Gate prose by ~25–35 lines by eliminating five overlapping redundancies
- Remove Step 4 non-determinism: replace 3-condition self-compute with a wrapper-emitted `STEP4_MODE` directive
- Keep all `/design` runtime behavior unchanged; only SKILL.md prose, reference files, one shell script, and test assertions change

### Non-goals
- No change to `design-step35-settle.sh` runtime rc behavior, Python-owned rc values, postplan semantics, or settle retry mechanics
- No new flags; no control-flow changes to plan review, Gate B, or Gate C
- No changes to Python modules or the broader larch test suite

### Approach sketch
- Delete wrapper-rc fallback table and site-variant table from `settle-rc-dispatch.md`; add one fail-closed rule for missing action row; update Gate A/Gate B consumer prose in `SKILL.md`, `approval-gates.md`, `discussion-rounds.md`
- Collapse two Step 3 entry fences in `SKILL.md` into one parameterized call (`design-step3-entry.sh ${STEP3_REENTRY_FLAG}`)
- Dedup Gate-B-bypass in `SKILL.md` to routing row + single fence; delete status elaboration paragraphs
- Add probe-only dialectic call to `design-step3b-entry.sh --mode finalize`; emit `STEP4_MODE=foreground|background`; Step 4 reads it and picks the `run_in_background` flag
- Update `test-design-structure.sh` assertions to pin collapsed prose contract

### Surfaces in scope
- `skills/design/references/settle-rc-dispatch.md`
- `skills/design/references/approval-gates.md`
- `skills/design/references/discussion-rounds.md`
- `skills/design/scripts/design-step35-settle.md`
- `skills/design/SKILL.md`
- `skills/design/scripts/design-step3b-entry.sh`
- `skills/design/scripts/design-step3b-entry.md`
- `scripts/test-design-structure.sh`

### Open questions
- None.
