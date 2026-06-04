#!/usr/bin/env bash
# restore-finalize-state.sh - rebuild finalize-state.sh from ship-pr-state.sh.

set -euo pipefail
LC_ALL=C
export LC_ALL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPLEMENT_TMPDIR=""

usage() {
    cat >&2 <<'USAGE'
Usage:
  restore-finalize-state.sh --implement-tmpdir PATH
USAGE
}

die_usage() {
    echo "restore-finalize-state.sh: $1" >&2
    usage
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || die_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) die_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir is required"
[ -d "$IMPLEMENT_TMPDIR" ] || die_usage "--implement-tmpdir must exist"

STATE_FILE="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
FINALIZE_FILE="$IMPLEMENT_TMPDIR/finalize-state.sh"
BAIL_REASON_FILE="$IMPLEMENT_TMPDIR/final-bail-reason.txt"

if [ ! -f "$STATE_FILE" ]; then
    echo "restore-finalize-state.sh: warning: missing ship-pr state file: $STATE_FILE" >&2
    exit 1
fi

# shellcheck source=scripts/lib-finalize-state-keys.sh
source "$SCRIPT_DIR/lib-finalize-state-keys.sh" || { echo "restore-finalize-state.sh: failed to source lib-finalize-state-keys.sh" >&2; exit 1; }
[ "${LARCH_LIB_FINALIZE_STATE_KEYS_LOADED:-}" = "1" ] || { echo "restore-finalize-state.sh: lib-finalize-state-keys.sh sourced but sentinel missing" >&2; exit 1; }

read_state() {
    local key=$1 default=${2-}
    awk -F= -v k="$key" -v d="$default" '
        $1 == k {
            print substr($0, index($0, "=") + 1)
            found = 1
            exit
        }
        END {
            if (!found) print d
        }
    ' "$STATE_FILE"
}

read_finalize() {
    local key=$1 default=${2-}
    [ -f "$FINALIZE_FILE" ] || { printf '%s\n' "$default"; return; }
    awk -F= -v k="$key" -v d="$default" '
        $1 == k {
            print substr($0, index($0, "=") + 1)
            found = 1
            exit
        }
        END {
            if (!found) print d
        }
    ' "$FINALIZE_FILE"
}

write_finalize_state() {
    local tmp key default
    tmp="$FINALIZE_FILE.tmp.$$"
    {
        for key in "${LARCH_FINALIZE_STATE_KEYS[@]}"; do
            default=$(larch_finalize_state_default "$key")
            value=$(read_state "$key" "")
            if [ -z "$value" ]; then
                value=$(read_finalize "$key" "$default")
            fi
            printf '%s=%s\n' "$key" "$value"
        done
    } > "$tmp" && mv "$tmp" "$FINALIZE_FILE"
    printf '%s' "$(read_state BAIL_REASON)" > "$BAIL_REASON_FILE"
    _rid=$(read_state RUN_ID)
    if [ -s "$BAIL_REASON_FILE" ] && [ -n "$_rid" ]; then
        "$SCRIPT_DIR/larch-log.sh" write \
            --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
            --skill implement \
            --run-id "$_rid" \
            --batch final-bail-reason \
            --input-file "$BAIL_REASON_FILE" >/dev/null 2>&1 || true
    fi
}

write_finalize_state
