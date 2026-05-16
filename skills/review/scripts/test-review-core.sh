#!/usr/bin/env bash
# Regression harness skeleton for review-core.sh.

set -euo pipefail

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
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --panel) panel="$2"; shift 2 ;;
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
printf 'SLOT_COUNT=2\n'
printf 'PANEL_MANIFEST=%s/panel-manifest.ndjson\n' "$tmp"
printf 'DISPATCH_OK=true\n'
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
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
accepted="${TEST_ACCEPTED:-0}"
rejected="${TEST_REJECTED:-0}"
printf 'FINDING_1_ACCEPTED=%s\n' "$([[ "$accepted" -gt 0 ]] && printf true || printf false)" > "$tmp/review-tally.env"
if [[ "$accepted" -gt 0 ]]; then
  printf '### FINDING_1: Example\n- **Concern**: concern\n' > "$tmp/accepted-findings.md"
else
  : > "$tmp/accepted-findings.md"
fi
printf 'ACCEPTED_COUNT=%s\nREJECTED_COUNT=%s\nTALLY_FILE=%s/review-tally.env\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nTALLY_OK=true\n' "$accepted" "$rejected" "$tmp" "$tmp"
STUB
    cat > "$TMP/emit.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in --review-tmpdir) tmp="$2"; shift 2 ;; *) shift 2 ;; esac
done
printf '# summary\n' > "$tmp/review-round-summary.md"
printf '{"schema_version":1}\n' > "$tmp/review-summary.json"
printf '# rejected\n' > "$tmp/rejected-findings.md"
printf '# oos\n' > "$tmp/oos-accepted-review.md"
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
printf 'INTENDED_SLOTS=12\nSUCCEEDED_SLOTS=12\nFAILED_SLOTS=0\nCOUNTED_SLOTS=12\nTHRESHOLD_OK=%s\nTHRESHOLD_REASON=\n' "$ok"
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
printf 'VOTER_1_PATH=%s/claude-vote-output.txt\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$review_tmpdir"
printf 'VOTER_2_PATH=%s/codex-vote-output.txt\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$review_tmpdir"
printf 'VOTER_3_PATH=%s/cursor-vote-output.txt\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$review_tmpdir"
printf 'DISPATCH_OK=true\n'
STUB
    chmod +x "$TMP"/*.sh
}

run_core() {
    local outdir="$1" mode="${2:-diff}" session_env="${3:-}"
    local args=(--mode "$mode" --output-dir "$outdir" --codex-available true --cursor-available true --panel simple)
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

write_stubs

out=$(TEST_FINDINGS=0 run_core "$TMP/zero")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
assert_contains "$out" 'PANEL_SHAPE=simple'
[[ -f "$TMP/zero/review-dirty-tree-summary.env" ]]

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_REJECTED=0 run_core "$TMP/fix")
assert_contains "$out" 'REVIEW_CORE_STATUS=fix-required'
assert_contains "$out" "ACCEPTED_FINDINGS_FILE=$TMP/fix/accepted-findings.md"

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=0 TEST_REJECTED=1 run_core "$TMP/rejected")
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 TEST_PANEL_MODE=both-down run_core "$TMP/both")
assert_contains "$out" 'PANEL_MODE=both-down'

out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 run_core "$TMP/desc" description)
assert_contains "$out" 'REVIEW_CORE_STATUS=ok'

parent="$TMP/parent"
mkdir -p "$parent"
out=$(TEST_FINDINGS=1 TEST_ACCEPTED=1 run_core "$TMP/parent-run" diff "$parent/session.env")
assert_contains "$out" 'REVIEW_CORE_STATUS=fix-required'
[[ -f "$parent/rejected-findings.md" ]]
[[ -f "$parent/oos-accepted-review.md" ]]
[[ -f "$parent/review-dirty-tree-summary.env" ]]

out=$(TEST_FINDINGS=0 TEST_DIRTY_STATUS=dirty TEST_CHECKPOINT_STATUS=dirty run_core "$TMP/dirty")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'ANY_DIRTY=true' "$TMP/dirty/review-dirty-tree-summary.env"
grep -Fq 'RECOVERY_TAKEN=true' "$TMP/dirty/review-dirty-tree-summary.env"

out=$(TEST_FINDINGS=0 TEST_DIRTY_STATUS=unknown TEST_CHECKPOINT_STATUS=unknown run_core "$TMP/unknown")
assert_contains "$out" 'REVIEW_CORE_STATUS=zero-findings'
grep -Fq 'LAUNCHERS_DIRTY=codex-specialist-structure-output.txt' "$TMP/unknown/review-dirty-tree-summary.env"

echo "All assertions passed."
