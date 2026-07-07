#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HOOK="$SCRIPT_DIR/hook-deny-run-in-background.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-deny-run-bg.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry"
mkdir -p "$HOME" "$LARCH_BGJOB_REGISTRY_ROOT" "$TMP/clone"

payload() {
  jq -cn --arg cwd "$TMP/clone" '{tool_name:"Bash", cwd:$cwd, tool_input:{command:"sleep 1", run_in_background:true}}'
}

out=$(payload | "$HOOK")
[ -z "$out" ] || { echo "expected no active registry allow, got $out" >&2; exit 1; }
cat >"$LARCH_BGJOB_REGISTRY_ROOT/run-demo.env" <<EOF
CLONE_PATH=$TMP/clone
EOF
out=$(payload | "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null

echo 'PASS: hook-deny-run-in-background'
