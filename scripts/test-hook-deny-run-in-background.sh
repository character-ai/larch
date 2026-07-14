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

mkdir -p "$TMP/no-jq/bin"
ln -s /bin/cat "$TMP/no-jq/bin/cat"
ln -s "$(command -v dirname)" "$TMP/no-jq/bin/dirname"
ln -s /bin/bash "$TMP/no-jq/bin/bash"
out=$(payload | PATH="$TMP/no-jq/bin" "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null

mkdir -p "$TMP/no-python/bin"
ln -s "$(command -v cat)" "$TMP/no-python/bin/cat"
ln -s "$(command -v dirname)" "$TMP/no-python/bin/dirname"
ln -s "$(command -v jq)" "$TMP/no-python/bin/jq"
out=$(payload | PATH="$TMP/no-python/bin" "$(command -v bash)" "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null

mkdir -p "$TMP/kv-fail/bin"
ln -s "$(command -v cat)" "$TMP/kv-fail/bin/cat"
ln -s "$(command -v dirname)" "$TMP/kv-fail/bin/dirname"
ln -s "$(command -v jq)" "$TMP/kv-fail/bin/jq"
ln -s "$(command -v bash)" "$TMP/kv-fail/bin/bash"
cat >"$TMP/kv-fail/bin/python3" <<EOF
#!/bin/bash
if [ "\$2" = "kv" ] && [ "\$3" = "get" ]; then
  exit 1
fi
exec "$(command -v python3)" "\$@"
EOF
chmod +x "$TMP/kv-fail/bin/python3"
out=$(payload | PATH="$TMP/kv-fail/bin" "$(command -v bash)" "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null

echo 'PASS: hook-deny-run-in-background'
