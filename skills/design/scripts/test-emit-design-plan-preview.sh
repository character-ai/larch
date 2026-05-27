#!/usr/bin/env bash
# Regression harness for emit-design-plan-preview.sh (Step 3 + Gate C preview).

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
SUBJECT="$SCRIPT_DIR/emit-design-plan-preview.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-emit-design-plan-preview-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

d="$TMPROOT/d1"
mkdir -p "$d"
{
    printf '# Title\n\n'
    for _ in $(seq 1 130); do
        printf 'body line %s\n' "$_"
    done
} >"$d/plan.txt"

# Large plan, no ##/### outline lines — must fall back to first 30 lines (not abort under pipefail).
out=$("$SUBJECT" --design-tmpdir "$d" --variant step3)
printf '%s\n' "$out" | grep -Fq '## Plan Candidate for Review' || fail "step3 missing header"
printf '%s\n' "$out" | grep -Fq 'body line 28' || fail "empty-outline fallback missing expected line from first 30 lines"
printf '%s\n' "$out" | grep -Fq 'very large' || fail "large-plan note missing"

# Large plan with outline headings
d2="$TMPROOT/d2"
mkdir -p "$d2"
{
    printf '# T2\n\n'
    printf '## Sec A\n\npara\n\n'
    for _ in $(seq 1 125); do
        printf 'x\n'
    done
} >"$d2/plan.txt"
out2=$("$SUBJECT" --design-tmpdir "$d2" --variant step3)
printf '%s\n' "$out2" | grep -Fq '**Section outline:**' || fail "outline mode missing section outline"
printf '%s\n' "$out2" | grep -Fq '## Sec A' || fail "outline missing heading"

# Small plan — full body (under default threshold)
d3="$TMPROOT/d3"
mkdir -p "$d3"
printf '# Small\n\nHello\n\ndiff_lines: 1\n' >"$d3/plan.txt"
out3=$("$SUBJECT" --design-tmpdir "$d3" --variant step3)
printf '%s\n' "$out3" | grep -Fq 'Hello' || fail "small plan should include full body"
printf '%s\n' "$out3" | grep -Fq 'very large' && fail "small plan should not print large-plan note"

# Sentinel: second step3 invocation is a no-op
[[ -f "$d3/.step3-entry-plan-printed" ]] || fail "sentinel not created"
out3b=$("$SUBJECT" --design-tmpdir "$d3" --variant step3)
[[ -z "$(printf '%s' "$out3b" | tr -d '\n')" ]] || fail "second step3 should emit nothing"

# Gate C header path
d4="$TMPROOT/d4"
mkdir -p "$d4"
printf '# G\n\nLine\n' >"$d4/plan.txt"
out4=$("$SUBJECT" --design-tmpdir "$d4" --variant gatec)
printf '%s\n' "$out4" | grep -Fq '## Final Design Plan' || fail "gatec missing final header"

# Gate C large plan: empty-outline fallback + Gate C bold note (mirrors step3 summary path)
d6="$TMPROOT/d6"
mkdir -p "$d6"
{
    printf '# GateLarge\n\n'
    for _ in $(seq 1 130); do
        printf 'gcline %s\n' "$_"
    done
} >"$d6/plan.txt"
out6=$("$SUBJECT" --design-tmpdir "$d6" --variant gatec)
printf '%s\n' "$out6" | grep -Fq '## Final Design Plan' || fail "gatec large missing header"
printf '%s\n' "$out6" | grep -Fq 'gcline 28' || fail "gatec large empty-outline fallback"
printf '%s\n' "$out6" | grep -Fq 'pick "See full plan" on the prompt below if you want it printed in chat before deciding' || fail "gatec large missing See-full-plan-path note"

# Invalid / zero threshold normalization (falls back to 120; 125-line plan still summarizes)
d7="$TMPROOT/d7"
mkdir -p "$d7"
{
    printf '# Tnorm\n\n'
    for _ in $(seq 1 125); do printf 'x\n'; done
} >"$d7/plan.txt"
out7=$(env LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD=abc "$SUBJECT" --design-tmpdir "$d7" --variant step3)
printf '%s\n' "$out7" | grep -Fq 'very large' || fail "non-numeric threshold should fall back to 120"
d7z="$TMPROOT/d7z"
mkdir -p "$d7z"
cp "$d7/plan.txt" "$d7z/plan.txt"
out7z=$(env LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD=0 "$SUBJECT" --design-tmpdir "$d7z" --variant step3)
printf '%s\n' "$out7z" | grep -Fq 'very large' || fail "zero threshold should fall back to 120"

# Gate C honors the same threshold override as step3
d8="$TMPROOT/d8"
mkdir -p "$d8"
{
    printf '# T8\n\n'
    for _ in $(seq 1 15); do printf 'L%s\n' "$_"; done
} >"$d8/plan.txt"
out8=$(
    env LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD=5 "$SUBJECT" --design-tmpdir "$d8" --variant gatec
)
printf '%s\n' "$out8" | grep -Fq '## Final Design Plan' || fail "gatec threshold header"
printf '%s\n' "$out8" | grep -Fq '**Section outline:**' || fail "gatec low threshold should trigger summary"

# Custom threshold via env (numeric path used by emit_plan_body)
d5="$TMPROOT/d5"
mkdir -p "$d5"
{
    printf '# T5\n\n'
    for _ in $(seq 1 15); do printf 'L%s\n' "$_"; done
} >"$d5/plan.txt"
out5=$(
    env LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD=5 "$SUBJECT" --design-tmpdir "$d5" --variant step3
)
printf '%s\n' "$out5" | grep -Fq '**Section outline:**' || fail "low threshold should trigger summary mode"

# Empty --design-tmpdir after flag: friendly step3 path (not expansion-abort from :?)
if ! out_empty=$("$SUBJECT" --design-tmpdir '' --variant step3); then
    fail "empty --design-tmpdir should exit 0 for step3"
fi
printf '%s\n' "$out_empty" | grep -Fq '**⚠ 3: DESIGN_TMPDIR missing or invalid' || fail "empty tmpdir should warn"

echo "PASS: test-emit-design-plan-preview.sh"
