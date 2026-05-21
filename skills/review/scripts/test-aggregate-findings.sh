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

echo "All aggregate-findings harness assertions passed."
