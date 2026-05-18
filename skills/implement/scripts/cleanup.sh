#!/usr/bin/env bash
# cleanup.sh — Step 18 cleanup-tmpdir wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { larch_err "Usage: cleanup.sh --implement-tmpdir PATH"; }

fail_usage() {
    usage
    emit_kv CLEANED false
    emit_kv ERROR "$1"
    exit 2
}

IMPLEMENT_TMPDIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir) [ $# -ge 2 ] || fail_usage "--implement-tmpdir requires a value"; IMPLEMENT_TMPDIR=$2; shift 2 ;;
        --help) usage; exit 0 ;;
        *) fail_usage "unknown option: $1" ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || fail_usage "--implement-tmpdir is required"

if "$PLUGIN_ROOT/scripts/cleanup-tmpdir.sh" --dir "$IMPLEMENT_TMPDIR"; then
    emit_kv CLEANED true
    exit 0
else
    rc=$?
fi

emit_kv CLEANED false
emit_kv ERROR "cleanup-tmpdir failed"
exit "$rc"
