## Proposed Design Outline

### Goals
- On `resume@<STEP>`, refresh `source-env.sh` with `ISSUE_NUMBER` and `REPO` so Step 5c publish receives a non-empty `--issue`.
- Add a test asserting the resumed `source-env.sh` carries these values.

### Non-goals
- Do not re-run init-runparams (rename, write-run-params) on resume paths.
- Do not change the pause/save format or route-state env schema.
- Do not fix the `.completed/step-3` snapshot exclusion (separate concern).

### Approach sketch
- In `_finish_step0_route()` in `design_step0.py`, when `route.startswith("resume@")`, call `session write-design-env` as a subprocess with `ISSUE_NUMBER`, `REPO`, and `SESSION_ID` from `ctx.env`.
- Emit a warning and return non-zero if the call fails, to fail early instead of failing at Step 5c.
- Add `test_step0_route_resume_rehydrates_source_env` to `test_design_lifecycle.py` using the existing `monkeypatch` pattern.

### Surfaces in scope
- `python/larch/design/design_step0.py` (`_finish_step0_route`)
- `python/tests/design/test_design_lifecycle.py`

### Open questions
- None.
