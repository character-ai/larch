#!/usr/bin/env bash
# test-aggregate-findings.sh — regression harness for aggregate-findings.sh.

set -euo pipefail

# Avoid inheriting disabled flag from outer /implement or operator shells.
unset LARCH_AGGREGATOR_DISABLED || true
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR || true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
AGG="$REPO_ROOT/skills/review/scripts/aggregate-findings.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-aggregate-findings.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[[ -z "${LARCH_EXECUTION_ISSUES_LOG:-}" ]] || fail "harness entry must clear LARCH_EXECUTION_ISSUES_LOG (restore unset prelude or unset outer env)"

[[ -x "$AGG" ]] || fail "$AGG not executable"

write_stub_dispatch() {
    cat > "$TMP/stub-dispatch.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
slots=""
CURSOR_PRESENT=""
CODEX_PRESENT=""
argv_log="${AGGREGATE_STUB_ARGV_LOG:-}"
[[ -n "$argv_log" ]] && printf '%s\n' "$*" >>"$argv_log"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slots-file) slots="${2:?}"; shift 2 ;;
        --codex-present) CODEX_PRESENT="${2:?}"; shift 2 ;;
        --cursor-present) CURSOR_PRESENT="${2:?}"; shift 2 ;;
        --mode) shift 2 ;;
        --diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
        --require-result-pattern) printf '%s\n' "${2:?}" >"${AGGREGATE_STUB_REQUIRE_PATTERN_LOG:-/dev/null}"; shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
tool=$(jq -r '.tool' "$slots")
ot_tool="$tool"
if [[ "$tool" == "cursor" && "$CURSOR_PRESENT" != "true" ]]; then
    ot_tool=claude
elif [[ "$tool" == "codex" && "$CODEX_PRESENT" != "true" ]]; then
    ot_tool=claude
fi
emit_dispatch_ok() {
    paths_out="${AGGREGATE_STUB_OUTPUT_FILES_PATH:-${slots}.output-files}"
    legacy_out="${AGGREGATE_STUB_ALL_OUTPUT_FILES:-$out}"
    if [[ "${AGGREGATE_STUB_OMIT_OUTPUT_FILES_PATH:-false}" != "true" ]]; then
        printf '%s\n' "$out" >"$paths_out"
        printf 'DISPATCH_OK=true\nALL_OUTPUT_FILES=%s\nALL_OUTPUT_FILES_PATH=%s\nALL_OUTPUT_TOOLS=%s\n' "$legacy_out" "$paths_out" "$ot_tool"
    else
        printf 'DISPATCH_OK=true\nALL_OUTPUT_FILES=%s\nALL_OUTPUT_TOOLS=%s\n' "$legacy_out" "$ot_tool"
    fi
}
mode="${AGGREGATE_STUB_MODE:-ok}"
case "$mode" in
    fail_dispatch)
        printf 'DISPATCH_OK=false\nALL_OUTPUT_FILES=\nALL_OUTPUT_TOOLS=\n'
        ;;
    ok)
        case "${AGGREGATE_STUB_MERGE_KIND:-merge}" in
            preamble_contradiction)
                cat > "$out" <<'EOF'
We have multiple `### FINDING_N:` blocks in the input.

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

EOF
                ;;
            numbered_prose_contradiction)
                cat > "$out" <<'EOF'
Research complete: inputs are the supplied reviewer blocks only (no repo reads). Merging duplicate concerns, preserving `[OUT_OF_SCOPE]` on merged headings where any source carried it, and omitting suggested-revision bullets where the source gave none (FINDING_24-28).

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

EOF
                ;;
            merge)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

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
- **Severity**: important
- **Concern**: x
- **Suggested revision**: fix

### FINDING_2: [OUT_OF_SCOPE] **code-quality** [`x`]
- **Reviewer(s)**: cursor-a-output.txt
- **Severity**: latent
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
            zero_findings_impure_attest)
                cat > "$out" <<'EOF'
Aggregator narrative: near-attestation line should be dropped before strip.

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED junk-suffix

EOF
                ;;
            zero_findings_nonconforming_heading)
                cat > "$out" <<'EOF'
Aggregator narrative: pseudo-heading should fail validation.

### FINDING_1 not-a-valid-heading-line

EOF
                ;;
            zero_findings_nospace_pseudo_heading)
                cat > "$out" <<'EOF'
Aggregator narrative: tight ###FINDING_ typo should fail validation.

###FINDING_1: not a strict heading (no space after ###)

