## Final Design Plan

The plan is very large. Showing the full plan body below.

## Plan

Scope follows the approved outline and discussion constraints. `NO_SKETCHES` was present, so this plan uses direct repository inspection only.

## Approach

- Treat #6591 as likely covered by the shared fixes (#6580 stable `LARCH_CLAUDE_PID`, #6595 daemon owner-validation hardening).
- Add static regression tests that pin the shared launcher owner-pid contract without a live end-to-end harness kill.
- Keep all tests fake-time or static. Do not use real sleeps.
- Do not change daemon or launcher code unless the new tests expose a real Step 3 gap.
- During `/implement`, after tests pass, post one correcting comment on #6591 with `gh issue comment 6591 --body-file <file>`. Do not reopen #6591. Do not change its close reason. Verify the comment with a read-back command.

## Static confirmation from drafting

- Step 3 uses `skills/implement/scripts/run-step-checks.sh`, step slug `implement-step3-checks`, and passes `--owner-pid "${LARCH_CLAUDE_PID:-$PPID}"`.
- The shared implement runner exports `LARCH_CLAUDE_PID="${LARCH_CLAUDE_PID:-<pid>}"`, so Step 3 should inherit the stable session owner instead of a transient foreground wrapper pid.
- The daemon already uses a consecutive owner-validation failure threshold and grace window before declaring `BGJOB_RC=orphaned`.
- Step 7a launches bgjob through Python and does not pass `--owner-pid`; `bgjob start` falls back to `LARCH_CLAUDE_PID` when the arg is empty. Existing daemon coverage in `test_owner_identity_from_env_uses_session_pid_env` already pins that fallback; extend the Step 7a launch test to assert argv omits explicit `--owner-pid`.
- `skills/implement/scripts/step-5-resume.sh:217` hardcodes `STEP="implement-step5-resume"`; treat that slug as a fixed literal in tests, not a dynamic `$STEP` variable.
- `skills/implement/scripts/step-8-ship.sh:309-316` passes `--owner-pid` and `--merge-result-env` only; it does not pass `--sentinel`.

## Files to modify/create

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add a parameterized static regression test for shared implement bgjob launcher surfaces.

Cover these cases with fixed expected step slugs:

| Case | Launcher script | Expected step slug |
|------|-----------------|-------------------|
| `step3` | `skills/implement/scripts/run-step-checks.sh` (site `step3`) | `implement-step3-checks` |
| `step5` | `skills/implement/scripts/step-5-review.sh` | `implement-step5-review` |
| `step5-resume` | `skills/implement/scripts/step-5-resume.sh` | `implement-step5-resume` |
| `step6` | `skills/implement/scripts/step-6-entry.sh` | `implement-step6-checks` |
| `step8` | `skills/implement/scripts/step-8-ship.sh` | `implement-step8-ship` |

For every row, assert the shell launcher passes:

- `bgjob start`
- the fixed expected step slug from the table above
- `--owner-pid "${LARCH_CLAUDE_PID:-$PPID}"`

Per-launcher merge/sentinel assertions (do not apply a uniform sentinel check to all rows):

- **step3, step5, step5-resume, step6**: also assert `--sentinel` and the stable merge-result env shape where already present in each script.
- **step8**: assert `--merge-result-env` only; do **not** require `--sentinel` (Step 8 omits it by design).

Keep the test narrow. It should prove the shared launcher steps do not regress back to transient `$PPID` ownership when `LARCH_CLAUDE_PID` is available, without overfitting dynamic slug names or forcing incorrect Step 8 sentinel expectations.

### UPDATED: python/tests/implement/test_step_7a.py

Extend `test_step7a_bgjob_launch_starts_transport` to assert:

- the launch argv still calls `bgjob start`
- it does **not** pass an explicit `--owner-pid` token
- owner resolution remains covered by existing daemon fallback tests (`test_owner_identity_from_env_uses_session_pid_env` in `python/tests/bgjob/test_daemon.py`)

This makes the Step 7a env-fallback contract explicit at the launch site without duplicating daemon-level owner-resolution coverage.

