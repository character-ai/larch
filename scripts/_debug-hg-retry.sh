#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_ROOT="$(mktemp -d)"
export REPO_ROOT TMPDIR_ROOT

# Minimal extract: run one health-gate case inline.
case_dir="$TMPDIR_ROOT/health-debug"
call_file="$case_dir/checker-call"
mkdir -p "$case_dir/scripts" "$case_dir/bin" "$case_dir/python/stubs/session" "$case_dir/python/stubs/agent"
cp "$REPO_ROOT/scripts/lib-external-launcher-common.sh" "$case_dir/scripts/lib-external-launcher-common.sh"
cp "$REPO_ROOT"/python/*.py "$case_dir/python/"
mv "$case_dir/python/cli.py" "$case_dir/python/real-cli.py"
cp "$REPO_ROOT/scripts/test-lib-external-launcher-common.sh" /tmp/hg-test-snippet.sh
# Use the test file's stub by running only run_health_gate_case via bash subshell
bash -c '
REPO_ROOT="'"$REPO_ROOT"'"
TMPDIR_ROOT="'"$TMPDIR_ROOT"'"
pass(){ :;}
fail(){ echo fail "$@"; exit 1;}
source <(awk "/^run_health_gate_case\\(\\)/,/^assert_health_gate_rc\\(\\)/{if(/^assert_health_gate_rc\\(\\)/) exit; print}" "'"$REPO_ROOT"'/scripts/test-lib-external-launcher-common.sh")
d=$(run_health_gate_case debug codex 5 "" "" "CODEX_PRESENT=true" 0 "" 2 0 "" "CODEX_PRESENT=false")
echo rc=$(cat "$d/rc")
echo lines=$(wc -l < "$d/checker-call")
cat -n "$d/checker-call"
'