EOF
                ;;
            zero_findings_prose_finding_ids)
                cat > "$out" <<'EOF'
Aggregator narrative: empty merge; prose mentions FINDING_ids.

### FINDING_ids are stable across reviewers.

EOF
                ;;
            zero_findings_padded_attest_rejected)
                cat > "$out" <<'EOF'
Aggregator narrative: padded empty-merge token line.

  LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED  

EOF
                ;;
            merge_plus_spurious_attest)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

EOF
                ;;
            merge_plus_impure_attest)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTEDjunk-suffix

EOF
                ;;
            labelled_slot)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt (via C.2 coverage gap), cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

EOF
                ;;
            trace_wrapped)
                cat > "$out" <<'EOF'
### FINDING_1: merged
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: nit
- **Concern**: merged
- **Suggested revisions**:
  - From cursor-a-output.txt: alpha one
    alpha two tail
  - From cursor-b-output.txt: beta phrase here

EOF
                ;;
            unknown_from_slot)
                cat > "$out" <<'EOF'
### FINDING_1: merged
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: merged
- **Suggested revisions**:
  - From cursor-typo-output.txt: same bug

EOF
                ;;
            untraceable_rev)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revisions**:
  - From cursor-a-output.txt: totally_unique_garbage_marker_xyzzy12345

EOF
                ;;
            prefix_collision)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revisions**:
  - From cursor-a-output.txt: alpha beta gamma delta epsilon zeta unique_tail_token_qwerty99
  - From cursor-b-output.txt: fix
  - From cursor-c-output.txt: fix

EOF
                ;;
            revision_concern_fold)
                cat > "$out" <<'EOF'
### FINDING_1: merged
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt
- **Severity**: nit
- **Concern**: merged
- **Suggested revisions**:
  - From cursor-a-output.txt: first line of fix
    - **Concern**: looks like a heading but is verbatim fix text
    tail still here
  - From cursor-b-output.txt: beta phrase here

EOF
                ;;
            suggested_revisions_orphan_preamble)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revisions**:
  wedged preamble before first From line
  - From cursor-a-output.txt: fix
  - From cursor-b-output.txt: fix
  - From cursor-c-output.txt: fix

EOF
                ;;
            merge_missing_severity)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Concern**: normalized concern
- **Suggested revision**: fix

EOF
                ;;
            merge_severity_important)
                cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: important
- **Concern**: normalized concern
- **Suggested revision**: fix

EOF
                ;;
            *)
                echo "stub: bad AGGREGATE_STUB_MERGE_KIND" >&2
                exit 2
                ;;
        esac
        emit_dispatch_ok
        ;;
    *)
        echo "stub: bad AGGREGATE_STUB_MODE" >&2
        exit 2
        ;;
esac
STUB
    chmod +x "$TMP/stub-dispatch.sh"
}

