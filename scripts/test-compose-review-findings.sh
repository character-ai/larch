#!/usr/bin/env bash
# test-compose-review-findings.sh — NDJSON composer harness.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSE="$SCRIPT_DIR/compose-review-findings.sh"

[ -x "$COMPOSE" ] || { echo "FAIL: $COMPOSE not executable" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "FAIL: jq not found" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-compose-review-findings.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

echo "=== empty inputs ==="
mkdir -p "$TMP/a-design" "$TMP/a-impl"
out="$TMP/a.ndjson"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/a-design" --implement-tmpdir "$TMP/a-impl" --issue 1 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=0"* ]] || fail "empty total missing: $stdout"
[ -f "$out" ] || fail "empty output missing"
[ ! -s "$out" ] || fail "empty output should be zero bytes"

echo "=== accepted and rejected findings ==="
mkdir -p "$TMP/b-design" "$TMP/b-impl"
cat > "$TMP/b-design/accepted-plan-findings.md" <<'EOF'
### FINDING_1: Architecture boundary
- **Concern**: scripts/foo.sh:42 does too much.
- **Resolution**: Split the helper.
EOF
cat > "$TMP/b-design/rejected-findings.md" <<'EOF'
### [Plan Review] Cursor-Architecture
**Finding**: Plan issue.
**Reason not implemented**: Out of scope.
EOF
cat > "$TMP/b-impl/rejected-findings.md" <<'EOF'
### [Code Review] Cursor-Security
**Finding**: token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD appears.
**Reason not implemented**: fixture.
EOF
out="$TMP/b.ndjson"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/b-design" --implement-tmpdir "$TMP/b-impl" --issue 7 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=3"* ]] || fail "total missing: $stdout"
line_count="$(wc -l < "$out" | tr -d ' ')"
[ "$line_count" = "3" ] || fail "expected 3 lines, got $line_count"
jq -e 'select(.id == "FINDING_1" and .phase == "plan-review" and .outcome == "accepted" and .issue_number == 7)' "$out" >/dev/null \
    || fail "accepted finding record missing"
jq -e 'select(.id == "REJ_P1" and .category == "architecture")' "$out" >/dev/null \
    || fail "plan rejected record missing"
jq -e 'select(.id == "REJ_C1" and .category == "security")' "$out" >/dev/null \
    || fail "code rejected record missing"
grep -q '<REDACTED-TOKEN>' "$out" || fail "token was not redacted"

echo "=== invalid issue fails ==="
set +e
bad="$("$COMPOSE" --issue nope --output "$TMP/bad.ndjson" 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "invalid issue exit $rc"
[[ "$bad" == *"FAILED=true"* ]] || fail "invalid issue envelope missing"

echo "All assertions passed."
