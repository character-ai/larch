#!/usr/bin/env bash
# sleep-seconds.sh — Sleep for a specified number of seconds.
#
# Thin wrapper around `sleep` to avoid direct Bash commands in
# skill SKILL.md files.
#
# Usage:
#   sleep-seconds.sh <seconds>
#
# Arguments:
#   First positional argument — number of seconds to sleep
#
# Exit codes:
#   0 — always

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

if [[ $# -lt 1 ]]; then
    larch_err "Usage: sleep-seconds.sh <seconds>"
    exit 1
fi

sleep "$1"
