## Goal
Implement issue #6444: [IMPLEMENTING] A few changes to final report in /design and /implement.

## Implementation Plan
## Plan

## Approach

Implement the approved outline in the shared final-summary renderer. Keep the heading unchanged: `## /<skill> run <run-id>: <raw-outcome>`.

Add a small outcome display mapper:

- `DONE` for success outcomes:
  - `/implement`: `merged`, `force-merged-externally`, `pr-created`, `pr-created-draft`, `design-only`, `forked-dry-run`
  - `/design`: `approved`, `approved-partition`
- `STALLED` for `stalled`
- raw outcome for all other values

Always emit `- **Outcome**: <display>` as the first bullet after the blank line. Remove only the `- **Mode**:` bullet. Keep `/implement` `- **Path**:` when `workflow_path` is present.

Update stalled-summary reconciliation to rewrite the `Outcome` bullet to `DONE` rather than delete it. Update the degraded `/design` fallback to use the shared mapper. Update tests to assert the new display values.

## Files to modify/create

### UPDATED: python/larch/git/pr_body.py

- Add a module-private `_map_outcome_display(outcome: str) -> str` helper.
- Use module-private frozen sets for success values.
- In `render_run_summary`:
  - Remove the existing conditional Outcome block entirely: `if outcome.startswith(("bailed", "stalled", "cancelled-", "failed-")) or outcome == "publish-skipped": lines.append(...)`.
  - Replace it with one unconditional first bullet: `lines.append(f"- **Outcome**: {_map_outcome_display(outcome)}")`.
  - Remove the `- **Mode**:` append (`if skill != "design": lines.append(f"- **Mode**: ...")`).
- Preserve existing `/implement`-only fields such as `Path`, `PR`, code review, line counts, and merge downgrade.

### UPDATED: python/larch/report/final_report.py

- In `reconcile_stalled_summary_from_manifest`: instead of `del lines[outcome_idx]`, rewrite that line to `- **Outcome**: DONE` (import and use `_map_outcome_display("merged")` from `pr_body` or hardcode the `DONE` constant — the outcome after reconciliation is always `merged`).
- Extend the post-rewrite safety guard (line 586 check) to reject both `stalled` and `STALLED` residue (case-insensitive or explicit alternation).
- Change `_summary_stalled_outcome_index` regex to match both `stalled` and `STALLED` for backward compat with legacy summaries.

### UPDATED: python/larch/design/design_summary.py

- In the degraded fallback writer (lines 644-652): import `_map_outcome_display` from `pr_body` (or define a thin local equivalent) and emit `- **Outcome**: {_map_outcome_display(outcome)}\n` instead of `f"- **Outcome**: {outcome}\n"`. This ensures `approved` shows `DONE` and `stalled` shows `STALLED` on the degraded path.

### UPDATED: python/tests/git/test_pr_body.py

- Add focused tests for outcome display mapping:
  - implement success maps to `DONE`
  - design success maps to `DONE`
  - `stalled` maps to `STALLED`
  - non-success outcomes stay raw
- Assert the `Outcome` bullet appears before `Path`, `Duration`, and other bullets.
- Assert implement summaries no longer include `- **Mode**:`.
- Adjust existing render-summary expectations that relied on successful outcomes omitting `Outcome`.

### UPDATED: python/tests/report/test_run_logs.py

- Add a reconciliation test with `- **Outcome**: STALLED` in the fixture (new format): verify reconciliation still fires and rewrites heading + replaces `STALLED` → `DONE`.
- Keep existing tests that use `- **Outcome**: stalled` (lowercase): these confirm backward compat with legacy summaries; verify the `Outcome` line is rewritten to `DONE`, not deleted.
- Assert that after successful reconciliation, `- **Outcome**: DONE` is present and neither `stalled` nor `STALLED` appears in the output.
- For the flush pre-recovery test: assert `- **Outcome**: STALLED` in the stall phase and `- **Outcome**: DONE` after recovery. Reject both `stalled` and `STALLED` residue in the final state.

