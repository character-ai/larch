#!/usr/bin/env bash
# write-tally.sh — atomically compose and write an implement tally log batch.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3

COMPOSE_TALLY_RECORD="${LARCH_WRITE_TALLY_COMPOSER:-$SCRIPT_DIR/compose-tally-record.sh}"
LARCH_LOG="${LARCH_WRITE_TALLY_LOGGER:-$SCRIPT_DIR/larch-log.sh}"

LOG_ROOT=""
SKILL=""
RUN_ID=""
PHASE=""
MODE=""
ROUNDS="0"
ACCEPTED="0"
REJECTED="0"
BODY_FILE=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: write-tally.sh --log-root D --skill S --run-id R \
    --phase plan-review|code-review --mode simple|hard \
    [--rounds N] [--accepted N] [--rejected N] --body-file PATH
USAGE
}

fail() {
    larch_err "ERROR=$1"
    exit 2
}

require_value() {
    local flag="$1"
    local value="${2-}"
    [ -n "$value" ] || fail "$flag requires a value"
}

require_non_negative_integer() {
    local name="$1"
    local value="$2"
    case "$value" in
        ""|*[!0-9]*) fail "$name must be a non-negative integer: $value" ;;
    esac
}

while [ $# -gt 0 ]; do
    case "$1" in
        --log-root) require_value "$1" "${2-}"; LOG_ROOT="$2"; shift 2 ;;
        --skill) require_value "$1" "${2-}"; SKILL="$2"; shift 2 ;;
        --run-id) require_value "$1" "${2-}"; RUN_ID="$2"; shift 2 ;;
        --phase) require_value "$1" "${2-}"; PHASE="$2"; shift 2 ;;
        --mode) require_value "$1" "${2-}"; MODE="$2"; shift 2 ;;
        --rounds) require_value "$1" "${2-}"; ROUNDS="$2"; shift 2 ;;
        --accepted) require_value "$1" "${2-}"; ACCEPTED="$2"; shift 2 ;;
        --rejected) require_value "$1" "${2-}"; REJECTED="$2"; shift 2 ;;
        --body-file) require_value "$1" "${2-}"; BODY_FILE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; fail "unknown flag: $1" ;;
    esac
done

[ -n "$LOG_ROOT" ] || { usage; fail "--log-root is required"; }
[ -n "$SKILL" ] || { usage; fail "--skill is required"; }
[ -n "$RUN_ID" ] || { usage; fail "--run-id is required"; }
[ -n "$PHASE" ] || { usage; fail "--phase is required"; }
[ -n "$MODE" ] || { usage; fail "--mode is required"; }
[ -n "$BODY_FILE" ] || { usage; fail "--body-file is required"; }

case "$PHASE" in
    plan-review) BATCH="plan-review-tally" ;;
    code-review) BATCH="code-review-tally" ;;
    *) fail "--phase must be plan-review or code-review: $PHASE" ;;
esac

case "$MODE" in
    simple|hard) ;;
    *) fail "--mode must be simple or hard: $MODE" ;;
esac

require_non_negative_integer "--rounds" "$ROUNDS"
require_non_negative_integer "--accepted" "$ACCEPTED"
require_non_negative_integer "--rejected" "$REJECTED"

[ -x "$COMPOSE_TALLY_RECORD" ] || fail "compose-tally-record.sh not executable: $COMPOSE_TALLY_RECORD"
[ -x "$LARCH_LOG" ] || fail "larch-log.sh not executable: $LARCH_LOG"
[ -f "$BODY_FILE" ] || fail "body file not found: $BODY_FILE"
[ ! -L "$BODY_FILE" ] || fail "body file must not be a symlink: $BODY_FILE"

RECORD_FILE="$(mktemp "${TMPDIR:-/tmp}/write-tally-record.XXXXXX")" || fail "cannot create tally temp file"
trap 'rm -f "${RECORD_FILE:-}"' EXIT

if ! "$COMPOSE_TALLY_RECORD" \
    --phase "$PHASE" \
    --mode "$MODE" \
    --rounds "$ROUNDS" \
    --accepted "$ACCEPTED" \
    --rejected "$REJECTED" \
    --body-file "$BODY_FILE" > "$RECORD_FILE"; then
    emit_kv FAILED true
    emit_kv ERROR "compose-tally-record.sh failed"
    exit 2
fi

set +e
WRITER_OUT="$("$LARCH_LOG" write \
    --log-root "$LOG_ROOT" \
    --skill "$SKILL" \
    --run-id "$RUN_ID" \
    --batch "$BATCH" \
    --input-file "$RECORD_FILE")"
WRITER_RC=$?
set -e

while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    case "$line" in
        [A-Za-z_][A-Za-z0-9_]*=*) emit_kv "${line%%=*}" "${line#*=}" ;;
        *) emit "$line" ;;
    esac
done <<EOF
$WRITER_OUT
EOF

exit "$WRITER_RC"
