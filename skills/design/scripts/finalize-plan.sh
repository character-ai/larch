#!/usr/bin/env bash
# Final mechanical artifact validation for /design plan review.

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

DESIGN_TMPDIR=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
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
            larch_err "finalize-plan.sh: unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$DESIGN_TMPDIR" ]]; then
    larch_err "finalize-plan.sh: --design-tmpdir is required"
    usage
    exit 2
fi

if [[ ! -d "$DESIGN_TMPDIR" ]]; then
    emit_kv FINALIZE_PLAN_STATUS missing-design-tmpdir
    exit 1
fi

for may_be_empty in rejected-findings.md accepted-plan-findings.md oos.md; do
    path="$DESIGN_TMPDIR/$may_be_empty"
    if [[ ! -e "$path" ]]; then
        : > "$path"
    elif [[ ! -f "$path" || -L "$path" ]]; then
        emit_kv FINALIZE_PLAN_STATUS invalid-artifact
        emit_kv FINALIZE_PLAN_ARTIFACT "$may_be_empty"
        exit 1
    fi
done

for required in plan.txt diff-lines.txt voting-tally.md; do
    if [[ ! -s "$DESIGN_TMPDIR/$required" ]]; then
        emit_kv FINALIZE_PLAN_STATUS missing-artifact
        emit_kv FINALIZE_PLAN_ARTIFACT "$required"
        exit 1
    fi
done

emit_kv FINALIZE_PLAN_STATUS ok