### MAY_UPDATE: python/tests/bgjob/test_bgjob_cli.py

Only update this file if review during `/implement` finds a gap that the dispatch launcher test plus existing daemon and Step 7a tests do not cover.

If needed, add a `cli.start_main(...)` capture test that:

- unsets or clears `LARCH_BGJOB_OWNER_PID`, `CLAUDE_PID`, and `LARCH_BG_POLL_GUARD_SESSION_PID` before setting `LARCH_CLAUDE_PID=12345` (mirror `test_owner_identity_from_env_fails_closed_without_session_pid` / `test_owner_identity_from_env_uses_session_pid_env` env hygiene in `python/tests/bgjob/test_daemon.py`)
- monkeypatches `daemon.start_daemon` to capture the `JobSpec` and avoid spawning a daemon
- calls `cli.start_main(...)` without `--owner-pid`
- asserts rc `0` and captured spec owner pid is `12345`

Prefer **not** adding this file unless the slimmer test set leaves Step 7a fallback untested.

### MAY_UPDATE: python/tests/bgjob/test_daemon.py

Only update this file if the new dispatch and Step 7a tests reveal a daemon-level false-orphan gap not already covered by `test_monitor_starts_owner_grace_after_consecutive_validation_failures`.

If needed, add a fake-time test where owner validation fails once or twice due to a transient probe failure, then succeeds, and assert the child is not killed as orphaned.

Do not use real sleeps. Monkeypatch `time.monotonic`, `time.sleep`, and process validation as existing tests do.

## Issue comment step

After the regression tests pass, write a file-backed body under the implementation tmpdir, then run:

- `gh issue comment 6591 --body-file <body-file>`

Body content should say:

- #6591 matched the same harness-kill false-orphan class as #6580 and #6595.
- Step 3 uses the shared `LARCH_CLAUDE_PID` owner path.
- The behavior is now pinned by the new regression test names.
- The issue remains closed as-is per operator direction. This is a correcting comment only.

Then verify with a read-only GitHub command, for example:

- `gh issue view 6591 --comments`

If GitHub is unavailable, report that code/tests are done but the tracker comment was not posted.

## Edge cases

- Step 7a uses env fallback instead of explicit `--owner-pid`; cover launch argv omission plus existing daemon fallback tests, not a duplicate CLI capture test unless the MAY_UPDATE path triggers.
- `LARCH_CLAUDE_PID` may be absent; shell launchers still fall back to `$PPID`. Do not remove that fallback.
- Step 5 resume slug is static (`implement-step5-resume`); do not derive it from wrapper-local `$STEP` variables in assertions.
- Step 8 has no `--sentinel`; do not add one to satisfy a shared assertion helper.
- Avoid asserting brittle line numbers or exact large source slices.
- Do not add an end-to-end 120s harness-kill test.
- Do not mutate #6591 during design.

## Failure modes

- A test may expose that one launcher bypasses `LARCH_CLAUDE_PID`. If so, make the smallest production fix for that launcher and add the matching test assertion.
- A GitHub write may fail. Stop and surface the failure. Do not claim the tracker correction was posted.
- A daemon-level test can become flaky if it uses real time. Use injected monotonic values and no-op sleep.
- A CLI owner-fallback test that leaves higher-priority env vars set (`LARCH_BGJOB_OWNER_PID`, `CLAUDE_PID`) can pass without exercising the Step 7a `LARCH_CLAUDE_PID` path; clear them if the MAY_UPDATE CLI test is added.

## Testing strategy

Run only changed-file tests:

- `python3 -m pytest python/tests/implement/test_implement_dispatch.py python/tests/implement/test_step_7a.py`
- Add `python/tests/bgjob/test_bgjob_cli.py` or `python/tests/bgjob/test_daemon.py` only if those MAY_UPDATE files change.

Then run the relevant lint target for changed Python files if available in the repo workflow, for example:

- `make py-lint`

Do not run broad unrelated suites unless the changed tests reveal a shared failure.

difficulty: MODERATE
diff_added: 75
diff_deleted: 0
mechanical_churn: false
diff_lines: 75
