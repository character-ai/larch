#!/usr/bin/env bash
# test-compose-review-findings.sh — JSONL composer harness.
# Plan-review category fixtures (strict canonical ## tags, empty category) ship with
# the unified Step 5 / review-findings workstream; see release notes [29.8.64].

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
record_reviewer_slot0() {
    # $1: file, $2: id → first reviewer_slots entry (or empty).
    jq -r --arg id "$2" 'select(.id == $id) | .reviewer_slots[0] // empty' "$1"
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

## architecture: scripts/foo.sh

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
    printf '%s' "$line" | jq -e 'has("id") and has("issue_number") and has("phase") and has("outcome") and has("reviewer_slots") and has("schema_version") and has("round_num") and has("category") and has("prose_body")' >/dev/null \
        || fail "missing required keys in record: $line"
    [[ "$(printf '%s' "$line" | jq -r '.schema_version')" == "2" ]] || fail "schema_version must be 2: $line"
done < "$out"

# Plan-review accepted finding
[[ "$(record_field_by_id "$out" FINDING_1 phase)" == "plan-review" ]] || fail "FINDING_1 phase"
[[ "$(record_field_by_id "$out" FINDING_1 outcome)" == "accepted" ]] || fail "FINDING_1 outcome"
[[ "$(record_reviewer_slot0 "$out" FINDING_1)" == "panel" ]] || fail "FINDING_1 reviewer"
[[ "$(record_field_by_id "$out" FINDING_1 round_num)" == "" ]] || fail "FINDING_1 round_num"

# Code-review accepted finding
[[ "$(record_field_by_id "$out" FINDING_2 phase)" == "code-review" ]] || fail "FINDING_2 phase"
[[ "$(record_field_by_id "$out" FINDING_2 outcome)" == "accepted" ]] || fail "FINDING_2 outcome"
[[ "$(record_reviewer_slot0 "$out" FINDING_2)" == "Codex-Structure" ]] || fail "FINDING_2 reviewer"
[[ "$(record_field_by_id "$out" FINDING_2 round_num)" == "1" ]] || fail "FINDING_2 round_num"

# Plan-review accepted uses strict canonical '##' scanning (synthetic prose title skipped).
[[ "$(record_field_by_id "$out" FINDING_1 category)" == "architecture" ]] \
    || fail "FINDING_1 category: got $(record_field_by_id "$out" FINDING_1 category)"
# Code-review accepted still uses best-effort category from the synthetic '## <title>' line.
[[ "$(record_field_by_id "$out" FINDING_2 category)" == "Runtime bug" ]] \
    || fail "FINDING_2 category: got $(record_field_by_id "$out" FINDING_2 category)"

# Plan-review rejected finding
[[ "$(record_field_by_id "$out" REJ_P1 phase)" == "plan-review" ]] || fail "REJ_P1 phase"
[[ "$(record_field_by_id "$out" REJ_P1 outcome)" == "rejected" ]] || fail "REJ_P1 outcome"
[[ "$(record_reviewer_slot0 "$out" REJ_P1)" == "Cursor-Architecture" ]] || fail "REJ_P1 reviewer"
[[ "$(record_field_by_id "$out" REJ_P1 round_num)" == "" ]] || fail "REJ_P1 round_num"

# Code-review rejected finding
[[ "$(record_field_by_id "$out" REJ_CR1_1 phase)" == "code-review" ]] || fail "REJ_CR1_1 phase"
[[ "$(record_field_by_id "$out" REJ_CR1_1 outcome)" == "rejected" ]] || fail "REJ_CR1_1 outcome"
[[ "$(record_reviewer_slot0 "$out" REJ_CR1_1)" == "Cursor-Security" ]] || fail "REJ_CR1_1 reviewer"
[[ "$(record_field_by_id "$out" REJ_CR1_1 round_num)" == "1" ]] || fail "REJ_CR1_1 round_num"

# Token-shaped secret is redacted in the prose_body
body_with_token=$(record_field_by_id "$out" REJ_CR1_1 prose_body)
grep -qF '<REDACTED-TOKEN>' <<<"$body_with_token" || fail "token was not redacted in JSONL prose_body"
grep -qF 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD' <<<"$body_with_token" \
    && fail "raw token leaked into JSONL prose_body"
grep -qF 'Suggested revision' <<<"$body_with_token" || fail "rejected body lost 'Suggested revision'"

# JSONL preserves literal '<', '>', and '&' (no HTML escaping).
grep -qF '<config> & test' <<<"$body_with_token" \
    || fail "JSONL prose_body should preserve literal angle brackets and ampersand"

echo "=== plan-review accepted: empty category when only non-canonical ##; multi-skip before canonical ==="
mkdir -p "$TMP/pr-empty-cat-design" "$TMP/pr-empty-cat-impl"
cat > "$TMP/pr-empty-cat-design/accepted-plan-findings.md" <<'EOF'
### FINDING_EMPTY: Prose-only plan title

## notes: not a focus-area tag
## Discussion — unordered list style

- **Concern**: Strict scan should skip non-canonical ## lines and leave category empty.

### FINDING_MULTI: Another title

## junk heading one: still not canonical
## junk heading two: also not canonical
## architecture: scripts/plan.md

- **Concern**: Multiple junk ## lines then canonical tag should yield architecture.
EOF
out="$TMP/pr-empty-cat.jsonl"
stdout="$("$COMPOSE" --design-artifacts-dir "$TMP/pr-empty-cat-design" --implement-tmpdir "$TMP/pr-empty-cat-impl" --issue 2484 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=2"* ]] || fail "plan-review empty-category total: $stdout"
[[ -z "$(record_field_by_id "$out" FINDING_EMPTY category)" ]] \
    || fail "FINDING_EMPTY category must be empty, got $(record_field_by_id "$out" FINDING_EMPTY category)"
