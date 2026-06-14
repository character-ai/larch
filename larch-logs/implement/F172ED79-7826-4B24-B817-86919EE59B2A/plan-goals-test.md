## Goal
Implement issue #4290: [IMPLEMENTING] [BUG] design-step3-review.sh exits silently when phase_driver_write_result_env fails: STEP3_REVIEW_LOOP_STATUS never surfaced to orchestrator.

## Implementation Plan
## Plan

## Approach

- Keep the fix narrow.
- Treat `phase_driver_write_result_env` failure as an observability failure in the Step 3 loop.
- Do **not** convert an operational loop status to `panel-failed` inside `step3_loop_persist_envelope`.
- Use `design-step3-review.sh` as the production handoff fallback.
- Preserve existing review, voting, and postplan logic.
- Add a wrapper regression for the missing-result-env case where child stdout already carries `STEP3_REVIEW_LOOP_STATUS`.
- Keep `LOOP_STATUS=zero-findings-degraded-panel` recovery out of scope.
- Do **not** map `LOOP_STATUS=zero-findings-degraded-panel` to `STEP3_REVIEW_LOOP_STATUS=complete`.
- Add `/dev/null` stdin redirection to the Cursor branch in `scripts/launch-review.sh`.
- Do **not** edit Codex launch branches. Codex already gets `stdin=subprocess.DEVNULL` through `run-external-agent`.
- Do **not** touch `dispatch-plan-voters.sh`.

## Files to modify/create

### UPDATED: `skills/design/scripts/review-design-step3-loop.sh`

- Add a small helper near `step3_loop_persist_envelope`, for example `step3_loop_record_result_env_write_failure`.
- In the helper:
  - Allocate the diagnostic file with `mktemp` under `$DESIGN_TMPDIR`, for example `"$DESIGN_TMPDIR/step3-result-env-write.failure.XXXXXX.log"`.
  - Do not use a predictable diagnostic filename.
  - If `mktemp` fails, skip `append-failure` and keep the loop alive.
  - Include the attempted result env basename, original Step 3 status, mapped `LOOP_STATUS`, round, and reason `phase_driver_write_result_env failed`.
  - Best-effort call:
    - `python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure`
    - `--log "$DESIGN_TMPDIR/execution-issues.md"`
    - `--site "design Step 3 review loop"`
    - `--tool "phase_driver_write_result_env"`
    - `--exit-code 1`
    - `--category "Tool Failures"`
    - `--output-file "$diag_file"`
    - `--redact`
  - Resolve `PLUGIN_ROOT` from `${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}`.
  - Suppress helper stdout/stderr.
  - Never fail the loop because diagnostic allocation or failure logging failed.
- In the existing `if ! phase_driver_write_result_env ...` branch:
  - Keep the existing `emit`/`emit_kv WARN` behavior (no new raw stderr).
  - Call the new failure-log helper.
  - Do **not** emit fallback `STEP3_REVIEW_LOOP_STATUS=panel-failed`.
  - Do **not** emit fallback `LOOP_STATUS=panel-failed`.
  - Do **not** emit any replacement status that can clobber the operational status already emitted by `step3_loop_emit_envelope`.
- Rationale:
  - `step3_loop_emit_envelope` emits the real status before persistence.
  - Persist failure must not overwrite `main-agent-vote-required` or similar operational states.
  - `design-step3-review.sh` owns the final production fallback when no usable Step 3 status reaches the wrapper.

### UPDATED: `skills/design/scripts/design-step3-review.sh`

- Replace the existing elif block (lines 458–461) that sets only `LOOP_STATUS=panel-failed` with a broader guard.
- After `_safe_step3_env` sourcing and `_plan_review_stdout_file` merge, before the status normalization block:
  - If `STEP3_REVIEW_LOOP_STATUS` is empty:
    - If `LOOP_STATUS` is a known recoverable loop token, map it back to `STEP3_REVIEW_LOOP_STATUS`:
      - `complete` → `complete`
      - `cap-reached` → `cap-hit`
      - `main-agent-vote-required` → `main-agent-vote-required`
      - `main-agent-apply-required` → `main-agent-apply-required`
      - `per-round-approval-required` → `per-round-approval-required`
      - `postplan-operator-required` → `postplan-operator-required`
      - `postplan-failed` → `postplan-failed`
      - `panel-failed` → `panel-failed`
      - `tally-error` → `tally-error`
      - `degraded-empty-collector` → `degraded-empty-collector`
    - If `LOOP_STATUS=zero-findings-degraded-panel`, do not map; preserve existing legacy routing.
    - Otherwise (truly empty or unrecognized): emit `**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**` via `larch_err`; set `STEP3_REVIEW_LOOP_STATUS=panel-failed` and `LOOP_STATUS=panel-failed`.
- The existing printf block at lines 463–464 emits both KVs to orchestrator stdout.
- Do not print prose to stdout.
- Ensure `STEP3_REVIEW_LOOP_STATUS` is always set (never empty) before reaching line 463.