write_external_tool_stubs() {
    local dir="$1"
    mkdir -p "$dir"
    cat > "$dir/codex" <<'STUB'
#!/usr/bin/env bash
out=""
last=""
log="${CODEX_STUB_LOG:-}"
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then out="$arg"; fi
    last="$arg"
done
[[ -n "$out" ]] || exit 9
[[ -n "$log" ]] && printf '%s\n' "$*" >>"$log"
if [[ "${CODEX_STUB_FAIL:-false}" == "true" ]]; then
    exit 7
fi
printf '%s\n' "${CODEX_STUB_RESULT_CONTENT:-codex ok}" >"$out"
STUB
    cat > "$dir/cursor" <<'STUB'
#!/usr/bin/env bash
log="${CURSOR_STUB_LOG:-}"
[[ -n "$log" ]] && printf '%s\n' "$*" >>"$log"
if [[ "${CURSOR_STUB_FAIL:-false}" == "true" ]]; then
    exit 8
fi
jq -nc --arg r "${CURSOR_STUB_RESULT_CONTENT:-cursor ok}" \
    '{result:$r,usage:{inputTokens:1,outputTokens:1,cacheReadTokens:0,cacheWriteTokens:0}}'
STUB
    chmod +x "$dir/codex" "$dir/cursor"
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

echo "=== zero output FINDING blocks fails closed when input had findings (#2536) ==="
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
grep -Fq 'AGGREGATED=false' "$TMP/out-zero.env" || fail "zero-findings AGGREGATED"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-zero.env" || fail "zero-findings REASON"
grep -Fq 'INPUT_COUNT=3' "$TMP/out-zero.env" || fail "zero-findings INPUT_COUNT"
cmp -s "$TMP/in3.md" "$TMP/in3-zero.md" || fail "findings unchanged on zero-findings validator rejection"

echo "=== zero output without model attestation: validator rejects empty-merge (#2563) ==="
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
cmp -s "$TMP/in3.md" "$TMP/in3-zero-na.md" || fail "findings unchanged on empty-merge validator rejection"
EX="$TMP/exec-issues-no-attest"
mkdir -p "$EX"
cp "$TMP/in3.md" "$EX/in.md"
: >"$EX/execution-issues.md"
write_stub_dispatch
LARCH_EXECUTION_ISSUES_LOG="$EX/execution-issues.md" \
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_no_attest \
"$AGG" \
    --findings-file "$EX/in.md" \
    --review-tmpdir "$EX" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zero-na-exec.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-zero-na-exec.env" || fail "no-attest exec-isolation AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-zero-na-exec.env" || fail "no-attest exec-isolation REASON"
grep -Fq 'merged output failed validation' "$EX/execution-issues.md" || fail "empty-merge rejection must log merged-output validation failure to execution-issues.md"
cmp -s "$TMP/in3.md" "$EX/in.md" || fail "findings unchanged on no-attest exec-isolation validator rejection"

echo "=== zero_findings_impure_attest: validator rejects and findings stay clean ==="
cp "$TMP/in3.md" "$TMP/in3-zero-impure.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_impure_attest \
"$AGG" \
    --findings-file "$TMP/in3-zero-impure.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zero-impure.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-zero-impure.env" || fail "impure-attest AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-zero-impure.env" || fail "impure-attest REASON"
grep -Fq 'junk-suffix' "$TMP/in3-zero-impure.md" && fail "impure attestation suffix must not survive into findings.md"
cmp -s "$TMP/in3.md" "$TMP/in3-zero-impure.md" || fail "findings unchanged on impure-attest validator rejection"

echo "=== zero_findings_nonconforming_heading: validation-failed ==="
cp "$TMP/in3.md" "$TMP/in3-nonconf.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_nonconforming_heading \
"$AGG" \
    --findings-file "$TMP/in3-nonconf.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-nonconf.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-nonconf.env" || fail "nonconforming-heading AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-nonconf.env" || fail "nonconforming-heading REASON"

echo "=== zero_findings_nospace_pseudo_heading: validation-failed ==="
cp "$TMP/in3.md" "$TMP/in3-nospace-pseudo.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_nospace_pseudo_heading \
"$AGG" \
    --findings-file "$TMP/in3-nospace-pseudo.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-nospace-pseudo.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-nospace-pseudo.env" || fail "nospace-pseudo AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-nospace-pseudo.env" || fail "nospace-pseudo REASON"

echo "=== zero_findings_prose_finding_ids: validation-failed ==="
cp "$TMP/in3.md" "$TMP/in3-finding-ids-prose.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_prose_finding_ids \
"$AGG" \
    --findings-file "$TMP/in3-finding-ids-prose.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-finding-ids-prose.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-finding-ids-prose.env" || fail "finding-ids-prose AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-finding-ids-prose.env" || fail "finding-ids-prose REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-finding-ids-prose.md" || fail "findings unchanged on prose FINDING_ids validator rejection"

echo "=== zero_findings_input_nonempty rejected: input had findings, output empty + attestation => validation-exhausted (#2782) ==="
cp "$TMP/in3.md" "$TMP/in3-zfn.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings \
"$AGG" \
    --findings-file "$TMP/in3-zfn.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zfn.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-zfn.env" || fail "#2782: aggregation must fail when input had findings and output is empty"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-zfn.env" || fail "#2782: REASON must be validation-exhausted"
grep -Fq 'AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input' "$TMP/aggregator-validate.stderr" \
    || fail "#2782: validator must emit empty_merge_from_nonempty_input reason"
cmp -s "$TMP/in3.md" "$TMP/in3-zfn.md" || fail "#2782: findings.md must remain unchanged on validator rejection"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-zfn.md" | tr -d '[:space:]')" == "3" ]] \
    || fail "#2782: original 3 FINDING blocks must survive"

echo "=== zero output rejects whitespace-padded empty-merge attestation for nonempty input (#2536) ==="
cp "$TMP/in3.md" "$TMP/in3-zero-pad.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_padded_attest_rejected \
"$AGG" \
    --findings-file "$TMP/in3-zero-pad.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-zero-pad.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-zero-pad.env" || fail "padded-attest AGGREGATED"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-zero-pad.env" || fail "padded-attest REASON"
