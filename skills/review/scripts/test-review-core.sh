#!/usr/bin/env bash
# Regression harness skeleton for review-core.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/review-core.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-review-core.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

assert_contains() {
    local haystack="$1" needle="$2"
    grep -Fq "$needle" <<< "$haystack" || { echo "FAIL: missing '$needle'" >&2; echo "$haystack" >&2; exit 1; }
}

write_stubs() {
    cat > "$TMP/gather.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
mode=""
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) mode="$2"; shift 2 ;;
    --output-dir) out="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$out"
printf 'DIFF_FILE=%s/diff.patch\n' "$out"
printf 'FILE_LIST_FILE=%s/scope-files.txt\n' "$out"
printf 'COMMIT_LOG_FILE=%s/commits.txt\n' "$out"
printf 'COMMIT_COUNT=1\n'
printf 'SCOPE_FILES_COUNT=%s\n' "${TEST_SCOPE_COUNT:-1}"
printf 'MODE=%s\n' "$mode"
STUB
    cat > "$TMP/dispatch.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tmp=""
panel="hard"
round_num="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --panel) panel="$2"; shift 2 ;;
    --round-num) round_num="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$tmp"
external="$tmp/codex-specialist-structure-output.txt"
claude="$tmp/claude-generic-output.txt"
printf 'reviewer finding\n' > "$external"
printf 'claude finding\n' > "$claude"
printf '0\n' > "$claude.done"
case "${TEST_DIRTY_STATUS:-clean}" in
  missing) : ;;
  dirty)
    printf 'tracked\0' > "$tmp/tracked.z"
    printf 'STATUS=dirty\nTRACKED_PATHS_FILE=%s/tracked.z\n' "$tmp" > "$external.dirty-tree"
    printf 'STATUS=clean\n' > "$claude.dirty-tree"
    ;;
  unknown)
    printf 'STATUS=unknown\n' > "$external.dirty-tree"
    printf 'STATUS=clean\n' > "$claude.dirty-tree"
    ;;
  *)
    printf 'STATUS=clean\n' > "$external.dirty-tree"
    printf 'STATUS=clean\n' > "$claude.dirty-tree"
    ;;
esac
printf 'EXTERNAL_OUTPUT_FILES=%s\n' "$external"
printf 'CLAUDE_OUTPUT_FILES=%s\n' "$claude"
printf 'PANEL_MODE=%s\n' "${TEST_PANEL_MODE:-normal}"
printf 'PANEL_SHAPE=%s\n' "$panel"
printf 'SCOUT_STATUS=%s\n' "${TEST_SCOUT_STATUS:-na}"
printf 'DYNAMIC_SLOTS=%s\n' "${TEST_DYNAMIC_SLOTS:-0}"
printf 'SCOUT_MANIFEST=%s/scout-round%s-manifest.json\n' "$tmp" "$round_num"
printf 'SLOT_COUNT=2\n'
printf 'PANEL_MANIFEST=%s/panel-manifest.ndjson\n' "$tmp"
printf 'DISPATCH_OK=true\n'
cat > "$tmp/panel-manifest.ndjson" <<EOF
{"slot":"structure","tool":"cursor","output":"$external","agent":"agents/reviewer-structure.md"}
{"slot":"generic","tool":"claude","output":"$claude","agent":"agents/reviewer-generic.md"}
EOF
STUB
    cat > "$TMP/collect.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
findings=""
oos=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) oos="$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$(dirname "$findings")"
: > "$oos"
if [[ "${TEST_FINDINGS:-0}" -eq 0 ]]; then
  : > "$findings"
else
  cat > "$findings" <<'EOF'
