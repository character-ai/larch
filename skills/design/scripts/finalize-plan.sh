#!/usr/bin/env bash
# Final mechanical artifact validation for /design plan review.

set -euo pipefail

DESIGN_TMPDIR=""

usage() {
    cat >&2 <<'USAGE'
usage: finalize-plan.sh --design-tmpdir DIR
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "finalize-plan.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" ]]; then
    echo "finalize-plan.sh: --design-tmpdir is required" >&2
    usage
    exit 2
fi

if [[ ! -d "$DESIGN_TMPDIR" ]]; then
    echo "FINALIZE_PLAN_STATUS=missing-design-tmpdir"
    exit 1
fi

for may_be_empty in rejected-findings.md accepted-plan-findings.md oos.md; do
    path="$DESIGN_TMPDIR/$may_be_empty"
    if [[ ! -e "$path" ]]; then
        : > "$path"
    elif [[ ! -f "$path" || -L "$path" ]]; then
        printf 'FINALIZE_PLAN_STATUS=invalid-artifact\n'
        printf 'FINALIZE_PLAN_ARTIFACT=%s\n' "$may_be_empty"
        exit 1
    fi
done

for required in plan.txt diff-lines.txt voting-tally.md; do
    if [[ ! -s "$DESIGN_TMPDIR/$required" ]]; then
        printf 'FINALIZE_PLAN_STATUS=missing-artifact\n'
        printf 'FINALIZE_PLAN_ARTIFACT=%s\n' "$required"
        exit 1
    fi
done

printf '%s\n' 'FINALIZE_PLAN_STATUS=ok'
