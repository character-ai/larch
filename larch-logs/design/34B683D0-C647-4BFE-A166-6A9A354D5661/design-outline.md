## Proposed Design Outline

### Goals
- Port 3 `/design` shell helpers to in-process Python, no behavior change: `design-stage-terminal-state.sh`, `design-failure-report.sh`, `design-step-final-summary.sh`.
- Register `cli.py design` verbs `stage-terminal-state`, `failure-report`, `step-final-summary`; cut every real caller.
- Hard-delete the 3 `.sh`, their `.md` siblings, and their test harnesses.

### Non-goals
- No thin wrappers, no shims. Full in-process ports only.
- No output-contract change. Markers, `REPORT_GATE_SIDECARS_FILE=`, terminal-state env files, the report gate, sentinels, and fallbacks stay byte-identical.
- Other G6 pieces (G6.4 #4677, G6.5 #4678) stay out of scope.

### Approach sketch
- Add `stage_terminal_state_main`, `failure_report_main`, `step_final_summary_main` to `python/design_lifecycle.py`; wire into the `cli.py design` dispatcher.
- Retarget `python/design_summary.py` to call the failure-report gate in-process (import, not subprocess).
- Add `python/session_env.py` launcher mappings so prompt fences keep the 3 `.sh` basenames.
- Convert Python callers (`plan_review.py`, `clarify.py`) to import the new functions.
- Update lint, docs, Makefile, and `python/migrated-scripts.tsv`.

### Surfaces in scope
- Runtime: `python/design_lifecycle.py`, `python/design_summary.py`, `python/session_env.py`, `python/cli.py`, `python/plan_review.py`, `python/clarify.py`.
- Deletes: the 3 `.sh` + `.md` + `test-design-*` harnesses; debug scaffolds `_dbg-stage.sh`, `_debug-step5c.sh`, `scripts/debug-step5c-once.sh`.
- Lint/docs/tests: `python/checks.py`, `Makefile`, `agent-lint.toml`, `docs/linting.md`, `SECURITY.md`, `python/migrated-scripts.tsv`, and the affected `python/test_*` suites.

### Open questions
- None. Caller surface re-verified against current HEAD during plan drafting.
