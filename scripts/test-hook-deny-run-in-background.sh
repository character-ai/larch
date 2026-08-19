#!/usr/bin/env bash
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HOOK="$SCRIPT_DIR/hook-deny-run-in-background.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-deny-run-bg.XXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home"
export LARCH_BGJOB_REGISTRY_ROOT="$TMP/registry"
mkdir -p "$HOME" "$LARCH_BGJOB_REGISTRY_ROOT" "$TMP/clone"
BASH_BIN=$(command -v bash)
PLUGIN_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
PLUGIN_VERSION=$(awk -F '"' '$2 == "version" { print $4 }' "$PLUGIN_ROOT/.claude-plugin/plugin.json")
case "$(uname -s):$(uname -m)" in
  Darwin:arm64|Darwin:aarch64) LARCH_TARGET=aarch64-apple-darwin ;;
  Darwin:x86_64|Darwin:amd64) LARCH_TARGET=x86_64-apple-darwin ;;
  Linux:arm64|Linux:aarch64) LARCH_TARGET=aarch64-unknown-linux-gnu ;;
  Linux:x86_64|Linux:amd64) LARCH_TARGET=x86_64-unknown-linux-gnu ;;
  *) echo "unsupported harness target" >&2; exit 1 ;;
esac
export LARCH_BINARY="$TMP/larch-fixture"
cat >"$LARCH_BINARY" <<EOF
#!$BASH_BIN
set -u
if [[ "\${1:-}" == --version ]]; then printf '%s\n' 'larch $PLUGIN_VERSION'; exit 0; fi
if [[ "\${1:-}" == bootstrap && "\${2:-}" == self-check ]]; then
  printf '%s\n' '{"schema_version":1,"version":"$PLUGIN_VERSION","target":"$LARCH_TARGET"}'
  exit 0
fi
if [[ "\${1:-}" == kv && "\${2:-}" == get ]]; then
  [[ "\${LARCH_KV_FAIL:-}" != 1 ]] || exit 1
  shift 2
  key="" file=""
  while [[ \$# -gt 0 ]]; do
    case "\$1" in --key) key="\$2"; shift 2 ;; --file) file="\$2"; shift 2 ;; *) shift ;; esac
  done
  while IFS= read -r line || [[ -n "\$line" ]]; do
    case "\$line" in "\$key="*) printf '%s\n' "\${line#*=}"; exit 0 ;; esac
  done <"\$file"
  printf '\n'
  exit 0
fi
exit 2
EOF
chmod +x "$LARCH_BINARY"

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
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecisionReason | contains("active larch bgjob")' >/dev/null

wait_payload() {
  jq -cn --arg cwd "$TMP/clone" \
    --arg cmd '${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh bgjob wait --step complete-umbrella-leaf-1 --tmpdir /tmp/x --max-wait-s 7200' \
    '{tool_name:"Bash", cwd:$cwd, tool_input:{command:$cmd, run_in_background:true}}'
}
out=$(wait_payload | "$HOOK")
[ -z "$out" ] || { echo "expected documented bgjob wait allow, got $out" >&2; exit 1; }

decoy_payload() {
  jq -cn --arg cwd "$TMP/clone" \
    --arg cmd '/tmp/decoy/larch.sh bgjob wait --step x --tmpdir /tmp/x --max-wait-s 7200' \
    '{tool_name:"Bash", cwd:$cwd, tool_input:{command:$cmd, run_in_background:true}}'
}
out=$(decoy_payload | "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecisionReason | contains("active larch bgjob")' >/dev/null

wrapped_payload() {
  jq -cn --arg cwd "$TMP/clone" \
    --arg cmd 'sleep 1 && ${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh bgjob wait --step x --tmpdir /tmp/x --max-wait-s 7200' \
    '{tool_name:"Bash", cwd:$cwd, tool_input:{command:$cmd, run_in_background:true}}'
}
out=$(wrapped_payload | "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecisionReason | contains("active larch bgjob")' >/dev/null

multiline_payload() {
  jq -cn --arg cwd "$TMP/clone" \
    --arg cmd $'"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" bgjob wait \\\n  --step complete-umbrella-leaf-1 \\\n  --tmpdir /tmp/x \\\n  --max-wait-s 7200' \
    '{tool_name:"Bash", cwd:$cwd, tool_input:{command:$cmd, run_in_background:true}}'
}
out=$(multiline_payload | "$HOOK")
[ -z "$out" ] || { echo "expected multiline bgjob wait allow, got $out" >&2; exit 1; }

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
ln -s "$(command -v awk)" "$TMP/no-python/bin/awk"
ln -s "$(command -v uname)" "$TMP/no-python/bin/uname"
ln -s "$BASH_BIN" "$TMP/no-python/bin/bash"
out=$(payload | PATH="$TMP/no-python/bin" "$BASH_BIN" "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecisionReason | contains("active larch bgjob")' >/dev/null

mkdir -p "$TMP/kv-fail/bin"
ln -s "$(command -v cat)" "$TMP/kv-fail/bin/cat"
ln -s "$(command -v dirname)" "$TMP/kv-fail/bin/dirname"
ln -s "$(command -v jq)" "$TMP/kv-fail/bin/jq"
ln -s "$(command -v awk)" "$TMP/kv-fail/bin/awk"
ln -s "$(command -v uname)" "$TMP/kv-fail/bin/uname"
ln -s "$BASH_BIN" "$TMP/kv-fail/bin/bash"
out=$(payload | LARCH_KV_FAIL=1 PATH="$TMP/kv-fail/bin" "$BASH_BIN" "$HOOK")
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null
printf '%s' "$out" | jq -e '.hookSpecificOutput.permissionDecisionReason | contains("cannot read active bgjob registry entry")' >/dev/null

echo 'PASS: hook-deny-run-in-background'
