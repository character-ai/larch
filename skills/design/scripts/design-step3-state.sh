#!/usr/bin/env bash
# design-step3-state.sh — shared Step 3 sentinel mutations for /design.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
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
python3 "$SCRIPT_DIR/../../../python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
mkdir -p "$DESIGN_TMPDIR/.completed"

read_review_round_count() {
    local raw=""
    if [[ -s "$DESIGN_TMPDIR/review-round-count.txt" ]]; then
        raw="$(tr -d '[:space:]' <"$DESIGN_TMPDIR/review-round-count.txt" 2>/dev/null || true)"
    fi
    case "$raw" in
        ''|*[!0-9]*) printf '0\n' ;;
        *) printf '%s\n' "$((10#$raw))" ;;
    esac
}

cleanup_settled_step3_loop_state() {
    local max_round="$1" path base n
    case "$max_round" in ''|*[!0-9]*) return 0 ;; esac
    for path in "$DESIGN_TMPDIR"/.step3-round-*.phase "$DESIGN_TMPDIR"/plan-pre-apply-round-*.txt; do
        [[ -e "$path" ]] || continue
        [[ -L "$path" ]] && continue
        base="$(basename "$path")"
        n=""
        case "$base" in
            .step3-round-*.phase)
                n="${base#.step3-round-}"
                n="${n%.phase}"
                ;;
            plan-pre-apply-round-*.txt)
                n="${base#plan-pre-apply-round-}"
                n="${n%.txt}"
                ;;
        esac
        case "$n" in ''|*[!0-9]*) continue ;; esac
        if (( 10#$n <= 10#$max_round )); then
            rm -f "$path"
        fi
    done
}

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
        rm -f "$DESIGN_TMPDIR/.completed/step-3" "$DESIGN_TMPDIR/.completed/step-3.5" "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" "$DESIGN_TMPDIR/.completed/step-3b" "$DESIGN_TMPDIR/.completed/step-4" "$DESIGN_TMPDIR/.completed/step-4b"
        rm -f "$DESIGN_TMPDIR"/.gate-b-postapply-ready-*
        : >"$DESIGN_TMPDIR/.completed/step-1e"
        : >"$DESIGN_TMPDIR/.completed/step-2a"
        : >"$DESIGN_TMPDIR/.completed/step-2b"
        : >"$DESIGN_TMPDIR/.completed/step-2b.5"
        if [[ "$ACTION" == direct-review-entry ]]; then
            cleanup_settled_step3_loop_state "$(read_review_round_count)"
            rm -f "$DESIGN_TMPDIR/accepted-plan-findings-all.md" "$DESIGN_TMPDIR/.accepted-plan-findings-all.prev.md"
            rm -f "$DESIGN_TMPDIR/oos-accepted-design.md" "$DESIGN_TMPDIR/.oos-accepted-design.prev.md"
            rm -f "$DESIGN_TMPDIR/.step3-reentry"
        fi
        printf '%s\n' "STEP3_STATE=$ACTION"
        ;;
    auto-continuation-entry)
        rm -f "$DESIGN_TMPDIR/.completed/step-3" "$DESIGN_TMPDIR/.completed/step-3.5" "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" "$DESIGN_TMPDIR/.completed/step-3b" "$DESIGN_TMPDIR/.completed/step-4" "$DESIGN_TMPDIR/.completed/step-4b"
        cleanup_settled_step3_loop_state "$(read_review_round_count)"
        rm -f "$DESIGN_TMPDIR"/.gate-b-postapply-ready-*
        printf '%s\n' 'STEP3_STATE=auto-continuation-entry'
        ;;
esac