### FINDING_1: Example
- **Reviewer**: stub
- **Concern**: concern
- **Suggested revision**: fix it
EOF
fi
printf 'FINDINGS_COUNT=%s\n' "${TEST_FINDINGS:-0}"
printf 'OOS_COUNT=0\nDIRTY_DETECTED=false\nCOLLECT_OK=true\nCOLLECTOR_OUTPUT_FILE=collector.env\n'
STUB
cat > "$TMP/tally.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tmp=""
voter_count=0
manifest=""
collector=""
not_substantive=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --manifest-file) manifest="$2"; shift 2 ;;
    --collector-results-file) collector="$2"; shift 2 ;;
    --not-substantive-count) not_substantive="$2"; shift 2 ;;
    --voter-files)
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        voter_count=$((voter_count + 1))
        shift
      done
      ;;
    *) shift 2 ;;
  esac
done
accepted="${TEST_ACCEPTED:-0}"
rejected="${TEST_REJECTED:-0}"
status="${TEST_TALLY_STATUS:-ok}"
if [[ "$voter_count" -eq 0 ]]; then
  status="main-agent-vote-required"
  accepted=0
  rejected=0
fi
printf 'FINDING_1_ACCEPTED=%s\n' "$([[ "$accepted" -gt 0 ]] && printf true || printf false)" > "$tmp/review-tally.env"
{
  printf '# tally\n'
  [[ -n "$manifest" ]] && printf 'manifest=%s\n' "$manifest"
  [[ -n "$collector" ]] && printf 'collector=%s\n' "$collector"
  printf 'not_substantive=%s\n' "$not_substantive"
} > "$tmp/voting-tally.md"
if [[ "$accepted" -gt 0 ]]; then
  printf '### FINDING_1: Example\n- **Concern**: concern\n' > "$tmp/accepted-findings.md"
else
  : > "$tmp/accepted-findings.md"
fi
: > "$tmp/rejected-findings.md"
printf 'TALLY_STATUS=%s\nACCEPTED_COUNT=%s\nREJECTED_COUNT=%s\nTALLY_FILE=%s/review-tally.env\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nVOTING_TALLY_FILE=%s/voting-tally.md\nTALLY_OK=true\n' "$status" "$accepted" "$rejected" "$tmp" "$tmp" "$tmp" "$tmp"
STUB
    cat > "$TMP/emit.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tmp=""
session=""
scout_status="na"
dynamic_slots="0"
static_slot_count="0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --session-env-path) session="$2"; shift 2 ;;
    --scout-status) scout_status="$2"; shift 2 ;;
    --dynamic-slots) dynamic_slots="$2"; shift 2 ;;
    --static-slot-count) static_slot_count="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
printf '# summary\n' > "$tmp/review-round-summary.md"
printf '{"schema_version":2,"accepted_count":0,"rejected_count":0,"panel":{"scout_status":"%s","dynamic_slot_count":%s,"static_slot_count":%s,"total_slot_count":%s}}\n' \
  "$scout_status" "$dynamic_slots" "$static_slot_count" "$(( static_slot_count + dynamic_slots ))" > "$tmp/review-summary.json"
printf '# rejected\n' > "$tmp/rejected-findings.md"
printf '### [Code Review] Stub Reviewer\n\n**Finding**: full rejected body\n' > "$tmp/rejected-findings-full.md"
printf '# oos\n' > "$tmp/oos-accepted-review.md"
if [[ -n "$session" ]]; then
  parent_dir=$(dirname "$session")
  mkdir -p "$parent_dir"
  cp "$tmp/review-round-summary.md" "$parent_dir/review-round-summary.md" 2>/dev/null || true
  cp "$tmp/review-summary.json" "$parent_dir/review-summary.json" 2>/dev/null || true
  cp "$tmp/rejected-findings-full.md" "$parent_dir/rejected-findings-full.md" 2>/dev/null || true
fi
printf 'EMIT_OK=true\nROUND_SUMMARY_FILE=%s/review-round-summary.md\nREVIEW_SUMMARY_FILE=%s/review-summary.json\n' "$tmp" "$tmp"
STUB
    cat > "$TMP/check-dirty.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'STATUS=%s\nMODE=checkpoint\n' "${TEST_CHECKPOINT_STATUS:-clean}"