### UPDATED: `scripts/launch-review.sh`

- Add stdin redirection to the Cursor launch branch only:
  - Put `< /dev/null` on the outer `run-external-agent ... -- cursor agent ... "$WRAPPED_PROMPT"` command.
  - Preserve `2>>"$_STDERR_TARGET"` and backgrounding.
- Do not change command argv.
- Do not add stdin handling to Codex launch branches (already handled by `run-external-agent`).
- Do not touch `dispatch-plan-voters.sh`.

### UPDATED: `skills/design/scripts/review-design-step3-loop.md`

- Document that `phase_driver_write_result_env` failure now records a Tool Failures entry in `execution-issues.md` when possible.
- State that persist failure does not emit replacement Step 3 status KVs.
- Clarify that `design-step3-review.sh` is the production handoff fallback.

### UPDATED: `skills/design/scripts/design-step3-review.md`

- Document the replacement guard for the existing elif.
- State that an empty `STEP3_REVIEW_LOOP_STATUS` after merge is repaired from a valid recoverable `LOOP_STATUS` when possible.
- State that `LOOP_STATUS=zero-findings-degraded-panel` is not newly mapped.
- State that unrecoverable empty state degrades to `panel-failed`.

### UPDATED: `scripts/launch-review.md`

- Add invariant: Cursor review subprocess runs with stdin from `/dev/null`.
- State that Codex stdin is intentionally unchanged.

### UPDATED: `skills/design/scripts/test-review-design-step3-loop.sh`

- Add regression: symlink `.step3-review-result.env` to trigger symlink guard, call `step3_loop_emit_envelope main-agent-vote-required 1 1 1`.
- Assert: stdout contains `STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required`, does NOT contain `STEP3_REVIEW_LOOP_STATUS=panel-failed`, `$DESIGN_TMPDIR/execution-issues.md` contains `phase_driver_write_result_env`.
- Bash 3.2-safe.

### UPDATED: `skills/design/scripts/test-design-step3-review.sh`

- Add runtime wrapper regression with fake plugin root (fake `run-step3-review.sh` exits 0, writes no KVs).
- Assert stdout: `STEP3_REVIEW_LOOP_STATUS=panel-failed`, `LOOP_STATUS=panel-failed`.
- Assert stderr: new missing-result warning.
- Add regression: fake `run-step3-review.sh` emits only legacy `LOOP_STATUS=panel-failed`.
- Assert stdout: `STEP3_REVIEW_LOOP_STATUS=panel-failed` (recovered via back-map).

### UPDATED: `scripts/test-launch-review.sh`

- Extend Codex stub to optionally record fd 0 when `CODEX_STUB_FD0_LOG` is set.
- Add Cursor assertion: fd 0 resolves to `/dev/null` on a normal success path; tolerant of platforms where fd probing returns empty.
- Add Codex assertion: same pattern, verifies Codex stdin is not broken.

### UPDATED: `skills/design/scripts/test-review-design-step3-loop.md`, `test-design-step3-review.md`, `scripts/test-launch-review.md`

- Describe new regression cases in each sibling doc.

## Edge cases

- If `.step3-review-result.env` is a symlink, do not overwrite it.
- If `mktemp` fails while writing the primary result env, still emit fallback KVs.
- If the failure diagnostic file cannot be written, still emit fallback KVs and existing signals.
- If `python3` or `python/cli.py` is unavailable, skip failure logging and keep the handoff alive.
- If only a valid legacy `LOOP_STATUS` exists, back-map to `STEP3_REVIEW_LOOP_STATUS` rather than degrading.
- Keep all fallback KVs single-line.

## Failure modes when non-trivial

- `append-failure` can fail. Treat it as non-fatal.
- The back-map table in `design-step3-review.sh` must stay in sync with the `STEP3_REVIEW_LOOP_STATUS` allowlist at line 449. If a new status token is added to the allowlist, add it to the back-map table.
- Redirecting stdin on the outer wrapper depends on the child inheriting stdin from `run-external-agent`. This is the current launch shape and avoids argv changes.

## Testing strategy

- Run targeted tests:
  - `bash skills/design/scripts/test-review-design-step3-loop.sh`
  - `bash skills/design/scripts/test-design-step3-review.sh`
  - `bash scripts/test-launch-review.sh`
- Run repository relevant checks: `bash scripts/relevant-checks.sh`
- No `SECURITY.md` update needed.

## Acceptance

This plan is accepted when:
- `step3_loop_persist_envelope` failure records a Tool Failures entry in `execution-issues.md` and emits the existing FD-3 warning signals without adding raw stderr.
- `design-step3-review.sh` always sets `STEP3_REVIEW_LOOP_STATUS` before the printf block, either via back-map from a valid `LOOP_STATUS` or via the fallback to `panel-failed`.
- Cursor review subprocess runs with `< /dev/null`.
- All three regression harnesses pass.

diff_lines: 165

## Test plan
(no test plan section in plan-file)
