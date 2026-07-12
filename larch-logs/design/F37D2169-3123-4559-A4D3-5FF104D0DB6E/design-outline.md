## Proposed Design Outline

### Goals
- Give the operator-approved "proceed without assessment" leg a real mechanism: waiver file + ship-gate honor + driver-owned resume, so postmerge state, manifest, and final report come out right without manual verbs.
- Provide a generic `ship reconcile-manual-merge` back-fill so any operator-owned manual recovery yields `merged` state, `done` manifest, and a correct report through unmodified Steps 16-18.
- Make the deferred terminal-emit obligation survive a turn boundary, and repair run `BD267D84` committed records.

### Non-goals
- No changes to `emit_body` / `should_emit_updated_body` semantics beyond Task 6's flag source; no `IMPLEMENT_OUTCOME_SUCCEEDED` consumption; no emission keyed on `post-merge-sentinel`; no disk-backed Step 17 cache or Read fallback.
- No assessment-diagnostics fix (#7057); no `/design` report changes.

### Approach sketch
- New `ship waive-assessment` verb writes `assessment-operator-waiver.json`; `_combined_assessment_result` (`python/larch/implement/ship.py`) subtracts validated waived kinds from `unavailable_kinds` (violation branch untouched).
- New `ship reconcile-manual-merge` verb: probe PR merged, preserve-and-rewrite `ship-pr-state.sh` (PR/URL/MERGE_RESULT/PHASE=done plus the driver's done clear-set), write `post-merge-sentinel`, flush manifest `done` + `pr_number`.
- Rewrite the operator-bail contract in `skills/implement/SKILL.md` + `ship-pr-exit-matrix.md`: waive-then-reship for assessment-unavailable; hard ordering rule (no Steps 16-18 while approved recovery pending; manual recovery ends with reconcile).
- Deferred-emit carry-over prose in NEVER #17, terminal-emit precedence, and `skills/shared/final-summary-emit.md`, pinned by one anti-halt harness needle.
- `step18b` gains `--step17-emitted` flag taking precedence over the `.step17-emitted` file.

### Surfaces in scope
- `python/larch/implement/` (ship.py, new waiver/reconcile modules), `python/larch/cli.py` verb wiring
- `python/larch/report/final_report.py`, `skills/implement/scripts/step-18.sh`
- `skills/implement/SKILL.md`, `skills/implement/references/ship-pr-exit-matrix.md`, `skills/shared/final-summary-emit.md`
- `scripts/test-implement-anti-halt.sh` (+ `.md`), `python/tests/implement/test_ship.py`, `python/tests/report/test_final_report.py`, new verb tests
- `larch-logs/implement/BD267D84-8B70-4E30-9FC7-E60E4328D5FE/` (data repair)

### Open questions
- None.
