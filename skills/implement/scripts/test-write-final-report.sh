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
stdout_summary_block() {
    printf '%s\n' "$1" | awk '
        /^COMMENT_URL=|^STATUS=|^REASON=|^ERROR=/ { exit }
        { print }
    '
}
assert_schema_ordered() {
    local body=$1 label=$2 prev=0 current
    shift 2
    for needle in "$@"; do
        current=$(printf '%s\n' "$body" | awk -v needle="$needle" 'index($0, needle) { print NR; exit }')
        if [ -z "$current" ]; then
            fail "$label (missing $needle)"
            printf 'ACTUAL: %s\n' "$body" >&2
            return
        fi
        if [ "$current" -le "$prev" ]; then
            fail "$label (out of order at $needle)"
            printf 'ACTUAL: %s\n' "$body" >&2
            return
        fi
        prev=$current
    done
    pass "$label"
}
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cp "$REPO_ROOT/scripts/run-log-terminal-outcomes.inc.bash" "$plugin/scripts/run-log-terminal-outcomes.inc.bash"
cp "$REPO_ROOT/scripts/render-run-summary.sh" "$plugin/scripts/render-run-summary.sh"
cp "$REPO_ROOT/scripts/token-cost.sh" "$plugin/scripts/token-cost.sh"
cp "$REPO_ROOT/scripts/lib-cost-line-format.sh" "$plugin/scripts/lib-cost-line-format.sh"
cp "$REPO_ROOT/scripts/append-tool-failure.sh" "$plugin/scripts/append-tool-failure.sh"
cp "$REPO_ROOT/scripts/append-execution-issue.sh" "$plugin/scripts/append-execution-issue.sh"
cp "$REPO_ROOT/scripts/redact-secrets.sh" "$plugin/scripts/redact-secrets.sh"
chmod +x "$plugin/scripts/render-run-summary.sh" "$plugin/scripts/token-cost.sh" \
    "$plugin/scripts/append-tool-failure.sh" "$plugin/scripts/append-execution-issue.sh" \
    "$plugin/scripts/redact-secrets.sh"
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
mkdir -p "$impl_dir/larch-logs/implement/run-5"
cat > "$impl_dir/larch-logs/implement/run-5/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON

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
assert_contains '- **Cost**: N/A' "$(cat "$TMP_ROOT/content-bl.md")" 'missing token data renders cost N/A'
assert_not_contains '- **PR**:' "$(cat "$TMP_ROOT/content-bl.md")" 'bailed path omits PR bullet when PR is N/A'

impl_exec="$TMP_ROOT/impl-exec"; mkdir -p "$impl_exec/larch-logs/implement/run-exec"
printf 'ISSUE_NUMBER=11\nRUN_ID=run-exec\nADOPTED=true\n' > "$impl_exec/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_exec/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_exec/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_exec/finalize-state.sh"
cat > "$impl_exec/execution-issues.md" <<'EOF'
### External Reviewer Issues
- **findings aggregator**: ballot merge failed
EOF
cat > "$impl_exec/larch-logs/implement/run-exec/execution-issues.ndjson" <<'JSON'
{"category":"Warnings","body":"- **Step design Step 5 — tracking failed (exit 1)**:\n  ```\nwarn\n  ```"}
JSON
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-exec.md" \
      "$HELPER" --implement-tmpdir "$impl_exec")
assert_contains '- **Exec issues**: 1' "$(cat "$TMP_ROOT/content-exec.md")" 'aggregator-only execution issue counts as exec issue'
assert_contains '- **Warnings**: 0' "$(cat "$TMP_ROOT/content-exec.md")" 'md execution-issues path remains authoritative over ndjson fallback'

rm -f "$impl_exec/execution-issues.md"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-exec-ndjson.md" \
      "$HELPER" --implement-tmpdir "$impl_exec")
