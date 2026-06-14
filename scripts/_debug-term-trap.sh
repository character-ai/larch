#!/usr/bin/env bash
set -euo pipefail
TMPROOT=$(mktemp -d)
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$$" > "${CURSOR_STUB_PID_FILE:?}"
sleep 30
jq -nc '{result:"ok",usage:{inputTokens:1,outputTokens:1,cacheReadTokens:0,cacheWriteTokens:0}}'
STUB
chmod +x "$STUB_BIN/cursor"
prompt="$TMPROOT/p.txt"
printf 'x\n' > "$prompt"
manifest="$TMPROOT/m.ndjson"
printf '{"slot":"s","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/out.txt" "$prompt" > "$manifest"
pidfile="$TMPROOT/stub.pid"
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT" LARCH_TRANSIENT_RETRY_DELAY=0 LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0
export LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Linux
PATH="$STUB_BIN:$PATH" CURSOR_STUB_PID_FILE="$pidfile" \
  bash "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" --codex-present false --cursor-present true \
    --mode description --timeout 60 >/dev/null 2>&1 &
DPID=$!
for _ in $(seq 1 200); do [[ -f "$pidfile" ]] && break; sleep 0.05; done
SPID=$(cat "$pidfile")
echo "dispatcher=$DPID stub=$SPID"
phase_pids=$(pgrep -P "$DPID" 2>/dev/null | tr '\n' ' ' || true)
echo "dispatch_children=$phase_pids"
sleep 0.3
wp=$(echo "$phase_pids" | awk '{print $1}')
if [[ -n "$wp" ]]; then
  kill -TERM -"$wp" 2>/dev/null || kill -TERM "$wp" 2>/dev/null || true
  sleep 0.5
  if kill -0 "$SPID" 2>/dev/null; then echo STUB_ALIVE_AFTER_PG_KILL; else echo STUB_DEAD_AFTER_PG_KILL; fi
fi
kill -TERM "$DPID"
wait "$DPID" 2>/dev/null || true
kill -KILL "$SPID" 2>/dev/null || true
rm -rf "$TMPROOT"
