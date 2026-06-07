#!/usr/bin/env bash
# design-step3-state.sh — shared Step 3 sentinel mutations for /design.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$SCRIPT_DIR/../../../scripts/lib-design-tmpdir.sh"

usage() {
    printf '%s\n' 'usage: design-step3-state.sh --design-tmpdir DIR (--gate-b-bypass|--direct-review-entry|--direct-review-pause-hygiene|--auto-continuation-entry)' >&2
}

DESIGN_TMPDIR=""
ACTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"
            shift 2
            ;;
        --gate-b-bypass)
            [[ -z "$ACTION" ]] || { usage; exit 2; }
            ACTION="${1#--}"
            shift
            ;;
        --direct-review-entry|--direct-review-pause-hygiene|--auto-continuation-entry)
            [[ -z "$ACTION" ]] || { usage; exit 2; }
            ACTION="${1#--}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

[[ -n "$DESIGN_TMPDIR" && -n "$ACTION" ]] || { usage; exit 2; }
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit 2
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
mkdir -p "$DESIGN_TMPDIR/.completed"

case "$ACTION" in
    gate-b-bypass)
        if [[ -f "$DESIGN_TMPDIR/.completed/step-3.5" ]]; then
            printf '%s\n' 'STEP3_STATE=refused-partial-gate-b-bypass'
            exit 1
        fi
        : >"$DESIGN_TMPDIR/.completed/step-3"
        : >"$DESIGN_TMPDIR/.completed/step-3.5"
        printf '%s\n' 'STEP3_STATE=gate-b-bypass'
        ;;
    direct-review-entry|direct-review-pause-hygiene)
        if [[ ! -f "$DESIGN_TMPDIR/.step3-reentry" ]]; then
            printf '%s\n' 'STEP3_STATE=noop'
            exit 0
        fi
        rm -f "$DESIGN_TMPDIR/.completed/step-3" "$DESIGN_TMPDIR/.completed/step-3.5" "$DESIGN_TMPDIR/.completed/step-3b" "$DESIGN_TMPDIR/.completed/step-4" "$DESIGN_TMPDIR/.completed/step-4b"
        rm -f "$DESIGN_TMPDIR"/.gate-b-postapply-ready-*
        : >"$DESIGN_TMPDIR/.completed/step-1e"
        : >"$DESIGN_TMPDIR/.completed/step-2a"
        : >"$DESIGN_TMPDIR/.completed/step-2a.5"
        : >"$DESIGN_TMPDIR/.completed/step-2b"
        : >"$DESIGN_TMPDIR/.completed/step-2b.5"
        if [[ "$ACTION" == direct-review-entry ]]; then
            rm -f "$DESIGN_TMPDIR/accepted-plan-findings-all.md" "$DESIGN_TMPDIR/.accepted-plan-findings-all.prev.md"
            rm -f "$DESIGN_TMPDIR/oos-accepted-design.md" "$DESIGN_TMPDIR/.oos-accepted-design.prev.md"
            rm -f "$DESIGN_TMPDIR/.step3-reentry"
        fi
        printf '%s\n' "STEP3_STATE=$ACTION"
        ;;
    auto-continuation-entry)
        rm -f "$DESIGN_TMPDIR/.completed/step-3" "$DESIGN_TMPDIR/.completed/step-3.5" "$DESIGN_TMPDIR/.completed/step-3b" "$DESIGN_TMPDIR/.completed/step-4" "$DESIGN_TMPDIR/.completed/step-4b"
        rm -f "$DESIGN_TMPDIR"/.gate-b-postapply-ready-*
        printf '%s\n' 'STEP3_STATE=auto-continuation-entry'
        ;;
esac
