#!/usr/bin/env bash
# Regression harness for collect-findings.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/collect-findings.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-collect-findings.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMP/execution-issues.md"

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

outf="$TMP/claude.txt"
cat > "$outf" <<'EOF'
### In-Scope Findings
- Missing validation in parser.

### Out-of-Scope Observations
- Cleanup old tests.
EOF
printf '0\n' > "$outf.done"
printf 'STATUS=clean\n' > "$outf.dirty-tree"

out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$outf" --mode description --timeout 1 --findings-file "$TMP/findings.md" --oos-file "$TMP/oos.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=2' <<< "$out"
grep -Fq 'OOS_COUNT=1' <<< "$out"
grep -Fq 'DIRTY_DETECTED=false' <<< "$out"
grep -Fq 'COLLECTOR_OUTPUT_FILE=' <<< "$out"
grep -Fq '### FINDING_1:' "$TMP/findings.md"

printf 'NO_ISSUES_FOUND\n' > "$TMP/no.txt"
printf '0\n' > "$TMP/no.txt.done"
printf 'STATUS=clean\n' > "$TMP/no.txt.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$TMP/no.txt" --mode diff --timeout 1 --findings-file "$TMP/findings2.md" --oos-file "$TMP/oos2.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=0' <<< "$out"

# JSON no-findings sentinel (canonical form per #2156) — when jq is present.
if command -v jq >/dev/null 2>&1; then
    printf '{"no_issues_found": true}\n' > "$TMP/json-sentinel.txt"
    printf '0\n' > "$TMP/json-sentinel.txt.done"
    printf 'STATUS=clean\n' > "$TMP/json-sentinel.txt.dirty-tree"
    out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$TMP/json-sentinel.txt" --mode diff --timeout 1 --findings-file "$TMP/findings-json.md" --oos-file "$TMP/oos-json.md")
    assert_stdout_cap "$out"
    grep -Fq 'FINDINGS_COUNT=0' <<< "$out"
fi

# Timeout degradation: a Claude slot with no .done file is logged as a failure but COLLECT_OK=true.
# wait-for-reviewers.sh exits 0 with TIMEOUT on stdout; collect-findings.sh must not abort.
timeout_out="$TMP/timeout-reviewer.txt"
# Do NOT create ${timeout_out}.done — the sentinel is absent, so wait-for-reviewers.sh will TIMEOUT.
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" \
    --claude-output-files "$timeout_out" --mode diff --timeout 1 \
    --findings-file "$TMP/findings-timeout.md" --oos-file "$TMP/oos-timeout.md")
assert_stdout_cap "$out"
grep -Fq 'COLLECT_OK=true' <<< "$out" || { echo "FAIL: COLLECT_OK not true when Claude slot timed out" >&2; exit 1; }
grep -Fq 'FINDINGS_COUNT=0' <<< "$out" || { echo "FAIL: FINDINGS_COUNT not 0 for timed-out slot" >&2; exit 1; }
grep -Fq 'slot-timeout' "$LARCH_EXECUTION_ISSUES_LOG" 2>/dev/null || { echo "FAIL: timed-out slot not logged to execution issues" >&2; exit 1; }

echo "All assertions passed."
