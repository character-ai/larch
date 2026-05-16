#!/usr/bin/env bash
# Regression harness for review-and-fix.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-review-and-fix.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

cat > "$TMP/run-external-agent-stub.sh" <<'EOF_AGENT'
#!/usr/bin/env bash
set -euo pipefail
tool=""
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) tool="$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    --timeout) shift 2 ;;
    --capture-stdout) shift ;;
    --) shift; break ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$output")"
case "${TEST_AGENT_BEHAVIOR:-codex-success}:$tool" in
  codex-success:codex)
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  cursor-success:cursor)
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  claude-success:codex|claude-success:cursor)
    printf 'failed\n' > "$output"
    exit 1
    ;;
  all-fail:codex|all-fail:cursor)
    printf 'failed\n' > "$output"
    exit 1
    ;;
  submodule-violation:codex)
    printf 'changed by coder\n' > vendor/lib/file.txt
    printf 'APPLIED: FINDING_1\n' > "$output"
    exit 0
    ;;
  *)
    printf 'failed\n' > "$output"
    exit 1
    ;;
esac
EOF_AGENT
chmod +x "$TMP/run-external-agent-stub.sh"

cat > "$TMP/launch-claude-subprocess-stub.sh" <<'EOF_CLAUDE'
#!/usr/bin/env bash
set -euo pipefail
output=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-file) output="$2"; shift 2 ;;
    --prompt-file|--timeout|--model|--timing-task-kind) shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$(dirname "$output")"
if [[ "${TEST_AGENT_BEHAVIOR:-}" == "claude-success" ]]; then
  printf 'APPLIED: FINDING_1\n' > "$output"
  printf 'STATUS=OK\nOUTPUT_FILE=%s\n' "$output"
  exit 0
fi
printf 'STATUS=ERROR\nOUTPUT_FILE=%s\n' "$output"
exit 1
EOF_CLAUDE
chmod +x "$TMP/launch-claude-subprocess-stub.sh"

cat > "$TMP/review-core-stub.sh" <<'EOF_CORE'
#!/usr/bin/env bash
set -euo pipefail
out=""
round="1"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    --round-num) round="$2"; shift 2 ;;
    *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
  esac
done
mkdir -p "$out"
: > "$out/findings.md"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
case "${TEST_CORE_STATUS:-fix-required}" in
  fix-required)
    cat > "$out/accepted-findings.md" <<'EOF_FINDING'
### FINDING_1: Stub finding
- **Location**: src/main.py
- **Concern**: Stub concern.
- **Suggested revision**: Stub fix.
EOF_FINDING
    cat > "$out/oos-accepted-review.md" <<'EOF_OOS'
### OOS_1: Stub follow-up
Description: deferred work
EOF_OOS
    printf 'REVIEW_CORE_STATUS=fix-required\nROUND_NUM=%s\nACCEPTED_COUNT=1\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    ;;
  wholesale-rejected)
    printf 'REVIEW_CORE_STATUS=wholesale-rejected\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=1\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=hard\n' "$round" "$out" "$out"
    ;;
  *)
    printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
    ;;
esac
EOF_CORE
chmod +x "$TMP/review-core-stub.sh"

make_work_repo() {
    local dir="$1"
    mkdir -p "$dir/src"
    git -C "$dir" init -q
    printf 'original\n' > "$dir/src/main.py"
    git -C "$dir" add src/main.py
    git -C "$dir" -c user.email=test@example.com -c user.name='Test User' commit -qm init
}

run_review_and_fix() {
    local work="$1"; shift
    (
        cd "$work"
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh" \
        REVIEW_AND_FIX_RUN_EXTERNAL_AGENT_SH="$TMP/run-external-agent-stub.sh" \
        REVIEW_AND_FIX_LAUNCH_CLAUDE_SUBPROCESS_SH="$TMP/launch-claude-subprocess-stub.sh" \
        "$SCRIPT" "$@"
    )
}

work_findings="$TMP/findings-mode"
make_work_repo "$work_findings"
empty="$work_findings/empty.md"
: > "$empty"
out=$(run_review_and_fix "$work_findings" --findings-file "$empty" --review-tmpdir "$work_findings/review")
grep -Fq 'REVIEW_AND_FIX_STATUS=no-findings' <<< "$out" || fail "findings no-findings status"
grep -Fq 'CODER_STATUS=skipped' <<< "$out" || fail "findings no-findings coder skipped"

cat > "$work_findings/findings.md" <<'EOF'
### FINDING_1: First
- **Location**: src/main.py
- **Concern**: First concern.
- **Suggested revision**: First fix.
EOF
out=$(TEST_AGENT_BEHAVIOR=codex-success run_review_and_fix "$work_findings" --findings-file "$work_findings/findings.md" --review-tmpdir "$work_findings/review2")
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "findings complete status"
grep -Fq 'CODER_TOOL=codex' <<< "$out" || fail "findings codex tool"
grep -Fq 'CODER_STATUS=applied' <<< "$out" || fail "findings coder applied"

