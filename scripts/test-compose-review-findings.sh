#!/usr/bin/env bash
# test-compose-review-findings.sh — JSONL composer harness.

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

# jq helpers — count records matching a phase/outcome and emit a single field.
count_records() {
    # $1: file, $2: phase, $3: outcome
    jq -c --arg phase "$2" --arg outcome "$3" \
        'select(.phase == $phase and .outcome == $outcome)' "$1" \
        | wc -l | tr -d ' '
}
record_field_by_id() {
    # $1: file, $2: id, $3: field name → prints the field value or empty.
    jq -r --arg id "$2" --arg field "$3" \
        'select(.id == $id) | .[$field] // empty' "$1"
}

echo "=== empty inputs ==="
mkdir -p "$TMP/a-design" "$TMP/a-impl"
out="$TMP/a.jsonl"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/a-design" --implement-tmpdir "$TMP/a-impl" --issue 1 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=0"* ]] || fail "empty total missing: $stdout"
[[ "$stdout" == *"MODE=jsonl"* ]] || fail "jsonl mode missing: $stdout"
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

Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

EOF
cat > "$TMP/b-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_2: Runtime bug
- **Reviewer**: Codex-Structure
- **Concern**: scripts/bar.sh exits incorrectly.
- **Suggested revision**: Return the captured status.
EOF
cp "$TMP/b-impl/rejected-findings.md" "$TMP/b-impl/round-1/rejected-findings.md"
cp "$TMP/b-impl/rejected-findings-full.md" "$TMP/b-impl/round-1/rejected-findings-full.md"
out="$TMP/b.jsonl"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/b-design" --implement-tmpdir "$TMP/b-impl" --issue 7 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=4"* ]] || fail "total missing: $stdout"
[[ "$(wc -l <"$out" | tr -d ' ')" == "4" ]] || fail "expected 4 JSONL records, got $(wc -l <"$out")"

# Each JSONL record must parse and have the expected fields.
while IFS= read -r line; do
    printf '%s' "$line" | jq -e 'has("id") and has("issue_number") and has("phase") and has("outcome") and has("reviewer") and has("round_num") and has("category") and has("prose_body")' >/dev/null \
        || fail "missing required keys in record: $line"
done < "$out"

# Plan-review accepted finding
[[ "$(record_field_by_id "$out" FINDING_1 phase)" == "plan-review" ]] || fail "FINDING_1 phase"
[[ "$(record_field_by_id "$out" FINDING_1 outcome)" == "accepted" ]] || fail "FINDING_1 outcome"
[[ "$(record_field_by_id "$out" FINDING_1 reviewer)" == "panel" ]] || fail "FINDING_1 reviewer"
[[ "$(record_field_by_id "$out" FINDING_1 round_num)" == "" ]] || fail "FINDING_1 round_num"

# Code-review accepted finding
[[ "$(record_field_by_id "$out" FINDING_2 phase)" == "code-review" ]] || fail "FINDING_2 phase"
[[ "$(record_field_by_id "$out" FINDING_2 outcome)" == "accepted" ]] || fail "FINDING_2 outcome"
[[ "$(record_field_by_id "$out" FINDING_2 reviewer)" == "Codex-Structure" ]] || fail "FINDING_2 reviewer"
[[ "$(record_field_by_id "$out" FINDING_2 round_num)" == "1" ]] || fail "FINDING_2 round_num"

# Plan-review rejected finding
[[ "$(record_field_by_id "$out" REJ_P1 phase)" == "plan-review" ]] || fail "REJ_P1 phase"
[[ "$(record_field_by_id "$out" REJ_P1 outcome)" == "rejected" ]] || fail "REJ_P1 outcome"
[[ "$(record_field_by_id "$out" REJ_P1 reviewer)" == "Cursor-Architecture" ]] || fail "REJ_P1 reviewer"
[[ "$(record_field_by_id "$out" REJ_P1 round_num)" == "" ]] || fail "REJ_P1 round_num"

# Code-review rejected finding
[[ "$(record_field_by_id "$out" REJ_C1 phase)" == "code-review" ]] || fail "REJ_C1 phase"
[[ "$(record_field_by_id "$out" REJ_C1 outcome)" == "rejected" ]] || fail "REJ_C1 outcome"
[[ "$(record_field_by_id "$out" REJ_C1 reviewer)" == "Cursor-Security" ]] || fail "REJ_C1 reviewer"
[[ "$(record_field_by_id "$out" REJ_C1 round_num)" == "1" ]] || fail "REJ_C1 round_num"

# Token-shaped secret is redacted in the prose_body
body_with_token=$(record_field_by_id "$out" REJ_C1 prose_body)
grep -qF '<REDACTED-TOKEN>' <<<"$body_with_token" || fail "token was not redacted in JSONL prose_body"
grep -qF 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' <<<"$body_with_token" \
    && fail "raw token leaked into JSONL prose_body"
grep -qF 'Suggested revision' <<<"$body_with_token" || fail "rejected body lost 'Suggested revision'"

# JSONL preserves literal '<', '>', and '&' (no HTML escaping).
grep -qF '<config> & test' <<<"$body_with_token" \
    || fail "JSONL prose_body should preserve literal angle brackets and ampersand"

echo "=== legacy code review rejected header is accepted ==="
mkdir -p "$TMP/e-impl"
cat > "$TMP/e-impl/rejected-findings-full.md" <<'EOF'
### [Code Review] Legacy-Reviewer
**Finding**: Legacy rejected body.
**Reason not implemented**: Kept for compatibility.
EOF
out="$TMP/e.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/e-impl" --issue 44 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "legacy rejected total: $stdout"
[[ "$(record_field_by_id "$out" REJ_C1 reviewer)" == "Legacy-Reviewer" ]] || fail "legacy reviewer"
[[ "$(record_field_by_id "$out" REJ_C1 outcome)" == "rejected" ]] || fail "legacy outcome"
[[ "$(record_field_by_id "$out" REJ_C1 round_num)" == "" ]] || fail "legacy round_num"
grep -qF 'Legacy rejected body.' <<<"$(record_field_by_id "$out" REJ_C1 prose_body)" \
    || fail "legacy rejected body missing from prose_body"

