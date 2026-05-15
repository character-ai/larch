#!/usr/bin/env bash
# detect-wholesale-rejection.sh — Detect all-findings-rejected early termination.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() { echo "Usage: detect-wholesale-rejection.sh --accepted-count N" >&2; }

ACCEPTED_COUNT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --accepted-count) ACCEPTED_COUNT="${2:?--accepted-count requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "detect-wholesale-rejection.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

case "$ACCEPTED_COUNT" in ''|*[!0-9]*) echo "detect-wholesale-rejection.sh: --accepted-count must be a non-negative integer" >&2; exit 2 ;; esac
if [[ "$ACCEPTED_COUNT" -eq 0 ]]; then
    emit_kv TERMINATE_EARLY true
else
    emit_kv TERMINATE_EARLY false
fi
