## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Implement the approved outline from direct repo inspection.
- Keep marker format unchanged: `PID`, `CLAUDE_PID`, `START_EPOCH`, `STEP`, `TIMEOUT_S`.
- Add only additive hook registrations and tests.
- Arm markers at the real outer background boundary:
  - `implement-step7a`: `python/cli.py implement step-7a`.
  - `implement-step6-checks`: `skills/implement/scripts/step-6-entry.sh`.
  - `implement-step5-resume`: `python/cli.py implement checks-step5-resume`.
  - `design-step4-tail`: `skills/design/scripts/design-step3b-tail.sh`.
- Also cover direct `checks-commit-route` background call sites found in the repo:
  - `implement-step3-checks`.
  - `implement-step5-self-review`.
  - Do not add nested markers when an outer wrapper already owns the marker.

## Files to modify/create

### UPDATED: python/larch/implement/step_7a.py

- Add small fail-open marker helpers local to this module or a private context manager:
  - create `$IMPLEMENT_TMPDIR/.bg-wait-active`.
  - clear no-progress sidecars before writing.
  - write `.completed/step-7a-terminal` before marker removal.
  - remove `.bg-wait-active` in `finally`.
- Wrap `run_step7a()` body after `implement_tmpdir.mkdir(...)` in the marker context.
- Use `STEP=implement-step7a`.
- Use `TIMEOUT_S=1800`.

### UPDATED: python/larch/implement/dispatch_commit_route.py

- Add marker support around Python-owned composite background boundaries.
- Wrap `checks_step5_resume_main()` with:
  - `STEP=implement-step5-resume`.
  - terminal sentinel `.completed/step-5-resume-terminal`.
  - timeout `32700`.
- For `checks_commit_route_main()`, arm markers only for direct background call sites that do not already have an outer wrapper marker:
  - `--checks-site step3`: `STEP=implement-step3-checks`, sentinel `.completed/step-3-terminal`, timeout `15600`.
  - `--checks-site step5-self-review`: `STEP=implement-step5-self-review`, sentinel `.completed/step-5-self-review-terminal`, timeout `14700`.
- Do not write a nested marker for `--checks-site step6` when invoked through `step-6-entry.sh`.
- Keep marker writes fail-open.
- Preserve existing stdout envelopes and return codes.

### UPDATED: skills/implement/scripts/step-6-entry.sh

- Add an EXIT trap at the outer wrapper boundary.
- Clear stale no-progress sidecars before writing marker.
- Write `.bg-wait-active` with `STEP=implement-step6-checks` and `TIMEOUT_S=15600`.
- On EXIT, write `.completed/step-6-terminal` before removing `.bg-wait-active`.
- Keep existing rehydration and `python3 ... implement step-6-entry "$@"` behavior unchanged.

### MAY_UPDATE: skills/implement/scripts/step-5-resume.sh

- Prefer no change if `checks_step5_resume_main()` owns the outer marker.
- Only update this file if implementation discovers a remaining direct background launch of this wrapper.
- Do not create nested marker thrash under `checks-step5-resume`.

### UPDATED: skills/design/scripts/design-step3b-tail.sh

- Add an EXIT trap around the Step 4 tail.
- Clear stale no-progress sidecars before writing marker.
- Write `.bg-wait-active` with `STEP=design-step4-tail` and `TIMEOUT_S=900`.
- Reuse `.completed/step-4` as the terminal sentinel.
- Ensure cleanup writes `.completed/step-4` before marker removal on all terminal paths.
- Preserve current rejected-findings, dialectic, preview, and `SKIP_APPROVE_REQUESTED_GATEC` stdout contracts.

### UPDATED: scripts/hook-bg-poll-guard.sh

- Extend `marker_step_completed` with:
  - `design-step4-tail` -> `.completed/step-4`.
  - `implement-step7a` -> `.completed/step-7a-terminal`.
  - `implement-step6-checks` -> `.completed/step-6-terminal`.
  - `implement-step5-resume` -> `.completed/step-5-resume-terminal`.
  - `implement-step5-self-review` -> `.completed/step-5-self-review-terminal`.
- Extend `reset_probe_counter_for_step` with matching sentinel names.
- Extend `probe_sentinel_name` and `bash_is_terminal_sentinel_foreground_probe` so `.completed/step-4` is an allowed design foreground probe.
- Do not add foreground-probe allowances for implement Step 7a, Step 6, Step 5-resume, or Step 5 self-review.
- Keep deny behavior fail-open on malformed markers.

### UPDATED: scripts/hook-no-progress-guard.sh

- Mirror the new `STEP` to sentinel mappings in `is_step_completed`.
- Add tests that the no-progress counter arms for each new live marker and auto-disarms when its terminal sentinel appears.
- Preserve symlink rejection for sentinels.

### UPDATED: scripts/test-hook-bg-poll-guard.sh

- Add assertions for all new marker steps:
  - Monitor and TaskOutput deny while marker is live.
  - ordinary tmpdir probes deny while marker is live.
  - terminal sentinel releases the marker.
  - symlink sentinels do not release.
- Add Step 4 foreground probe assertions:
  - `[ -f "$DESIGN_TMPDIR/.completed/step-4" ] && echo DONE || echo WAIT` allows while `design-step4-tail` is live.
  - repeated absent probes clamp.
  - non-Step-4 probes still deny.
- Add implement notification-only assertions that Step 7a, Step 6, Step 5-resume, and Step 5 self-review do not gain foreground probe carve-outs.

