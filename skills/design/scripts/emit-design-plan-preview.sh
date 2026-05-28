#!/usr/bin/env bash
# Emit Step 3 plan-candidate preview or Gate C final-plan preview (shared
# large-plan summary logic). See skills/design/SKILL.md Step 3 / Step 4b.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"

usage() {
    printf '%s\n' \
        'usage: emit-design-plan-preview.sh --design-tmpdir DIR --variant step3|gatec' \
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

emit_plan_body() {
    local plan_file="$1"
    local large_note_fmt="$2"
    local _plan_lines _plan_bytes _summary_threshold _outline

    _plan_lines=$(wc -l <"$plan_file" | tr -d ' ')
    _plan_bytes=$(wc -c <"$plan_file" | tr -d ' ')
    _summary_threshold=$(normalize_summary_threshold)
    if ((_plan_lines > _summary_threshold)); then
        head -n 1 "$plan_file"
        printf '\n**Section outline:**\n\n'
        _outline=$(grep -E '^#{2,3} ' "$plan_file" | head -n 40 || true)
        if [[ -n "$_outline" ]]; then
            printf '%s\n' "$_outline"
        else
            head -n 30 "$plan_file"
        fi
        # large_note_fmt is controlled here (two %s for line/byte counts only).
        # shellcheck disable=SC2059
        printf "\n${large_note_fmt}\n" "$_plan_lines" "$_plan_bytes"
    else
        cat "$plan_file"
    fi
    printf '\n'
}

# Literal `$DESIGN_TMPDIR` is intentional (operator-facing path hint, not expansion).
# shellcheck disable=SC2016
_large_note_step3='**The plan is very large (%s lines, %s bytes). Only the title and section outline are shown above. The full plan is at $DESIGN_TMPDIR/plan.txt — say "show full plan" to see the body in chat before voting begins.**'
# shellcheck disable=SC2016
_large_note_gatec='**The plan is very large (%s lines, %s bytes). Only the title and section outline are shown above. The full plan is at $DESIGN_TMPDIR/plan.txt — pick "See full plan" on the prompt below if you want it printed in chat before deciding.**'

case "$variant" in
    step3)
        if [[ -z "${design_tmpdir:-}" || ! -d "$design_tmpdir" ]]; then
            printf '%s\n' '**⚠ 3: DESIGN_TMPDIR missing or invalid; cannot present plan candidate for review**'
            exit 0
        fi
        if ! larch_design_tmpdir_validate "$design_tmpdir"; then
            printf '%s\n' '**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**'
            exit 0
        fi
        if [[ -e "$design_tmpdir/.step3-entry-plan-printed" ]]; then
            exit 0
        fi
        if [[ ! -s "$design_tmpdir/plan.txt" ]]; then
            printf '%s\n' '**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**'
            touch "$design_tmpdir/.step3-entry-plan-printed" || true
            exit 0
        fi
        printf '\n## Plan Candidate for Review\n\n'
        emit_plan_body "$design_tmpdir/plan.txt" "$_large_note_step3"
        touch "$design_tmpdir/.step3-entry-plan-printed" || true
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
    *)
        printf '%s\n' "emit-design-plan-preview.sh: invalid --variant (use step3 or gatec): $variant" >&2
        exit 2
        ;;
esac