body_empty=$(record_field_by_id "$out" FINDING_EMPTY prose_body)
grep -qF '## notes:' <<<"$body_empty" || fail "FINDING_EMPTY prose_body should retain non-canonical ## lines"
grep -qF 'Strict scan should skip' <<<"$body_empty" || fail "FINDING_EMPTY prose_body lost concern bullet"
[[ "$(record_field_by_id "$out" FINDING_MULTI category)" == "architecture" ]] \
    || fail "FINDING_MULTI category: got $(record_field_by_id "$out" FINDING_MULTI category)"

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
[[ "$(record_reviewer_slot0 "$out" REJ_C1)" == "Legacy-Reviewer" ]] || fail "legacy reviewer"
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
### FINDING_1: [OUT_OF_SCOPE] Follow-up docs drift
- **Reviewer**: cursor-docs-output.txt
- **Concern**: docs/example.md has a stale example.

### FINDING_2: [OUT_OF_SCOPE] Follow-up test naming
- **Reviewers**: codex-testing-output.txt
- **Concern**: tests should use clearer fixture names.

### FINDING_3: [OUT_OF_SCOPE] Follow-up cleanup
Reviewer: cursor-cleanup-output.txt
- **Concern**: an unrelated cleanup could be done later.
EOF
out="$TMP/i.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/i-impl" --issue 48 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=3"* ]] || fail "OOS total: $stdout"
for id in OOS_CR1_1 OOS_CR1_2 OOS_CR1_3; do
    [[ "$(record_field_by_id "$out" "$id" phase)" == "code-review" ]] || fail "$id phase"
    [[ "$(record_field_by_id "$out" "$id" outcome)" == "out_of_scope" ]] || fail "$id outcome"
    [[ "$(record_field_by_id "$out" "$id" round_num)" == "1" ]] || fail "$id round_num"
done
[[ "$(record_reviewer_slot0 "$out" OOS_CR1_2)" == "codex-testing-output.txt" ]] || fail "OOS_CR1_2 reviewer"
[[ "$(record_reviewer_slot0 "$out" OOS_CR1_3)" == "cursor-cleanup-output.txt" ]] || fail "OOS_CR1_3 reviewer"

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
[[ "$(record_reviewer_slot0 "$out" REJ_C1)" == "cursor-specialist-testing-output.txt" ]] \
    || fail "body reviewer rejected attribution"