cmp -s "$TMP/in3.md" "$TMP/in3-zero-pad.md" || fail "findings unchanged on padded-attest validator rejection"

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

echo "=== merged FINDING blocks plus impure adjacent attestation suffix: success path strips suffix line ==="
cp "$TMP/in3.md" "$TMP/in3-impure-success.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge_plus_impure_attest \
"$AGG" \
    --findings-file "$TMP/in3-impure-success.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-impure-success.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-impure-success.env" || fail "merge+impure-attest AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-impure-success.env" || fail "merge+impure-attest REASON"
grep -Fq 'MERGED_COUNT=1' "$TMP/out-impure-success.env" || fail "merge+impure-attest MERGED_COUNT"
grep -Fq 'junk-suffix' "$TMP/in3-impure-success.md" && fail "impure attestation suffix must not survive persisted findings.md on success path"
grep -Fq 'LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED' "$TMP/in3-impure-success.md" && fail "attestation token (any form) must not survive persisted findings.md on success path"
[[ "$(grep -c '^### FINDING_' "$TMP/in3-impure-success.md" | tr -d '[:space:]')" == "1" ]] || fail "expected one FINDING block after merge+impure-attest"

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

echo "=== revision traceability: wrapped From lines ==="
RT="$TMP/rt-wrapped"
mkdir -p "$RT"
cat > "$RT/in-trace.md" <<'EOF'
### FINDING_1: A
- **Reviewer**: cursor-a-output.txt
- **Concern**: first
- **Suggested revision**: alpha one alpha two tail

### FINDING_2: B
- **Reviewer**: cursor-b-output.txt
- **Concern**: second
- **Suggested revision**: beta phrase here

EOF
cp "$RT/in-trace.md" "$RT/in-trace-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=trace_wrapped \
"$AGG" \
    --findings-file "$RT/in-trace-work.md" \
    --review-tmpdir "$RT" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-trace-wrapped.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-trace-wrapped.env" || fail "trace-wrapped AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-trace-wrapped.env" || fail "trace-wrapped REASON"
grep -Fq 'not traceable' "$RT/aggregator-validate.stderr" && fail "unexpected untraceable warning"

echo "=== revision traceability: six-word prefix alone must not pass ==="
cat > "$TMP/in-prefix.md" <<'EOF'
### FINDING_1: Dup A
- **Reviewer**: cursor-a-output.txt
- **Concern**: prefix alpha beta gamma delta epsilon zeta omega noise
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
cp "$TMP/in-prefix.md" "$TMP/in-prefix-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=prefix_collision \
"$AGG" \
    --findings-file "$TMP/in-prefix-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-prefix.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-prefix.env" || fail "prefix-collision AGGREGATED"
grep -Fq 'not traceable to scoped input' "$TMP/aggregator-validate.stderr" || fail "expected prefix-only collision to warn untraceable"
cp "$TMP/in-prefix.md" "$TMP/in-prefix-fallback-work.md"
LARCH_AGGREGATE_REVISION_TRACE_PREFIX_FALLBACK=1 \
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=prefix_collision \
"$AGG" \
    --findings-file "$TMP/in-prefix-fallback-work.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-prefix-fallback.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-prefix-fallback.env" || fail "prefix-fallback AGGREGATED"
grep -Fq 'not traceable to scoped input' "$TMP/aggregator-validate.stderr" && fail "prefix fallback should silence untraceable warning"

echo "=== suggested revisions: field-like continuation line does not truncate ==="
RF="$TMP/rt-rev-fold"
mkdir -p "$RF"
cat > "$RF/in-fold.md" <<'EOF'
### FINDING_1: A
- **Reviewer**: cursor-a-output.txt
- **Concern**: first line of fix - **Concern**: looks like a heading but is verbatim fix text tail still here
- **Suggested revision**: alpha one alpha two tail

### FINDING_2: B
- **Reviewer**: cursor-b-output.txt
- **Concern**: second
- **Suggested revision**: beta phrase here

EOF
cp "$RF/in-fold.md" "$RF/in-fold-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=revision_concern_fold \
"$AGG" \
    --findings-file "$RF/in-fold-work.md" \
    --review-tmpdir "$RF" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-rev-fold.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-rev-fold.env" || fail "rev-fold AGGREGATED"
grep -Fq 'not traceable' "$RF/aggregator-validate.stderr" && fail "unexpected untraceable on concern-shaped continuation"

