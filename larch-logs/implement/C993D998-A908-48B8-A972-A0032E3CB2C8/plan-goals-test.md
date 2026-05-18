## Goal
Fix rejected-findings.md log detail (Item P) and add Read-poll PostToolUse hook (Item Q)

## Implementation Plan

Two independent items bundled to reduce issue count.

### Item P — rejected-findings detail in run logs

Root cause: `emit-tally.sh` preserves the full tally output to `rejected-findings-full.md` then overwrites `rejected-findings.md` with a bare grep ledger. `write-rejected-findings.sh` copies `rejected-findings.md` (bare) to the run log. Additionally, `compose-review-findings.sh`'s `parse_artifact code-review-rejected` looks for `### [Code Review] REVIEWER_NAME` but actual `rejected-findings-full.md` content uses `### [rejected] FINDING_N` format (from `tally-code-votes.sh` line: `printf '### [%s] %s\n\n' "$result" "$id"`), so the parser is dead code against real pipeline output.

**Changes:**

1. `skills/implement/scripts/write-rejected-findings.sh`: when `--run-id` and `--log-root` are set, prefer `$IMPLEMENT_TMPDIR/rejected-findings-full.md` over `rejected-findings.md` if it exists and is non-empty. The count heuristic still reads from whichever base `$file` (`rejected-findings.md`) is available.

2. `scripts/compose-review-findings.sh`: fix `parse_artifact` for `code-review-rejected`:
   - Change the separator regex from `\[Code[[:space:]]+Review\]` to `\[rejected\]`
   - The captured group becomes the finding ID (e.g., `FINDING_13`) used as `pending_reviewer`
   - Add a guard before the generic `### ` flush: when `kind=code-review-rejected` and `pending_id` is set, treat inner `### FINDING_N:` / `### OOS_N:` lines as body lines rather than block separators

3. `scripts/test-compose-review-findings.sh`: update the `rejected-findings-full.md` fixture to use the real `### [rejected] FINDING_1` + block content format; update assertions accordingly.

4. `skills/implement/scripts/test-write-rejected-findings.sh`: add a test case that creates both `rejected-findings.md` and `rejected-findings-full.md` in the tmpdir and verifies the log copy uses the full version.

5. `skills/implement/scripts/write-rejected-findings.md`: update to document full-file preference.

### Item Q — anti-poll PostToolUse hook for Read

**New files:**

6. `scripts/hook-anti-read-poll.sh`: PostToolUse hook on Read tool calls.
   - Reads JSON from stdin (Claude Code hook event payload)
   - Extracts `tool_name`, `tool_input.file_path`, `tool_input.offset` (default 0)
   - Maintains state in `${TMPDIR:-/tmp}/larch-read-poll-${CWD_HASH}.tsv` (one line: `last_path\tlast_offset\tcount\tfirst_ts`)
   - Logic: same path+offset as previous → increment count; different → reset count=1, first_ts=now
   - If count >= 3 and (now - first_ts) <= 30s: emit system-reminder JSON
   - Does NOT fire when count < 3 or time window exceeded
   - Different `tool_input.offset` values → treated as distinct (reset counter)
   - set -uo pipefail (no -e; hooks must not block tool use)

7. `scripts/hook-anti-read-poll.md`: sibling doc.

8. `scripts/test-hook-anti-read-poll.sh`: offline test harness.
   - Creates synthetic hook payloads for 3 consecutive identical reads
   - Verifies the 3rd fires the warning (stdout contains `system-reminder` or `additionalContext`)
   - Verifies the 2nd does NOT fire
   - Verifies different offset → no fire
   - Verifies different path → reset + no fire on 3rd of first path

9. `scripts/test-hook-anti-read-poll.md`: sibling doc stub.

**Modified files:**

10. `hooks/hooks.json`: add `PostToolUse` entry with `matcher: "Read"` pointing to `hook-anti-read-poll.sh`.


## Test plan

- Run `scripts/test-compose-review-findings.sh` after fixing the parser.
- Run `skills/implement/scripts/test-write-rejected-findings.sh` after fixing the copy logic.
- Run `scripts/test-hook-anti-read-poll.sh` to verify Q behavior.
- Run `/relevant-checks` at the end.