[[ -z "$(record_field_by_id "$out" REJ_C1 category)" ]] \
    || fail "title-only ### FINDING_ inner line must leave category empty, got $(record_field_by_id "$out" REJ_C1 category)"

echo "=== REJ_* category from ### FINDING_ triple-hash inner heading ==="
mkdir -p "$TMP/rej-cat-impl"
cat > "$TMP/rej-cat-impl/rejected-findings-full.md" <<'EOF'
### [rejected] FINDING_A

### FINDING_A: architecture: scripts/foo.sh:1-3
- **Reviewer**: rej-arch-reviewer.txt
- **Concern**: rejected architecture follow-up.

### [rejected] FINDING_B

### FINDING_B: security: token handling
- **Reviewer**: rej-sec-reviewer.txt
- **Concern**: rejected security follow-up.
EOF
out="$TMP/rej-cat.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/rej-cat-impl" --issue 2479 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=2"* ]] || fail "REJ triple-hash category total: $stdout"
[[ "$(record_field_by_id "$out" REJ_C1 category)" == "architecture" ]] \
    || fail "REJ_C1 category: got $(record_field_by_id "$out" REJ_C1 category)"
[[ "$(record_field_by_id "$out" REJ_C2 category)" == "security" ]] \
    || fail "REJ_C2 category: got $(record_field_by_id "$out" REJ_C2 category)"

echo "=== REJ_* category from ### FINDING_ canonical tag without location colon ==="
mkdir -p "$TMP/rej-cat-tagonly-impl"
cat > "$TMP/rej-cat-tagonly-impl/rejected-findings-full.md" <<'EOF'
### [rejected] FINDING_REG

### FINDING_REG: correctness
- **Reviewer**: rej-tagonly-reviewer.txt
- **Concern**: synthetic REJ body with tag-only triple-hash line (no trailing location colon).
EOF
out="$TMP/rej-cat-tagonly.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/rej-cat-tagonly-impl" --issue 2480 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "REJ tag-only triple-hash category total: $stdout"
[[ "$(record_field_by_id "$out" REJ_C1 category)" == "correctness" ]] \
    || fail "REJ_C1 tag-only category: got $(record_field_by_id "$out" REJ_C1 category)"

echo "=== preserve inner headings inside OOS code-review blocks ==="
mkdir -p "$TMP/k-impl/round-1"
cat > "$TMP/k-impl/round-1/oos.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Follow-up docs drift
- **Reviewer**: cursor-docs-output.txt
- **Concern**: docs/example.md has a stale example.

### Notes
This heading should remain inside the same OOS block.
EOF
out="$TMP/k.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/k-impl" --issue 50 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "OOS inner-heading total: $stdout"
body=$(record_field_by_id "$out" OOS_CR1_1 prose_body)
grep -qF '### Notes' <<<"$body" || fail "OOS inner heading missing from prose_body"
grep -qF 'This heading should remain inside the same OOS block.' <<<"$body" \
    || fail "OOS inner heading body missing"

echo "=== legacy OOS headings remain accepted ==="
mkdir -p "$TMP/l-impl/round-1"
cat > "$TMP/l-impl/round-1/oos.md" <<'EOF'
### OOS_1: Legacy follow-up docs drift
- **Reviewer**: legacy-oos-reviewer.txt
- **Concern**: old oos.md artifacts still compose.
EOF
out="$TMP/l.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/l-impl" --issue 51 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "legacy OOS total: $stdout"
[[ "$(record_reviewer_slot0 "$out" OOS_CR1_1)" == "legacy-oos-reviewer.txt" ]] || fail "legacy OOS reviewer"
grep -qF 'Legacy follow-up docs drift' <<<"$(record_field_by_id "$out" OOS_CR1_1 prose_body)" \
    || fail "legacy OOS body missing"