echo "=== suggested revisions: orphan preamble before first From warns ==="
ROR="$TMP/rt-orphan-rev"
mkdir -p "$ROR"
cp "$TMP/in3.md" "$ROR/in3.md"
cp "$ROR/in3.md" "$ROR/in3-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=suggested_revisions_orphan_preamble \
"$AGG" \
    --findings-file "$ROR/in3-work.md" \
    --review-tmpdir "$ROR" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-orphan-rev.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-orphan-rev.env" || fail "orphan-rev AGGREGATED"
grep -Fq 'unexpected line in Suggested revisions sub-list before first' "$ROR/aggregator-validate.stderr" || fail "missing orphan-preamble stderr warning"

echo "=== unknown From slot label emits stderr warning ==="
RTU="$TMP/rt-unknown-from"
mkdir -p "$RTU"
cp "$TMP/in3.md" "$RTU/in3.md"
cp "$RTU/in3.md" "$RTU/in3-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=unknown_from_slot \
"$AGG" \
    --findings-file "$RTU/in3-work.md" \
    --review-tmpdir "$RTU" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-unknown-from.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-unknown-from.env" || fail "unknown-from AGGREGATED"
grep -Fq 'unknown From slot label' "$RTU/aggregator-validate.stderr" || fail "missing unknown-slot stderr"

echo "=== untraceable revision bullet emits stderr warning ==="
RTX="$TMP/rt-untraceable"
mkdir -p "$RTX"
cp "$TMP/in3.md" "$RTX/in3.md"
cp "$RTX/in3.md" "$RTX/in3-work.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=untraceable_rev \
"$AGG" \
    --findings-file "$RTX/in3-work.md" \
    --review-tmpdir "$RTX" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-untr.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-untr.env" || fail "untraceable AGGREGATED"
grep -Fq 'not traceable to scoped input' "$RTX/aggregator-validate.stderr" || fail "missing untraceable stderr"

echo "=== LARCH_AGGREGATE_REVISION_TRACE_STRICT fails validation on untraceable ==="
RTS="$TMP/rt-strict"
mkdir -p "$RTS"
cp "$TMP/in3.md" "$RTS/in3.md"
cp "$RTS/in3.md" "$RTS/in3-work.md"
write_stub_dispatch
LARCH_AGGREGATE_REVISION_TRACE_STRICT=1 \
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=untraceable_rev \
"$AGG" \
    --findings-file "$RTS/in3-work.md" \
    --review-tmpdir "$RTS" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-strict.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-strict.env" || fail "strict untraceable AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-strict.env" || fail "strict untraceable REASON"

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

echo "=== inherited LARCH_EXECUTION_ISSUES_LOG cannot leak past harness-style prelude (#2617) ==="
# Shape A: production aggregate-findings still prefers LARCH_EXECUTION_ISSUES_LOG over
# --review-tmpdir when both are set; this harness clears inherited vars at entry. Re-run
# aggregate-findings in a child process with a contaminated env, then apply the same unset
# prelude as this script before invoking the script-under-test.
SENTINEL="/tmp/larch-test-env-leak-$$.md"
rm -f "$SENTINEL"
LP_VISIBLE="$TMP/leak-probe-visible"
mkdir -p "$LP_VISIBLE"
cp "$TMP/in3.md" "$LP_VISIBLE/in3-disp.md"
write_stub_dispatch
# No inner unset: proves append_warning reaches LARCH_EXECUTION_ISSUES_LOG when exported
# (regression if append_warning becomes a no-op while KV output still shows dispatch-failed).
(
    export LARCH_EXECUTION_ISSUES_LOG="$SENTINEL"
    export AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh"
    export AGGREGATE_STUB_MODE=fail_dispatch
    bash -c 'set -euo pipefail
        unset LARCH_AGGREGATOR_DISABLED || true
        exec "$@"' bash "$AGG" \
        --findings-file "$LP_VISIBLE/in3-disp.md" \
        --review-tmpdir "$LP_VISIBLE" \
        --codex-present true \
        --cursor-present true \
        --mode diff >"$TMP/out-leak-visible.env"
)
grep -Fq 'AGGREGATED=false' "$TMP/out-leak-visible.env" || fail "leak-visible dispatch-fail AGGREGATED"
grep -Fq 'REASON=dispatch-failed' "$TMP/out-leak-visible.env" || fail "leak-visible dispatch-fail REASON"
grep -Fq 'findings aggregator' "$SENTINEL" || fail "leak-visible: expected aggregator warning in LARCH_EXECUTION_ISSUES_LOG"
rm -f "$SENTINEL"
LP="$TMP/leak-probe"
mkdir -p "$LP"
cp "$TMP/in3.md" "$LP/in3-disp.md"
write_stub_dispatch
env LARCH_EXECUTION_ISSUES_LOG="$SENTINEL" SESSION_ENV_PATH="/nonexistent/session-env.sh" IMPLEMENT_TMPDIR="/nonexistent/implement-tmp" \
    AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
    AGGREGATE_STUB_MODE=fail_dispatch \
    bash -c 'set -euo pipefail
        unset LARCH_AGGREGATOR_DISABLED || true
        unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR || true
        exec "$@"' bash "$AGG" \
        --findings-file "$LP/in3-disp.md" \
        --review-tmpdir "$LP" \
        --codex-present true \
        --cursor-present true \
        --mode diff >"$TMP/out-leak-probe.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-leak-probe.env" || fail "leak-probe dispatch-fail AGGREGATED"
