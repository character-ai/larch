## Proposed Design Outline

### Goals
- Port `design-stage-terminal-state.sh`, `design-failure-report.sh`, and `design-step-final-summary.sh` to in-process Python. No behavior change.
- Register `cli.py design` verbs, cut every real caller, then hard-delete the 3 `.sh` plus `.md` siblings plus their shell test harnesses.

### Non-goals
- No thin delegation wrappers and no shims. Full in-process ports only.
- Other G6 pieces (G6.4 #4677, G6.5 #4678) stay out of scope.
- No output-contract changes. Markers, `REPORT_GATE_SIDECARS_FILE=` handoff, terminal-state env files, the failure-report gate, sentinels, and fallbacks stay byte-identical.

### Approach sketch
- Add `stage_terminal_state_main`, `failure_report_main`, `step_final_summary_main` to `python/design_lifecycle.py`; wire them into the `cli.py design` dispatcher.
- Retarget `python/design_summary.py` to call the failure-report gate in-process (import, not subprocess).
- Add `python/session_env.py` launcher mappings so prompt-side `SKILL.md` fences keep the `.sh` basenames.
- Cut Python callers (`plan_review.py`, `clarify.py`) to in-process calls; update prompt, doc, lint, and Makefile references; append to `python/migrated-scripts.tsv`.

### Surfaces in scope
- Runtime: `python/design_lifecycle.py`, `python/design_summary.py`, `python/session_env.py`, `python/cli.py`, `python/plan_review.py`, `python/clarify.py`.
- Deletes: the 3 `.sh` plus `.md` plus their `test-design-*` shell harnesses; debug scaffolds `_dbg-stage.sh`, `_debug-step5c.sh`, `scripts/debug-step5c-once.sh`.
- Lint, docs, tests: `python/checks.py`, `Makefile`, `agent-lint.toml`, `docs/linting.md`, `SECURITY.md`, `python/migrated-scripts.tsv`, and the affected `python/test_*.py`.

### Open questions
- None. Caller files confirmed present this run; the drafter re-verifies exact call sites against current HEAD.
