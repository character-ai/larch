#!/usr/bin/env bash
# Regression harness skeleton for review-core.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
unset LARCH_QUIET_BREADCRUMB_FD || true
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
if [[ -n "${TEST_SCOUT_FAIL_REASON:-}" ]]; then
  printf 'SCOUT_FAIL_REASON=%s\n' "$TEST_SCOUT_FAIL_REASON"
fi
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
rtmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) oos="$2"; shift 2 ;;
    --review-tmpdir) rtmp="$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$(dirname "$findings")"
: > "$oos"
if [[ -n "${TEST_REVIEW_CORE_AGG_ORDER:-}" ]]; then
  rtmp="${rtmp:-$(dirname "$findings")}"
  printf 'collect\n' >> "$rtmp/invoke-order.log"
fi
if [[ "${TEST_FINDINGS:-0}" -eq 0 ]]; then
  : > "$findings"
elif [[ -n "${TEST_REVIEW_CORE_AGG_ORDER:-}" ]]; then
  cat > "$findings" <<'EOF'
### FINDING_1: First stub finding
- **Reviewer**: stub-one-output.txt
- **Concern**: concern one
- **Suggested revision**: fix it

### FINDING_2: Second stub finding
- **Reviewer**: stub-two-output.txt
- **Concern**: concern two
- **Suggested revision**: fix it

EOF
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
round_num="${TEST_ROUND_NUM:-1}"
emit_classification="${TEST_TALLY_EMIT_CLASSIFICATION:-true}"
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
if [[ "$emit_classification" == "true" ]]; then
  printf 'finding_id\treviewer_slots\tvoting_result\n' > "$tmp/findings-classification-round-${round_num}.tsv"
fi
printf 'TALLY_STATUS=%s\nACCEPTED_COUNT=%s\nREJECTED_COUNT=%s\nTALLY_FILE=%s/review-tally.env\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nVOTING_TALLY_FILE=%s/voting-tally.md\n' "$status" "$accepted" "$rejected" "$tmp" "$tmp" "$tmp" "$tmp"
if [[ "$emit_classification" == "true" ]]; then
  printf 'FINDINGS_CLASSIFICATION_TSV_FILE=%s/findings-classification-round-%s.tsv\n' "$tmp" "$round_num"
fi
printf 'TALLY_OK=true\n'
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
if [[ "${TEST_EMIT_FAIL:-false}" == "true" ]]; then
  printf 'emit failed sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' >&2
  exit 7
fi
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
printf 'dispatch-voters\n' >> "$review_tmpdir/dispatch-voters.log"
if [[ -n "${TEST_REVIEW_CORE_AGG_ORDER:-}" ]]; then
  printf 'voters\n' >> "$review_tmpdir/invoke-order.log"
fi
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
    cat > "$TMP/aggregate-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --review-tmpdir) review_tmpdir="${2:?}"; shift 2 ;;
        --slots-file) slots="${2:?}"; shift 2 ;;
        --codex-present|--cursor-present|--mode) shift 2 ;;
        --diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
mode="${AGGREGATE_STUB_MODE:-ok}"
case "$mode" in
    fail_dispatch)
        printf 'DISPATCH_OK=false\nALL_OUTPUT_FILES=\nALL_OUTPUT_FILES_PATH=\nALL_OUTPUT_TOOLS=\n'
        ;;
    ok)
        cat > "$out" <<'EOF'
### FINDING_1: merged example
- **Reviewer(s)**: stub-one-output.txt, stub-two-output.txt
- **Concern**: merged concern
- **Suggested revision**: fix it

EOF
        printf '%s\n' "$out" > "$review_tmpdir/aggregate-output-files.txt"
        printf 'DISPATCH_OK=true\nALL_OUTPUT_FILES=%s\nALL_OUTPUT_FILES_PATH=%s\nALL_OUTPUT_TOOLS=%s\n' \
            "$out" \
            "$review_tmpdir/aggregate-output-files.txt" \
            "${AGGREGATE_STUB_OUTPUT_TOOL:-cursor}"
        ;;
    *)
        echo "stub: bad AGGREGATE_STUB_MODE" >&2
        exit 2
        ;;
esac
STUB
    cat > "$TMP/aggregate-log.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