grep -Fq 'REASON=dispatch-failed' "$TMP/out-leak-probe.env" || fail "leak-probe dispatch-fail REASON"
grep -Fq 'findings aggregator' "$LP/execution-issues.md" || fail "leak-probe: expected aggregator warning in review-tmpdir execution-issues"
if [[ -f "$SENTINEL" && -s "$SENTINEL" ]]; then
    fail "sentinel execution-issues log leaked non-empty content ($(wc -c <"$SENTINEL" | tr -d "[:space:]") bytes)"
fi
rm -f "$SENTINEL"

echo "=== zero_findings_preamble_contradiction: validator stderr token (single-phase cap) ==="
cp "$TMP/in3.md" "$TMP/in3-pream.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=preamble_contradiction \
"$AGG" \
    --findings-file "$TMP/in3-pream.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-pream.env"
grep -Fq 'AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring' "$TMP/aggregator-validate.stderr" || fail "expected preamble_finding_substring validator stderr"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-pream.env" || fail "narrow trigger should surface validation-exhausted"

echo "=== zero_findings_numbered_prose_contradiction: prose FINDING_N refs trip preamble signal ==="
cp "$TMP/in3.md" "$TMP/in3-numpr.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=numbered_prose_contradiction \
"$AGG" \
    --findings-file "$TMP/in3-numpr.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-numpr.env"
grep -Fq 'AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring' "$TMP/aggregator-validate.stderr" || fail "expected preamble_finding_substring for prose FINDING_24 reference"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-numpr.env" || fail "narrow trigger should surface validation-exhausted for numbered prose"

echo "=== validation_exhausted: narrow-trigger validator failure logs one execution issue ==="
WF="$TMP/validation-exhausted"
mkdir -p "$WF"
cp "$TMP/in3.md" "$WF/in.md"
: >"$WF/execution-issues.md"
write_stub_dispatch
LARCH_EXECUTION_ISSUES_LOG="$WF/execution-issues.md" \
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=preamble_contradiction \
"$AGG" \
    --findings-file "$WF/in.md" \
    --review-tmpdir "$WF" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-wf-ex.env"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-wf-ex.env" || fail "validation exhausted REASON"
grep -Fq 'PHASES_ATTEMPTED=' "$TMP/out-wf-ex.env" && fail "PHASES_ATTEMPTED must not be emitted"
[[ -f "$WF/aggregator-output.txt" && ! -e "$WF/aggregator-output-codex.txt" && ! -e "$WF/aggregator-output-claude.txt" ]] || fail "expected only base aggregator output file"
cmp -s "$TMP/in3.md" "$WF/in.md" || fail "findings unchanged on exhaustion"
grep -c '^- \*\*findings aggregator' "$WF/execution-issues.md" | grep -q '^1$' || fail "expected exactly one execution-issues entry"

echo "=== output resolution prefers ALL_OUTPUT_FILES_PATH over legacy ALL_OUTPUT_FILES ==="
SIDE="$TMP/sidecar-resolution"
mkdir -p "$SIDE"
cp "$TMP/in3.md" "$SIDE/in.md"
write_stub_dispatch
printf 'stale legacy path\n' >"$SIDE/stale-output.txt"
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge \
AGGREGATE_STUB_ALL_OUTPUT_FILES="$SIDE/stale-output.txt" \
AGGREGATE_STUB_ARGV_LOG="$SIDE/dispatch.argv" \
"$AGG" \
    --findings-file "$SIDE/in.md" \
    --review-tmpdir "$SIDE" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-sidecar.env"
