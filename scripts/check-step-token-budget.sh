#!/usr/bin/env bash
# check-step-token-budget.sh — Test whether combined vendor tokens spent since
# the last timing-ledger mark exceed a configured cap for the current session.
#
# Usage:
#   check-step-token-budget.sh --cap N [--step NAME]
#
# Stdout (exactly one line):
#   STATUS=cap_hit TOTAL=N CAP=N STEP=NAME
#   STATUS=under_cap TOTAL=N CAP=N STEP=NAME
#
# Requires LARCH_TOKEN_SESSION_ID or IMPLEMENT_TMPDIR in env to locate the
# JSONL ledger.  Fails open: under_cap is returned on any ledger read error
# so a transient failure never hard-blocks a launcher.
#
# Exit: always 0.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

CAP=""
STEP="unknown"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cap)  CAP="${2:?--cap requires a value}"; shift 2 ;;
        --step) STEP="${2:?--step requires a value}"; shift 2 ;;
        *)  echo "check-step-token-budget.sh: unknown flag: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "$CAP" ]]; then
    echo "check-step-token-budget.sh: --cap is required" >&2
    exit 1
fi
case "$CAP" in
    ''|*[!0-9]*) echo "check-step-token-budget.sh: --cap must be a positive integer" >&2; exit 1 ;;
esac
if (( 10#$CAP < 1 )); then
    echo "check-step-token-budget.sh: --cap must be >= 1" >&2
    exit 1
fi

# Pull LARCH_TOKEN_SESSION_ID from IMPLEMENT_TMPDIR if not already set.
if [[ -z "${LARCH_TOKEN_SESSION_ID:-}" && -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    LARCH_TOKEN_SESSION_ID=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    export LARCH_TOKEN_SESSION_ID
fi

# Sum all vendor "total" fields since the last "mark" row in the JSONL ledger.
# Each mark resets the running total so the sum reflects the current step only.
# Fail-open: on any read / parse error TOTAL stays 0 and STATUS=under_cap.
TOTAL=0
TOTAL=$("$PLUGIN_ROOT/scripts/token-ledger.sh" dump 2>/dev/null | \
    awk '
      /^{/ {
        if ($0 ~ /"type"[[:space:]]*:[[:space:]]*"mark"/) {
            total = 0
        } else if ($0 ~ /"type"[[:space:]]*:[[:space:]]*"vendor"/) {
            t = $0
            sub(/.*"total"[[:space:]]*:[[:space:]]*/, "", t)
            sub(/[^0-9].*/, "", t)
            if (t ~ /^[0-9]+$/) total += t + 0
        }
      }
      END { print (total == "" ? 0 : total) }
    ' 2>/dev/null) || TOTAL=0
[[ "$TOTAL" =~ ^[0-9]+$ ]] || TOTAL=0

if (( TOTAL >= 10#$CAP )); then
    emit "STATUS=cap_hit TOTAL=$TOTAL CAP=$CAP STEP=$STEP"
else
    emit "STATUS=under_cap TOTAL=$TOTAL CAP=$CAP STEP=$STEP"
fi
