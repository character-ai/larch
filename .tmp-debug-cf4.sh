#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT=/Users/zhupanov/larch4
PLUGIN_ROOT="$REPO_ROOT"
TMP=$(mktemp -d)
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
LARCH_QUIET_DISABLE=1 larch_quiet_init
ext="$TMP/codex-generalist-fail-a.txt"
: > "$ext"
printf '1\n' > "${ext}.done"
printf 'non-transient failure\n' > "${ext}.diag"
printf 'external stderr tail alpha\n' > "${ext}.stderr-tail"
collector_stderr="$TMP/collector.stderr"
LARCH_QUIET_DISABLE=1 "$PLUGIN_ROOT/scripts/collect-agent-results.sh" --timeout 5 --substantive-validation --validation-mode \
  "$ext" >"$TMP/out" 2>"$collector_stderr"
wc -c "$collector_stderr"
grep alpha "$collector_stderr" || echo NO_ALPHA