AGG="$REPO_ROOT/skills/review/scripts/aggregate-findings.sh"
rtmp=""
args=("\$@")
i=0
while [[ \$i -lt \${#args[@]} ]]; do
  if [[ "\${args[i]}" == --review-tmpdir ]]; then
    rtmp="\${args[i+1]}"
    break
  fi
  i=\$((i + 1))
done
    printf 'aggregate\n' >> "\${rtmp:?}/invoke-order.log"
exec "\$AGG" "\$@"
EOF
cat > "$TMP/aggregate-exhausted-stub.sh" <<'STUB'
#!/usr/bin/env bash
printf 'AGGREGATED=false\nINPUT_COUNT=2\nMERGED_COUNT=0\nREASON=validation-exhausted\n'
exit 0
STUB
cat > "$TMP/aggregate-zero-success-stub.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
findings=""
review_tmpdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --review-tmpdir) review_tmpdir="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
if [[ -n "${TEST_REVIEW_CORE_AGG_ORDER:-}" ]]; then
  printf 'aggregate\n' >> "${review_tmpdir:?}/invoke-order.log"
fi
: > "${findings:?}"
printf 'AGGREGATED=true\nINPUT_COUNT=2\nMERGED_COUNT=0\nREASON=ok\n'
STUB
cat > "$TMP/aggregate-zero-success-missing-count-stub.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
findings=""
review_tmpdir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --review-tmpdir) review_tmpdir="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
if [[ -n "${TEST_REVIEW_CORE_AGG_ORDER:-}" ]]; then
  printf 'aggregate\n' >> "${review_tmpdir:?}/invoke-order.log"
fi
: > "${findings:?}"
printf 'AGGREGATED=true\nINPUT_COUNT=2\nREASON=ok\n'
STUB
    chmod +x "$TMP"/*.sh
}

run_core_agg_order() {
    local outdir="$1"
    local args=(--mode diff --output-dir "$outdir" --codex-available true --cursor-available true --panel simple --round-num "${TEST_ROUND_NUM:-1}")
    unset LARCH_AGGREGATOR_DISABLED || true
    AGGREGATE_DISPATCH_SH="$TMP/aggregate-dispatch.sh" \
    AGGREGATE_STUB_MODE=ok \
    REVIEW_CORE_AGGREGATE_FINDINGS_SH="$TMP/aggregate-log.sh" \
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

run_core() {
    local outdir="$1" mode="${2:-diff}" session_env="${3:-}"
    local args=(--mode "$mode" --output-dir "$outdir" --codex-available true --cursor-available true --panel simple --round-num "${TEST_ROUND_NUM:-1}")
    [[ -n "$session_env" ]] && args+=(--session-env-path "$session_env")
    LARCH_AGGREGATOR_DISABLED=1 REVIEW_CORE_GATHER_CONTEXT_SH="$TMP/gather.sh" \
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
    LARCH_AGGREGATOR_DISABLED=1 REVIEW_CORE_GATHER_CONTEXT_SH="$TMP/gather.sh" \
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
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE=$TMP/zero/findings-classification-round-1.tsv"
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/zero/findings-classification-round-1.tsv"
[[ -f "$TMP/zero/review-dirty-tree-summary.env" ]] || { echo "FAIL: missing review-dirty-tree-summary.env" >&2; exit 1; }
[[ -f "$TMP/zero/voting-tally.md" ]] || { echo "FAIL: missing zero-findings voting-tally.md" >&2; exit 1; }
[[ -f "$TMP/zero/findings-classification-round-map.env" ]] || { echo "FAIL: missing zero-findings classification round map" >&2; exit 1; }
read -r zero_classification_header < "$TMP/zero/findings-classification-round-1.tsv"
[[ "$zero_classification_header" == $'finding_id\treviewer_slots\tvoting_result' ]] || { echo "FAIL: zero-findings classification TSV should be header-only" >&2; exit 1; }
grep -Fq "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/zero/findings-classification-round-1.tsv" "$TMP/zero/findings-classification-round-map.env" || {
    echo "FAIL: zero-findings round map missing round-1 binding" >&2
    exit 1
}
jq -e '.schema_version == 2 and .accepted_count == 0 and .rejected_count == 0 and .panel.scout_status == "na" and .panel.static_slot_count == 0 and .panel.dynamic_slot_count == 0 and .panel.total_slot_count == 0' \
    "$TMP/zero/review-summary.json" >/dev/null || { echo "FAIL: zero-findings review-summary.json missing panel fields" >&2; cat "$TMP/zero/review-summary.json" >&2; exit 1; }

out=$(TEST_FINDINGS=0 TEST_SCOUT_STATUS=ok TEST_DYNAMIC_SLOTS=3 run_core "$TMP/zero-scout")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'SCOUT_STATUS=ok'
assert_contains "$out" 'DYNAMIC_SLOTS=3'
jq -e '.panel.scout_status == "ok" and .panel.dynamic_slot_count == 3 and .panel.total_slot_count == 3' \
    "$TMP/zero-scout/review-summary.json" >/dev/null || { echo "FAIL: zero-scout review-summary.json missing dynamic panel fields" >&2; exit 1; }

out=$(TEST_FINDINGS=0 TEST_SCOUT_STATUS=parse-failed TEST_SCOUT_FAIL_REASON=json_parse run_core "$TMP/zero-scout-parse-failed")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'SCOUT_STATUS=parse-failed'
assert_contains "$out" 'SCOUT_FAIL_REASON=json_parse'
grep -Fq 'SCOUT_FAIL_REASON=json_parse' "$TMP/zero-scout-parse-failed/scout-round1-status.env"

out=$(TEST_FINDINGS=0 TEST_NOT_SUBSTANTIVE_SLOTS=2 run_core "$TMP/zero-degraded")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'not_substantive=2' "$TMP/zero-degraded/voting-tally.md" || { echo "FAIL: zero-findings tally missing degraded slot count" >&2; exit 1; }

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_REJECTED=0 run_core "$TMP/fix")
assert_contains "$out" 'REVIEW_CORE_STATUS=fix-required'
assert_contains "$out" "ACCEPTED_FINDINGS_FILE=$TMP/fix/accepted-findings.md"
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/fix/findings-classification-round-1.tsv"
grep -Fq "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/fix/findings-classification-round-1.tsv" "$TMP/fix/findings-classification-round-map.env" || {
    echo "FAIL: missing round map binding for fix round" >&2
    exit 1
}

fix_breadcrumbs_out="$TMP/fix-breadcrumbs.out"
fix_breadcrumbs_err="$TMP/fix-breadcrumbs.err"
TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_REJECTED=0 run_core "$TMP/fix-breadcrumbs" >"$fix_breadcrumbs_out" 2>"$fix_breadcrumbs_err"
grep -Fq 'REVIEW_CORE_STATUS=fix-required' "$fix_breadcrumbs_out" || { echo "FAIL: fix-breadcrumbs status" >&2; cat "$fix_breadcrumbs_out" >&2; exit 1; }
grep -Fq '→ review: consolidating findings' "$fix_breadcrumbs_err" || { echo "FAIL: fix-breadcrumbs breadcrumb" >&2; cat "$fix_breadcrumbs_err" >&2; exit 1; }

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=0 TEST_REJECTED=1 run_core "$TMP/rejected")
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=0 TEST_REJECTED=1 TEST_TALLY_EMIT_CLASSIFICATION=false run_core "$TMP/rejected-no-classification")
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'
if grep -Fq 'FINDINGS_CLASSIFICATION_TSV_FILE=' <<< "$out"; then
    echo "FAIL: rejected-no-classification should not emit classification kv" >&2
    exit 1
fi
[[ ! -e "$TMP/rejected-no-classification/findings-classification-round-map.env" ]] || {
    echo "FAIL: rejected-no-classification should not write round map" >&2
    exit 1
}

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_PANEL_MODE=both-down run_core "$TMP/both")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
assert_contains "$out" 'PANEL_MODE=both-down'

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=0 REVIEW_CORE_AGGREGATE_FINDINGS_SH="$TMP/aggregate-zero-success-stub.sh" run_core "$TMP/agg-zero")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
if grep -Fq 'VOTER_' <<< "$out"; then
    echo "FAIL: agg-zero should not emit voter status lines" >&2
    echo "$out" >&2
    exit 1
fi
[[ ! -e "$TMP/agg-zero/dispatch-voters.log" ]] || { echo "FAIL: agg-zero should not dispatch voters" >&2; exit 1; }
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/agg-zero/findings-classification-round-1.tsv"
read -r agg_zero_classification_header < "$TMP/agg-zero/findings-classification-round-1.tsv"
[[ "$agg_zero_classification_header" == $'finding_id\treviewer_slots\tvoting_result' ]] || { echo "FAIL: agg-zero classification TSV should be header-only" >&2; exit 1; }
grep -Fq "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/agg-zero/findings-classification-round-1.tsv" "$TMP/agg-zero/findings-classification-round-map.env" || {
    echo "FAIL: agg-zero round map missing round-1 binding" >&2
    exit 1
}
[[ ! -s "$TMP/agg-zero/accepted-findings.md" ]] || { echo "FAIL: agg-zero accepted-findings.md should remain empty" >&2; exit 1; }
[[ -f "$TMP/agg-zero/voting-tally.md" ]] || { echo "FAIL: agg-zero missing voting-tally.md" >&2; exit 1; }

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=0 REVIEW_CORE_AGGREGATE_FINDINGS_SH="$TMP/aggregate-zero-success-missing-count-stub.sh" run_core "$TMP/agg-zero-missing-count")
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'
if grep -Fq 'REVIEW_CORE_STATUS=zero-findings' <<< "$out"; then
    echo "FAIL: agg-zero-missing-count should not degrade to zero-findings when MERGED_COUNT is absent" >&2
    exit 1
fi
[[ -f "$TMP/agg-zero-missing-count/dispatch-voters.log" ]] || { echo "FAIL: agg-zero-missing-count should dispatch voters" >&2; exit 1; }
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/agg-zero-missing-count/findings-classification-round-1.tsv"
grep -Fq "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/agg-zero-missing-count/findings-classification-round-1.tsv" "$TMP/agg-zero-missing-count/findings-classification-round-map.env" || {
    echo "FAIL: agg-zero-missing-count round map missing round-1 binding" >&2
    exit 1
}

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
jq -e '.schema_version == 2 and .accepted_count == 0 and .rejected_count == 0 and .panel.scout_status == "ok" and .panel.dynamic_slot_count == 2 and .panel.total_slot_count == 2' \
    "$TMP/panel-failed/review-summary.json" >/dev/null || { echo "FAIL: panel-failed review-summary.json missing panel telemetry" >&2; exit 1; }

mkdir -p "$TMP/agg-exhaust-core"
: >"$TMP/agg-exhaust-core/.marker"
set +e
out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 REVIEW_CORE_AGGREGATE_FINDINGS_SH="$TMP/aggregate-exhausted-stub.sh" run_core "$TMP/agg-exhaust-core")
rc=$?
set -e
if [[ "$rc" -ne 2 ]]; then
    echo "FAIL: aggregator validation-exhausted should exit 2" >&2
    exit 1
fi
assert_contains "$out" 'REVIEW_CORE_STATUS=aggregator-validation-exhausted'
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/agg-exhaust-core/findings-classification-round-1.tsv"
[[ -f "$TMP/agg-exhaust-core/findings-classification-round-map.env" ]] || {
    echo "FAIL: aggregator exhaustion should persist round classification map" >&2
    exit 1
}
jq -e '.schema_version == 2 and .accepted_count == 0 and .rejected_count == 0' \
    "$TMP/agg-exhaust-core/review-summary.json" >/dev/null || { echo "FAIL: agg-exhaust review-summary.json" >&2; exit 1; }

out=$(TEST_FINDINGS=1 TEST_TALLY_STATUS=main-agent-vote-required run_core "$TMP/main-agent")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
assert_contains "$out" 'ACCEPTED_COUNT=0'
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE=$TMP/main-agent/findings-classification-round-1.tsv"
assert_contains "$out" "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/main-agent/findings-classification-round-1.tsv"
read -r main_agent_classification_header < "$TMP/main-agent/findings-classification-round-1.tsv"
[[ "$main_agent_classification_header" == $'finding_id\treviewer_slots\tvoting_result' ]] || { echo "FAIL: main-agent classification TSV should be header-only" >&2; exit 1; }
grep -Fq "FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_1=$TMP/main-agent/findings-classification-round-1.tsv" "$TMP/main-agent/findings-classification-round-map.env" || {
    echo "FAIL: main-agent round map missing round-1 binding" >&2
    exit 1
}
jq -e '.schema_version == 2 and .accepted_count == 0 and .rejected_count == 0' \
    "$TMP/main-agent/review-summary.json" >/dev/null || { echo "FAIL: main-agent review-summary.json missing summary output" >&2; exit 1; }

out=$(TEST_FINDINGS=1 TEST_TALLY_STATUS=main-agent-vote-required TEST_SCOUT_STATUS=ok TEST_DYNAMIC_SLOTS=4 run_core "$TMP/main-agent-scout")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
assert_contains "$out" 'SCOUT_STATUS=ok'
assert_contains "$out" 'DYNAMIC_SLOTS=4'
jq -e '.schema_version == 2 and .panel.scout_status == "ok" and .panel.dynamic_slot_count == 4' \
    "$TMP/main-agent-scout/review-summary.json" >/dev/null || { echo "FAIL: main-agent-scout review-summary.json missing panel telemetry" >&2; exit 1; }

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

emit_fail_parent="$TMP/emit-fail-parent"
mkdir -p "$emit_fail_parent"
set +e
out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_THRESHOLD_OK=false TEST_EMIT_FAIL=true run_core "$TMP/panel-failed-emit" diff "$emit_fail_parent/session.env")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "FAIL: panel-failed emit failure should preserve exit 2" >&2; exit 1; }
assert_contains "$out" 'REVIEW_CORE_STATUS=panel-failed'
grep -Fq 'emit-tally.sh (panel-failed) failed (exit 7' "$emit_fail_parent/execution-issues.md" || {
    echo "FAIL: missing panel-failed emit execution issue" >&2
    exit 1
}
if grep -Fq 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' "$emit_fail_parent/execution-issues.md"; then
    echo "FAIL: execution-issues should redact panel-failed emit stderr" >&2
    exit 1
fi

emit_fail_parent="$TMP/emit-fail-zero-parent"
mkdir -p "$emit_fail_parent"
out=$(TEST_FINDINGS=0 TEST_EMIT_FAIL=true run_core "$TMP/zero-emit-fail" diff "$emit_fail_parent/session.env")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'emit-tally.sh (zero-findings) failed (exit 7' "$emit_fail_parent/execution-issues.md" || {
    echo "FAIL: missing zero-findings emit execution issue" >&2
    exit 1
}

emit_fail_parent="$TMP/emit-fail-main-agent-parent"
mkdir -p "$emit_fail_parent"
out=$(TEST_FINDINGS=1 TEST_TALLY_STATUS=main-agent-vote-required TEST_EMIT_FAIL=true run_core "$TMP/main-agent-emit-fail" diff "$emit_fail_parent/session.env")
assert_contains "$out" 'REVIEW_CORE_STATUS=main-agent-vote-required'
grep -Fq 'emit-tally.sh (main-agent-vote-required) failed (exit 7' "$emit_fail_parent/execution-issues.md" || {
    echo "FAIL: missing main-agent emit execution issue" >&2
    exit 1
}

# Empty export is ignored (same semantics as review-and-fix.sh / test-review-and-fix.sh).
set +e
out=$(LARCH_DYNAMIC_ARCHETYPES_MAX='' run_core "$TMP/empty-env")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "FAIL: empty LARCH_DYNAMIC_ARCHETYPES_MAX expected exit 0 got $rc" >&2; echo "$out" >&2; exit 1; }
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'DYNAMIC_SLOTS=0'

ord="$TMP/aggregate-order"
mkdir -p "$ord"
: > "$ord/invoke-order.log"
out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_REVIEW_CORE_AGG_ORDER=1 run_core_agg_order "$ord")
assert_contains "$out" 'REVIEW_CORE_STATUS=fix-required'
grep -Fxq 'collect' "$ord/invoke-order.log" || { echo "FAIL: invoke-order missing collect" >&2; exit 1; }
grep -Fxq 'aggregate' "$ord/invoke-order.log" || { echo "FAIL: invoke-order missing aggregate" >&2; exit 1; }
grep -Fxq 'voters' "$ord/invoke-order.log" || { echo "FAIL: invoke-order missing voters" >&2; exit 1; }
awk 'BEGIN{n=0} /^collect$/{c++} /^aggregate$/{a++} /^voters$/{v++} END{if(c!=1||a!=1||v!=1) exit 1}' "$ord/invoke-order.log" || {
    echo "FAIL: invoke-order should contain exactly one collect, aggregate, voters line each" >&2
    cat "$ord/invoke-order.log" >&2
    exit 1
}
first=$(head -n1 "$ord/invoke-order.log")
mid=$(sed -n '2p' "$ord/invoke-order.log")
last=$(tail -n1 "$ord/invoke-order.log")
[[ "$first" == collect && "$mid" == aggregate && "$last" == voters ]] || {
    echo "FAIL: expected collect → aggregate → voters ordering" >&2
    cat "$ord/invoke-order.log" >&2
    exit 1
}

echo "All assertions passed."