run_orchestrator_case() {
    local label="$1" behavior="$2" expected_tool="$3"
    local work="$TMP/$label" implement_tmp out rc
    make_work_repo "$work"
    implement_tmp="$work/implement"
    mkdir -p "$implement_tmp"
    printf 'CODEX_HEALTHY=true\nCURSOR_HEALTHY=true\n' > "$implement_tmp/session-env.sh"
    set +e
    out=$(TEST_AGENT_BEHAVIOR="$behavior" run_review_and_fix "$work" \
        --implement-tmpdir "$implement_tmp" --mode diff --panel simple --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
    rc=$?
    set -e
    [[ "$rc" -eq 3 ]] || { echo "$out" >&2; fail "$label expected exit 3 got $rc"; }
    grep -Fq 'REVIEW_AND_FIX_STATUS=fix-required' <<< "$out" || fail "$label status"
    grep -Fq "CODER_TOOL=$expected_tool" <<< "$out" || fail "$label tool"
    grep -Fq 'CODER_STATUS=applied' <<< "$out" || fail "$label applied"
    [[ -f "$implement_tmp/round-1/coder-output.log" ]] || fail "$label coder output"
    jq -e '.schema_version == 2 and .status == "fix-required" and .accepted_count == 1 and .coder_tool == "'"$expected_tool"'" and .coder_status == "applied" and .submodule_scrub_count == 0 and .submodule_revert_count == 0' "$implement_tmp/review-and-fix-summary.json" >/dev/null \
        || fail "$label summary schema"
    [[ -s "$implement_tmp/accumulated-oos.jsonl" ]] || fail "$label oos jsonl"
    [[ -s "$implement_tmp/oos-accepted-review.md" ]] || fail "$label oos markdown"
}

run_orchestrator_case codex-case codex-success codex
run_orchestrator_case cursor-case cursor-success cursor
run_orchestrator_case claude-case claude-success claude-subagent

work_fail="$TMP/all-fail"
make_work_repo "$work_fail"
implement_tmp="$work_fail/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_HEALTHY=true\nCURSOR_HEALTHY=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=all-fail run_review_and_fix "$work_fail" \
    --implement-tmpdir "$implement_tmp" --mode diff --panel simple --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "all-fail expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=coder-failed' <<< "$out" || fail "all-fail status"
grep -Fq 'CODER_TOOL=none' <<< "$out" || fail "all-fail tool"
grep -Fq 'CODER_STATUS=failed' <<< "$out" || fail "all-fail coder status"

work_sub="$TMP/submodule-violation"
make_work_repo "$work_sub"
mkdir -p "$work_sub/vendor/lib"
cat > "$work_sub/.gitmodules" <<'EOF'
[submodule "vendor/lib"]
	path = vendor/lib
EOF
printf 'original submodule content\n' > "$work_sub/vendor/lib/file.txt"
git -C "$work_sub" add .gitmodules vendor/lib/file.txt
git -C "$work_sub" -c user.email=test@example.com -c user.name='Test User' commit -qm submodule-fixture
implement_tmp="$work_sub/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_HEALTHY=true\nCURSOR_HEALTHY=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_AGENT_BEHAVIOR=submodule-violation run_review_and_fix "$work_sub" \
    --implement-tmpdir "$implement_tmp" --mode diff --panel simple --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "submodule violation expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=coder-failed' <<< "$out" || fail "submodule violation status"
grep -Fq 'CODER_STATUS=submodule-violation' <<< "$out" || fail "submodule violation coder status"
grep -Fq 'SUBMODULE_REVERT_COUNT=1' <<< "$out" || fail "submodule violation revert count"
grep -Fq 'original submodule content' "$work_sub/vendor/lib/file.txt" || fail "submodule path was not reverted"

work_zero="$TMP/zero"
make_work_repo "$work_zero"
implement_tmp="$work_zero/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_HEALTHY=true\nCURSOR_HEALTHY=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=zero run_review_and_fix "$work_zero" \
    --implement-tmpdir "$implement_tmp" --mode diff --panel simple --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "$out" >&2; fail "zero expected exit 0 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out" || fail "zero status"
jq -e '.schema_version == 2 and .status == "complete" and .coder_status == "skipped"' "$implement_tmp/review-and-fix-summary.json" >/dev/null \
    || fail "zero summary"

work_wholesale="$TMP/wholesale"
make_work_repo "$work_wholesale"
implement_tmp="$work_wholesale/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_HEALTHY=true\nCURSOR_HEALTHY=true\n' > "$implement_tmp/session-env.sh"
set +e
out=$(TEST_CORE_STATUS=wholesale-rejected run_review_and_fix "$work_wholesale" \
    --implement-tmpdir "$implement_tmp" --mode diff --panel hard --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "$out" >&2; fail "wholesale expected exit 2 got $rc"; }
grep -Fq 'REVIEW_AND_FIX_STATUS=wholesale-rejected' <<< "$out" || fail "wholesale status"

echo "test-review-and-fix: ok"
