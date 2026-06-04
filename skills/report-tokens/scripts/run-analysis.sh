#!/usr/bin/env bash
# run-analysis.sh - Thin wrapper for the Python /report-tokens analyzer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'EOF'
Usage: run-analysis.sh --skill <design|implement> [--no-issue] [--no-plot]

Flags:
  --skill <name>           Required. Which skill's larch-logs to scan (design or implement).
  --no-issue               Skip posting the analysis report GitHub issue.
  --no-plot                Skip plot generation (text analysis still printed).

Removed:
  --plot-from <N>          Removed; /report-tokens now scans committed larch-logs directly.
EOF
}

SKILL=""
NO_ISSUE_FLAG=""
NO_PLOT_FLAG=""

validate_skill() {
    case "${1:-}" in
        design|implement) return 0 ;;
        "") larch_err "ERROR: --skill is required (allowed: design, implement)"; return 1 ;;
        *) larch_err "ERROR: --skill must be design or implement (got: $1)"; return 1 ;;
    esac
}

while [ $# -gt 0 ]; do
    case "${1:-}" in
        --help|-h) usage; exit 0 ;;
        --skill)
            SKILL="${2:-}"
            shift 2
            ;;
        --no-issue)
            NO_ISSUE_FLAG="--no-issue"
            shift
            ;;
        --no-plot)
            NO_PLOT_FLAG="--no-plot"
            shift
            ;;
        --plot-from)
            larch_err "ERROR: --plot-from has been removed; scan committed larch-logs instead"
            exit 2
            ;;
        *)
            larch_err "ERROR: unknown argument: $1"
            usage
            exit 1
            ;;
    esac
done

if ! validate_skill "$SKILL"; then
    usage
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    larch_err "ERROR: required command not found: python3"
    exit 1
fi

export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

# Restore caller-visible streams after lib-quiet setup so Python's stdout/stderr
# contract is visible to /report-tokens callers even when quiet mode is active.
if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
    exec 1>&3 2>&4
fi

ARGS=(--skill "$SKILL")
[ -z "$NO_ISSUE_FLAG" ] || ARGS+=("$NO_ISSUE_FLAG")
[ -z "$NO_PLOT_FLAG" ] || ARGS+=("$NO_PLOT_FLAG")
exec python3 "$PLUGIN_ROOT/python/report_tokens_cli.py" "${ARGS[@]}"
