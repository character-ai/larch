#!/usr/bin/env bash
# test-aggregate-findings.sh — regression harness for aggregate-findings.sh.

set -euo pipefail

# Avoid inheriting disabled flag from outer /implement or operator shells.
unset LARCH_AGGREGATOR_DISABLED || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
AGG="$REPO_ROOT/skills/review/scripts/aggregate-findings.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-aggregate-findings.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -x "$AGG" ]] || fail "$AGG not executable"

write_stub_dispatch() {
    cat > "$TMP/stub-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        --codex-present|--cursor-present|--mode) shift 2 ;;
        --diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
mode="${AGGREGATE_STUB_MODE:-ok}"
case "$mode" in
    fail_dispatch)
        printf 'DISPATCH_OK=false\nALL_OUTPUT_FILES=\n'
        ;;
    ok)
        case "${AGGREGATE_STUB_MERGE_KIND:-merge}" in
            merge)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Concern**: normalized concern
- **Suggested revision**: fix it

EOF
                ;;
            malformed)
                cat > "$out" <<'EOF'
### FINDING_1: bad
- **Concern**: missing reviewer line
- **Suggested revision**: n/a

EOF
                ;;
            missing_input_reviewer)
                cat > "$out" <<'EOF'
### FINDING_1: partial merge
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Concern**: dropped c
- **Suggested revision**: fix

EOF
                ;;
            oos_drop_tag)
                cat > "$out" <<'EOF'
### FINDING_1: merged without OOS tag
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Concern**: merged
- **Suggested revision**: fix

EOF
                ;;
            oos_shared_slot_merge)
                cat > "$out" <<'EOF'
### FINDING_1: in-scope A
- **Reviewer(s)**: cursor-a-output.txt
- **Concern**: x
- **Suggested revision**: fix

### FINDING_2: [OUT_OF_SCOPE] **code-quality** [`x`]
- **Reviewer(s)**: cursor-a-output.txt
- **Concern**: oos
- **Suggested revision**: n/a

EOF
                ;;
            zero_findings)
                cat > "$out" <<'EOF'
Aggregator narrative: all input findings were resolved as duplicates; no merged FINDING blocks.

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

EOF
                ;;
            zero_findings_no_attest)
                cat > "$out" <<'EOF'
Aggregator narrative: all input findings were resolved as duplicates; no merged FINDING blocks.

EOF
                ;;
            zero_findings_padded_attest)
                cat > "$out" <<'EOF'
Aggregator narrative: padded empty-merge token line.

  LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED  

EOF
                ;;
            merge_plus_spurious_attest)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Concern**: normalized concern
- **Suggested revision**: fix it

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

EOF
                ;;
            labelled_slot)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt (via C.2 coverage gap), cursor-b-output.txt, cursor-c-output.txt
- **Concern**: normalized concern
- **Suggested revision**: fix it

EOF
                ;;
            *)
                echo "stub: bad AGGREGATE_STUB_MERGE_KIND" >&2
                exit 2
                ;;
        esac
        printf 'DISPATCH_OK=true\nALL_OUTPUT_FILES=%s\n' "$out"
        ;;
    *)
        echo "stub: bad AGGREGATE_STUB_MODE" >&2
        exit 2
        ;;
esac
STUB
    chmod +x "$TMP/stub-dispatch.sh"
}

echo "=== LARCH_AGGREGATOR_DISABLED=1 pass-through ==="
cat > "$TMP/f1.md" <<'EOF'
### FINDING_1: A
- **Reviewer**: a-output.txt
- **Concern**: x
- **Suggested revision**: y

### FINDING_2: B
- **Reviewer**: b-output.txt
- **Concern**: z
- **Suggested revision**: w

EOF
cp "$TMP/f1.md" "$TMP/f1-copy.md"
LARCH_AGGREGATOR_DISABLED=1 "$AGG" \
    --findings-file "$TMP/f1-copy.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-disabled.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-disabled.env" || fail "disabled AGGREGATED"
grep -Fq 'REASON=disabled' "$TMP/out-disabled.env" || fail "disabled REASON"
grep -Fq 'INPUT_COUNT=0' "$TMP/out-disabled.env" || fail "disabled INPUT_COUNT"
grep -Fq 'MERGED_COUNT=0' "$TMP/out-disabled.env" || fail "disabled MERGED_COUNT"
cmp -s "$TMP/f1.md" "$TMP/f1-copy.md" || fail "findings changed when disabled"

echo "=== insufficient input (<2 blocks) ==="
cat > "$TMP/one.md" <<'EOF'
### FINDING_1: Only
- **Reviewer**: only-output.txt
- **Concern**: x
- **Suggested revision**: y

EOF
cp "$TMP/one.md" "$TMP/one-copy.md"
"$AGG" \
    --findings-file "$TMP/one-copy.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-insufficient.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-insufficient.env" || fail "single-block AGGREGATED"
grep -Fq 'REASON=insufficient-input' "$TMP/out-insufficient.env" || fail "single-block REASON"
cmp -s "$TMP/one.md" "$TMP/one-copy.md" || fail "findings changed on insufficient"

