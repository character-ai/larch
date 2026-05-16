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
grep -Fq -- '- **Concern**: - Missing validation in parser.' "$TMP/findings.md"

multiline="$TMP/multiline.txt"
cat > "$multiline" <<'EOF'
### In-Scope Findings
1. Parser misses a guard.
Continuation line keeps the same finding together.
EOF
printf '0\n' > "$multiline.done"
printf 'STATUS=clean\n' > "$multiline.dirty-tree"
out=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 "$SCRIPT" --claude-output-files "$multiline" --mode description --timeout 1 --findings-file "$TMP/findings-multiline.md" --oos-file "$TMP/oos-multiline.md")
assert_stdout_cap "$out"
grep -Fq 'FINDINGS_COUNT=1' <<< "$out"
grep -Fq '### FINDING_1: Parser misses a guard.' "$TMP/findings-multiline.md"
grep -Fq -- '- **Concern**: 1. Parser misses a guard. Continuation line keeps the same finding together.' "$TMP/findings-multiline.md"
if grep -Fq '### FINDING_2:' "$TMP/findings-multiline.md"; then
    echo "FAIL: multiline finding was split" >&2
    exit 1
fi

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

echo "All assertions passed."