echo "=== security-tagged OOS is held back from JSONL ==="
mkdir -p "$TMP/m-impl/round-1"
cat > "$TMP/m-impl/round-1/oos.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Public follow-up
- **Reviewer**: public-reviewer.txt
- **Concern**: regular follow-up stays visible.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] Sensitive follow-up
- **Reviewer**: security-reviewer.txt
- **Concern**: focus-area = security must stay local.

Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted
EOF
out="$TMP/m.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/m-impl" --issue 52 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "security OOS holdback total: $stdout"
[[ "$(record_reviewer_slot0 "$out" OOS_CR1_1)" == "public-reviewer.txt" ]] || fail "public OOS reviewer"
[[ -z "$(record_reviewer_slot0 "$out" OOS_CR1_2)" ]] || fail "security-tagged OOS should be held back"

echo "=== synthetic rejected ids are unique across rounds ==="
mkdir -p "$TMP/n-impl/round-1" "$TMP/n-impl/round-2"
cat > "$TMP/n-impl/round-1/rejected-findings-full.md" <<'EOF'
### [rejected] FINDING_1

### FINDING_1: First round rejected
- **Reviewer**: round-1-reviewer.txt
- **Concern**: first round rejected body.
EOF
cat > "$TMP/n-impl/round-2/rejected-findings-full.md" <<'EOF'
### [rejected] FINDING_1

### FINDING_1: Second round rejected
- **Reviewer**: round-2-reviewer.txt
- **Concern**: second round rejected body.
EOF
out="$TMP/n.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/n-impl" --issue 53 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=2"* ]] || fail "multi-round rejected total: $stdout"
[[ "$(record_reviewer_slot0 "$out" REJ_CR1_1)" == "round-1-reviewer.txt" ]] || fail "REJ_CR1_1 reviewer"
[[ "$(record_reviewer_slot0 "$out" REJ_CR2_1)" == "round-2-reviewer.txt" ]] || fail "REJ_CR2_1 reviewer"

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

echo "=== OOS bold-markdown ## line extracts category (not colon leak) ==="
mkdir -p "$TMP/bold-impl/round-1"
cat > "$TMP/bold-impl/round-1/oos.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] **risk-integration** — [`scripts/handler.go`](https://example.com/handler)
- **Reviewer**: cursor-dynamic-output.txt
- **Concern**: Follow-up integration risk.

### FINDING_2: [OUT_OF_SCOPE] risk-integration: scripts/legacy.sh:1-5
- **Reviewer**: cursor-docs-output.txt
- **Concern**: Static colon format still works.
EOF
out="$TMP/bold.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/bold-impl" --issue 2417 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=2"* ]] || fail "bold OOS total: $stdout"
[[ "$(record_field_by_id "$out" OOS_CR1_1 category)" == "risk-integration" ]] \
    || fail "bold-markdown OOS category: got $(record_field_by_id "$out" OOS_CR1_1 category)"
[[ "$(record_field_by_id "$out" OOS_CR1_2 category)" == "risk-integration" ]] \
    || fail "static colon OOS category: got $(record_field_by_id "$out" OOS_CR1_2 category)"

echo "=== mangled OOS categories return empty; valid tags pass ==="
mkdir -p "$TMP/mangled-oos-impl/round-1"
cat > "$TMP/mangled-oos-impl/round-1/oos.md" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] TOCTOU: reviewer-invented heading shape
- **Reviewer**: cursor-shape-3.txt
- **Concern**: invented category token should not leak into JSONL.

### FINDING_2: [OUT_OF_SCOPE] `scripts/create-pr.sh:40-43`: file-link-as-category shape
- **Reviewer**: cursor-shape-4.txt
- **Concern**: path-like heading should not become category.

### FINDING_3: [OUT_OF_SCOPE] Pure prose paragraph with no colon delimiter anywhere
- **Reviewer**: cursor-shape-5.txt
- **Concern**: prose-only heading should yield empty category.

### FINDING_4: [OUT_OF_SCOPE] docs, `docs/voting-process.md`: comma-separated token list
- **Reviewer**: cursor-shape-6.txt
- **Concern**: comma-separated blob should yield empty category.

