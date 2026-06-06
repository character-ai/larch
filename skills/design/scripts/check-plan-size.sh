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


_drift_multiple="${LARCH_DESIGN_DRIFT_MULTIPLE:-2}"
case "$_drift_multiple" in
    ''|*[!0-9]*) _drift_multiple=2 ;;
esac
_drift_multiple=$((10#$_drift_multiple))
if (( _drift_multiple <= 0 )); then
    _drift_multiple=2
fi

ratio_token() {
    local current="$1" baseline="$2"
    if (( baseline == 0 )); then
        if (( current > 0 )); then
            printf 'inf'
        else
            printf '1'
        fi
        return 0
    fi
    python3 - "$current" "$baseline" <<'PYR'
import sys
cur = int(sys.argv[1])
base = int(sys.argv[2])
val = cur / base
if val.is_integer():
    print(str(int(val)))
else:
    print(("%.2f" % val).rstrip("0").rstrip("."))
PYR
}

drift_exceeds() {
    local current="$1" baseline="$2" multiple="$3"
    if (( baseline == 0 )); then
        (( current > 0 )) && return 0
        return 1
    fi
    (( current > baseline * multiple ))
}

baseline_plan_lines="$plan_lines"
baseline_diff_lines="$diff_lines"
drift_trigger=false
_drift_baseline="$DESIGN_TMPDIR/drift-baseline.env"
if [[ -f "$_drift_baseline" && ! -L "$_drift_baseline" ]]; then
    _bp=$(awk -F= '$1 == "BASELINE_PLAN_LINES" { print $2; found=1; exit } END { if (!found) print "" }' "$_drift_baseline" 2>/dev/null || true)
    _bd=$(awk -F= '$1 == "BASELINE_DIFF_LINES" { print $2; found=1; exit } END { if (!found) print "" }' "$_drift_baseline" 2>/dev/null || true)
    if [[ "$_bp" == '' || "$_bp" == *[!0-9]* || "$_bd" == '' || "$_bd" == *[!0-9]* ]]; then
        emit_kv WARN "check-plan-size: drift baseline unreadable; proceeding without drift trigger"
    else
        baseline_plan_lines=$((10#$_bp))
        baseline_diff_lines=$((10#$_bd))
    fi
    if [[ "$baseline_plan_lines" != "$plan_lines" || "$baseline_diff_lines" != "$diff_lines" ]] \
        && [[ "$_bp" != '' && "$_bp" != *[!0-9]* && "$_bd" != '' && "$_bd" != *[!0-9]* ]]; then
        if drift_exceeds "$plan_lines" "$baseline_plan_lines" "$_drift_multiple" || drift_exceeds "$diff_lines" "$baseline_diff_lines" "$_drift_multiple"; then
            drift_trigger=true
        fi
    fi
elif [[ -e "$_drift_baseline" ]]; then
    emit_kv WARN "check-plan-size: drift baseline unreadable; proceeding without drift trigger"
else
    _baseline_tmp="${_drift_baseline}.tmp.$$"
    if { printf 'BASELINE_PLAN_LINES=%s\n' "$plan_lines"; printf 'BASELINE_DIFF_LINES=%s\n' "$diff_lines"; } >"$_baseline_tmp" 2>/dev/null && mv -f "$_baseline_tmp" "$_drift_baseline" 2>/dev/null; then
        :
    else
        rm -f "$_baseline_tmp" 2>/dev/null || true
        emit_kv WARN "check-plan-size: could not write drift baseline; proceeding without drift trigger"
    fi
fi

drift_plan_ratio=$(ratio_token "$plan_lines" "$baseline_plan_lines")
drift_diff_ratio=$(ratio_token "$diff_lines" "$baseline_diff_lines")

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

emit_kv DRIFT_TRIGGER_FIRED "$drift_trigger"
emit_kv DRIFT_MULTIPLE "$_drift_multiple"
emit_kv DRIFT_PLAN_RATIO "$drift_plan_ratio"
emit_kv DRIFT_DIFF_RATIO "$drift_diff_ratio"
emit_kv BASELINE_PLAN_LINES "$baseline_plan_lines"
emit_kv BASELINE_DIFF_LINES "$baseline_diff_lines"

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
