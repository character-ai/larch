## Decision 1: Python module split
- **Question**: Single `plan_review.py` or split by concern?
- **Resolution**: Two modules: `plan_review_panel.py` (panel/voter dispatch) + `plan_review.py` (loop core, state management, tally, round artifacts, plan emit/finalize/preview, drift baseline, dedup, retally env).
- **Source**: user

## Decision 2: `review-design-step3-loop.sh` scope
- **Question**: Explicitly list `review-design-step3-loop.sh` (757 lines, sourced by `run-step3-review.sh`) as an absorb target?
- **Resolution**: Implicitly absorbed — its functions fold naturally into the Python port of `run-step3-review.sh`. No need to list separately.
- **Source**: user

## Decision 3: `design-step3-review.sh` wrapper cutover
- **Question**: Update the SKILL.md-facing bash wrapper in C3a1 or defer to C3b?
- **Resolution**: Update `design-step3-review.sh` in C3a1 to call `python3 cli.py plan-review run` (or equivalent verb). Wrapper stays bash; only the inner call changes.
- **Source**: user

## Decision 4: `snapshot-plan-round.sh` status
- **Question**: Issue body lists it (119 lines); file not in source tree.
- **Resolution**: Skip. Functionality is already inlined into `plan-review-loop.sh` (`_snapshot_round_dir` + related functions at lines 399–730). The runtime test stub (created in fake_design dir) confirms no standalone script exists. Do not create a Python CLI verb for it separately; the logic is part of the loop.
- **Source**: codebase

## Decision 5: `snapshot-plan-round.sh` assessor path
- **Question**: SECURITY.md references `snapshot-plan-round.sh revert-round` for the Step 3.6 assessor flow.
- **Resolution**: Assessor scripts (`assess-plan-round.sh`, `dispatch-plan-assessors.sh`, `tally-plan-assessor.sh`) are NOT in C3a1 scope. That `snapshot-plan-round.sh` reference is in a different subsystem.
- **Source**: codebase

## Decision 6: `dedup-plan-lines.py` handling
- **Question**: `gate-b-dedup-plan.sh` uses `dedup-plan-lines.py` from `skills/design/scripts/`. Should that Python file be moved?
- **Resolution**: Keep `dedup-plan-lines.py` in-place for now (it's a standalone utility). The Python port of `gate-b-dedup-plan.sh` will call it as a subprocess or import it directly. Deferred cleanup is C3b scope.
- **Source**: codebase

## Decision 7: Hard constraints to preserve
- `LOOP_STATUS` enum values must be byte-identical (bash wrappers read them).
- `.step3-review-result.env` and `.step3-plan-review-result.env` file formats must be preserved.
- `review-round-count.txt` management semantics: persist before launch, roll back on tally-error/degraded-empty-collector.
- Per-round artifact structure under `plan-review/round-N/` must be preserved.
- `lib-quiet.sh` fd-3 KV contract: Python uses `emit_kv`/`logging_util` equivalents.
- **Source**: codebase