### UPDATED: skills/implement/scripts/test-write-final-report.sh

- Update happy-path and matrix assertions:
  - success outcomes now contain `- **Outcome**: DONE`
  - stalled contains `- **Outcome**: STALLED`
  - bailed and other non-success outcomes retain raw values
  - implement summaries do not contain `- **Mode**:`
- Restructure the matrix format: the third field is now the expected `Outcome:` display value (e.g., `DONE`, `STALLED`, `bailed`, `bailed-needs-user-input`) rather than a boolean `present`/`absent`. Update the assertion logic to use `assert_contains "- **Outcome**: $expect_outcome_display"` when `$expect_outcome_display != absent`, and `assert_not_contains '- **Outcome**:'` only for any remaining cases that truly emit no Outcome bullet (none expected after this change).
- Keep title assertions raw, for example `: merged`, `: stalled`, and `: pr-created`.
- Keep PR presence assertions unchanged.

### UPDATED: skills/implement/scripts/write-final-report.md

- Update the renderer contract prose:
  - `Outcome` is always emitted first.
  - successful outcomes display as `DONE`.
  - `stalled` displays as `STALLED`.
  - other outcomes display raw.
  - `Mode` is no longer emitted.
- Keep the normalized outcome enum list unchanged because the raw `--outcome` values and heading remain unchanged.

## Edge cases

- Existing committed summaries may still contain lowercase `stalled`; reconciliation must keep supporting them and now REWRITE to `DONE` rather than delete the bullet.
- The raw heading remains the audit source for the exact normalized outcome.
- `workflow_path` must not disappear when removing `Mode`.
- Unknown or future outcomes must stay visible as raw values rather than being coerced to `DONE`.
- The degraded `/design` fallback path must emit the same `DONE`/`STALLED` contract as the normal renderer path.
- The old conditional Outcome block in `render_run_summary` must be fully removed to avoid duplicate Outcome bullets on non-success paths.

## Failure modes

- If the old conditional Outcome block is not removed (only a new unconditional one added), bailed/stalled paths emit two Outcome bullets.
- If reconciliation only matches lowercase `stalled`, old summaries with `STALLED` may fail to repair; and if the outcome line is deleted rather than rewritten, the always-present Outcome contract is broken post-reconciliation.
- If tests assert no `Outcome` bullet on success, the harness will fail after the renderer change.
- If `Mode` removal also removes `Path`, implement path diagnostics may regress.
- If the degraded fallback is not updated, a renderer failure on `/design` runs would emit raw outcome strings, breaking monitoring tools that parse `DONE`/`STALLED`.

## Testing strategy

Run targeted checks:

- `python3 -m pytest python/tests/git/test_pr_body.py -q -k render_run_summary`
- `python3 -m pytest python/tests/report/test_run_logs.py -q -k stalled_summary`
- `python3 -m pytest python/tests/design/test_design_summary.py -q`
- `bash skills/implement/scripts/test-write-final-report.sh`
- Prefer `make test-write-final-report` as the combined local harness when time allows.

No `SECURITY.md` update is needed. This changes report presentation, not secret handling or permission behavior.

confidence: high

## Acceptance

Run targeted checks:

- `python3 -m pytest python/tests/git/test_pr_body.py -q -k render_run_summary`
- `python3 -m pytest python/tests/report/test_run_logs.py -q -k stalled_summary`
- `python3 -m pytest python/tests/design/test_design_summary.py -q`
- `bash skills/implement/scripts/test-write-final-report.sh`
- Prefer `make test-write-final-report` as the combined local harness when time allows.

No `SECURITY.md` update is needed. This changes report presentation, not secret handling or permission behavior.

confidence: high

diff_lines: 155

## Test plan
(no test plan section in plan-file)