grep -Fq 'REASON=ok' "$TMP/out-sidecar.env" || fail "sidecar resolution REASON"
grep -Fq -- '--require-result-pattern' "$SIDE/dispatch.argv" || fail "expected --require-result-pattern threaded to dispatch"
grep -Fq '^(### FINDING_[0-9]+:|LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)' "$SIDE/dispatch.argv" || fail "expected aggregator result pattern"

echo "=== output resolution falls back to ALL_OUTPUT_FILES when sidecar is absent ==="
LEG="$TMP/legacy-output-resolution"
mkdir -p "$LEG"
cp "$TMP/in3.md" "$LEG/in.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge \
AGGREGATE_STUB_OMIT_OUTPUT_FILES_PATH=true \
"$AGG" \
    --findings-file "$LEG/in.md" \
    --review-tmpdir "$LEG" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-legacy.env"
grep -Fq 'REASON=ok' "$TMP/out-legacy.env" || fail "legacy output resolution REASON"

echo "=== pattern gate accepts full-line attestation and reaches validator ==="
PAT="$TMP/pattern-attestation"
mkdir -p "$PAT"
cp "$TMP/in3.md" "$PAT/in.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings \
AGGREGATE_STUB_REQUIRE_PATTERN_LOG="$PAT/require-pattern.txt" \
"$AGG" \
    --findings-file "$PAT/in.md" \
    --review-tmpdir "$PAT" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-pattern-attest.env"
grep -Fq 'REASON=validation-exhausted' "$TMP/out-pattern-attest.env" || fail "attestation should reach validator narrow-trigger path"
grep -Fq '^(### FINDING_[0-9]+:|LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED[[:space:]]*$)' "$PAT/require-pattern.txt" || fail "attestation pattern not threaded"

echo "=== codex_primary_narration_routes_to_phase2_cursor ==="
WR="$TMP/codex-primary-phase2"
mkdir -p "$WR"
cp "$TMP/in3.md" "$WR/in.md"
STUBBIN="$WR/bin"
write_external_tool_stubs "$STUBBIN"
PATH="$STUBBIN:$PATH" \
WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.01 \
LARCH_TRANSIENT_RETRY_DELAY=0 \
LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
CODEX_STUB_RESULT_CONTENT='Merging duplicate reviewer findings by behavioral risk.' \
CURSOR_STUB_RESULT_CONTENT=$'### FINDING_1: Cursor phase 2 merged title\n- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt\n- **Severity**: nit\n- **Concern**: Cursor phase 2 concern\n- **Suggested revision**: fix\n' \
"$AGG" \
    --findings-file "$WR/in.md" \
    --review-tmpdir "$WR" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-wf-rec.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-wf-rec.env" || fail "phase2 recover AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-wf-rec.env" || fail "phase2 recover REASON"
grep -Fq 'Cursor phase 2 concern' "$WR/in.md" || fail "expected cursor phase2 ballot persisted"
grep -Fq 'ALL_OUTPUT_TOOLS=cursor' "$WR/aggregator-dispatch.env" || fail "expected cursor final tool"
grep -Eq '^PHASE2_SLOTS=.+aggregator-output-phase2\.txt' "$WR/aggregator-dispatch.env" || fail "expected phase2 slot output"
grep -Fq 'PHASES_ATTEMPTED=' "$TMP/out-wf-rec.env" && fail "PHASES_ATTEMPTED must not be emitted"

echo "=== dispatcher_rejects_pseudo_finding_heading ==="
PSE="$TMP/pseudo-heading-fallback"
mkdir -p "$PSE"
cp "$TMP/in3.md" "$PSE/in.md"
STUBBIN="$PSE/bin"
write_external_tool_stubs "$STUBBIN"
PATH="$STUBBIN:$PATH" \
WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.01 \
LARCH_TRANSIENT_RETRY_DELAY=0 \
LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
CODEX_STUB_RESULT_CONTENT=$'### FINDING_1 not-a-valid-heading-line\n' \
CURSOR_STUB_RESULT_CONTENT=$'### FINDING_1: Cursor fallback after pseudo heading\n- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt\n- **Severity**: nit\n- **Concern**: cursor fallback concern\n- **Suggested revision**: fix\n' \
"$AGG" \
    --findings-file "$PSE/in.md" \
    --review-tmpdir "$PSE" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-pseudo.env"
grep -Fq 'REASON=ok' "$TMP/out-pseudo.env" || fail "pseudo-heading fallback REASON"
grep -Fq 'cursor fallback concern' "$PSE/in.md" || fail "pseudo-heading should fall through to cursor"
grep -Fq 'ALL_OUTPUT_TOOLS=cursor' "$PSE/aggregator-dispatch.env" || fail "pseudo-heading final tool"