echo "=== stub merges 3 findings into 1 ==="
cat > "$TMP/in3.md" <<'EOF'
### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt
- **Concern**: same bug other words
- **Suggested revision**: fix

### FINDING_3: Dup C
- **Reviewer**: cursor-c-output.txt
- **Concern**: same bug again
- **Suggested revision**: fix

EOF
cp "$TMP/in3.md" "$TMP/in3-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge \
"$AGG" \
    --findings-file "$TMP/in3-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-merge.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-merge.env" || fail "merge AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-merge.env" || fail "merge REASON"
grep -Fq 'MERGED_COUNT=1' "$TMP/out-merge.env" || fail "MERGED_COUNT"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-work.md" | tr -d '[:space:]')" == "1" ]] || fail "expected one FINDING block after merge"

echo "=== malformed merged output keeps original ==="
cp "$TMP/in3.md" "$TMP/in3-mal.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=malformed \
"$AGG" \
    --findings-file "$TMP/in3-mal.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-mal.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-mal.env" || fail "malformed AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-mal.env" || fail "malformed REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-mal.md" || fail "findings should be unchanged on malformed"

echo "=== dispatch failure keeps original ==="
cp "$TMP/in3.md" "$TMP/in3-disp.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=fail_dispatch \
"$AGG" \
    --findings-file "$TMP/in3-disp.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-disp.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-disp.env" || fail "dispatch-fail AGGREGATED"
grep -Fq 'REASON=dispatch-failed' "$TMP/out-disp.env" || fail "dispatch-fail REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-disp.md" || fail "findings unchanged on dispatch fail"

echo "=== validation rejects dropped input reviewer ==="
cp "$TMP/in3.md" "$TMP/in3-miss.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=missing_input_reviewer \
"$AGG" \
    --findings-file "$TMP/in3-miss.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-miss.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-miss.env" || fail "missing-reviewer AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-miss.env" || fail "missing-reviewer REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-miss.md" || fail "findings unchanged when input reviewer dropped"

echo "=== validation rejects merge that drops [OUT_OF_SCOPE] for only-OOS reviewer ==="
cat > "$TMP/in-oos.md" <<'EOF'
### FINDING_1: in-scope A
- **Reviewer**: cursor-a-output.txt
- **Concern**: x
- **Suggested revision**: fix

### FINDING_2: [OUT_OF_SCOPE] **code-quality** [`x`]
- **Reviewer**: cursor-b-output.txt
- **Concern**: oos
- **Suggested revision**: n/a

EOF
cp "$TMP/in-oos.md" "$TMP/in-oos-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=oos_drop_tag \
"$AGG" \
    --findings-file "$TMP/in-oos-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-oos.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-oos.env" || fail "oos-drop AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-oos.env" || fail "oos-drop REASON"
cmp -s "$TMP/in-oos.md" "$TMP/in-oos-work.md" || fail "findings unchanged on OOS tag drop"

echo "=== validation accepts merge when reviewer has both OOS and in-scope input findings (#2491) ==="
cat > "$TMP/in-oos-shared.md" <<'EOF'
### FINDING_1: in-scope A
- **Reviewer**: cursor-a-output.txt
- **Concern**: x
- **Suggested revision**: fix

### FINDING_2: [OUT_OF_SCOPE] **code-quality** [`x`]
- **Reviewer**: cursor-a-output.txt
- **Concern**: oos
- **Suggested revision**: n/a

EOF
cp "$TMP/in-oos-shared.md" "$TMP/in-oos-shared-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=oos_shared_slot_merge \
"$AGG" \
    --findings-file "$TMP/in-oos-shared-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-oos-shared.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-oos-shared.env" || fail "oos-shared AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-oos-shared.env" || fail "oos-shared REASON"
grep -Fq 'MERGED_COUNT=2' "$TMP/out-oos-shared.env" || fail "oos-shared MERGED_COUNT"
[[ "$(grep -c '^### FINDING_' "$TMP/in-oos-shared-work.md" | tr -d '[:space:]')" == "2" ]] || fail "expected two FINDING blocks after OOS shared-slot merge"
grep -Fq '[OUT_OF_SCOPE]' "$TMP/in-oos-shared-work.md" || fail "expected [OUT_OF_SCOPE] preserved in OOS shared-slot merge"

echo "=== zero output FINDING blocks accepts clean pass (#2536) ==="
cp "$TMP/in3.md" "$TMP/in3-zero.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings \
"$AGG" \
    --findings-file "$TMP/in3-zero.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zero.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-zero.env" || fail "zero-findings AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-zero.env" || fail "zero-findings REASON"
grep -Fq 'MERGED_COUNT=0' "$TMP/out-zero.env" || fail "zero-findings MERGED_COUNT"
grep -Fq 'INPUT_COUNT=3' "$TMP/out-zero.env" || fail "zero-findings INPUT_COUNT"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-zero.md" | tr -d '[:space:]')" == "0" ]] || fail "expected zero FINDING blocks after zero-findings merge"
grep -Fq 'LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED' "$TMP/in3-zero.md" && fail "attestation must not persist in findings.md"
cmp -s "$TMP/in3.md" "$TMP/in3-zero.md" && fail "expected findings.md rewritten on zero-findings merge"

