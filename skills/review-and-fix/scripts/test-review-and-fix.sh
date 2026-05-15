#!/usr/bin/env bash
# Regression harness for review-and-fix.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-review-and-fix.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

empty="$TMP/empty.md"
: > "$empty"
out=$("$SCRIPT" --findings-file "$empty" --review-tmpdir "$TMP/empty-run")
grep -Fq 'REVIEW_AND_FIX_STATUS=no-findings' <<< "$out"
grep -Fq 'FIX_COUNT=0' <<< "$out"

fixture="$TMP/findings.md"
cat > "$fixture" <<'EOF'
### FINDING_1: First
- **Location**: skills/review/SKILL.md
- **Concern**: First concern.
- **Suggested revision**: First fix.

### FINDING_2: Second
- **Location**: skills/review/scripts/dispatch-panel.sh
- **Concern**: Second concern.
- **Suggested revision**: Second fix.
EOF

out=$("$SCRIPT" --findings-file "$fixture" --review-tmpdir "$TMP/run")
grep -Fq 'FINDING_ID=FINDING_1' <<< "$out"
grep -Fq 'FINDING_ID=FINDING_2' <<< "$out"
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out"
grep -Fq 'FIX_COUNT=2' <<< "$out"
[[ -f "$TMP/run/FINDING_1.fixer.env" ]]
[[ -f "$TMP/run/FINDING_2.fixer.env" ]]
grep -Fq 'PATH_VALID=true' "$TMP/run/FINDING_1.fixer.env"

cat > "$TMP/review-core-stub.sh" <<'EOF_STUB'
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
- **Location**: skills/review/SKILL.md
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
EOF_STUB
chmod +x "$TMP/review-core-stub.sh"

implement_tmp="$TMP/implement"
mkdir -p "$implement_tmp"
printf 'CODEX_HEALTHY=true\nCURSOR_HEALTHY=true\n' > "$implement_tmp/session-env.sh"

set +e
out=$(REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --panel simple --round-num 1 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 3 ]] || { echo "expected orchestrator fix-required exit 3, got $rc" >&2; echo "$out" >&2; exit 1; }
grep -Fq 'REVIEW_AND_FIX_STATUS=fix-required' <<< "$out"
grep -Fq 'APPROVED_FIXES_FILE=' <<< "$out"
[[ -f "$implement_tmp/round-1/FINDING_1.fixer.env" ]]
[[ -f "$implement_tmp/review-and-fix-summary.json" ]]
jq -e '.schema_version == 1 and .status == "fix-required" and .accepted_count == 1 and .rounds_completed == 1' "$implement_tmp/review-and-fix-summary.json" >/dev/null
[[ -s "$implement_tmp/accumulated-oos.jsonl" ]]
[[ -s "$implement_tmp/oos-accepted-review.md" ]]

set +e
out=$(TEST_CORE_STATUS=zero REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --panel simple --round-num 2 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 0 ]] || { echo "expected orchestrator complete exit 0, got $rc" >&2; echo "$out" >&2; exit 1; }
grep -Fq 'REVIEW_AND_FIX_STATUS=complete' <<< "$out"
jq -e '.schema_version == 1 and .status == "complete" and .accepted_count == 1 and .rounds_completed == 2' "$implement_tmp/review-and-fix-summary.json" >/dev/null

set +e
out=$(TEST_CORE_STATUS=wholesale-rejected REVIEW_AND_FIX_REVIEW_CORE_SH="$TMP/review-core-stub.sh" \
    "$SCRIPT" --implement-tmpdir "$implement_tmp" --mode diff --panel hard --round-num 3 --session-env-path "$implement_tmp/session-env.sh")
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "expected orchestrator wholesale exit 2, got $rc" >&2; echo "$out" >&2; exit 1; }
grep -Fq 'REVIEW_AND_FIX_STATUS=wholesale-rejected' <<< "$out"

echo "All assertions passed."