### UPDATED: scripts/test-hook-no-progress-guard.sh

- Add no-progress coverage for:
  - `design-step4-tail`.
  - `implement-step7a`.
  - `implement-step6-checks`.
  - `implement-step5-resume`.
  - `implement-step5-self-review`.
- Assert each marker increments the counter while live.
- Assert each terminal sentinel clears the breaker.
- Assert symlink sentinels do not complete the wait.

### UPDATED: skills/shared/design-background-wait.md

- Confirm `.completed/step-4` is a valid foreground terminal sentinel for Step 4 tail recovery.
- State that Step 4 tail now arms `.bg-wait-active` with `STEP=design-step4-tail`.
- Keep the existing rule: one foreground non-sleeping probe only after a non-empty premature notification.

### NEW: python/larch/lint/lint_bg_wait_coverage.py

- Add a structural lint for `skills/{design,implement,review,review-and-fix}/**/*.md`.
- Find `run_in_background: true` launch directives and the nearby Bash fence they describe.
- Map each launch command to an expected marker step.
- Fail when a background launch has no known marker-backed command mapping.
- Include current known background commands:
  - `design-step3-review.sh`.
  - `design-step5c.sh`.
  - `design-step-final-summary.sh`.
  - `design-step3b-tail.sh`.
  - `python/cli.py implement checks-commit-route --checks-site step3`.
  - `python/cli.py implement checks-commit-route --checks-site step5-self-review`.
  - `skills/implement/scripts/step-5-review.sh`.
  - `python/cli.py implement checks-step5-resume`.
  - `skills/implement/scripts/step-6-entry.sh`.
  - `python/cli.py implement step-7a`.
  - `skills/implement/scripts/step-8-ship.sh`.
- Fail on any `/review` or `/review-and-fix` background launch unless it is added to the marker-backed mapping.

### NEW: python/test_lint_bg_wait_coverage.py

- Add fixture tests for:
  - accepted current design and implement background launch patterns.
  - rejected review background launch without a marker mapping.
  - rejected unknown implement background launch.
  - accepted direct `checks-step5-resume`.
  - accepted Step 4 tail command.
- Keep tests offline and stdlib-only.

### UPDATED: python/larch/cli.py

- Register `("lint", "bg-wait-coverage")` to the new lint module.

### UPDATED: Makefile

- Add `lint-bg-wait-coverage`.
- Add `test-lint-bg-wait-coverage`.
- Wire `lint-bg-wait-coverage` into `lint`.
- Wire `test-lint-bg-wait-coverage` into one harness shard with nearby hook or lint tests.

### UPDATED: .pre-commit-config.yaml

- Add a local hook for `python3 python/cli.py lint bg-wait-coverage`.
- Use `pass_filenames: false`.
- Scope files to `skills/(design|implement|review|review-and-fix)/`.

### UPDATED: python/larch/implement/checks_run_relevant.py

- Add relevant-check routing entries for the new lint and test files:
  - `python/larch/lint/lint_bg_wait_coverage.py`.
  - `python/test_lint_bg_wait_coverage.py`.
  - `Makefile`.
  - `.pre-commit-config.yaml`.
- Route to `test-lint-bg-wait-coverage` and any needed hook tests.

## Edge cases

- Marker write failures must not abort the background job.
- Marker cleanup must run on non-zero exits.
- Terminal sentinels must not be symlinks.
- `design-step4-tail` must allow the sanctioned foreground `.completed/step-4` probe, otherwise the new marker would block the documented recovery path.
- Implement Step 7a, Step 6, Step 5-resume, and Step 5 self-review remain notification-only. Do not add foreground probe exceptions for them.
- Avoid nested marker cleanup races. The outer background boundary owns the marker.

## Failure modes

- If a marker remains after process exit, existing PID liveness and timeout reaping should release it.
- If a terminal sentinel is written but marker cleanup has not run yet, both hooks should release based on the sentinel.
- If Step 4 probe regex omits `step-4`, `hook-bg-poll-guard.sh` will deny the sanctioned recovery probe.
- If structural lint misses reference files, `/review` could regress into uncovered background mode.

## Testing strategy

- Run targeted shell harnesses:
  - `bash scripts/test-hook-bg-poll-guard.sh`
  - `bash scripts/test-hook-no-progress-guard.sh`
- Run new lint tests:
  - `python3 -m pytest python/test_lint_bg_wait_coverage.py -q`
- Run new lint directly:
  - `python3 python/cli.py lint bg-wait-coverage`
- Run changed Python tests for dispatch and Step 7a if touched:
  - `python3 -m pytest python/test_implement_dispatch.py -q`
  - existing Step 7a harness if available.
- Run changed shell syntax checks through existing targeted harnesses where practical.

## Acceptance

- Run targeted shell harnesses:
  - `bash scripts/test-hook-bg-poll-guard.sh`
  - `bash scripts/test-hook-no-progress-guard.sh`
- Run new lint tests:
  - `python3 -m pytest python/test_lint_bg_wait_coverage.py -q`
- Run new lint directly:
  - `python3 python/cli.py lint bg-wait-coverage`
- Run changed Python tests for dispatch and Step 7a if touched:
  - `python3 -m pytest python/test_implement_dispatch.py -q`
  - existing Step 7a harness if available.
- Run changed shell syntax checks through existing targeted harnesses where practical.

review_status: ok
rounds_completed: 1
diff_added: 650
diff_deleted: 60
mechanical_churn: false
diff_lines: 710
