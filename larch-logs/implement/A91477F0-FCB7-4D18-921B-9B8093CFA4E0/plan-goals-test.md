## Goal
Require --log-root flag in larch-log.sh, eliminate the silent env-based fallback in lib-larch-log.sh, update all invocations in skills/implement/SKILL.md, and add cross-session larch-logs handoff via PREV_IMPLEMENT_TMPDIR.

Require --log-root in larch-log.sh, remove env fallback, and add cross-session handoff.

## Implementation Plan

### 1. scripts/larch-log.sh
Add `--log-root <dir>` flag to `init`, `write`, `append`, `commit`, `manifest` subcommands.
- In each subcommand's arg loop, add: `--log-root) LOG_ROOT="${2:?--log-root requires a value}"; shift 2 ;;`
- After arg parsing, before path operations, call `require_log_root`:
  ```
  require_log_root() {
      [ -n "${LARCH_LOG_ROOT:-}" ] && return 0
      [ -z "${LOG_ROOT:-}" ] && larch_log_fail 1 "--log-root is required (or export LARCH_LOG_ROOT for test isolation)"
      export LARCH_LOG_ROOT="$LOG_ROOT"
  }
  ```
- Validate LOG_ROOT is absolute: `[[ "$LOG_ROOT" == /* ]] || larch_log_fail 1 "--log-root must be an absolute path: $LOG_ROOT"`
- Call `require_log_root` before `require_common` in each subcommand (or right after parsing, before path operations)

### 2. scripts/lib-larch-log.sh
Simplify `larch_log_root()` to single-tier (LARCH_LOG_ROOT only):
```bash
larch_log_root() {
    if [ -n "${LARCH_LOG_ROOT:-}" ]; then
        printf '%s\n' "$LARCH_LOG_ROOT"
    else
        larch_log_fail 1 "LARCH_LOG_ROOT is not set; pass --log-root to larch-log.sh (or export LARCH_LOG_ROOT for test isolation)"
    fi
}
```
Remove IMPLEMENT_TMPDIR and LARCH_LOG_REPO_ROOT fallback tiers.

### 3. scripts/larch-log.md
Update "Log-root resolution" section:
- Change to single-tier: `$LARCH_LOG_ROOT` (set by `--log-root <dir>`, or explicitly exported for test isolation)
- Document `--log-root <dir>` as required for `init`, `write`, `append`, `commit`, `manifest`

### 4. scripts/lib-larch-log.md
Update stub to reflect simplified `larch_log_root()` (no IMPLEMENT_TMPDIR or LARCH_LOG_REPO_ROOT tiers).

### 5. scripts/test-larch-log.sh
Update the commit test section (currently uses IMPLEMENT_TMPDIR env fallback):
- Change to pass `--log-root "$_staging/larch-logs"` to each `larch-log.sh` invocation in the commit test block
- Remove IMPLEMENT_TMPDIR export/usage from commit test

### 6. skills/implement/SKILL.md
Add `--log-root "$IMPLEMENT_TMPDIR/larch-logs"` to every larch-log.sh invocation:

Code block invocations (exact edits):
- Branch 1 (line ~421): `larch-log.sh init ... --issue "$ISSUE_NUMBER"` → add `--log-root "$IMPLEMENT_TMPDIR/larch-logs"`
- Branch 2 (line ~455): `larch-log.sh init ... --issue "$ISSUE_ARG"` → add
- Branch 3 (line ~505): `larch-log.sh init ... --issue "$RECOVERED_N"` → add
- Branch 4 (line ~583): `larch-log.sh init ... --issue "$ISSUE_NUMBER"` → add
- Pre-bump write token-report (line ~1374): add `--log-root "$IMPLEMENT_TMPDIR/larch-logs"` before `|| true`
- Pre-bump write timing-report (line ~1375): add same
- Pre-bump commit (line ~1376): add `--log-root "$IMPLEMENT_TMPDIR/larch-logs"` before `--no-push`
- Step 2 Q/A append (line ~1010): add `--log-root "$IMPLEMENT_TMPDIR/larch-logs"`
- Step 18 write transcript (line ~1527-1530): add
- Step 18 commit transcript (line ~1531): add

Prose invocations (update the inline code examples):
- Step 1 plan-goals-test prose (line ~845): update the embedded larch-log.sh call to include `--log-root "$IMPLEMENT_TMPDIR/larch-logs"`
- Step 1 plan-review-tally prose (line ~846): same
- Step 5 code-review-tally prose (line ~1207): same
- Step 5 review-findings-full prose (line ~1231): same

Step 0 session_env_args block:
- Add `--prev-implement-tmpdir "$IMPLEMENT_TMPDIR"` to `session_env_args` array (or as a conditional append like the --claude-source-file pattern)

### 7. scripts/session-setup.sh
Add PREV_IMPLEMENT_TMPDIR to recognized caller-env keys:
- In the while loop, add: `PREV_IMPLEMENT_TMPDIR) CALLER_PREV_IMPLEMENT_TMPDIR="$value" ;;`
- Add `CALLER_PREV_IMPLEMENT_TMPDIR=""` to initial declarations
- After SESSION_TMPDIR creation (after line ~257), add best-effort copy:
  ```bash
  if [[ -n "${CALLER_PREV_IMPLEMENT_TMPDIR:-}" && \
        -d "${CALLER_PREV_IMPLEMENT_TMPDIR}/larch-logs" ]]; then
      cp -rp "${CALLER_PREV_IMPLEMENT_TMPDIR}/larch-logs/." \
             "$SESSION_TMPDIR/larch-logs/" 2>/dev/null || true
  fi
  ```

### 8. scripts/write-session-env.sh
Add `--prev-implement-tmpdir <path>` parameter:
- Declare `PREV_IMPLEMENT_TMPDIR_ARG=""`
- Parse: `--prev-implement-tmpdir) PREV_IMPLEMENT_TMPDIR_ARG="$2"; shift 2 ;;`
- Validate: non-empty absolute path, reasonable length (≤512 chars)
- Append to CONTENT: `[[ -n "$PREV_IMPLEMENT_TMPDIR_ARG" ]] && CONTENT="$CONTENT\nPREV_IMPLEMENT_TMPDIR=$PREV_IMPLEMENT_TMPDIR_ARG"`

## Edge Cases
- LARCH_LOG_ROOT exported by larch-log.sh after --log-root parsed — stays in scope for all larch_log_root() calls in the same process
- Test harness: sets LARCH_LOG_ROOT via `export` (tier 1) — still works since larch_log_root() still checks LARCH_LOG_ROOT
- commit test: currently uses IMPLEMENT_TMPDIR env (tier 2, being removed) — updated to pass --log-root directly
- PREV_IMPLEMENT_TMPDIR copy is best-effort: missing/empty/permission-denied path is silently skipped
- Validation: --log-root requires non-empty absolute path (starts with /)

## Test Plan
- Run `/relevant-checks` (pre-commit on modified files + agent-lint)
- The test-larch-log.sh harness validates larch-log.sh end-to-end (all tests should pass after commit test update)

## Test plan
- Run /relevant-checks (pre-commit + agent-lint)
- test-larch-log.sh verifies end-to-end larch-log.sh behavior
