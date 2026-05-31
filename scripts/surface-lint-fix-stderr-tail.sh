#!/usr/bin/env bash
# Parse lint-fix-loop.sh stdout and surface a redacted stderr tail to chat (caller scope).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-failed-agent-stderr-tail.sh"

fix_out=""
if [[ $# -gt 0 ]]; then
    fix_out="$1"
elif [[ ! -t 0 ]]; then
    fix_out=$(cat)
fi

stem=""
stem=$(printf '%s\n' "$fix_out" | awk -F= '/^STDERR_TAIL_PATH=/ { print substr($0, index($0,"=")+1); exit }')
if [[ -z "$stem" ]]; then
    stem=$(printf '%s\n' "$fix_out" | awk -F= '/^CODER_LOG_FILE=/ { print substr($0, index($0,"=")+1); exit }')
fi
[[ -n "$stem" ]] || exit 0
emit_failed_agent_stderr_tail_larch_err "$stem" || true