assert_contains '- **Exec issues**: 0' "$(cat "$TMP_ROOT/content-exec-ndjson.md")" 'ndjson fallback keeps exec issue count at zero without exec categories'
assert_contains '- **Warnings**: 1' "$(cat "$TMP_ROOT/content-exec-ndjson.md")" 'ndjson fallback counts warning bodies without markdown headers'

impl_cost="$TMP_ROOT/impl-cost"; mkdir -p "$impl_cost/larch-logs/implement/run-cost"
printf 'ISSUE_NUMBER=12\nRUN_ID=run-cost\nADOPTED=true\n' > "$impl_cost/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_cost/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/12\n'
    printf 'PR_NUMBER=12\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=merged\n'
    printf 'MERGE=true\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_cost/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_cost/finalize-state.sh"
cat > "$impl_cost/larch-logs/implement/run-cost/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
cost_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-cost.md" \
      "$HELPER" --implement-tmpdir "$impl_cost" --print-stdout)
cost_line=$(printf '%s\n' "$cost_stdout" | grep -F -- '- **Cost**:' || true)
assert_contains '💰 TOTAL' "$cost_line" 'per-agent stdout cost has total'
assert_contains 'Claude $' "$cost_line" 'per-agent stdout cost has Claude'
assert_contains 'Codex $' "$cost_line" 'per-agent stdout cost has Codex'
assert_contains 'Cursor $' "$cost_line" 'per-agent stdout cost has Cursor'
assert_contains 'Tokens: ' "$cost_line" 'per-agent stdout cost has token count'

cp "$plugin/scripts/render-run-summary.sh" "$TMP_ROOT/render-run-summary.real"
cat > "$impl_bl/larch-logs/implement/run-bl/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 0}},
  "cursor": {"totals": {"total": 0}},
  "BUCKETS_claude": {"input": 700, "cache_read": 100, "cache_create_5m": 0, "cache_create_1h": 0, "output": 200},
  "BUCKETS_codex": {"input": 0, "cached_input": 0, "output": 0},
  "BUCKETS_cursor": {"input": 0, "cache_read": 0, "output": 0}
}
JSON
cat > "$plugin/scripts/render-run-summary.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
run="RUN"
outcome="bailed"
cost_unavailable=false
calls_file="${WFR_STAGE1_CALLS_FILE:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --output-file) out=$2; shift 2 ;;
    --run-id) run=$2; shift 2 ;;
    --outcome) outcome=$2; shift 2 ;;
    --cost-unavailable) cost_unavailable=true; shift ;;
    *)
      if [ "$#" -ge 2 ] && [[ "$2" != --* ]]; then
        shift 2
      else
        shift
      fi
      ;;
  esac
done
[ -n "$calls_file" ] && printf 'call\n' >>"$calls_file"
[ "$cost_unavailable" = true ] || exit 1
[ -n "$out" ] || exit 2
cat >"$out" <<EOF
## /implement run $run — $outcome