echo "=== codex_absent_runs_cursor_in_phase2 ==="
WS="$TMP/waterfall-skip"
mkdir -p "$WS"
cp "$TMP/in3.md" "$WS/in.md"
STUBBIN="$WS/bin"
write_external_tool_stubs "$STUBBIN"
PATH="$STUBBIN:$PATH" \
WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.01 \
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.01 \
LARCH_TRANSIENT_RETRY_DELAY=0 \
LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
CURSOR_STUB_RESULT_CONTENT=$'### FINDING_1: Cursor phase 2 with Codex absent\n- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt\n- **Severity**: nit\n- **Concern**: codex absent cursor concern\n- **Suggested revision**: fix\n' \
"$AGG" \
    --findings-file "$WS/in.md" \
    --review-tmpdir "$WS" \
    --codex-present false \
    --cursor-present true \
    --mode diff >"$TMP/out-wf-skip.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-wf-skip.env" || fail "codex absent AGGREGATED"
grep -Fq 'REASON=ok' "$TMP/out-wf-skip.env" || fail "codex absent cursor REASON"
grep -Fq 'ALL_OUTPUT_TOOLS=cursor' "$WS/aggregator-dispatch.env" || fail "codex absent final tool"
grep -Eq '^PHASE2_SLOTS=.+aggregator-output-phase2\.txt' "$WS/aggregator-dispatch.env" || fail "codex absent should use phase2 cursor"

echo "=== empty_merge_negative_finding_prose: ### FINDING_ids must not trip preamble signal ==="
cp "$TMP/in3.md" "$TMP/in3-negprose.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=zero_findings_prose_finding_ids \
"$AGG" \
    --findings-file "$TMP/in3-negprose.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-negprose.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-negprose.env" || fail "FINDING_ids prose empty-merge must fail closed"
grep -Fq 'REASON=validation-failed' "$TMP/out-negprose.env" || fail "FINDING_ids prose empty-merge must fail validation"
grep -Fq 'AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring' "$TMP/aggregator-validate.stderr" 2>/dev/null && fail "FINDING_ids prose must not emit preamble_finding_substring"
grep -Fq 'output must include a line whose trimmed text equals' "$TMP/aggregator-validate.stderr" || fail "FINDING_ids prose must emit missing-attestation diagnostic"
cmp -s "$TMP/in3.md" "$TMP/in3-negprose.md" || fail "findings unchanged on FINDING_ids prose validator rejection"

echo "=== merged output must include - **Severity**: line ==="
cp "$TMP/in3.md" "$TMP/in3-sev.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge_severity_important \
"$AGG" \
    --findings-file "$TMP/in3-sev.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-sev.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-sev.env" || fail "severity-important AGGREGATED"
grep -Fq '**Severity**: important' "$TMP/in3-sev.md" || fail "expected important severity in merged findings"

echo "=== merged output missing Severity fails validation ==="
cp "$TMP/in3.md" "$TMP/in3-nosev.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge_missing_severity \
"$AGG" \
    --findings-file "$TMP/in3-nosev.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff >"$TMP/out-nosev.env"
grep -Fq 'AGGREGATED=false' "$TMP/out-nosev.env" || fail "missing-severity AGGREGATED"
grep -Fq 'REASON=validation-failed' "$TMP/out-nosev.env" || fail "missing-severity REASON"
grep -Fq 'missing - **Severity**' "$TMP/aggregator-validate.stderr" || fail "expected severity diagnostic on stderr"

echo "=== input-mode plan accepts merge output without Severity lines ==="
cp "$TMP/in3.md" "$TMP/in3-plan-mode.md"
write_stub_dispatch
AGGREGATE_DISPATCH_SH="$TMP/stub-dispatch.sh" \
AGGREGATE_STUB_MODE=ok \
AGGREGATE_STUB_MERGE_KIND=merge_missing_severity \
"$AGG" \
    --findings-file "$TMP/in3-plan-mode.md" \
    --review-tmpdir "$TMP" \
    --codex-present true \
    --cursor-present true \
    --mode diff \
    --input-mode plan >"$TMP/out-plan-mode.env"
grep -Fq 'AGGREGATED=true' "$TMP/out-plan-mode.env" || fail "plan mode missing-severity merge should aggregate"
grep -Fq 'REASON=ok' "$TMP/out-plan-mode.env" || fail "plan mode REASON ok"

echo "All aggregate-findings harness assertions passed."
