#!/usr/bin/env bash
# Structural regression test for /review Step 3e relevant-checks helper use.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SKILL_MD="$REPO_ROOT/skills/review/SKILL.md"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

helper_literal="run-relevant-checks-captured.sh\" --site review-step3e --tmpdir \"\$REVIEW_TMPDIR\""
count=$(grep -Fc "$helper_literal" "$SKILL_MD" || true)
[[ "$count" -eq 1 ]] || fail "expected exactly one review-step3e helper invocation, found $count"

line_no=$(grep -Fn "$helper_literal" "$SKILL_MD" | awk -F: 'NR==1{print $1}')
start=$((line_no - 8))
(( start < 1 )) && start=1
window=$(sed -n "${start},${line_no}p" "$SKILL_MD")

[[ "$window" == *'> **Continue after child returns.**'* ]] || fail "helper lacks nearby continuation callout"
[[ "$window" == *'RELEVANT_CHECKS_OK=true'* ]] || fail "callout lacks green-path token"
[[ "$window" == *'Step 3f'* ]] || fail "callout lacks immediate Step 3f continuation"
[[ "$window" == *'REDACTED_LOG_FILE'* ]] || fail "callout lacks redacted log guidance"
raw_log_needle="NOT raw \`LOG_FILE\`"
[[ "$window" == *"$raw_log_needle"* ]] || fail "callout does not forbid raw LOG_FILE"

if grep -qE "[Ii]nvoke \`?/relevant-checks\`?.*Skill tool|\`/relevant-checks\`" "$SKILL_MD"; then
    fail "legacy /relevant-checks Skill invocation prose remains in review skill"
fi

echo "test-review-relevant-checks-helper: ok"
