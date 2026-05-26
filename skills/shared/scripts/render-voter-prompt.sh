#!/usr/bin/env bash
# render-voter-prompt.sh — Emit the full external voter prompt body to stdout.
#
# IMPORTANT: This script does NOT call larch_quiet_init (or source lib-quiet.sh).
# Stdout is the prompt payload; lib-quiet redirects stdout after init and would
# silently empty the rendered prompt when this helper is invoked from quiet-aware parents.

set -euo pipefail

CORRECTNESS_ENUM='true|partially-true|false-positive|uncertain'
SEVERITY_ENUM='blocker|major|minor|nit|uncertain'
QUALITY_ENUM='excellent|good|adequate|weak|no-fix|uncertain'
UNCERTAIN_ENUM='true|false'

usage() {
    echo "Usage: render-voter-prompt.sh --ballot-file PATH --panel-role STRING --id-grammar finding-oos|finding-only --verification-context plan|diff-plan|code" >&2
}

BALLOT_FILE=""
PANEL_ROLE=""
ID_GRAMMAR=""
VERIFICATION_CONTEXT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?}"; shift 2 ;;
        --panel-role) PANEL_ROLE="${2:?}"; shift 2 ;;
        --id-grammar) ID_GRAMMAR="${2:?}"; shift 2 ;;
        --verification-context) VERIFICATION_CONTEXT="${2:?}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "render-voter-prompt.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" ]] || { echo "render-voter-prompt.sh: --ballot-file is required" >&2; usage; exit 2; }
[[ -n "$PANEL_ROLE" ]] || { echo "render-voter-prompt.sh: --panel-role is required" >&2; usage; exit 2; }
[[ -n "$ID_GRAMMAR" ]] || { echo "render-voter-prompt.sh: --id-grammar is required" >&2; usage; exit 2; }
[[ -n "$VERIFICATION_CONTEXT" ]] || { echo "render-voter-prompt.sh: --verification-context is required" >&2; usage; exit 2; }

case "$ID_GRAMMAR" in
    finding-oos|finding-only) ;;
    *) echo "render-voter-prompt.sh: --id-grammar must be finding-oos or finding-only" >&2; usage; exit 2 ;;
esac

case "$VERIFICATION_CONTEXT" in
    plan|diff-plan|code) ;;
    *) echo "render-voter-prompt.sh: --verification-context must be plan, diff-plan, or code" >&2; usage; exit 2 ;;
esac

printf 'You are a %s.\n' "$PANEL_ROLE"
printf '%s\n' 'Vote EXONERATE rather than YES when the concern is legitimate but the proposed change introduces more complexity than it warrants.'
printf '%s\n' 'When in doubt between YES and EXONERATE, prefer EXONERATE.'
printf '%s\n' 'Do NOT vote NO solely because you dislike or distrust the proposed fix — fix proposals are informational; the coder decides the exact change. Vote NO only when the stated problem is not real or not worth raising.'

case "$ID_GRAMMAR" in
    finding-only)
        printf '%s\n' "For items prefixed with \`[OUT_OF_SCOPE]\`: vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy."
        ;;
    finding-oos)
        printf '%s\n' "For \`OOS_N:\` items (or items prefixed with \`[OUT_OF_SCOPE]\` in code review): vote based on whether the **problem described** is real, concrete, and worth filing as a GitHub issue. Treat any suggested remedy in the item body as *informational only* — do not vote NO because you disagree with the proposed fix. The future implementer of the OOS issue chooses the actual remedy."
        ;;
esac

printf '%s\n' 'Do NOT modify files. Do NOT commit. Do NOT push.'
printf '\n'
printf 'Read the ballot from this path: %s\n' "$BALLOT_FILE"

case "$VERIFICATION_CONTEXT" in
    plan)
        printf '\n%s\n' '**Verify silently** — do not produce narrative output, reasoning explanations, or status updates before, between, or after the vote lines. You may read the ballot file and silently inspect the plan or referenced repo files for verification, but do not invoke planning/status tools.'
        ;;
    diff-plan|code)
        printf '\n%s\n' 'Use the ballot path and any provided diff/plan context files to verify the ballot claims before voting.'
        printf '%s\n' '**Verify silently** — do not produce narrative output, reasoning explanations, or status updates before, between, or after the vote lines. You may read the ballot file and any provided diff/plan context files for verification, but do not invoke planning/status tools or any other tools beyond those file reads.'
        ;;
esac

if [[ "$ID_GRAMMAR" == "finding-oos" ]]; then
    printf '\n%s\n' 'For each ballot item output exactly one line using the same ID from the ballot:'
    printf '%s\n' "Rate each item on four axes: CORRECTNESS is whether the claim is accurate, SEVERITY is the impact if left unfixed, QUALITY is how actionable the suggested fix is, and UNCERTAIN marks low confidence. Use lowercase axis values only. Axis tokens must precede any optional \`-- reason\` rationale; the parser ignores axis-looking tokens after \`-- \`."
    printf '  FINDING_N: YES CORRECTNESS=<%s> SEVERITY=<%s> QUALITY=<%s> UNCERTAIN=<%s>\n' "$CORRECTNESS_ENUM" "$SEVERITY_ENUM" "$QUALITY_ENUM" "$UNCERTAIN_ENUM"
    printf '%s\n' '  FINDING_N: NO CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason'
    printf '%s\n' '  FINDING_N: EXONERATE CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason'
    printf '  OOS_N: YES CORRECTNESS=<%s> SEVERITY=<%s> QUALITY=<%s> UNCERTAIN=<%s>\n' "$CORRECTNESS_ENUM" "$SEVERITY_ENUM" "$QUALITY_ENUM" "$UNCERTAIN_ENUM"
    printf '%s\n' '  OOS_N: NO CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason'
    printf '%s\n' '  OOS_N: EXONERATE CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason'
else
    printf '\n%s\n' 'For every ballot item, output exactly one line using the same FINDING_N: id from the ballot heading:'
    printf '%s\n' "Rate each item on four axes: CORRECTNESS is whether the claim is accurate, SEVERITY is the impact if left unfixed, QUALITY is how actionable the suggested fix is, and UNCERTAIN marks low confidence. Use lowercase axis values only. Axis tokens must precede any optional \`-- reason\` rationale; the parser ignores axis-looking tokens after \`-- \`."
    printf '  FINDING_N: YES CORRECTNESS=<%s> SEVERITY=<%s> QUALITY=<%s> UNCERTAIN=<%s>\n' "$CORRECTNESS_ENUM" "$SEVERITY_ENUM" "$QUALITY_ENUM" "$UNCERTAIN_ENUM"
    printf '%s\n' '  FINDING_N: NO CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason'
    printf '%s\n' '  FINDING_N: EXONERATE CORRECTNESS=<...> SEVERITY=<...> QUALITY=<...> UNCERTAIN=<...> -- one-line reason'
fi

printf '%s\n' 'You must vote on every item. Do NOT skip any.'

if [[ "$ID_GRAMMAR" == "finding-oos" ]]; then
    printf '%s\n' '**Output ONLY vote lines.** Lines that do not start with the exact ballot ID from the ballot heading (FINDING_N: or OOS_N:) followed by YES, NO, or EXONERATE are silently ignored.'
else
    printf '%s\n' '**Output ONLY vote lines.** Lines that do not start with FINDING_N: followed by YES, NO, or EXONERATE are silently ignored. Use the exact ID from the ballot heading.'
fi
