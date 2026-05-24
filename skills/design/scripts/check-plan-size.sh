#!/usr/bin/env bash
# Mechanical plan-size thresholds for /design Step 2b.5 (issue #2670).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

DESIGN_TMPDIR=""
PLAN_FILE=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
usage: check-plan-size.sh --design-tmpdir DIR [--plan-file PATH]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        --plan-file)
            PLAN_FILE="${2:?--plan-file requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            larch_err "check-plan-size.sh: unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" ]]; then
    larch_err "check-plan-size.sh: --design-tmpdir is required"
    usage
    exit 2
fi

if [[ -z "$PLAN_FILE" ]]; then
    PLAN_FILE="$DESIGN_TMPDIR/plan.txt"
fi

if [[ ! -f "$PLAN_FILE" ]]; then
    emit_kv PLAN_SIZE_STATUS missing-plan
    exit 2
fi

last_nonempty=$(awk 'NF { line=$0 } END { print line }' "$PLAN_FILE")
if [[ -z "$last_nonempty" ]]; then
    emit_kv PLAN_SIZE_STATUS missing-diff-lines
    exit 2
fi

if ! printf '%s\n' "$last_nonempty" | awk '/^diff_lines:[[:space:]]+[0-9]+$/ { exit 0 } { exit 1 }'; then
    emit_kv PLAN_SIZE_STATUS missing-diff-lines
    exit 2
fi

diff_lines=$(printf '%s\n' "$last_nonempty" | awk -F':[[:space:]]*' '/^diff_lines:/ { print $2; exit }')
case "$diff_lines" in
    ''|*[!0-9]*)
        emit_kv PLAN_SIZE_STATUS missing-diff-lines
        exit 2
        ;;
esac

trailer_nr=$(awk 'NF { nr=NR } END { print nr+0 }' "$PLAN_FILE")
if [[ -z "$trailer_nr" || "$trailer_nr" -eq 0 ]]; then
    emit_kv PLAN_SIZE_STATUS missing-diff-lines
    exit 2
fi

plan_lines=$(( trailer_nr - 1 ))
if [[ "$plan_lines" -lt 0 ]]; then
    plan_lines=0
fi

FILES_COUNT=$(grep -cE '^###[[:space:]]*(NEW|UPDATED|REWRITTEN)[[:space:]]*:' "$PLAN_FILE" || true)

soft_plan=0
hard_plan=0
if [[ "$plan_lines" -gt 250 ]]; then soft_plan=1; fi
if [[ "$plan_lines" -gt 800 ]]; then hard_plan=1; fi

soft_diff=0
hard_diff=0
if [[ "$diff_lines" -gt 600 ]]; then soft_diff=1; fi
if [[ "$diff_lines" -gt 1500 ]]; then hard_diff=1; fi

soft_files=0
if [[ "$FILES_COUNT" -gt 8 ]]; then soft_files=1; fi

hard_trigger=0
if [[ "$hard_plan" -eq 1 || "$hard_diff" -eq 1 ]]; then
    hard_trigger=1
fi

soft_trigger=0
if [[ "$hard_trigger" -eq 0 ]]; then
    if [[ "$soft_plan" -eq 1 || "$soft_diff" -eq 1 || "$soft_files" -eq 1 ]]; then
        soft_trigger=1
    fi
fi

reasons=()
if [[ "$soft_plan" -eq 1 || "$hard_plan" -eq 1 ]]; then
    reasons+=("plan-body-lines")
fi
if [[ "$soft_diff" -eq 1 || "$hard_diff" -eq 1 ]]; then
    reasons+=("diff-lines")
fi
if [[ "$soft_files" -eq 1 ]]; then
    reasons+=("files-count")
fi

TRIGGER_REASONS=""
if [[ "${#reasons[@]}" -gt 0 ]]; then
    IFS=,
    TRIGGER_REASONS="${reasons[*]}"
    IFS=$' \t\n'
fi

if [[ "$hard_trigger" -eq 1 ]]; then
    emit_kv HARD_TRIGGER_FIRED true
    emit_kv SOFT_TRIGGER_FIRED false
else
    emit_kv HARD_TRIGGER_FIRED false
    if [[ "$soft_trigger" -eq 1 ]]; then
        emit_kv SOFT_TRIGGER_FIRED true
    else
        emit_kv SOFT_TRIGGER_FIRED false
    fi
fi

emit_kv TRIGGER_REASONS "$TRIGGER_REASONS"
emit_kv PLAN_LINES "$plan_lines"
emit_kv DIFF_LINES "$diff_lines"
emit_kv FILES_COUNT "$FILES_COUNT"
exit 0