- **Outcome**: $outcome
- **Mode**: N/A
- **Path**: N/A
- **Duration**: N/A
- **Cost**: N/A
- **Issue**: N/A
- **Plan review**: N/A
- **Code review**: N/A
- **OOS filed**: 0
- **Exec issues**: 0
- **Warnings**: 1
- **Run logs**: \`larch-logs/implement/$run/\`

<!-- larch:run-summary v=1 -->
EOF
STUB
chmod +x "$plugin/scripts/render-run-summary.sh"
stage1_calls="$TMP_ROOT/wfr-stage1.calls"
: >"$stage1_calls"
rm -f "$impl_bl/execution-issues.md"
fallback_stage1=$(WFR_STAGE1_CALLS_FILE="$stage1_calls" CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-fallback-stage1.md" \
      "$HELPER" --implement-tmpdir "$impl_bl" --print-stdout 2>/dev/null)
assert_contains '- **Cost**: N/A' "$fallback_stage1" 'renderer fallback stage1 prints cost N/A'
assert_contains '- **Warnings**: 1' "$fallback_stage1" 'renderer fallback stage1 refreshes warning count'
assert_contains '<!-- larch:run-summary v=1 -->' "$fallback_stage1" 'renderer fallback stage1 keeps sentinel'
test "$(wc -l <"$stage1_calls" | tr -d ' ')" = "2" || fail 'renderer fallback stage1 must invoke renderer twice'
[ ! -e "$impl_bl/wfr-fallback-stage1.log" ] || fail 'renderer fallback stage1 must not retain fallback stderr sidecar'

cat > "$plugin/scripts/render-run-summary.sh" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$plugin/scripts/render-run-summary.sh"
rm -f "$impl_bl/execution-issues.md"
fallback_stage2=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-fallback-stage2.md" \
      "$HELPER" --implement-tmpdir "$impl_bl" --print-stdout 2>/dev/null)
assert_schema_ordered "$fallback_stage2" 'renderer fallback stage2 keeps ordered implement schema' \
    '## /implement run run-bl — bailed' \
    '- **Outcome**: bailed' \
    '- **Mode**: N/A' \
    '- **Path**: N/A' \
    '- **Duration**: N/A' \
    '- **Cost**: N/A' \
    '- **Issue**: #9 — https://github.com/owner/repo/issues/9' \
    '- **Plan review**: N/A' \
    '- **Code review**: N/A' \
    '- **OOS filed**: 0' \
    '- **Exec issues**: 0' \
    '- **Warnings**: 2' \
    "- **Run logs**: \`larch-logs/implement/run-bl/\`" \
    '<!-- larch:run-summary v=1 -->'
assert_not_contains '- **PR**:' "$fallback_stage2" 'renderer fallback stage2 omits PR when N/A'
assert_contains '### Warnings' "$(cat "$impl_bl/execution-issues.md")" 'renderer fallback stage2 records warning section'
cp "$TMP_ROOT/render-run-summary.real" "$plugin/scripts/render-run-summary.sh"
chmod +x "$plugin/scripts/render-run-summary.sh"

impl_fork_fb="$TMP_ROOT/impl-fork-fb"; mkdir -p "$impl_fork_fb"
printf 'ISSUE_NUMBER=18\nRUN_ID=run-fork-fb\nADOPTED=true\n' > "$impl_fork_fb/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_fork_fb/session-env.sh"
{
    printf 'PR_URL=https://example.test/pr/18\n'
    printf 'PR_NUMBER=18\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=true\n'
} > "$impl_fork_fb/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_fork_fb/finalize-state.sh"
cat > "$plugin/scripts/render-run-summary.sh" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
chmod +x "$plugin/scripts/render-run-summary.sh"
fork_fb=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-fork-fb.md" \
      "$HELPER" --implement-tmpdir "$impl_fork_fb" --print-stdout 2>/dev/null)
assert_contains '## Fork CI Dry-Run Complete' "$fork_fb" 'renderer fallback stage2 preserves fork notes after sentinel'
cp "$TMP_ROOT/render-run-summary.real" "$plugin/scripts/render-run-summary.sh"
chmod +x "$plugin/scripts/render-run-summary.sh"

rm -f "$impl_bl/.step17-printed"
step18_printed=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-step18-print.md" bash -c '
  _wfr_args=(--implement-tmpdir "$1")
  [ ! -f "$1/.step17-printed" ] && _wfr_args+=(--print-stdout)
  "$2" "${_wfr_args[@]}" || true
' bash "$impl_bl" "$HELPER" 2>/dev/null)
assert_contains '## /implement run run-bl — bailed' "$step18_printed" 'Step 18 absent sentinel prints summary body'
touch "$impl_bl/.step17-printed"
step18_suppressed=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-step18-suppressed.md" bash -c '
  _wfr_args=(--implement-tmpdir "$1")
  [ ! -f "$1/.step17-printed" ] && _wfr_args+=(--print-stdout)
  "$2" "${_wfr_args[@]}" || true
' bash "$impl_bl" "$HELPER" 2>/dev/null)
assert_not_contains '## /implement run run-bl — bailed' "$step18_suppressed" 'Step 18 sentinel suppresses summary body'
assert_not_contains '- **Cost**:' "$step18_suppressed" 'Step 18 sentinel suppresses summary cost line'

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

impl_badjson="$TMP_ROOT/impl-badjson"; mkdir -p "$impl_badjson/larch-logs/implement/run-badjson"
printf 'ISSUE_NUMBER=21\nRUN_ID=run-badjson\nADOPTED=true\n' > "$impl_badjson/parent-issue.md"
printf 'REPO=owner/repo\n' > "$impl_badjson/session-env.sh"
{
    printf 'PR_URL=N/A\n'
    printf 'PR_NUMBER=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'MERGE_RESULT=\n'
    printf 'MERGE=false\n'
    printf 'DRAFT=false\n'
    printf 'FORKED_TARGET=false\n'
} > "$impl_badjson/ship-pr-state.sh"
printf 'DESIGN_ONLY_DONE=false\nBAIL_NEEDS_USER_INPUT=false\n' > "$impl_badjson/finalize-state.sh"
printf '{not-json\n' > "$impl_badjson/larch-logs/implement/run-badjson/token-report.json"
badjson_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content-badjson.md" \
      "$HELPER" --implement-tmpdir "$impl_badjson" --print-stdout)
assert_contains '- **Cost**: N/A' "$badjson_stdout" 'malformed token-report renders cost N/A'
assert_not_contains "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$badjson_stdout" 'malformed token-report omits misleading zero-dollar breakdown'

make_impl_fixture() {
    local dir=$1 issue=$2 run=$3 pr_url=$4 pr_number=$5 stall=$6 merge_result=$7 merge=$8 draft=$9 forked=${10} design_only=${11} bail_user=${12}
    mkdir -p "$dir/larch-logs/implement/$run"
    printf 'ISSUE_NUMBER=%s\nRUN_ID=%s\nADOPTED=true\n' "$issue" "$run" > "$dir/parent-issue.md"
    printf 'REPO=owner/repo\n' > "$dir/session-env.sh"
    {
        printf 'PR_URL=%s\n' "$pr_url"
        printf 'PR_NUMBER=%s\n' "$pr_number"
        printf 'STALL_TRACKING=%s\n' "$stall"
        printf 'MERGE_RESULT=%s\n' "$merge_result"
        printf 'MERGE=%s\n' "$merge"
        printf 'DRAFT=%s\n' "$draft"
        printf 'FORKED_TARGET=%s\n' "$forked"
    } > "$dir/ship-pr-state.sh"
    printf 'DESIGN_ONLY_DONE=%s\nBAIL_NEEDS_USER_INPUT=%s\n' "$design_only" "$bail_user" > "$dir/finalize-state.sh"
    cat > "$dir/larch-logs/implement/$run/token-report.json" <<'JSON'
{
  "claude": {"totals": {"total": 1000}},
  "codex": {"totals": {"total": 2000}},
  "cursor": {"totals": {"total": 3000}},
  "BUCKETS_claude": {"input": 500, "cache_read": 100, "cache_create_5m": 50, "cache_create_1h": 50, "output": 300},
  "BUCKETS_codex": {"input": 1000, "cached_input": 500, "output": 500},
  "BUCKETS_cursor": {"input": 1500, "cache_read": 500, "output": 1000}
}
JSON
}

make_impl_fixture "$TMP_ROOT/impl-pr-created" 30 run-pr-created https://example.test/pr/30 30 false "" false false false false false
make_impl_fixture "$TMP_ROOT/impl-pr-created-draft" 31 run-pr-created-draft https://example.test/pr/31 31 false "" false true false false false
make_impl_fixture "$TMP_ROOT/impl-forked" 32 run-forked https://example.test/pr/32 32 false "" false false true false false
make_impl_fixture "$TMP_ROOT/impl-force-merged" 33 run-force-merged https://example.test/pr/33 33 false already_merged true false false false false

for outcome_case in \
    "merged:$impl_dir:absent:present" \
    "stalled:$impl_st:present:present" \
    "design-only:$impl_do:absent:absent" \
    "bailed-needs-user-input:$impl_bu:present:absent" \
    "bailed:$impl_bl:present:absent" \
    "forked-dry-run:$TMP_ROOT/impl-forked:absent:present" \
    "pr-created:$TMP_ROOT/impl-pr-created:absent:present" \
    "pr-created-draft:$TMP_ROOT/impl-pr-created-draft:absent:present" \
    "force-merged-externally:$TMP_ROOT/impl-force-merged:absent:present"
do
    IFS=: read -r expected fixture expect_outcome expect_pr <<EOF
$outcome_case
EOF
    matrix_stdout=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/matrix-${expected}.md" \
        "$HELPER" --implement-tmpdir "$fixture" --print-stdout)
    matrix_summary="$(stdout_summary_block "$matrix_stdout")"
    cost_line=$(printf '%s\n' "$matrix_summary" | grep -F -- '- **Cost**:' || true)
    assert_contains "## /implement run " "$matrix_summary" "matrix $expected prints summary title"
    assert_contains "— $expected" "$matrix_summary" "matrix $expected title outcome"
    assert_contains '- **Cost**:' "$matrix_summary" "matrix $expected prints cost line"
    assert_contains '<!-- larch:run-summary v=1 -->' "$matrix_summary" "matrix $expected keeps sentinel"
    cmp -s <(printf '%s\n' "$matrix_summary") "$fixture/summary-final.md" || fail "matrix $expected stdout summary/file mismatch"
    assert_contains "## /implement run " "$(cat "$fixture/summary-final.md")" "matrix $expected file prints summary title"
    assert_contains "— $expected" "$(cat "$fixture/summary-final.md")" "matrix $expected file title outcome"
    assert_contains '- **Cost**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file prints cost line"
    assert_contains '<!-- larch:run-summary v=1 -->' "$(cat "$fixture/summary-final.md")" "matrix $expected file keeps sentinel"
    if [ "$expected" = "merged" ] || [ "$expected" = "forked-dry-run" ] || [ "$expected" = "pr-created" ] || [ "$expected" = "pr-created-draft" ] || [ "$expected" = "force-merged-externally" ]; then
        assert_contains '💰 TOTAL' "$cost_line" "matrix $expected cost line has total"
        assert_contains 'Claude $' "$cost_line" "matrix $expected cost line has Claude"
        assert_contains 'Codex $' "$cost_line" "matrix $expected cost line has Codex"
        assert_contains 'Cursor $' "$cost_line" "matrix $expected cost line has Cursor"
        assert_contains 'Tokens: ' "$cost_line" "matrix $expected cost line has token count"
    fi
    if [ "$expect_outcome" = present ]; then
        assert_contains "- **Outcome**: $expected" "$matrix_summary" "matrix $expected emits Outcome bullet"
        assert_contains "- **Outcome**: $expected" "$(cat "$fixture/summary-final.md")" "matrix $expected file emits Outcome bullet"
    else
        assert_not_contains '- **Outcome**:' "$matrix_summary" "matrix $expected omits Outcome bullet"
        assert_not_contains '- **Outcome**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file omits Outcome bullet"
    fi
    if [ "$expect_pr" = present ]; then
        assert_contains '- **PR**:' "$matrix_summary" "matrix $expected emits PR bullet"
        assert_contains '- **PR**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file emits PR bullet"
    else
        assert_not_contains '- **PR**:' "$matrix_summary" "matrix $expected omits PR bullet"
        assert_not_contains '- **PR**:' "$(cat "$fixture/summary-final.md")" "matrix $expected file omits PR bullet"
    fi
done

finish
