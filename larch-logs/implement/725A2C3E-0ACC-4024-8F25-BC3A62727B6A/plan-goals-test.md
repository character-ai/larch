## Goal
Implement issue #4325: [IMPLEMENTING] /design terminal: failed-publish at design-publish via failed (unrecoverable at publish).

## Implementation Plan
## Plan

## Approach

- Use the approved outline as binding scope.
- `approach-synthesis.txt` is exactly `NO_SKETCHES`, so base the plan on direct code inspection.
- Keep the fix narrow:
  - read `SESSION_ID` from `source-env.sh` for design reports,
  - prevent `STAGED=false` from aborting `design-publish.sh`,
  - prove `ROOT_CAUSE_HINT=environment` reaches the public report.

## Files to modify/create

### UPDATED: skills/implement/scripts/stall-recovery-report.sh

- Add a small helper near `kv_get` or `read_run_id` to read `SESSION_ID` from `source-env.sh`.
  - `source-env.sh` uses `export SESSION_ID='<UUID>'` format (single-quoted, written by `_export_line` in `python/session_env.py:568-569`).
  - Strip leading/trailing single and double quotes from the extracted value. Pattern: same as `source_env_get` in `scripts/design-pause-save.sh:30-46`.
  - Use awk (not `session read-key`/`kv_get`): those only match `KEY=value`, not `export KEY=value`.
  - Return empty on missing, unreadable, or malformed input.
  - Pass the stripped value through `safe_run_id_value` as the final sanitizer.
- Update `read_run_id()` to include the design fallback:
  - existing `parent-issue.md` `RUN_ID`,
  - existing runtime state files,
  - `source-env.sh` `SESSION_ID`,
  - then `unknown`.
- Keep `safe_run_id_value` as the final sanitizer.
- Update `compose_tier_a_issue()` to print `read_run_id "$tmpdir"` instead of reading only `parent-issue.md`.
- Do not change Branch or PR URL behavior.

### UPDATED: skills/design/scripts/design-publish.sh

- Set `SESSION_ENV_PATH` to `source-env.sh` when it exists.
  - Fall back to `session-env.sh` for older tests or older tmpdirs.
- Add `|| true` to both direct `stage_design_terminal_state` call sites:
  - failed plan write,
  - failed publish.
- Leave `stage_design_terminal_state()` itself unchanged.
  - It may still return `1` for `STAGED=false`.
  - Callers decide whether that is fatal.
- Keep `ROOT_CAUSE_HINT=environment` on the failed-publish staging call.

### UPDATED: skills/design/scripts/test-design-failure-report.sh

- Extend `stage_terminal()` to accept optional extra arguments.
- Add a case that stages `failed-publish` with `--root-cause-hint environment`.
- Write `source-env.sh` with an exported `SESSION_ID`.
- Run `design-failure-report.sh`.
- Assert:
  - `design-failure-root-cause.md` contains `verdict=environment`,
  - the generated issue or chat artifact contains `verdict=environment`,
  - the report metadata contains the `SESSION_ID` value as Run ID.

### UPDATED: skills/design/scripts/test-design-stage-terminal-state.sh

- Add a preservation case that stages one terminal state, then calls `design-stage-terminal-state.sh` for a different outcome; assert `STAGED=false` and `PRESERVED=true` in stdout.
- This tests the helper's preservation behavior only.

### UPDATED: skills/design/scripts/test-design-publish.sh

- Add an integration case that exercises the `set -e` abort path in `design-publish.sh`:
  - Pre-seed `design-failure-terminal-state.env` with a different `FAILURE_OUTCOME` (e.g. `failed-plan-write`) to trigger `STAGED=false` on the `failed-publish` staging call.
  - Stub `design-log-publish.sh` to return non-zero (simulate failed publish).
  - Run `design-publish.sh` on the failed-publish path with `PLAN_WRITE_OK` already set.
  - Assert `design-publish.sh` exits 0 (not killed by `set -e`).
  - Assert `final-summary.md` is non-empty.
  - Assert `.design-publish-result.env` contains `PUBLISH_OK=false`.

## Edge cases

- `source-env.sh` may be absent in old tmpdirs. Fall back without error.
- `source-env.sh` uses exported shell syntax. Do not rely only on `session read-key`.
- A preserved terminal state is useful evidence. It must not abort publish result recording.
- A malicious or malformed `SESSION_ID` must become `redacted` or `unknown` through the existing sanitizer.

## Failure modes

- If `stage_design_terminal_state` fails for a real validation error, `design-publish.sh` should still record publish results and render the final summary.
- If `source-env.sh` cannot be parsed, reports should keep `Run ID: unknown`.
- If the environment root-cause hint is not propagated, the new test should fail before filing behavior changes ship.

## Testing strategy

- Run targeted tests:
  - `bash skills/design/scripts/test-design-failure-report.sh`
  - `bash skills/design/scripts/test-design-stage-terminal-state.sh`
  - `bash skills/design/scripts/test-design-publish.sh`
  - `bash skills/implement/scripts/test-stall-recovery-report-3.sh`
- Then run the repo-relevant check:
  - `bash scripts/relevant-checks.sh`

## Acceptance

- `Run ID` in design terminal failure reports is populated from `source-env.sh SESSION_ID` (not `unknown`).
- `design-publish.sh` exits 0 when `stage_design_terminal_state` returns 1 (STAGED=false), with `PUBLISH_OK=false` recorded in result env.
- `verdict=environment` appears in the filed root-cause finding when `ROOT_CAUSE_HINT=environment` was staged.
- All targeted tests pass: `test-design-failure-report.sh`, `test-design-stage-terminal-state.sh`, `test-design-publish.sh`, `test-stall-recovery-report-3.sh`.
- `bash scripts/relevant-checks.sh` passes without new failures.

diff_lines: 104

## Test plan
(no test plan section in plan-file)
