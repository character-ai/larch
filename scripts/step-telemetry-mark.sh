#!/usr/bin/env bash
# step-telemetry-mark.sh — read ledger keys from session-env and emit token/timing marks.
#
# Pure telemetry for /implement step-ENTRY sites. Never fatal: omit -e so sibling
# failures cannot abort the orchestrator; always exit 0.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMPLEMENT_TMPDIR=""
LABEL=""

while [ $# -gt 0 ]; do
    case "$1" in
        --implement-tmpdir)
            [ $# -ge 2 ] || exit 0
            case "$2" in --*) exit 0 ;; esac
            IMPLEMENT_TMPDIR="$2"
            shift 2
            ;;
        --label)
            [ $# -ge 2 ] || exit 0
            LABEL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

[ -n "$IMPLEMENT_TMPDIR" ] || exit 0
[ -d "$IMPLEMENT_TMPDIR" ] || exit 0
[ -n "$LABEL" ] || exit 0

_session_env="${IMPLEMENT_TMPDIR:-}/session-env.sh"
_read="$SCRIPT_DIR/read-session-env-key.sh"

LARCH_TOKEN_SESSION_ID=$("$_read" --file "$_session_env" --key LARCH_TOKEN_SESSION_ID --default "" 2>/dev/null || true)
LARCH_CLAUDE_SOURCE_FILE=$("$_read" --file "$_session_env" --key LARCH_CLAUDE_SOURCE_FILE --default "" 2>/dev/null || true)
LARCH_TIMING_LEDGER=$("$_read" --file "$_session_env" --key LARCH_TIMING_LEDGER --default "" 2>/dev/null || true)

export IMPLEMENT_TMPDIR LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER

"$SCRIPT_DIR/token-ledger.sh" mark "$LABEL" || true
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$SCRIPT_DIR/timing-ledger.sh" mark "$LABEL" || true

exit 0
