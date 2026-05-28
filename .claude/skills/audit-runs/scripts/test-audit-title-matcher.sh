#!/usr/bin/env bash
# test-audit-title-matcher.sh — Hermetic coverage for match_audit_report_title.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=.claude/skills/audit-runs/scripts/audit-title-matcher.sh
. "$SCRIPT_DIR/audit-title-matcher.sh"

PASS=0
FAIL=0

assert_match() {
    local skill="$1" title="$2" expect="$3" label="$4"
    if match_audit_report_title --skill "$skill" --title "$title"; then
        got=0
    else
        got=1
    fi
    if [ "$got" -eq "$expect" ]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: $label (expected match=$expect got=$got)" >&2
    fi
}

echo "=== test-audit-title-matcher ==="

assert_match implement "[Run Logs Audit 2026-01-01 Report] tail" 0 "legacy implement title + implement skill"
assert_match implement "[Implement Run Logs Audit 2026-01-01 Report] tail" 0 "new implement title + implement skill"
assert_match implement "[Design Run Logs Audit 2026-01-01 Report] tail" 1 "design title + implement skill"
assert_match design "[Design Run Logs Audit 2026-01-01 Report] tail" 0 "design title + design skill"
assert_match design "[Run Logs Audit 2026-01-01 Report] tail" 1 "legacy implement title + design skill"
assert_match design "[Implement Run Logs Audit 2026-01-01 Report] tail" 1 "new implement title + design skill"

echo "test-audit-title-matcher: $PASS passed, $FAIL failed."
[ "$FAIL" -eq 0 ]
