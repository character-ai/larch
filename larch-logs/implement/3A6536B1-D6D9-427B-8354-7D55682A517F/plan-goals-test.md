## Goal
Convert 19 scripts in /design and /fix-issue to use lib-quiet.sh (Phase 3)

## Implementation Plan
## Quiet-by-default Scripts — Phase 3: /design + /fix-issue

**Goal**: Convert 19 scripts to use lib-quiet.sh so incidental stdout/stderr is redirected to a per-process log file; only contract KEY=VALUE output reaches callers via emit_kv/emit.


### Conversion pattern (per script)

1. After `set -euo pipefail`, add SCRIPT_DIR if missing, then:
   ```bash
   SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
   # shellcheck source=scripts/lib-quiet.sh
   source "$SCRIPT_DIR/<relative>/lib-quiet.sh"
   larch_quiet_init
   ```
2. `echo "KEY=VALUE"` → `emit_kv KEY "VALUE"`
3. `printf 'KEY=VALUE\n'` → `emit_kv KEY "VALUE"`
4. `printf 'KEY=%s\n' "$var"` → `emit_kv KEY "$var"`
5. Dynamic keys: `emit_kv "KEY_${i}" "$(cmd)"` pattern
6. Leave `>&2` echoes as-is (become log entries after init)
7. Pure-content renderers / filters: add `LARCH_QUIET_DISABLE=1` before source+init

### Relative paths to lib-quiet.sh
- `scripts/` → `"$SCRIPT_DIR/lib-quiet.sh"`
- `skills/design/scripts/` → `"$SCRIPT_DIR/../../../scripts/lib-quiet.sh"`
- `skills/fix-issue/scripts/` → `"$SCRIPT_DIR/../../../scripts/lib-quiet.sh"`

### Scripts (19 total)

**scripts/sanitize-mermaid-fragment.sh** — has SCRIPT_DIR; convert echo STATUS/FENCE_*/FENCE_COUNT; dynamic FENCE_${i}_HEADING keys
**scripts/write-run-params.sh** — no SCRIPT_DIR; all echoes are >&2; just source+init
**scripts/resolve-repo.sh** — no SCRIPT_DIR; single `printf '%s\n'` output → `emit "$RESOLVED"`
**scripts/check-clean-tree.sh** — no SCRIPT_DIR; convert printf CLEAN/DIRTY_OUT/PROBE_ERROR

**skills/design/scripts/classify-issue.sh** — has SCRIPT_DIR; convert printf CLASSIFICATION/CLASSIFICATION_REASON/CLASSIFICATION_SOURCE
**skills/design/scripts/design-driver.sh** — has SCRIPT_DIR; convert printf STEP_*/ACTION_PASSTHROUGH
**skills/design/scripts/emit-plan.sh** — no SCRIPT_DIR; convert printf EMIT_PLAN_STATUS/DIFF_LINES
**skills/design/scripts/finalize-plan.sh** — no SCRIPT_DIR; convert echo/printf FINALIZE_PLAN_STATUS
**skills/design/scripts/read-design-manifest.sh** — no SCRIPT_DIR; convert echo MANIFEST_FAILED/MANIFEST_OK + all key outputs
**skills/design/scripts/render-plan-review-prompt.sh** — no SCRIPT_DIR; pure renderer → LARCH_QUIET_DISABLE=1 before init
**skills/design/scripts/tally-plan-review.sh** — no SCRIPT_DIR; convert only terminal printf TALLY_PLAN_REVIEW_STATUS/VOTING_TALLY_FILE
**skills/design/scripts/write-design-manifest.sh** — no SCRIPT_DIR; convert only terminal printf MANIFEST_WRITTEN

**skills/fix-issue/scripts/blocker-helpers.sh** — sourced library, audit only: all echo calls inside functions are used in $() command-substitution by callers, no contract KEY=VALUE output → no changes
**skills/fix-issue/scripts/finalize-umbrella.sh** — has SCRIPT_DIR; convert echo FINALIZED/ERROR/ALREADY_FINALIZED/REASON/RENAMED/CLOSED
**skills/fix-issue/scripts/find-lock-issue.sh** — SCRIPT_DIR at line 226; add at top; convert echo ELIGIBLE/ERROR/IS_UMBRELLA/ISSUE_NUMBER/etc.
**skills/fix-issue/scripts/get-issue-details.sh** — has SCRIPT_DIR; convert only `echo "OUTPUT_FILE=$OUTPUT_PATH"`
**skills/fix-issue/scripts/issue-lifecycle.sh** — has SCRIPT_DIR; convert echo LOCK_ACQUIRED/COMMENTED/CLOSED/etc.
**skills/fix-issue/scripts/parse-prose-blockers.sh** — pure stdin-to-stdout filter → LARCH_QUIET_DISABLE=1 before init
**skills/fix-issue/scripts/umbrella-handler.sh** — has SCRIPT_DIR; convert echo IS_UMBRELLA/CHILDREN/CHILD_NUMBER/etc.

### Top-level scripts fix-issue-specific
**scripts/resolve-repo.sh** and **scripts/check-clean-tree.sh** — covered above

### Test files (add `export LARCH_QUIET_DISABLE=1`)
- skills/design/scripts/test-design-manifest.sh
- skills/design/scripts/test-classify-issue.sh
- skills/design/scripts/test-design-driver.sh
- skills/design/scripts/test-emit-plan.sh
- skills/design/scripts/test-finalize-plan.sh
- skills/design/scripts/test-plan-review-prompt.sh
- skills/design/scripts/test-tally-plan-review.sh
- scripts/test-mermaid-fragments.sh
- scripts/test-write-run-params.sh
- skills/fix-issue/scripts/test-*.sh (all that invoke the converted scripts)

### .md sibling files to update
Add "On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout." to each converted script's .md sibling.


## Test plan
- `make test` — runs the full test suite
- Check each converted script can be invoked and outputs KEY=VALUE contract correctly
