#!/usr/bin/env bash
# test-write-final-report.sh — offline harness for write-final-report.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-final-report.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
assert_not_contains(){ case "$2" in *"$1"*) fail "$3 (unexpected $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; *) pass "$3" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cp "$REPO_ROOT/scripts/run-log-terminal-outcomes.inc.bash" "$plugin/scripts/run-log-terminal-outcomes.inc.bash"
cp "$REPO_ROOT/scripts/render-run-summary.sh" "$plugin/scripts/render-run-summary.sh"
cp "$REPO_ROOT/scripts/token-cost.sh" "$plugin/scripts/token-cost.sh"
chmod +x "$plugin/scripts/render-run-summary.sh" "$plugin/scripts/token-cost.sh"
cat > "$plugin/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" != manifest ]; then exit 0; fi
shift
if [ "${LARCH_LOG_MANIFEST_FAIL:-false}" = true ]; then
    printf 'manifest stub failure\n' >&2
    exit 1
fi
log="${LARCH_LOG_MANIFEST_LOG:-}"
[ -n "$log" ] || exit 0
printf '%s\n' "$*" >>"$log"
exit 0
STUB
chmod +x "$plugin/scripts/larch-log.sh"
cat > "$plugin/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${TRACKING_FAIL:-false}" = "true" ]; then
  printf '%s' "${TRACKING_ERR:-summary failed}" >&2
  exit "${TRACKING_RC:-1}"
fi
while [ $# -gt 0 ]; do case "$1" in --content-file) cp "$2" "${TRACKING_CONTENT_LOG:?}"; shift 2 ;; *) shift ;; esac; done
printf 'COMMENT_URL=https://example.test/comment/final\n'
STUB
chmod +x "$plugin/scripts/tracking-issue-summary.sh"

# Happy path: IMPLEMENT_TMPDIR with parent-issue.md, session-env.sh, ship-pr-state.sh
impl_dir="$TMP_ROOT/impl"; mkdir -p "$impl_dir"
printf 'ISSUE_NUMBER=7\nRUN_ID=run-5\nADOPTED=true\n' > "$impl_dir/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_dir/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/5\n'
    printf 'PR_NUMBER=5\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_dir/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\n' > "$impl_dir/finalize-state.sh"

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'STATUS=ok' "$out" 'happy path status ok'
assert_contains 'COMMENT_URL=https://example.test/comment/final' "$out" 'comment URL emitted'
assert_contains 'https://example.test/pr/5' "$(cat "$TMP_ROOT/content.md")" 'summary includes PR URL'
assert_contains '<!-- larch:run-summary v=1 -->' "$(cat "$TMP_ROOT/content.md")" 'summary includes run-summary sentinel'
assert_contains '## /implement run run-5 — merged' "$(cat "$TMP_ROOT/content.md")" 'summary title shows merged outcome'
assert_not_contains '**Outcome**:' "$(cat "$TMP_ROOT/content.md")" 'success path omits Outcome bullet'
if [ -s "$impl_dir/larch-logs/implement/run-5/final-summary.md" ]; then pass 'final summary file written'; else fail 'final summary file written'; fi
assert_contains '## /implement run run-5 — merged' "$(cat "$impl_dir/larch-logs/implement/run-5/final-summary.md")" 'final summary title merged'
assert_not_contains '**Outcome**:' "$(cat "$impl_dir/larch-logs/implement/run-5/final-summary.md")" 'final summary omits Outcome bullet on success'

# Comment-only path leaves the tracked run-log file untouched while still
# emitting the live tracking-comment projection.
printf 'legacy-stale-marker-do-not-touch\n' > "$impl_dir/larch-logs/implement/run-5/final-summary.md"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-comment-only.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --comment-only)
assert_contains 'STATUS=ok' "$out" 'comment-only status ok'
assert_contains 'https://example.test/pr/5' "$(cat "$TMP_ROOT/content-comment-only.md")" 'comment-only summary includes live PR'
assert_contains 'legacy-stale-marker-do-not-touch' "$(cat "$impl_dir/larch-logs/implement/run-5/final-summary.md")" 'comment-only does not rewrite tracked final summary'

# Upsert failure → STATUS=failed + non-zero exit
set +e
failed=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_FAIL=true TRACKING_ERR='gh auth failed' \
         "$HELPER" --implement-tmpdir "$impl_dir" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 1 ]; then pass 'upsert failure exits non-zero'; else fail 'upsert failure exits non-zero'; fi
assert_contains 'STATUS=failed' "$failed" 'upsert failure status failed'
assert_contains 'ERROR=' "$failed" 'upsert failure emits error'

# Missing --implement-tmpdir
set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing arg exits non-zero'; else fail 'missing arg exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing arg emits envelope'

# Stalled outcome (STALL_TRACKING=true)
impl_st="$TMP_ROOT/impl-stall"; mkdir -p "$impl_st"
printf 'ISSUE_NUMBER=2\nRUN_ID=run-st\nADOPTED=true\n' > "$impl_st/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_st/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/2\n'
    printf 'PR_NUMBER=2\n'
    printf 'STALL_TRACKING=true\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_st/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_st/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-stall.md" \
      "$HELPER" --implement-tmpdir "$impl_st")