STUB
    cat > "$TMP/check-threshold.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
# Test stub: emit the threshold result from TEST_THRESHOLD_OK (default true).
ok="${TEST_THRESHOLD_OK:-true}"
printf 'INTENDED_SLOTS=12\nSUCCEEDED_SLOTS=12\nFAILED_SLOTS=0\nCOUNTED_SLOTS=12\nTHRESHOLD_OK=%s\nTHRESHOLD_REASON=\nNOT_SUBSTANTIVE_SLOTS=%s\n' "$ok" "${TEST_NOT_SUBSTANTIVE_SLOTS:-0}"
STUB
    cat > "$TMP/dispatch-voters.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
review_tmpdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) review_tmpdir="$2"; shift 2 ;;
    --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$review_tmpdir"
printf 'FINDING_1: YES\n' > "$review_tmpdir/claude-vote-output.txt"
printf 'FINDING_1: YES\n' > "$review_tmpdir/codex-vote-output.txt"
printf 'FINDING_1: YES\n' > "$review_tmpdir/cursor-vote-output.txt"
if [[ "${TEST_PANEL_MODE:-}" == "both-down" ]]; then
  printf 'VOTER_1_PATH=%s/claude-vote-output.txt\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=failed\n' "$review_tmpdir"
  printf 'VOTER_2_PATH=%s/codex-vote-output.txt\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=failed\n' "$review_tmpdir"
  printf 'VOTER_3_PATH=%s/cursor-vote-output.txt\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=failed\n' "$review_tmpdir"
else
  printf 'VOTER_1_PATH=%s/claude-vote-output.txt\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$review_tmpdir"
  printf 'VOTER_2_PATH=%s/codex-vote-output.txt\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$review_tmpdir"
  printf 'VOTER_3_PATH=%s/cursor-vote-output.txt\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$review_tmpdir"