echo "=== zero output without empty-merge attestation fails validation ==="
cp "$TMP/in3.md" "$TMP/in3-zero-na.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_no_attest \
"$AGG" \
    --findings-file "$TMP/in3-zero-na.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zero-na.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-zero-na.env" || fail "no-attest AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-zero-na.env" || fail "no-attest REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-zero-na.md" || fail "findings unchanged when attestation missing"

echo "=== zero output accepts whitespace-padded empty-merge attestation (#2536) ==="
cp "$TMP/in3.md" "$TMP/in3-zero-pad.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_padded_attest \
"$AGG" \
    --findings-file "$TMP/in3-zero-pad.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zero-pad.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-zero-pad.env" || fail "padded-attest AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-zero-pad.env" || fail "padded-attest REASON"
grep -Fq 'MERGED_COUNT=0' "$TMP/out-zero-pad.env" || fail "padded-attest MERGED_COUNT"
grep -Fq 'LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED' "$TMP/in3-zero-pad.md" && fail "attestation must not persist (padded)"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-zero-pad.md" | tr -d '[:space:]')" == "0" ]] || fail "expected zero FINDING blocks after padded-attest merge"

echo "=== merged FINDING blocks plus spurious empty-merge token fails validation ==="
cp "$TMP/in3.md" "$TMP/in3-spurious.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge_plus_spurious_attest \
"$AGG" \
    --findings-file "$TMP/in3-spurious.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-spurious.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-spurious.env" || fail "spurious-attest AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-spurious.env" || fail "spurious-attest REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-spurious.md" || fail "findings unchanged when spurious attestation with blocks"

echo "=== input reviewer parenthetical suffixes normalize on successful merge ==="
cat > "$TMP/in3-inparen.md" <<'EOF'
### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt (slot note A)
- **Concern**: same bug
- **Suggested revision**: fix

### FINDING_2: Dup B
- **Reviewer**: cursor-b-output.txt (slot note B)
- **Concern**: same bug other words
- **Suggested revision**: fix

### FINDING_3: Dup C
- **Reviewer**: cursor-c-output.txt (slot note C)
- **Concern**: same bug again
- **Suggested revision**: fix

EOF
cp "$TMP/in3-inparen.md" "$TMP/in3-inparen-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge \
"$AGG" \
    --findings-file "$TMP/in3-inparen-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-inparen.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-inparen.env" || fail "input-paren AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-inparen.env" || fail "input-paren REASON"
grep -Fq 'MERGED_COUNT=1' "$TMP/out-inparen.env" || fail "input-paren MERGED_COUNT"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-inparen-work.md" | tr -d '[:space:]')" == "1" ]] || fail "expected one FINDING block after input-paren merge"

echo "=== input reviewer parenthetical suffixes interact with OOS-only rule ==="
cat > "$TMP/in-oos-paren.md" <<'EOF'
### FINDING_1: in-scope A
- **Reviewer**: cursor-a-output.txt (note)
- **Concern**: x
- **Suggested revision**: fix

### FINDING_2: [OUT_OF_SCOPE] **code-quality** [`x`]
- **Reviewer**: cursor-b-output.txt (OOS attribution)
- **Concern**: oos
- **Suggested revision**: n/a

EOF
cp "$TMP/in-oos-paren.md" "$TMP/in-oos-paren-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=oos_drop_tag \
"$AGG" \
    --findings-file "$TMP/in-oos-paren-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-oos-paren.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-oos-paren.env" || fail "oos-paren AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-oos-paren.env" || fail "oos-paren REASON"
cmp -s "$TMP/in-oos-paren.md" "$TMP/in-oos-paren-work.md" || fail "findings unchanged on OOS tag drop (input parens)"

echo "=== labelled reviewer slot suffix accepted (#2536) ==="
cp "$TMP/in3.md" "$TMP/in3-label.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=labelled_slot \
"$AGG" \
    --findings-file "$TMP/in3-label.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-label.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-label.env" || fail "labelled-slot AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-label.env" || fail "labelled-slot REASON"
grep -Fq 'MERGED_COUNT=1' "$TMP/out-label.env" || fail "labelled-slot MERGED_COUNT"

issues_parent="$TMP/agg-exec-issues"
mkdir -p "$issues_parent"
: > "$issues_parent/execution-issues.md"
touch "$issues_parent/session-env.sh"
cp "$TMP/in3.md" "$TMP/in3-session.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=malformed \
"$AGG" \
    --findings-file "$TMP/in3-session.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff \
    --session-env-path "$issues_parent/session-env.sh" >"$TMP/out-session.env"
grep -Fq 'findings aggregator' "$issues_parent/execution-issues.md" || fail "execution-issues missing aggregator warning"

echo "All aggregate-findings harness assertions passed."
