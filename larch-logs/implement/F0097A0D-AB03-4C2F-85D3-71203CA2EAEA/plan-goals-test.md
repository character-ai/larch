## Goal
Implement issue #6437: [IMPLEMENTING] [BUG] ci-fix: gh run-logs truncates to 100 lines, hiding most failing CI checks.

## Implementation Plan
## Plan

## Approach

Use the approved simple fix.

- Return the full `gh run view --log-failed` output from `run_logs_failed`.
- Remove the hardcoded `tail_lines=100` behavior and update the header text so it no longer claims a tail.
- Keep the same exit codes:
  - `0` when logs are ready.
  - `3` when GitHub says logs are still in progress.
  - `1` for other `gh` failures.
- Reword ci-fix Step 6 as a hard rule:
  - enumerate every failing job or check in the captured log,
  - fix all revealed failures before checks, staging, commit, push, and ship re-entry,
  - treat the 30-attempt counter as a safety net for flaky or newly surfaced failures.
- Keep scope tight. Do not add `--tail-lines`, `--all`, per-job log calls, sentinel changes, health-check changes, or attempt-counter changes.

## Files to modify/create

### UPDATED: python/larch/git/gh.py

- Change `run_logs_failed` so it no longer slices `combined.splitlines()[-tail_lines:]`.
- Remove the `tail_lines` parameter if no caller needs it.
- Build `text` from the pointer plus the full combined stdout and stderr.
- Preserve newline behavior:
  - pointer always ends with one newline,
  - non-empty combined output ends with one trailing newline,
  - empty combined output still prints the pointer.
- Update the pointer wording from `last 100 lines shown` to wording such as `failed log shown` or `failed-job log shown`.
- Keep `run_logs_main` arguments unchanged: only `--run-id` and `--repo`.

### UPDATED: python/tests/git/test_gh.py

- Replace `test_run_logs_main_tails_raw_log` with a regression test for full output.
- Use a fake `--log-failed` payload longer than 100 lines.
- Include distinct markers near the beginning, middle, and end, representing separate failed jobs.
- Assert all markers survive in stdout.
- Assert the old `last 100 lines shown` phrase is absent.
- Keep the existing in-progress and failure tests, but update expected pointer text if needed.

### UPDATED: skills/implement/references/ship-pr-ci-fix.md

- Keep Step 5 command shape unchanged.
- Reword Step 6 from singular minimal-edit wording to a hard all-revealed-failures rule.
- Make clear that the agent must inspect the redacted capture, enumerate every failing job/check it reveals, and fix all actionable failures before Step 7 through Step 12.
- State that repeated attempts remain for flaky, environmental, or newly surfaced failures, not for one-known-failure-per-push workflow.

### UPDATED: scripts/test-implement-structure.sh

- Replace the stale `Make the minimal repo edit` needle with a stable phrase from the new all-failures rule.
- Keep the assertion in place; only the required substring changes.

### UPDATED: scripts/test-implement-step8-exit3-first-fixer.sh

- Replace the stale `Make the minimal repo edit` needle with the same stable phrase chosen for the new all-failures Step 6 rule.
- Use the identical anchor substring as `test-implement-structure.sh` to keep both harnesses in sync.

## Edge cases

- If `gh run view --log-failed` returns non-zero with useful stderr, include that stderr in the emitted log just as today.
- If the run is still in progress, keep returning exit `3` after printing the pointer and any GitHub message.
- If the log is large, allow the caller to redirect it to the redacted tmpdir file. This path is file-destined by design.
- Do not redact in `gh run-logs`; the existing Step 5 pipe to `redact secrets` owns redaction.

## Failure modes

- A stale test may still assert `last 100 lines shown`; update only tests tied to this CLI behavior.
- Very large logs may increase tmpdir artifact size, but this is preferable to hiding failed jobs.
- Adjacent Python CI monitor helpers still have their own tailing behavior. Treat that as outside this approved surface unless Gate C expands scope.

## Testing strategy

Run changed-file checks only:

- `python3 -m pytest python/tests/git/test_gh.py -k run_logs`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`

## Acceptance

Run changed-file checks only:

- `python3 -m pytest python/tests/git/test_gh.py -k run_logs`
- `bash scripts/test-implement-structure.sh`
- `bash scripts/test-implement-step8-exit3-first-fixer.sh`

mechanical_churn: false
diff_lines: 55

## Test plan
(no test plan section in plan-file)
