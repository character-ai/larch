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


# Large plan with fresh generated summary uses plan-summary.md instead of synthetic outline.
d2s="$TMPROOT/d2s"
mkdir -p "$d2s"
{
    printf '# SummaryPlan

'
    printf '## Synthetic heading that should be hidden by fresh summary

'
    for _ in $(seq 1 125); do printf 'summary-body
'; done
} >"$d2s/plan.txt"
printf 'Generated drafter summary
' >"$d2s/plan-summary.md"
touch "$d2s/plan.txt"
sleep 1
touch "$d2s/plan-summary.md"
out2s=$("$SUBJECT" --design-tmpdir "$d2s" --variant step3)
printf '%s
' "$out2s" | grep -Fq 'Generated drafter summary' || fail "fresh generated summary should be used"
printf '%s
' "$out2s" | grep -Fq 'Synthetic heading that should be hidden' && fail "fresh summary should replace synthetic outline"

# Large plan with stale or empty summary falls back to synthetic outline.
d2stale="$TMPROOT/d2stale"
mkdir -p "$d2stale"
{
    printf '# StaleSummaryPlan

'
    printf '## Fresh Plan Heading

'
    for _ in $(seq 1 125); do printf 'stale-body
'; done
} >"$d2stale/plan.txt"
printf 'Stale generated summary
' >"$d2stale/plan-summary.md"
touch -t 202001010000 "$d2stale/plan-summary.md"
touch -t 202001010001 "$d2stale/plan.txt"
out2stale=$("$SUBJECT" --design-tmpdir "$d2stale" --variant step3)
printf '%s
' "$out2stale" | grep -Fq '## Fresh Plan Heading' || fail "stale generated summary should fall back to outline"
printf '%s
' "$out2stale" | grep -Fq 'Stale generated summary' && fail "stale summary should not be printed"
: >"$d2stale/plan-summary.md"
touch "$d2stale/plan-summary.md"
out2empty=$("$SUBJECT" --design-tmpdir "$d2stale" --variant step3)
printf '%s
' "$out2empty" | grep -Fq '## Fresh Plan Heading' || fail "empty generated summary should fall back to outline"

# Small plan — full body (under default threshold)
d3="$TMPROOT/d3"
mkdir -p "$d3"
printf '# Small\n\nHello\n\ndiff_lines: 1\n' >"$d3/plan.txt"
printf 'Fresh summary ignored for small plan\n' >"$d3/plan-summary.md"
out3=$("$SUBJECT" --design-tmpdir "$d3" --variant step3)
printf '%s\n' "$out3" | grep -Fq 'Hello' || fail "small plan should include full body"
printf '%s\n' "$out3" | grep -Fq 'very large' && fail "small plan should not print large-plan note"
printf '%s\n' "$out3" | grep -Fq 'Fresh summary ignored for small plan' && fail "small plan should ignore generated summary"

# Step 2b small plan — implementation-plan header and full body.
d_step2b_small="$TMPROOT/d_step2b_small"
mkdir -p "$d_step2b_small"
printf '# Step2bSmall\n\nSmall body\n\ndiff_lines: 1\n' >"$d_step2b_small/plan.txt"
out_step2b_small=$("$SUBJECT" --design-tmpdir "$d_step2b_small" --variant step2b)
printf '%s\n' "$out_step2b_small" | grep -Fq '## Implementation Plan' || fail "step2b small missing implementation-plan header"
printf '%s\n' "$out_step2b_small" | grep -Fq 'Small body' || fail "step2b small should include full body"

# Step 2b large plan with fresh generated summary uses plan-summary.md.
d_step2b_summary="$TMPROOT/d_step2b_summary"
mkdir -p "$d_step2b_summary"
{
    printf '# Step2bSummary\n\n'
    printf '## Step2b heading hidden by summary\n\n'
    for _ in $(seq 1 125); do printf 'step2b-summary-body\n'; done
} >"$d_step2b_summary/plan.txt"
printf 'Generated step2b summary\n' >"$d_step2b_summary/plan-summary.md"
touch "$d_step2b_summary/plan.txt"
sleep 1
touch "$d_step2b_summary/plan-summary.md"
out_step2b_summary=$("$SUBJECT" --design-tmpdir "$d_step2b_summary" --variant step2b)
printf '%s\n' "$out_step2b_summary" | grep -Fq 'Generated step2b summary' || fail "step2b fresh generated summary should be used"
printf '%s\n' "$out_step2b_summary" | grep -Fq 'Step2b heading hidden by summary' && fail "step2b fresh summary should replace synthetic outline"
printf '%s\n' "$out_step2b_summary" | grep -Fq 'See full plan' && fail "step2b large note should not reference See full plan interaction"

