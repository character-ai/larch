#!/usr/bin/env bash
# Standalone phantom untracked probe + warn helper for /implement.
# See scripts/phantom-probe-with-warn.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-phantom-probe.sh
source "$SCRIPT_DIR/lib-phantom-probe.sh"

usage() {
    printf 'usage: %s --step <step-token>\n' "$(basename "$0")" >&2
    exit 2
}

step_token=""
while [ $# -gt 0 ]; do
    case "$1" in
        --step)
            [ $# -ge 2 ] || usage
            step_token="$2"
            shift 2
            ;;
        *) usage ;;
    esac
done

[ -n "$step_token" ] || usage

emit_breadcrumb --category=progress "→ phantom-probe: ${step_token}"
phantom_probe_with_warn "$step_token"
exit 0
