## Implementation Plan

Fix two silent code-review pipeline bugs (#2222):

**Fix A — launch-claude-subprocess.sh allowed-roots extension**
- Add `--allow-root DIR` repeatable flag to `scripts/launch-claude-subprocess.sh`
- Pass `--allow-root $(dirname "$DIFF_FILE")` from `scripts/dispatch-code-voters.sh` (launch_claude_voter)
- Pass `--allow-root $(dirname "$DIFF_FILE")` from `skills/review/scripts/dispatch-panel.sh` (launch_claude_slot)
- Emit ⚠ warning in dispatch-code-voters.sh when VOTER_1_STATUS=failed

**Fix B — Cursor inline-TSV recovery**
- Add inline-TSV short-circuit in `scripts/validate-research-output.sh --validation-mode` (prevents NOT_SUBSTANTIVE false positive)
- Add `parse_output_tsv()` helper and TSV fallback in `skills/review/scripts/collect-findings.sh` (recovers findings)
- Emit ⚠ warning when TSV fallback activates

**Tests**
- `scripts/test-launch-claude-subprocess.sh`: --allow-root accept/reject cases
- `scripts/test-collect-agent-results.sh`: inline-TSV cursor cases

**MD siblings** — `scripts/launch-claude-subprocess.md`, `scripts/validate-research-output.md`, `skills/review/scripts/collect-findings.md`

## Goals and Test Criteria

- GOAL_A: no `context file outside allowed roots` errors for review-diff.patch in execution-issues
- GOAL_B: no `NOT_SUBSTANTIVE` errors from plan-mode sidecar refusal; cursor inline-TSV findings captured
- GOAL_C: user-visible ⚠ warnings for both failure modes
- GOAL_D: regression test coverage for --allow-root and inline-TSV recovery