assert_contains 'STATUS=ok' "$out" 'stalled path status ok'
assert_contains '**Outcome**: stalled' "$(cat "$TMP_ROOT/content-stall.md")" 'stalled outcome in summary'

# Design-only outcome
impl_do="$TMP_ROOT/impl-do"; mkdir -p "$impl_do"
printf 'ISSUE_NUMBER=3\nRUN_ID=run-do\nADOPTED=true\n' > "$impl_do/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_do/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_do/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=true\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_do/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-do.md" \
      "$HELPER" --implement-tmpdir "$impl_do")
assert_contains 'STATUS=ok' "$out" 'design-only status ok'
assert_contains '## /implement run run-do — design-only' "$(cat "$TMP_ROOT/content-do.md")" 'design-only title'
assert_not_contains '**Outcome**:' "$(cat "$TMP_ROOT/content-do.md")" 'design-only success omits Outcome bullet'

# BAIL_NEEDS_USER_INPUT → distinct outcome when still bailed
impl_bu="$TMP_ROOT/impl-bu"; mkdir -p "$impl_bu"
printf 'ISSUE_NUMBER=4\nRUN_ID=run-bu\nADOPTED=true\n' > "$impl_bu/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_bu/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_bu/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=true\n' > "$impl_bu/finalize-state.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-bu.md" \
      "$HELPER" --implement-tmpdir "$impl_bu")
assert_contains 'STATUS=ok' "$out" 'bail-user path status ok'
assert_contains '**Outcome**: bailed-needs-user-input' "$(cat "$TMP_ROOT/content-bu.md")" 'bail-user outcome'

# Plain bailed outcome (early exit without user-input flag)
impl_bl="$TMP_ROOT/impl-bl"; mkdir -p "$impl_bl"
printf 'ISSUE_NUMBER=9\nRUN_ID=run-bl\nADOPTED=true\n' > "$impl_bl/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_bl/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_bl/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_bl/finalize-state.sh"
printf 'NO_ISSUES=false\n' > "$impl_bl/run-flags.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-bl.md" \
      "$HELPER" --implement-tmpdir "$impl_bl")
assert_contains 'STATUS=ok' "$out" 'bailed path status ok'
assert_contains '**Outcome**: bailed' "$(cat "$TMP_ROOT/content-bl.md")" 'plain bailed outcome in summary'

# Bail + manifest.json: larch-log manifest stamps steps_ran.* and hard-fails on manifest error
impl_mfb="$TMP_ROOT/impl-mfb"; mkdir -p "$impl_mfb/larch-logs/implement/run-mfb"
printf 'ISSUE_NUMBER=11\nRUN_ID=run-mfb\nADOPTED=true\n' > "$impl_mfb/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_mfb/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_mfb/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_mfb/finalize-state.sh"
printf 'NO_ISSUES=false\n' > "$impl_mfb/run-flags.sh"
printf '{"schema_version":2,"steps_ran":{}}\n' > "$impl_mfb/larch-logs/implement/run-mfb/manifest.json"
mf_log="$TMP_ROOT/mf-invoke.log"
: >"$mf_log"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" LARCH_LOG_MANIFEST_LOG="$mf_log" TRACKING_CONTENT_LOG="$TMP_ROOT/content-mfb.md" \
      "$HELPER" --implement-tmpdir "$impl_mfb")
assert_contains 'STATUS=ok' "$out" 'bail manifest stamp path status ok'
assert_contains 'steps_ran.step9a1=false' "$(cat "$mf_log")" 'manifest stamp includes step9a1 false'
assert_contains 'steps_ran.step8=false' "$(cat "$mf_log")" 'manifest stamp includes step8 false'
assert_contains 'steps_ran.step7a=false' "$(cat "$mf_log")" 'manifest stamp includes step7a false'
assert_contains '--log-root' "$(cat "$mf_log")" 'manifest forwards --log-root'
assert_contains '--skill implement' "$(cat "$mf_log")" 'manifest forwards --skill'
assert_contains '--run-id run-mfb' "$(cat "$mf_log")" 'manifest forwards --run-id'

set +e
out_mf_fail=$(CLAUDE_PLUGIN_ROOT="$plugin" LARCH_LOG_MANIFEST_FAIL=true LARCH_LOG_MANIFEST_LOG="$TMP_ROOT/mf-fail.log" \
    TRACKING_CONTENT_LOG="$TMP_ROOT/content-mf-fail.md" \
    "$HELPER" --implement-tmpdir "$impl_mfb" 2>/dev/null)
rc_mf=$?
set -e
if [ "$rc_mf" -eq 1 ]; then pass 'manifest update failure exits non-zero'; else fail 'manifest update failure exits non-zero'; fi
assert_contains 'STATUS=failed' "$out_mf_fail" 'manifest failure status failed'
assert_contains 'larch-log.sh manifest steps_ran update failed' "$out_mf_fail" 'manifest failure error text'

finish
