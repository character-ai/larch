#!/usr/bin/env bash
# read-result-env.sh — safely convert result-env KVs into a sourceable allowlisted env.
# Delegates allowlist filtering, symlink refusal, CR/LF rejection, fallback-input
# logic, WARN/ERROR stdout replay, and single-quote encoding to the Python
# design lifecycle helper.

set -euo pipefail

_RRE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
_REPO_ROOT="$(cd "$_RRE_SCRIPT_DIR/.." && pwd -P)"
CLAUDE_PLUGIN_ROOT="$_REPO_ROOT"
export CLAUDE_PLUGIN_ROOT

exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design read-result-env "$@"
