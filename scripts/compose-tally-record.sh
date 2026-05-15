#!/usr/bin/env bash
# compose-tally-record.sh — wrap tally prose in a canonical JSON record.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3

PHASE=""
MODE=""
ROUNDS="0"
ACCEPTED="0"
REJECTED="0"
BODY_FILE=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: compose-tally-record.sh --phase plan-review|code-review --mode simple|hard \
    [--rounds N] [--accepted N] [--rejected N] --body-file PATH
USAGE
}

fail() {
    larch_err "ERROR=$1"
    exit 2
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
        --phase) PHASE="${2:?--phase requires a value}"; shift 2 ;;
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --rounds) ROUNDS="${2:?--rounds requires a value}"; shift 2 ;;
        --accepted) ACCEPTED="${2:?--accepted requires a value}"; shift 2 ;;
        --rejected) REJECTED="${2:?--rejected requires a value}"; shift 2 ;;
        --body-file) BODY_FILE="${2:?--body-file requires a value}"; shift 2 ;;
        *) usage; fail "unknown flag: $1" ;;
    esac
done

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

command -v jq >/dev/null 2>&1 || fail "jq is required"
[ -f "$BODY_FILE" ] || fail "body file not found: $BODY_FILE"
[ ! -L "$BODY_FILE" ] || fail "body file must not be a symlink: $BODY_FILE"

jq -cn \
    --arg phase "$PHASE" \
    --arg batch "$BATCH" \
    --arg mode "$MODE" \
    --argjson rounds "$ROUNDS" \
    --argjson accepted_count "$ACCEPTED" \
    --argjson rejected_count "$REJECTED" \
    --rawfile body "$BODY_FILE" \
    '{
        schema_version: 1,
        phase: $phase,
        batch: $batch,
        mode: $mode,
        rounds: $rounds,
        accepted_count: $accepted_count,
        rejected_count: $rejected_count,
        body: $body
    }'
