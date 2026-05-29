#!/usr/bin/env bash
# Mechanical plan-size thresholds for /design Step 2b.5 (issue #2670).

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"
# shellcheck source=skills/design/scripts/lib-plan-optional-trailers.sh
source "$SCRIPT_DIR/lib-plan-optional-trailers.sh"

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
            exit 3
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" ]]; then
    larch_err "check-plan-size.sh: --design-tmpdir is required"
    usage
    exit 3
fi

larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit 3

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

# Trailer must match emit-plan.sh: exactly `diff_lines: ` (one ASCII space) then digits only.
if ! printf '%s\n' "$last_nonempty" | awk '/^diff_lines: [0-9]+$/ { exit 0 } { exit 1 }'; then
    emit_kv PLAN_SIZE_STATUS missing-diff-lines
    exit 2
fi

diff_lines="${last_nonempty#diff_lines: }"
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

initial_plan_lines=$(( trailer_nr - 1 ))
if [[ "$initial_plan_lines" -lt 0 ]]; then
    initial_plan_lines=0
fi

_metadata_parse=$(parse_plan_optional_metadata "$PLAN_FILE")
metadata_trailer_lines=$(printf '%s\n' "$_metadata_parse" | sed -n '1p')
_diff_added_raw=$(printf '%s\n' "$_metadata_parse" | sed -n '2p')
_diff_deleted_raw=$(printf '%s\n' "$_metadata_parse" | sed -n '3p')
mechanical_churn=$(printf '%s\n' "$_metadata_parse" | sed -n '4p')
diff_added=""
diff_deleted=""
if [[ "$_diff_added_raw" != "-" ]]; then
    if [[ "$_diff_added_raw" == "08" || "$_diff_added_raw" == "09" ]]; then
        :
    else
        diff_added="$_diff_added_raw"
    fi
fi
if [[ "$_diff_deleted_raw" != "-" ]]; then
    if [[ "$_diff_deleted_raw" == "08" || "$_diff_deleted_raw" == "09" ]]; then
        :
    else
        diff_deleted="$_diff_deleted_raw"
    fi
fi
unset _metadata_parse _diff_added_raw _diff_deleted_raw

plan_lines=$(( initial_plan_lines - metadata_trailer_lines ))
if [[ "$plan_lines" -lt 0 ]]; then
    plan_lines=0
fi

hard_plan=0
if (( plan_lines > 800 )); then hard_plan=1; fi

hard_diff_raw=0
diff_basis="diff-lines"
if [[ -n "$diff_added" ]]; then
    if (( 10#$diff_added > 2000 )); then hard_diff_raw=1; fi
    diff_basis="diff-added"
else
    if (( 10#$diff_lines > 1500 )); then hard_diff_raw=1; fi
fi

soft_advisory=0
hard_diff=0
if [[ "$mechanical_churn" == "true" ]]; then
    if [[ "$hard_diff_raw" -eq 1 ]]; then soft_advisory=1; fi
else
    hard_diff="$hard_diff_raw"
fi

hard_trigger=0
if [[ "$hard_plan" -eq 1 || "$hard_diff" -eq 1 ]]; then
    hard_trigger=1
fi

reasons=()
if [[ "$hard_plan" -eq 1 ]]; then
    reasons+=("plan-body-lines")
fi
if [[ "$hard_diff" -eq 1 ]]; then
    reasons+=("$diff_basis")
fi

TRIGGER_REASONS=""
if [[ "${#reasons[@]}" -gt 0 ]]; then
    IFS=,
    TRIGGER_REASONS="${reasons[*]}"
    IFS=$' \t\n'
fi

if [[ "$hard_trigger" -eq 1 ]]; then
    emit_kv HARD_TRIGGER_FIRED true
else
    emit_kv HARD_TRIGGER_FIRED false
fi

emit_kv TRIGGER_REASONS "$TRIGGER_REASONS"
emit_kv PLAN_LINES "$plan_lines"
emit_kv DIFF_LINES "$diff_lines"
emit_kv DIFF_ADDED "$diff_added"
emit_kv DIFF_DELETED "$diff_deleted"
emit_kv MECHANICAL_CHURN "$mechanical_churn"
if [[ "$soft_advisory" -eq 1 ]]; then
    emit_kv SOFT_ADVISORY true
else
    emit_kv SOFT_ADVISORY false
fi
exit 0
