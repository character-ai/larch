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
# Rejected Findings

10:FINDING_1_OUTCOME=rejected
EOF
cat > "$TMP/b-impl/rejected-findings-full.md" <<'EOF'
### [rejected] FINDING_1

### FINDING_1: Security token leak in <config> & test
- **Reviewer**: Cursor-Security
- **Concern**: token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD appears.
- **Suggested revision**: Redact the token.

Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=0

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
# Count only structured finding headers (the emit_record format): ### ID: reviewer [phase/outcome]
structured_count="$(grep -cE '^### [^:]+: .+ \[(plan-review|code-review)/(accepted|rejected)\]' "$out" || true)"
[ "$structured_count" = "4" ] || fail "expected 4 structured sections, got $structured_count"
grep -Fq '### FINDING_1: panel [plan-review/accepted]' "$out" \
    || fail "accepted finding section missing"
grep -Fq '### FINDING_2: panel [code-review/accepted]' "$out" \
    || fail "code accepted section missing"
grep -Fq '### REJ_P1: Cursor-Architecture [plan-review/rejected]' "$out" \
    || fail "plan rejected section missing"
grep -Fq '### REJ_C1: FINDING_1 [code-review/rejected]' "$out" \
    || fail "code rejected section missing"
grep -qF '&lt;REDACTED-TOKEN&gt;' "$out" || fail "token was not redacted (expected HTML-escaped form)"
grep -Fq 'Suggested revision' "$out" || fail "full rejected artifact body was not used"
# Verify body HTML escaping: < and & in the body must be escaped
grep -qF '&lt;config&gt;' "$out" || fail "angle brackets in body were not HTML-escaped"
grep -qF '&amp; test' "$out" || fail "ampersand in body was not HTML-escaped"

echo "=== legacy code review rejected header is accepted ==="
mkdir -p "$TMP/e-impl"
cat > "$TMP/e-impl/rejected-findings-full.md" <<'EOF'
### [Code Review] Legacy-Reviewer
**Finding**: Legacy rejected body.
**Reason not implemented**: Kept for compatibility.
EOF
out="$TMP/e.md"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/e-impl" --issue 44 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "legacy rejected total: $stdout"
grep -Fq '### REJ_C1: Legacy-Reviewer [code-review/rejected]' "$out" \
    || fail "legacy code-review rejected header missing"
grep -Fq 'Legacy rejected body.' "$out" || fail "legacy rejected body missing"

echo "=== preserve inner headings inside rejected code-review blocks ==="
mkdir -p "$TMP/f-impl"
cat > "$TMP/f-impl/rejected-findings-full.md" <<'EOF'
### [rejected] Reviewer-With-Notes
**Finding**: Primary rejected body.

### Notes
This heading should remain inside the same rejected block.
EOF
out="$TMP/f.md"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/f-impl" --issue 45 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "inner-heading total: $stdout"
structured_count="$(grep -cE '^### [^:]+: .+ \[(plan-review|code-review)/(accepted|rejected)\]' "$out" || true)"
[ "$structured_count" = "1" ] || fail "expected 1 structured section with inner heading, got $structured_count"
grep -Fq '### Notes' "$out" || fail "inner heading missing from rejected body"
grep -Fq 'This heading should remain inside the same rejected block.' "$out" \
    || fail "inner heading body missing"

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

echo "=== preserve existing HTML entities while escaping raw tags ==="
mkdir -p "$TMP/d-impl/round-1"
cat > "$TMP/d-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_4: Preserve pre-escaped content
- **Concern**: Already escaped &lt;tag&gt; and &#35; entity should survive, but raw <other> & marker should still escape.
- **Suggested revision**: Preserve existing entities.
EOF
out="$TMP/d.md"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/d-impl" --issue 43 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "entity preservation total: $stdout"
grep -Fq 'Already escaped &lt;tag&gt; and &#35; entity should survive, but raw &lt;other&gt; &amp; marker should still escape.' "$out" \
    || fail "existing entities were not preserved while raw markup escaped"
if grep -qF '&amp;lt;tag&amp;gt;' "$out"; then fail "existing named entity was double-encoded"; fi
if grep -qF '&amp;#35;' "$out"; then fail "existing numeric entity was double-encoded"; fi

echo "=== invalid issue fails ==="
set +e
bad="$("$COMPOSE" --issue nope --output "$TMP/bad.md" 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "invalid issue exit $rc"
[[ "$bad" == *"FAILED=true"* ]] || fail "invalid issue envelope missing"

echo "All assertions passed."
