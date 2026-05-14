#!/usr/bin/env bash
# test-compose-review-findings.sh — markdown composer harness.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
COMPOSE="$SCRIPT_DIR/compose-review-findings.sh"

[ -x "$COMPOSE" ] || { echo "FAIL: $COMPOSE not executable" >&2; exit 1; }
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-compose-review-findings.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

echo "=== empty inputs ==="
mkdir -p "$TMP/a-design" "$TMP/a-impl"
out="$TMP/a.md"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/a-design" --implement-tmpdir "$TMP/a-impl" --issue 1 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=0"* ]] || fail "empty total missing: $stdout"
[[ "$stdout" == *"MODE=markdown"* ]] || fail "markdown mode missing: $stdout"
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
out="$TMP/b.md"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/b-design" --implement-tmpdir "$TMP/b-impl" --issue 7 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=3"* ]] || fail "total missing: $stdout"
section_count="$(grep -c '^###' "$out" || true)"
[ "$section_count" = "3" ] || fail "expected 3 sections, got $section_count"
grep -Fq '### FINDING_1: panel [plan-review/accepted]' "$out" \
    || fail "accepted finding section missing"
grep -Fq '### REJ_P1: Cursor-Architecture [plan-review/rejected]' "$out" \
    || fail "plan rejected section missing"
grep -Fq '### REJ_C1: Cursor-Security [code-review/rejected]' "$out" \
    || fail "code rejected section missing"
grep -q '<REDACTED-TOKEN>' "$out" || fail "token was not redacted"

echo "=== invalid issue fails ==="
set +e
bad="$("$COMPOSE" --issue nope --output "$TMP/bad.md" 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "invalid issue exit $rc"
[[ "$bad" == *"FAILED=true"* ]] || fail "invalid issue envelope missing"

echo "All assertions passed."