### FINDING_5: [OUT_OF_SCOPE] code-quality: valid tag with colon form
- **Reviewer**: cursor-valid-cq.txt
- **Concern**: canonical focus-area tag.

### FINDING_6: [OUT_OF_SCOPE] architecture: valid tag with colon form
- **Reviewer**: cursor-valid-arch.txt
- **Concern**: architecture focus-area tag.

### FINDING_7: [OUT_OF_SCOPE] security: valid tag with colon form
- **Reviewer**: cursor-valid-sec.txt
- **Concern**: security focus-area tag.

### FINDING_8: [OUT_OF_SCOPE] **not-a-focus-tag** — [`scripts/foo.sh`](https://example.com/foo)
- **Reviewer**: cursor-invalid-bold-tag.txt
- **Concern**: Bold token that is not a whitelisted focus-area tag must not populate category.
EOF
out="$TMP/mangled-oos.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/mangled-oos-impl" --issue 2447 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=8"* ]] || fail "mangled OOS total: $stdout"
[[ -z "$(record_field_by_id "$out" OOS_CR1_1 category)" ]] \
    || fail "invented heading should yield empty category, got $(record_field_by_id "$out" OOS_CR1_1 category)"
[[ -z "$(record_field_by_id "$out" OOS_CR1_2 category)" ]] \
    || fail "file-link heading should yield empty category, got $(record_field_by_id "$out" OOS_CR1_2 category)"
[[ -z "$(record_field_by_id "$out" OOS_CR1_3 category)" ]] \
    || fail "prose heading should yield empty category, got $(record_field_by_id "$out" OOS_CR1_3 category)"
[[ -z "$(record_field_by_id "$out" OOS_CR1_4 category)" ]] \
    || fail "comma-list heading should yield empty category, got $(record_field_by_id "$out" OOS_CR1_4 category)"
[[ "$(record_field_by_id "$out" OOS_CR1_5 category)" == "code-quality" ]] \
    || fail "code-quality category: got $(record_field_by_id "$out" OOS_CR1_5 category)"
[[ "$(record_field_by_id "$out" OOS_CR1_6 category)" == "architecture" ]] \
    || fail "architecture category: got $(record_field_by_id "$out" OOS_CR1_6 category)"
[[ "$(record_field_by_id "$out" OOS_CR1_7 category)" == "security" ]] \
    || fail "security category: got $(record_field_by_id "$out" OOS_CR1_7 category)"
[[ -z "$(record_field_by_id "$out" OOS_CR1_8 category)" ]] \
    || fail "non-whitelisted bold OOS heading should yield empty category, got $(record_field_by_id "$out" OOS_CR1_8 category)"

echo "=== **Reviewer(s):** splits into reviewer_slots array ==="
mkdir -p "$TMP/rsplit-impl/round-1"
cat > "$TMP/rsplit-impl/round-1/accepted-findings.md" <<'EOF'
### FINDING_88: merged slots
- **Reviewer(s)**: cursor-a-output.txt, codex-b-output.txt
- **Concern**: combined concern.

- **Suggested revision**: fix it.
EOF
out="$TMP/rsplit.jsonl"
stdout="$("$COMPOSE" --implement-tmpdir "$TMP/rsplit-impl" --issue 2483 --output "$out")"
[[ "$stdout" == *"FINDINGS_TOTAL=1"* ]] || fail "reviewer(s) split total: $stdout"
[[ "$(jq -r 'select(.id == "FINDING_88") | .schema_version' "$out")" == "2" ]] \
    || fail "schema_version for FINDING_88"
jq -e 'select(.id == "FINDING_88") | (.reviewer_slots | length) == 2 and .reviewer_slots[0] == "cursor-a-output.txt" and .reviewer_slots[1] == "codex-b-output.txt"' "$out" >/dev/null \
    || fail "reviewer_slots split mismatch for FINDING_88"

echo "=== invalid issue fails ==="
set +e
bad="$("$COMPOSE" --issue nope --output "$TMP/bad.jsonl" 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "invalid issue exit $rc"
[[ "$bad" == *"FAILED=true"* ]] || fail "invalid issue envelope missing"

echo "All assertions passed."
