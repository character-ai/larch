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
EXONERATED="0"
BODY_FILE=""

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage: write-tally.sh --log-root D --skill S --run-id R \
    --phase plan-review|code-review --mode simple|hard \
    [--rounds N] [--accepted N] [--rejected N] [--exonerated N] --body-file PATH

Optional deprecated argv accepted for compatibility: two ASCII hyphens, literal neutral, then N (ignored; not forwarded to the composer).
USAGE
}

fail() {
    larch_err "ERROR=$1"
    exit 2
}

validate_code_review_headers() {
    local body_file="$1"
    command -v python3 >/dev/null 2>&1 || return 5
    python3 -c 'import re, sys' >/dev/null 2>&1 || return 5
    python3 - "$body_file" <<'PYEOF'
import sys
import re

allowed = {
    "# Rejected Findings",
    "## Accepted Findings",
    "## Rejected Code Review Findings",
    "## Voting Tally",
    "# Code Review Voting Tally",
    "## Per-finding vote breakdown",
    "## Reviewer Competition Scoreboard",
}

in_fence = False
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if re.match(r"^# Review Round [0-9]+$", line):
                continue
            if line.startswith("### [Code Review] "):
                continue
            if re.match(r"^### \[rejected\] FINDING_[0-9]+$", line):
                continue
            if re.match(r"^### FINDING_[0-9]+: ", line):
                continue
            if re.match(r"^#{1,6}\s", line) and line in allowed:
                continue
            if re.match(r"^#{1,6}\s", line):
                print(line)
                sys.exit(4)
except Exception as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(3)
sys.exit(0)
PYEOF
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

_dash='-'
_deprecated_neutral_argv="${_dash}${_dash}neutral"

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
        --exonerated) require_value "$1" "${2-}"; EXONERATED="$2"; shift 2 ;;
        "${_deprecated_neutral_argv}")
            require_value "$1" "${2-}"
            require_non_negative_integer "${_deprecated_neutral_argv}" "$2"
            shift 2
            ;;
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
require_non_negative_integer "--exonerated" "$EXONERATED"

[ -x "$COMPOSE_TALLY_RECORD" ] || fail "compose-tally-record.sh not executable: $COMPOSE_TALLY_RECORD"
[ -x "$LARCH_LOG" ] || fail "larch-log.sh not executable: $LARCH_LOG"
[ -f "$BODY_FILE" ] || fail "body file not found: $BODY_FILE"
[ ! -L "$BODY_FILE" ] || fail "body file must not be a symlink: $BODY_FILE"

if [ "$PHASE" = "code-review" ]; then
    set +e
    validation_out="$(validate_code_review_headers "$BODY_FILE" 2>&1)"
    validation_rc=$?
    set -e
    case "$validation_rc" in
        0) ;;
        3) fail "code-review body header validation failed: ${validation_out:-python3 validation error}" ;;
        4) fail "unrecognized section header in code-review body: $validation_out" ;;
        5) fail "python3 is required for --phase code-review header validation" ;;
        *) fail "code-review body header validation failed" ;;
    esac
fi

RECORD_FILE="$(mktemp "${TMPDIR:-/tmp}/write-tally-record.XXXXXX")" || fail "cannot create tally temp file"
trap 'rm -f "${RECORD_FILE:-}"' EXIT

if ! "$COMPOSE_TALLY_RECORD" \
    --phase "$PHASE" \
    --mode "$MODE" \
    --rounds "$ROUNDS" \
    --accepted "$ACCEPTED" \
    --rejected "$REJECTED" \
    --exonerated "$EXONERATED" \
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

printf '%s\n' "$WRITER_OUT" | while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    case "$line" in
        [A-Za-z_][A-Za-z0-9_]*=*) emit_kv "${line%%=*}" "${line#*=}" ;;
        *) emit "$line" ;;
    esac
done

exit "$WRITER_RC"
