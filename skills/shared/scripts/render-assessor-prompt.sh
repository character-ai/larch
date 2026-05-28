#!/usr/bin/env bash
# render-assessor-prompt.sh — Render cross-model plan-quality assessor prompt body.

set -euo pipefail

PLAN_ORIGINAL=""
PLAN_PREV=""
PLAN_CURRENT=""
FEATURE_FILE=""
OUTPUT=""

usage() {
    echo "Usage: render-assessor-prompt.sh --plan-original PATH --plan-prev PATH --plan-current PATH --feature-file PATH --output PATH" >&2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan-original) PLAN_ORIGINAL="${2:?}"; shift 2 ;;
        --plan-prev) PLAN_PREV="${2:?}"; shift 2 ;;
        --plan-current) PLAN_CURRENT="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --output) OUTPUT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "render-assessor-prompt.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

for req in PLAN_ORIGINAL PLAN_PREV PLAN_CURRENT FEATURE_FILE OUTPUT; do
    val="${!req}"
    [[ -n "$val" ]] || { echo "render-assessor-prompt.sh: all path arguments are required" >&2; usage; exit 2; }
done

for f in "$PLAN_ORIGINAL" "$PLAN_PREV" "$PLAN_CURRENT" "$FEATURE_FILE"; do
    [[ -f "$f" ]] || { echo "render-assessor-prompt.sh: file not readable: $f" >&2; exit 2; }
done

mkdir -p "$(dirname "$OUTPUT")"
tmp=$(mktemp "$(dirname "$OUTPUT")/.assessor-prompt.XXXXXX")

{
    printf '%s\n' 'You are a senior pragmatic software engineer on a plan-quality assessment panel.'
    printf '%s\n' 'Bias against unnecessary complexity: prefer the smallest change that fulfills the refined problem statement.'
    printf '%s\n' 'Compare whether the **current** plan is better, worse, or tied versus the **previous round** plan, using the original anchor for context.'
    printf '%s\n' 'Do NOT modify files. Do NOT commit. Do NOT push.'
    printf '\n'
    printf '%s\n' '## Refined problem statement'
    cat "$FEATURE_FILE"
    printf '\n'
    printf '%s\n' '## Original plan (anchor)'
    printf '%s\n' '```markdown'
    cat "$PLAN_ORIGINAL"
    printf '%s\n' '```'
    printf '\n'
    printf '%s\n' '## Previous round plan'
    printf '%s\n' '```markdown'
    cat "$PLAN_PREV"
    printf '%s\n' '```'
    printf '\n'
    printf '%s\n' '## Current round plan'
    printf '%s\n' '```markdown'
    cat "$PLAN_CURRENT"
    printf '%s\n' '```'
    printf '\n'
    printf '%s\n' '## Required output grammar'
    printf '%s\n' 'Output exactly this structure (no FINDING_N / OOS_N vote lines):'
    printf '%s\n' 'ASSESSMENT: BETTER|WORSE|TIE'
    printf '%s\n' 'REASONING:'
    printf '%s\n' '<free-form paragraphs explaining the verdict>'
    printf '%s\n' 'QUALIFICATIONS:'
    printf '%s\n' '<one line summarizing your basis for the verdict>'
} >"$tmp"

mv -f "$tmp" "$OUTPUT"
exit 0