fi
printf 'DISPATCH_OK=true\n'
STUB
    chmod +x "$TMP"/*.sh
}

run_core() {
    local outdir="$1" mode="${2:-diff}" session_env="${3:-}"
    local args=(--mode "$mode" --output-dir "$outdir" --codex-available true --cursor-available true --panel simple --round-num "${TEST_ROUND_NUM:-1}")
    [[ -n "$session_env" ]] && args+=(--session-env-path "$session_env")
    REVIEW_CORE_GATHER_CONTEXT_SH="$TMP/gather.sh" \
    REVIEW_CORE_DISPATCH_PANEL_SH="$TMP/dispatch.sh" \
    REVIEW_CORE_COLLECT_FINDINGS_SH="$TMP/collect.sh" \
    REVIEW_CORE_TALLY_VOTES_SH="$TMP/tally.sh" \
    REVIEW_CORE_EMIT_TALLY_SH="$TMP/emit.sh" \
    REVIEW_CORE_CHECK_DIRTY_TREE_SH="$TMP/check-dirty.sh" \
    REVIEW_CORE_CHECK_THRESHOLD_SH="$TMP/check-threshold.sh" \
    REVIEW_CORE_DISPATCH_VOTERS_SH="$TMP/dispatch-voters.sh" \
    "$SCRIPT" "${args[@]}"
}

run_core_with_log_stub() {
    local outdir="$1" session_env="$2"
    # flush_round_log requires IMPLEMENT_TMPDIR/larch-logs; without it write-round
    # is skipped and execution-issues never receives the failure record.
    local impl_tmp="$TMP/implement-for-write-round"
    mkdir -p "$impl_tmp"
    local log_stub="$TMP/larch-log-fail.sh"
    cat > "$log_stub" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'write-round failed with sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' >&2
exit 7
STUB
    chmod +x "$log_stub"
    local args=(--mode diff --output-dir "$outdir" --codex-available true --cursor-available true --panel simple --run-id test-run)
    [[ -n "$session_env" ]] && args+=(--session-env-path "$session_env")
    IMPLEMENT_TMPDIR="$impl_tmp" \
    REVIEW_CORE_GATHER_CONTEXT_SH="$TMP/gather.sh" \
    REVIEW_CORE_DISPATCH_PANEL_SH="$TMP/dispatch.sh" \
    REVIEW_CORE_COLLECT_FINDINGS_SH="$TMP/collect.sh" \
    REVIEW_CORE_TALLY_VOTES_SH="$TMP/tally.sh" \
    REVIEW_CORE_EMIT_TALLY_SH="$TMP/emit.sh" \
    REVIEW_CORE_CHECK_DIRTY_TREE_SH="$TMP/check-dirty.sh" \
    REVIEW_CORE_CHECK_THRESHOLD_SH="$TMP/check-threshold.sh" \
    REVIEW_CORE_DISPATCH_VOTERS_SH="$TMP/dispatch-voters.sh" \
    REVIEW_CORE_LARCH_LOG_SH="$log_stub" \
    "$SCRIPT" "${args[@]}"
}

write_stubs

out=$(TEST_FINDINGS=0 run_core "$TMP/zero")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'PANEL_SHAPE=simple'
assert_contains "$out" 'SCOUT_STATUS=na'
assert_contains "$out" 'DYNAMIC_SLOTS=0'
assert_contains "$out" "VOTING_TALLY_FILE=$TMP/zero/voting-tally.md"
[[ -f "$TMP/zero/review-dirty-tree-summary.env" ]] || { echo "FAIL: missing review-dirty-tree-summary.env" >&2; exit 1; }
[[ -f "$TMP/zero/voting-tally.md" ]] || { echo "FAIL: missing zero-findings voting-tally.md" >&2; exit 1; }
jq -e '.schema_version == 2 and .accepted_count == 0 and .rejected_count == 0 and .panel.scout_status == "na" and .panel.static_slot_count == 0 and .panel.dynamic_slot_count == 0 and .panel.total_slot_count == 0' \
    "$TMP/zero/review-summary.json" >/dev/null || { echo "FAIL: zero-findings review-summary.json missing panel fields" >&2; cat "$TMP/zero/review-summary.json" >&2; exit 1; }

out=$(TEST_FINDINGS=0 TEST_SCOUT_STATUS=ok TEST_DYNAMIC_SLOTS=3 run_core "$TMP/zero-scout")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'SCOUT_STATUS=ok'
assert_contains "$out" 'DYNAMIC_SLOTS=3'
jq -e '.panel.scout_status == "ok" and .panel.dynamic_slot_count == 3 and .panel.total_slot_count == 3' \
    "$TMP/zero-scout/review-summary.json" >/dev/null || { echo "FAIL: zero-scout review-summary.json missing dynamic panel fields" >&2; exit 1; }

out=$(TEST_FINDINGS=0 TEST_NOT_SUBSTANTIVE_SLOTS=2 run_core "$TMP/zero-degraded")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'not_substantive=2' "$TMP/zero-degraded/voting-tally.md" || { echo "FAIL: zero-findings tally missing degraded slot count" >&2; exit 1; }

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_REJECTED=0 run_core "$TMP/fix")
assert_contains "$out" 'REVIEW_CORE_STATUS=fix-required'
assert_contains "$out" "ACCEPTED_FINDINGS_FILE=$TMP/fix/accepted-findings.md"

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=0 TEST_REJECTED=1 run_core "$TMP/rejected")
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_PANEL_MODE=both-down run_core "$TMP/both")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
assert_contains "$out" 'PANEL_MODE=both-down'

set +e
out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_THRESHOLD_OK=false TEST_SCOUT_STATUS=ok TEST_DYNAMIC_SLOTS=2 run_core "$TMP/panel-failed")
rc=$?
set -e
if [[ "$rc" -ne 2 ]]; then
    echo "FAIL: panel-failed should exit 2" >&2
    exit 1
fi
assert_contains "$out" 'REVIEW_CORE_STATUS=panel-failed'
assert_contains "$out" 'SCOUT_STATUS=ok'
assert_contains "$out" 'DYNAMIC_SLOTS=2'

out=$(TEST_FINDINGS=1 TEST_TALLY_STATUS=main-agent-vote-required run_core "$TMP/main-agent")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
assert_contains "$out" 'ACCEPTED_COUNT=0'

out=$(TEST_FINDINGS=1 TEST_TALLY_STATUS=main-agent-vote-required TEST_SCOUT_STATUS=ok TEST_DYNAMIC_SLOTS=4 run_core "$TMP/main-agent-scout")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
assert_contains "$out" 'SCOUT_STATUS=ok'
assert_contains "$out" 'DYNAMIC_SLOTS=4'

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 run_core "$TMP/desc" description)
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'

parent="$TMP/parent"
mkdir -p "$parent"
out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 run_core "$TMP/parent-run" diff "$parent/session.env")
assert_contains "$out" 'REVIEW_CORE_STATUS=fix-required'
[[ -f "$parent/rejected-findings.md" ]] || { echo "FAIL: missing parent rejected-findings.md" >&2; exit 1; }
[[ -f "$parent/rejected-findings-full.md" ]] || { echo "FAIL: missing parent rejected-findings-full.md" >&2; exit 1; }
[[ -f "$parent/oos-accepted-review.md" ]] || { echo "FAIL: missing parent oos-accepted-review.md" >&2; exit 1; }
[[ -f "$parent/review-dirty-tree-summary.env" ]] || { echo "FAIL: missing parent review-dirty-tree-summary.env" >&2; exit 1; }

out=$(TEST_FINDINGS=0 TEST_DIRTY_STATUS=dirty TEST_CHECKPOINT_STATUS=dirty run_core "$TMP/dirty")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'ANY_DIRTY=true' "$TMP/dirty/review-dirty-tree-summary.env"

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_SCOUT_STATUS=ok TEST_DYNAMIC_SLOTS=2 TEST_ROUND_NUM=3 run_core "$TMP/round3")
assert_contains "$out" 'SCOUT_STATUS=ok'
assert_contains "$out" 'DYNAMIC_SLOTS=2'
grep -Fq 'SCOUT_STATUS=ok' "$TMP/round3/scout-round3-status.env"
grep -Fq 'RECOVERY_TAKEN=true' "$TMP/dirty/review-dirty-tree-summary.env"

out=$(TEST_FINDINGS=0 TEST_DIRTY_STATUS=unknown TEST_CHECKPOINT_STATUS=unknown run_core "$TMP/unknown")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'LAUNCHERS_DIRTY=codex-specialist-structure-output.txt' "$TMP/unknown/review-dirty-tree-summary.env"

issues_parent="$TMP/issues-parent"
mkdir -p "$issues_parent"
out=$(TEST_FINDINGS=0 run_core_with_log_stub "$TMP/log-fail" "$issues_parent/session.env")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'larch-log.sh write-round failed (exit 7' "$issues_parent/execution-issues.md" || {
    echo "FAIL: missing review-core write-round execution issue" >&2
    exit 1
}
if grep -Fq 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' "$issues_parent/execution-issues.md"; then
    echo "FAIL: execution-issues should redact write-round stderr" >&2
    exit 1
fi

# Empty export is ignored (same semantics as review-and-fix.sh / test-review-and-fix.sh).
set +e
out=$(LARCH_DYNAMIC_ARCHETYPES_MAX='' run_core "$TMP/empty-env")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "FAIL: empty LARCH_DYNAMIC_ARCHETYPES_MAX expected exit 0 got $rc" >&2; echo "$out" >&2; exit 1; }
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'DYNAMIC_SLOTS=0'

echo "All assertions passed."
