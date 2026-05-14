## Goal
Implement quiet-by-default contract output for larch scripts via shared lib-quiet.sh library

## Implementation Plan

### Objective
Create `scripts/lib-quiet.sh` (shared quiet library), `scripts/lib-quiet.md` (contract doc), and `scripts/test-lib-quiet.sh` (11 unit tests). Modify `scripts/ship-pr.sh`, `scripts/implement-finalize.sh`, and 19 existing direct helpers to source the library and call `larch_quiet_init` near the top, converting contract-emitting echo/printf lines to emit/emit_kv/emit_breadcrumb. Update affected test-*.sh files to add `LARCH_QUIET_DISABLE=1`. Add `scripts/lib-quiet.md` to AGENTS.md canonical sources.

### Files to Create
1. `scripts/lib-quiet.sh` — exactly as the reference implementation in issue #2109 body.
2. `scripts/lib-quiet.md` — contract doc mirroring the public API surface.
3. `scripts/test-lib-quiet.sh` — 11 unit tests covering all specified cases.

### Files to Modify
For each script in the list below, add near the top (after set/LC_ALL/SCRIPT_DIR but before arg parsing):
```bash
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
```
Then convert contract-emitting lines (KEY=value output to the caller) from `echo`/`printf` to `emit_kv`/`emit`. Plain noisy echo/printf lines that go to "user feedback" or internal logging are left as-is (they route to the log file automatically after the redirect). Progress breadcrumb lines are converted to `emit_breadcrumb`.

**Scripts to modify:**
- `scripts/ship-pr.sh` — source+init; replace decorative stdout breadcrumbs (✅/⏩ lines) with emit_breadcrumb; keep `2>"$fail_file"` patterns (belt-and-suspenders per issue)
- `scripts/implement-finalize.sh` — source+init; convert ~30 contract-emitting echo/printf (STATUS=, FINALIZE_SUBCOMMAND=, etc.) to emit/emit_kv; convert phase boundary printf breadcrumbs to emit_breadcrumb
- `scripts/run-relevant-checks-captured.sh` — source+init; convert STATUS=, RELEVANT_CHECKS_OK=, LOG_FILE=, FAILURE_REASON= to emit_kv
- `scripts/check-bump-version.sh` — source+init; convert HAS_BUMP=, COMMITS_BEFORE=, STATUS=, VERIFIED=, etc. to emit_kv
- `.claude/skills/bump-version/scripts/apply-bump.sh` — source (path-relative from its SCRIPT_DIR); convert APPLIED=, COMMIT_SHA=, ERROR= to emit_kv
- `scripts/create-pr.sh` — source+init; convert PR_NUMBER=, PR_URL=, PR_TITLE=, PR_STATUS= to emit_kv
- `scripts/gh-pr-body-update.sh` — source+init; convert UPDATED=, ERROR= to emit_kv
- `scripts/ci-wait.sh` — source+init; convert ACTION=, CI_STATUS=, BEHIND_COUNT=, FAILED_RUN_ID= to emit_kv; breadcrumb progress dots already go to stderr (leave as-is)
- `scripts/ci-status.sh` — source+init; convert CI_STATUS=, BEHIND_COUNT=, FAILED_RUN_ID= to emit_kv
- `scripts/ci-decide.sh` — source+init; convert ACTION= to emit_kv
- `scripts/merge-pr.sh` — source+init; convert MERGE_RESULT=, PR_STATE=, etc. to emit_kv
- `scripts/rebase-push.sh` — source+init; convert SKIPPED_ALREADY_FRESH=, SKIPPED_ALREADY_PUSHED=, CONFLICT_FILES=, REBASE_ERROR= to emit_kv
- `scripts/git-force-push.sh` — source+init; convert PUSH_STATUS=, etc. to emit_kv
- `scripts/launch-cursor-ci.sh` — source+init; convert contract output to emit_kv
- `scripts/launch-codex-ci.sh` — source+init; convert contract output to emit_kv
- `scripts/append-token-record.sh` — source+init; convert contract output to emit_kv
- `scripts/append-tool-failure.sh` — source+init; convert FAILED=, ERROR= to emit_kv
- `scripts/append-execution-issue.sh` — source+init; convert FAILED=, ERROR= to emit_kv
- `scripts/tracking-issue-write.sh` — source+init; convert FAILED=, ERROR=, ISSUE_NUMBER=, ISSUE_URL=, COMMENT_ID=, COMMENT_URL=, RENAMED=, etc. to emit_kv
- `scripts/refresh-run-logs.sh` — source+init; convert contract output to emit_kv
- `scripts/redact-secrets.sh` — source+init (minimal, it's a pure stdin→stdout filter; just add init for consistency)
- `scripts/redact-tmpdir-paths.sh` — source+init (pure sed filter; add init for consistency)

**AGENTS.md** — add row for `scripts/lib-quiet.md` in the Canonical sources table.

### Test Updates
For each test-*.sh that asserts against stdout of a now-quiet script, add `export LARCH_QUIET_DISABLE=1` near the top. Affected files to check: `test-check-bump-version.sh`, `test-apply-bump.sh`, `test-create-pr.sh`, `test-gh-pr-body-update.sh`, `test-ci-wait.sh`, `test-launch-cursor-ci.sh`, `test-launch-codex-ci.sh`, `test-tracking-issue-write.sh`, `test-refresh-run-logs.sh`, `test-ship-pr.sh`, `test-implement-finalize.sh`.

### Wiring
After writing test-lib-quiet.sh, add it to the Makefile as a new `test-lib-quiet` target (adjacent to existing test-*.sh targets).


## Test plan
- `make test-lib-quiet` passes (11 tests)
- `make lint` passes (pre-commit on modified files)
- Existing tests that now need LARCH_QUIET_DISABLE=1 pass with that flag set
