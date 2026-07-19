#!/usr/bin/env bash
# step-8-python-guard.sh — shared Python 3.11 guard for /implement Step 8.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  # shellcheck source=/dev/null
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
export CLAUDE_PLUGIN_ROOT

if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  exit 0
fi
printf '%s\n' 'ERROR: Python ship driver requires Python 3.11 or newer' >&2
printf '%s\n' '{"detail":"Python ship driver requires Python 3.11 or newer","failed_run_id":"","ledger_dispatcher":"","ledger_exit_code":null,"ledger_failure_detail_log":"","ledger_phase":"","ledger_ready":false,"ledger_site":"","ledger_step":"","ledger_trigger":"","merge_result":"","needs_user_reason":"","outcome":"STALLED","pr_number":null,"pr_url":""}'
exit 4