echo "=== preserve inner headings inside rejected code-review blocks ==="
mkdir -p "$TMP/f-impl"
cat > "$TMP/f-impl/rejected-findings-full.md" <<'EOF'
### [rejected] Reviewer-With-Notes
**Finding**: Primary rejected body.

### Notes
This heading should remain inside the same rejected block.
EOF
out="$TMP/f.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/f-impl" --issue 45 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "inner-heading total: $stdout"
[[ "$(wc -l <"$out" | tr -d ' ')" == "1" ]] || fail "expected 1 JSONL record"
body=$(record_field_by_id "$out" REJ_C1 prose_body)
grep -qF '### Notes' <<<"$body" || fail "inner heading missing from prose_body"
grep -qF 'This heading should remain inside the same rejected block.' <<<"$body" \
    || fail "inner heading body missing"

echo "=== multi-round findings include round numbers ==="
mkdir -p "$TMP/h-impl/round-1" "$TMP/h-impl/round-2"
cat > "$TMP/h-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_10: First round issue
- **Reviewer**: round-one-reviewer.txt
- **Concern**: First round concern.
EOF
cat > "$TMP/h-impl/round-2/accepted-findings.md" <<'EOF'
### FINDING_11: Second round issue
- **Reviewer**: round-two-reviewer.txt
- **Concern**: Second round concern.
EOF
out="$TMP/h.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/h-impl" --issue 47 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=2"* ]] || fail "multi-round total: $stdout"
[[ "$(record_field_by_id "$out" FINDING_10 round_num)" == "1" ]] || fail "FINDING_10 round_num"
[[ "$(record_field_by_id "$out" FINDING_11 round_num)" == "2" ]] || fail "FINDING_11 round_num"

echo "=== OOS review findings are captured ==="
mkdir -p "$TMP/i-impl/round-1"
cat > "$TMP/i-impl/round-1/oos.md" <<'EOF'
### OOS_1: Follow-up docs drift
- **Reviewer**: cursor-docs-output.txt
- **Concern**: docs/example.md has a stale example.

### OOS_2: Follow-up test naming
- **Reviewer**: codex-testing-output.txt
- **Concern**: tests should use clearer fixture names.

### OOS_3: Follow-up cleanup
- **Reviewer**: cursor-cleanup-output.txt
- **Concern**: an unrelated cleanup could be done later.
EOF
out="$TMP/i.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/i-impl" --issue 48 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=3"* ]] || fail "OOS total: $stdout"
for id in OOS_C1 OOS_C2 OOS_C3; do
    [[ "$(record_field_by_id "$out" "$id" phase)" == "code-review" ]] || fail "$id phase"
    [[ "$(record_field_by_id "$out" "$id" outcome)" == "out_of_scope" ]] || fail "$id outcome"
    [[ "$(record_field_by_id "$out" "$id" round_num)" == "1" ]] || fail "$id round_num"
done
[[ "$(record_field_by_id "$out" OOS_C2 reviewer)" == "codex-testing-output.txt" ]] || fail "OOS_C2 reviewer"

echo "=== rejected [rejected] headers use body reviewer attribution ==="
mkdir -p "$TMP/j-impl"
cat > "$TMP/j-impl/rejected-findings-full.md" <<'EOF'
### [rejected] FINDING_18

### FINDING_18: Review finding title
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: rejected body concern.
EOF
out="$TMP/j.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/j-impl" --issue 49 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "body reviewer rejected total: $stdout"
[[ "$(record_field_by_id "$out" REJ_C1 reviewer)" == "cursor-specialist-testing-output.txt" ]] \
    || fail "body reviewer rejected attribution"

echo "=== JSONL preserves XML-like tags literally (no HTML escaping) ==="
mkdir -p "$TMP/c-impl/round-1"
cat > "$TMP/c-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_3: Prompt injection guard
- **Concern**: The </reviewer_diff> tag, <scout_notes> element, and A & B marker are unescaped.
- **Suggested revision**: HTML-escape all <…> sequences.
EOF
out="$TMP/c.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/c-impl" --issue 42 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "xml literal total: $stdout"
body=$(record_field_by_id "$out" FINDING_3 prose_body)
grep -qF '</reviewer_diff>' <<<"$body" || fail "literal </reviewer_diff> missing"
grep -qF '<scout_notes>' <<<"$body" || fail "literal <scout_notes> missing"
grep -qF 'A & B' <<<"$body" || fail "literal ampersand missing"

echo "=== category is extracted from the leading '## <cat>:' line when present ==="
mkdir -p "$TMP/g-impl/round-1"
cat > "$TMP/g-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_5: correctness: scripts/foo.sh:1-3

- **Concern**: example
EOF
out="$TMP/g.jsonl"
"$COMPOSE" --implement-tmpdir "$TMP/g-impl" --issue 46 --output "$out" >/dev/null
[[ "$(record_field_by_id "$out" FINDING_5 category)" == "correctness" ]] \
    || fail "category extraction from '## <cat>: ...' failed"

echo "=== invalid issue fails ==="
set +e
bad="$("$COMPOSE" --issue nope --output "$TMP/bad.jsonl" 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "invalid issue exit $rc"
[[ "$bad" == *"FAILED=true"* ]] || fail "invalid issue envelope missing"

echo "All assertions passed."
