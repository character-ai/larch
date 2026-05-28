#!/usr/bin/env bash
# test-audit-title-matcher.sh — Hermetic coverage for title matcher helpers.
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

assert_design_pr() {
    local title="$1" expect_match="$2" expect_id="$3" label="$4"
    local got_match=1 got_id=""
    if match_design_run_log_pr_title "$title"; then
        got_match=0
    fi
    got_id=$(extract_design_run_log_pr_id "$title" 2>/dev/null || true)
    if [ "$got_match" -eq "$expect_match" ] && [ "$got_id" = "$expect_id" ]; then
        PASS=$((PASS + 1))
        echo "  ok: $label"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: $label (expected match=$expect_match id=$expect_id got match=$got_match id=$got_id)" >&2
    fi
}

echo "=== test-audit-title-matcher ==="

assert_match implement "[Run Logs Audit 2026-01-01 Report] tail" 0 "legacy implement title + implement skill"
assert_match implement "[Implement Run Logs Audit 2026-01-01 Report] tail" 0 "new implement title + implement skill"
assert_match implement "[Design Run Logs Audit 2026-01-01 Report] tail" 1 "design title + implement skill"
assert_match design "[Design Run Logs Audit 2026-01-01 Report] tail" 0 "design title + design skill"
assert_match design "[Run Logs Audit 2026-01-01 Report] tail" 1 "legacy implement title + design skill"
assert_match design "[Implement Run Logs Audit 2026-01-01 Report] tail" 1 "new implement title + design skill"
assert_design_pr "chore(larch-logs): design run 90628862-9A18-4A56-8420-63DE723F9D81" 0 "90628862-9A18-4A56-8420-63DE723F9D81" "uppercase design PR title matches and extracts"
assert_design_pr "chore(larch-logs): design run 90628862-9a18-4a56-8420-63de723f9d81" 1 "" "lowercase design PR title rejected"
assert_design_pr "chore(larch-logs): flush design run 90628862-9A18-4A56-8420-63DE723F9D81" 1 "" "flush title rejected"

echo "test-audit-title-matcher: $PASS passed, $FAIL failed."
[ "$FAIL" -eq 0 ]
