## Goal
Move session-transcript capture from Step 18 to Step 7a pre-bump log flush so every merged /implement run includes session-transcript.jsonl

## Implementation Plan
Move session-transcript capture from Step 18 (post-merge, suppressed) to Step 7a tail (pre-bump log flush) so every merged /implement run includes session-transcript.jsonl.


### 1. skills/implement/SKILL.md — Step 7a table + pre-bump flush + Step 18

**Batch mapping table (~line 752):**
Add `session-transcript` to the Step 7a row:
  | Step 7a tail (pre-bump log flush) | `token-report`, `timing-report`, `execution-issues` (pre-bump), `session-transcript` (truncated at pre-bump boundary), and log-flush commit |

**Pre-bump log flush bash block (~lines 1670-1677):**
Add capture-session-transcript.sh invocation before the `larch-log.sh commit` call:
  "${CLAUDE_PLUGIN_ROOT}/scripts/capture-session-transcript.sh" \
    --source-file "$LARCH_CLAUDE_SOURCE_FILE" \
    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
    --skill implement \
    --run-id "$RUN_ID" \
    --no-logs-commit "${no_logs_commit:-false}" \
    --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md" || true

Update the prose after the bash block (~line 1680):
  - Add "session-transcript" to the batch mapping row description
  - Update refresh-run-logs.sh description (~line 1682) to include session-transcript

**Step 18 (~lines 1924-1946):**
  - Remove the "Capture and commit the session transcript" paragraph and its bash block
  - Replace the trailing prose about three suppression mechanisms with a simpler note

### 2. scripts/capture-session-transcript.sh

Remove:
  - `current_branch_is_default()` function (lines 80-97) — no longer needed
  - `suppressed-post-merge-sentinel` branch (lines 184-186)
  - `suppressed-default-branch` branch (lines 188-190)
Update:
  - `append_warning` entries that reference "Step 18" → "Step 7a"

### 3. scripts/capture-session-transcript.md

Remove `suppressed-post-merge-sentinel` and `suppressed-default-branch` from status list.
Update Purpose section: "Step 7a (pre-bump log flush)" instead of "Step 18".
Update Callers section: primary caller is the Step 7a pre-bump flush.
Update Edit-in-sync: reference Step 7a instead of Step 18.

### 4. scripts/refresh-run-logs.sh — Triggers A-C

After the existing `timing-report` write (~line 83), add session-transcript re-capture:
  "${SCRIPT_DIR}/capture-session-transcript.sh" \
    --source-file "${LARCH_CLAUDE_SOURCE_FILE:-}" \
    --log-root "$log_root" \
    --skill implement \
    --run-id "$run_id" \
    --no-logs-commit "false" \
    --execution-issues-log "$issue_log" 2>/dev/null || true

### 5. docs/run-logs.md — session-transcript.jsonl row

Update "Written: Step 18, terminal cleanup" → "Written: Step 7a tail (pre-bump log flush). The transcript is truncated at the pre-bump boundary; Steps 8+ (version bump, PR, CI, merge) are not included."

### 6. scripts/test-capture-session-transcript.sh

Remove tests for `suppressed-post-merge-sentinel` and `suppressed-default-branch` statuses.
Add: test that on a feature branch (non-main) with a valid transcript, the script emits `captured`.
Add: test that if invoked on main with a valid transcript, the script now emits `commit-failed`
  (loud failure from larch-log.sh refusing to commit on default branch — no silent suppression).

### 7. docs/run-logs-required-files.tsv — NEW

Machine-readable manifest with one row per required file:
  relative_path\tcondition\tbatch_slug\textension

### 8. scripts/verify-run-log-completeness.sh — NEW

Shell script that reads docs/run-logs-required-files.tsv and checks a given
larch-logs/implement/<RUN_ID>/ path, emitting OK or MISSING=<list>.

### 9. scripts/verify-run-log-completeness.md — NEW

Sibling doc as required by script-md-siblings rule.

### 10. Makefile

Add `test-verify-run-log-completeness` Phony target and wire into test-harnesses group.


## Test plan

Run `make test-capture-session-transcript` — should pass with updated tests.
Run `scripts/verify-run-log-completeness.sh larch-logs/implement/C068D05A-E9B5-45EC-86E4-3AB8A9161C9D/` 
  → should emit MISSING=session-transcript.jsonl.
Run `/relevant-checks`.
