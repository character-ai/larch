#!/usr/bin/env bash
# Emit Step 2b implementation-plan preview, Step 3 plan-candidate preview, or
# Gate C final-plan preview, or Gate C full-plan display. See skills/design/SKILL.md.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"

usage() {
    printf '%s\n' \
        'usage: emit-design-plan-preview.sh --design-tmpdir DIR --variant step3|gatec|step2b|full' \
        >&2
}

design_tmpdir=""
design_tmpdir_set=0
variant=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            design_tmpdir="${2-}"
            design_tmpdir_set=1
            shift 2
            ;;
        --variant)
            variant="${2:?--variant requires a value}"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "emit-design-plan-preview.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ "$design_tmpdir_set" -eq 0 || -z "$variant" ]]; then
    printf '%s\n' 'emit-design-plan-preview.sh: --design-tmpdir and --variant are required' >&2
    usage
    exit 2
fi

normalize_summary_threshold() {
    local _raw _t
    _raw="${LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD:-120}"
    case "$_raw" in
        '' | 0 | *[!0-9]*) _t=120 ;;
        0[0-9]*) _t=120 ;;
        *) _t="$_raw" ;;
    esac
    printf '%s' "$((10#${_t}))"
}

plan_summary_is_fresh() {
    local plan_file="$1" summary_file="$2" _plan_mtime _summary_mtime
    [[ -s "$summary_file" && -s "$plan_file" ]] || return 1
    _plan_mtime=$(stat -c '%Y' "$plan_file" 2>/dev/null || stat -f '%m' "$plan_file" 2>/dev/null) || _plan_mtime=""
    _summary_mtime=$(stat -c '%Y' "$summary_file" 2>/dev/null || stat -f '%m' "$summary_file" 2>/dev/null) || _summary_mtime=""
    [[ -n "$_plan_mtime" && -n "$_summary_mtime" ]] || return 1
    [[ "$_summary_mtime" -ge "$_plan_mtime" ]]
}

emit_plan_body() {
    local plan_file="$1"
    local large_note_fmt="$2"
    local _plan_lines _plan_bytes _summary_threshold _outline _summary_file

    _plan_lines=$(wc -l <"$plan_file" | tr -d ' ')
    _plan_bytes=$(wc -c <"$plan_file" | tr -d ' ')
    _summary_threshold=$(normalize_summary_threshold)
    if ((_plan_lines > _summary_threshold)); then
        _summary_file="$(dirname "$plan_file")/plan-summary.md"
        if plan_summary_is_fresh "$plan_file" "$_summary_file"; then
            cat "$_summary_file"
        else
            head -n 1 "$plan_file"
            printf '
**Section outline:**

'
            _outline=$(grep -E '^#{2,3} ' "$plan_file" | head -n 40 || true)
            if [[ -n "$_outline" ]]; then
                printf '%s\n' "$_outline"
            else
                head -n 30 "$plan_file"
            fi
        fi
        # large_note_fmt is controlled here (two %s for line/byte counts only).
        # shellcheck disable=SC2059
        printf "
${large_note_fmt}
" "$_plan_lines" "$_plan_bytes"
    else
        cat "$plan_file"
    fi
    printf '
'
}

# Literal `$DESIGN_TMPDIR` is intentional (operator-facing path hint, not expansion).
# shellcheck disable=SC2016
_large_note_step3='**The plan is very large (%s lines, %s bytes). Only the title and section outline are shown above. The full plan is at $DESIGN_TMPDIR/plan.txt — say "show full plan" to see the body in chat before voting begins.**'
# shellcheck disable=SC2016
_large_note_gatec='**The plan is very large (%s lines, %s bytes). Only the title and section outline are shown above. The full plan is at $DESIGN_TMPDIR/plan.txt — pick "See full plan" on the prompt below if you want it printed in chat before deciding.**'
# shellcheck disable=SC2016
_large_note_step2b='**The plan is very large (%s lines, %s bytes). A generated summary or section outline is shown above. The full plan is at $DESIGN_TMPDIR/plan.txt.**'

case "$variant" in
    step2b)
        if [[ -z "${design_tmpdir:-}" || ! -d "$design_tmpdir" ]]; then
            printf '%s\n' '**⚠ 2b:** DESIGN_TMPDIR missing or invalid; cannot present implementation plan'
            exit 0
        fi
        if ! larch_design_tmpdir_validate "$design_tmpdir"; then
            printf '%s\n' '**⚠ 2b:** DESIGN_TMPDIR not under allowlist; cannot present implementation plan'
            exit 0
        fi
        if [[ ! -s "$design_tmpdir/plan.txt" ]]; then
            printf '%s\n' '**⚠ 2b:** plan.txt missing or empty; cannot present implementation plan'
            exit 0
        fi
        printf '\n## Implementation Plan\n\n'
        emit_plan_body "$design_tmpdir/plan.txt" "$_large_note_step2b"
        ;;
    step3)
        if [[ -z "${design_tmpdir:-}" || ! -d "$design_tmpdir" ]]; then
            printf '%s\n' '**⚠ 3: DESIGN_TMPDIR missing or invalid; cannot present plan candidate for review**'
            exit 0
        fi
        if ! larch_design_tmpdir_validate "$design_tmpdir"; then
            printf '%s\n' '**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**'
            exit 0
        fi
        if [[ ! -s "$design_tmpdir/plan.txt" ]]; then
            printf '%s\n' '**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**'
            exit 0
        fi
        printf '\n## Plan Candidate for Review\n\n'
        emit_plan_body "$design_tmpdir/plan.txt" "$_large_note_step3"
        ;;
    gatec)
        if [[ -z "${design_tmpdir:-}" || ! -d "$design_tmpdir" ]]; then
            printf '%s\n' '**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**'
            exit 0
        fi
        if ! larch_design_tmpdir_validate "$design_tmpdir"; then
            printf '%s\n' '**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**'
            exit 0
        fi
        if [[ ! -s "$design_tmpdir/plan.txt" ]]; then
            printf '%s\n' '**⚠ 4b: plan.txt missing or empty; cannot present final design plan**'
            exit 0
        fi
        printf '\n## Final Design Plan\n\n'
        emit_plan_body "$design_tmpdir/plan.txt" "$_large_note_gatec"
        ;;
    full)
        if [[ -z "${design_tmpdir:-}" || ! -d "$design_tmpdir" ]]; then
            printf '%s\n' '**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**'
            exit 0
        fi
        if ! larch_design_tmpdir_validate "$design_tmpdir"; then
            printf '%s\n' '**⚠ 4b: DESIGN_TMPDIR not under allowlist; cannot present final design plan**'
            exit 0
        fi
        if [[ ! -s "$design_tmpdir/plan.txt" ]]; then
            printf '%s\n' '**⚠ 4b: plan.txt missing or empty; cannot present final design plan**'
            exit 0
        fi
        printf '\n## Final Design Plan\n\n'
        cat "$design_tmpdir/plan.txt"
        printf '\n'
        ;;
    *)
        printf '%s\n' "emit-design-plan-preview.sh: invalid --variant (use step3, gatec, step2b, or full): $variant" >&2
        exit 2
        ;;
esac
