#!/usr/bin/env bash
# snapshot-plan-round.sh — write-once plan snapshots and round cursor for /design assessor.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

DESIGN_TMPDIR=""
SUBCMD=""
ROUND=""
CURSOR_VALUE=""

usage() {
    larch_err "Usage: snapshot-plan-round.sh write-original|write-after|read-cursor|write-cursor --design-tmpdir DIR [--round N] [--value N]"
}

atomic_copy_plan() {
    local src="$1" dest="$2" prefix="$3"
    local tmp
    tmp=$(mktemp "$DESIGN_TMPDIR/${prefix}.XXXXXX")
    cp -p "$src" "$tmp"
    mv -f "$tmp" "$dest"
}

parse_cursor_file() {
    local file="$1" raw reason="malformed"
    if [[ ! -f "$file" ]]; then
        printf '1'
        return 0
    fi
    IFS= read -r raw <"$file" || raw=""
    case "$raw" in
        ''|*[!0-9]*|0|-*)
            larch_errf '**⚠ snapshot-plan-round: cursor file %s; defaulting to 1**\n' "$reason"
            printf '1'
            ;;
        *)
            printf '%s' "$raw"
            ;;
    esac
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        write-original|write-after|read-cursor|write-cursor)
            SUBCMD="$1"
            shift
            ;;
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --round) ROUND="${2:?}"; shift 2 ;;
        --value) CURSOR_VALUE="${2:?}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) larch_err "snapshot-plan-round.sh: unknown argument: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$SUBCMD" ]] || { usage; exit 2; }
[[ -n "$DESIGN_TMPDIR" ]] || { larch_err "snapshot-plan-round.sh: --design-tmpdir is required"; exit 2; }
larch_design_tmpdir_validate "$DESIGN_TMPDIR" || exit $?
mkdir -p "$DESIGN_TMPDIR"

case "$SUBCMD" in
    write-original)
        src="$DESIGN_TMPDIR/plan.txt"
        dest="$DESIGN_TMPDIR/plan.txt-original"
        [[ -f "$src" ]] || { larch_err "snapshot-plan-round.sh: plan.txt missing"; exit 2; }
        if [[ -e "$dest" ]]; then
            emit "⏩ snapshot-plan-round: original already exists; preserved"
            exit 0
        fi
        atomic_copy_plan "$src" "$dest" ".snapshot-original"
        ;;
    write-after)
        [[ -n "$ROUND" ]] || { larch_err "snapshot-plan-round.sh: write-after requires --round"; exit 2; }
        case "$ROUND" in ''|*[!0-9]*|0) larch_err "snapshot-plan-round.sh: --round must be a positive integer"; exit 2 ;; esac
        ROUND=$((10#$ROUND))
        src="$DESIGN_TMPDIR/plan.txt"
        dest="$DESIGN_TMPDIR/plan-after-round-${ROUND}.txt"
        [[ -f "$src" ]] || { larch_err "snapshot-plan-round.sh: plan.txt missing"; exit 2; }
        if [[ -e "$dest" ]]; then
            emit "⏩ snapshot-plan-round: plan-after-round-${ROUND} already exists; preserved"
            exit 0
        fi
        atomic_copy_plan "$src" "$dest" ".snapshot-after"
        ;;
    read-cursor)
        cursor_file="$DESIGN_TMPDIR/plan-review-round-cursor.txt"
        n=$(parse_cursor_file "$cursor_file")
        emit_kv ROUND_CURSOR "$n"
        ;;
    write-cursor)
        [[ -n "$CURSOR_VALUE" ]] || { larch_err "snapshot-plan-round.sh: write-cursor requires --value"; exit 2; }
        case "$CURSOR_VALUE" in ''|*[!0-9]*|0) larch_err "snapshot-plan-round.sh: --value must be a positive integer"; exit 2 ;; esac
        CURSOR_VALUE=$((10#$CURSOR_VALUE))
        cursor_file="$DESIGN_TMPDIR/plan-review-round-cursor.txt"
        tmp=$(mktemp "$DESIGN_TMPDIR/.cursor.XXXXXX")
        printf '%s\n' "$CURSOR_VALUE" >"$tmp"
        mv -f "$tmp" "$cursor_file"
        ;;
    *)
        usage
        exit 2
        ;;
esac

exit 0
