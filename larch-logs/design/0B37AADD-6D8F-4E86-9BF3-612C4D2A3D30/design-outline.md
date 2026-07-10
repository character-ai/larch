## Proposed Design Outline

### Goals
- Stop the progress statusline from rendering a previous run's breadcrumb at new-job start and at Claude start.
- Clear the active-run `current` pointer at run end, bail, and pause across `/design` and `/implement`.
- Keep an orphaned old-run daemon from contaminating a newer run's log or masking staleness.

### Non-goals
- No terminal "run complete" marker and no visibility-window knob. Silent clear only.
- No change to reap for a live in-budget bgjob that belongs to the active run.
- No redesign of the breadcrumb format or statusline layout beyond run-id scoping.

### Approach sketch
- RC1: add a `progress deactivate` CLI verb wrapping existing `deactivate_run`; call it at design Step 5 finalize and bail, implement Step 18/cleanup and bail, and pause-save.
- RC2: activate the run at the top of Step 0 before reviewer probes in `design_step0.py` and `bootstrap.py`; make `--resume-plan-tail` re-activate its run id.
- RC3: add `resume`/`compact` to `RESET_SESSION_SOURCES` and scope the reset veto plus stale-suffix/hide suppression to bgjobs whose registry `RUN_ID` matches the active run.
- RC4: route daemon-side writers through `append_breadcrumb_for_run` / `progress note --run-id` so they write their own run id, not `current`.
- Update `docs/progress-reporting.md`; add and extend progress/statusline tests.

### Surfaces in scope
- `python/larch/report/statusline.py`, `python/larch/report/progress_file.py`, `python/larch/cli.py`
- `python/larch/design/design_step0.py`, `python/larch/state/bootstrap.py`
- pointer-following writers: `review_core_body.py`, `review_and_fix.py`, `plan_review.py`, `plan_review_round.py`, `ci_monitor.py`, `ship_state.py`, `timing.py`
- `/design` and `/implement` end/bail/pause call sites; `docs/progress-reporting.md`; progress tests.

### Open questions
- Exact bail/pause call sites that must invoke `progress deactivate` (resolved during drafting).
- Whether RC4 changes writer signatures or adds run-id-aware call paths (resolved during drafting/review).