# Step 2b large plan without a fresh summary falls back to section outline.
d_step2b_outline="$TMPROOT/d_step2b_outline"
mkdir -p "$d_step2b_outline"
{
    printf '# Step2bOutline\n\n'
    printf '## Step2b Visible Section\n\n'
    for _ in $(seq 1 125); do printf 'step2b-outline-body\n'; done
} >"$d_step2b_outline/plan.txt"
out_step2b_outline=$("$SUBJECT" --design-tmpdir "$d_step2b_outline" --variant step2b)
printf '%s\n' "$out_step2b_outline" | grep -Fq '## Implementation Plan' || fail "step2b outline missing implementation-plan header"
printf '%s\n' "$out_step2b_outline" | grep -Fq '**Section outline:**' || fail "step2b outline mode missing section outline"
printf '%s\n' "$out_step2b_outline" | grep -Fq '## Step2b Visible Section' || fail "step2b outline missing heading"

# step3 is a pure renderer: no sentinel written, always renders
[[ ! -e "$d3/.step3-entry-plan-printed" ]] || fail "step3 pure renderer must not write .step3-entry-plan-printed sentinel"
out3b=$("$SUBJECT" --design-tmpdir "$d3" --variant step3)
printf '%s\n' "$out3b" | grep -Fq '## Plan Candidate for Review' || fail "step3 second call should re-render (pure renderer, no sentinel)"

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

# Disallowed tmpdir: validate before step3 sentinel short-circuit or missing-plan sentinel writes.
d9=$(mktemp -d "$SCRIPT_DIR/emit-design-plan-preview-disallowed.XXXXXX")
trap 'rm -rf "$TMPROOT" "$d9"' EXIT
out9=$("$SUBJECT" --design-tmpdir "$d9" --variant step3)
printf '%s\n' "$out9" | grep -Fq '**⚠ 3: DESIGN_TMPDIR not under allowlist' || fail "step3 should validate allowlist before early exits"
[[ ! -e "$d9/.step3-entry-plan-printed" ]] || fail "step3 should not write sentinel before allowlist validation"
touch "$d9/.step3-entry-plan-printed"
out9b=$("$SUBJECT" --design-tmpdir "$d9" --variant step3)
printf '%s\n' "$out9b" | grep -Fq '**⚠ 3: DESIGN_TMPDIR not under allowlist' || fail "existing sentinel must not bypass allowlist validation"

# Full variant — small plan: header + full body, no summary markers
d_full_small="$TMPROOT/d_full_small"
mkdir -p "$d_full_small"
printf '# FullSmall\n\nHello full body\n\ndiff_lines: 1\n' >"$d_full_small/plan.txt"
out_full_small=$("$SUBJECT" --design-tmpdir "$d_full_small" --variant full)
printf '%s\n' "$out_full_small" | grep -Fq '## Final Design Plan' || fail "full small missing header"
printf '%s\n' "$out_full_small" | grep -Fq 'Hello full body' || fail "full small should include full body"
printf '%s\n' "$out_full_small" | grep -Fq '**Section outline:**' && fail "full small should not print section outline"
printf '%s\n' "$out_full_small" | grep -Fq 'very large' && fail "full small should not print large-plan note"

# Full variant — large plan: full body past summary window, no summary markers
d_full_large="$TMPROOT/d_full_large"
mkdir -p "$d_full_large"
{
    printf '# FullLarge\n\n'
    for _ in $(seq 1 130); do
        printf 'full-body line %s\n' "$_"
    done
} >"$d_full_large/plan.txt"
out_full_large=$("$SUBJECT" --design-tmpdir "$d_full_large" --variant full)
printf '%s\n' "$out_full_large" | grep -Fq '## Final Design Plan' || fail "full large missing header"
printf '%s\n' "$out_full_large" | grep -Fq 'full-body line 125' || fail "full large should include body past summary window"
printf '%s\n' "$out_full_large" | grep -Fq '**Section outline:**' && fail "full large should not print section outline"
printf '%s\n' "$out_full_large" | grep -Fq 'very large' && fail "full large should not print large-plan note"

# Full variant — empty tmpdir: friendly warning, exit 0
if ! out_full_empty=$("$SUBJECT" --design-tmpdir '' --variant full); then
    fail "empty --design-tmpdir should exit 0 for full"
fi
printf '%s\n' "$out_full_empty" | grep -Fq '**⚠ 4b: DESIGN_TMPDIR missing or invalid' || fail "full empty tmpdir should warn"

# Full variant — missing plan: friendly warning, exit 0
d_full_noplan="$TMPROOT/d_full_noplan"
mkdir -p "$d_full_noplan"
out_full_noplan=$("$SUBJECT" --design-tmpdir "$d_full_noplan" --variant full)
printf '%s\n' "$out_full_noplan" | grep -Fq '**⚠ 4b: plan.txt missing or empty' || fail "full missing plan should warn"

# Full variant — disallowed tmpdir: allowlist warning
d_full_bad=$(mktemp -d "$SCRIPT_DIR/emit-design-plan-preview-full-disallowed.XXXXXX")
trap 'rm -rf "$TMPROOT" "$d9" "$d_full_bad"' EXIT
out_full_bad=$("$SUBJECT" --design-tmpdir "$d_full_bad" --variant full)
printf '%s\n' "$out_full_bad" | grep -Fq '**⚠ 4b: DESIGN_TMPDIR not under allowlist' || fail "full should validate allowlist"

echo "PASS: test-emit-design-plan-preview.sh"
