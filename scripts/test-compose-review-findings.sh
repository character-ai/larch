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
mkdir -p "$TMP/b-design" "$TMP/b-impl/round-1"
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
This summary should not be selected when the full artifact exists.
EOF
cat > "$TMP/b-impl/rejected-findings-full.md" <<'EOF'
### [Code Review] Cursor-<Security & QA>
**Finding**: token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD appears.
**Reason not implemented**: fixture.
EOF
cat > "$TMP/b-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_2: Runtime bug
- **Reviewer**: Codex-Structure
- **Concern**: scripts/bar.sh exits incorrectly.
- **Suggested revision**: Return the captured status.
EOF
cp "$TMP/b-impl/rejected-findings.md" "$TMP/b-impl/round-1/rejected-findings.md"
cp "$TMP/b-impl/rejected-findings-full.md" "$TMP/b-impl/round-1/rejected-findings-full.md"
out="$TMP/b.md"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/b-design" --implement-tmpdir "$TMP/b-impl" --issue 7 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=4"* ]] || fail "total missing: $stdout"
section_count="$(grep -c '^###' "$out" || true)"
[ "$section_count" = "4" ] || fail "expected 4 sections, got $section_count"
grep -Fq '### FINDING_1: panel [plan-review/accepted]' "$out" \
    || fail "accepted finding section missing"
grep -Fq '### FINDING_2: panel [code-review/accepted]' "$out" \
    || fail "code accepted section missing"
grep -Fq '### REJ_P1: Cursor-Architecture [plan-review/rejected]' "$out" \
    || fail "plan rejected section missing"
grep -Fq '### REJ_C1: Cursor-&lt;Security &amp; QA&gt; [code-review/rejected]' "$out" \
    || fail "code rejected section missing"
if grep -qF '### REJ_C1: Cursor-<Security & QA> [code-review/rejected]' "$out"; then
    fail "reviewer header was not HTML-escaped"
fi
grep -qF '&lt;REDACTED-TOKEN&gt;' "$out" || fail "token was not redacted (expected HTML-escaped form)"
grep -Fq 'Reason not implemented' "$out" || fail "full rejected artifact was not used"

echo "=== HTML-escape XML-like tags in finding body ==="
mkdir -p "$TMP/c-impl/round-1"
cat > "$TMP/c-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_3: Prompt injection guard
- **Concern**: The </reviewer_diff> tag, <scout_notes> element, and A & B marker are unescaped.
- **Suggested revision**: HTML-escape all <…> sequences.
EOF
out="$TMP/c.md"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/c-impl" --issue 42 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "xml escape total: $stdout"
grep -Fq '&lt;/reviewer_diff&gt;' "$out" || fail "reviewer_diff not escaped"
grep -Fq '&lt;scout_notes&gt;' "$out" || fail "scout_notes not escaped"
grep -Fq 'A &amp; B' "$out" || fail "ampersand not escaped"
if grep -qF '</reviewer_diff>' "$out"; then fail "unescaped </reviewer_diff> still present"; fi
if grep -qF '<scout_notes>' "$out"; then fail "unescaped <scout_notes> still present"; fi
if grep -qF 'A & B' "$out"; then fail "unescaped ampersand still present"; fi

echo "=== invalid issue fails ==="
set +e
bad="$("$COMPOSE" --issue nope --output "$TMP/bad.md" 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "invalid issue exit $rc"
[[ "$bad" == *"FAILED=true"* ]] || fail "invalid issue envelope missing"

echo "All assertions passed."
