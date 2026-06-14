#!/usr/bin/env bash
set -euo pipefail
TMPROOT=$(mktemp -d)
REPO_ROOT=/Users/zhupanov/larch7
COLLECTOR=$REPO_ROOT/scripts/collect-agent-results.sh
F5B_RETRY="$TMPROOT/cursor-retry-source-output.txt"
: > "$F5B_RETRY"
printf '0\n' > "$F5B_RETRY.done"
F5B_BIN="$TMPROOT/case5b-bin"
mkdir -p "$F5B_BIN"
cat > "$F5B_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
printf 'CURSOR_DEGRADED_RESPONSE\n'
STUB
chmod +x "$F5B_BIN/cursor"
jq -cn --arg cursor "$F5B_BIN/cursor" --arg workspace "$REPO_ROOT" \
  '[$cursor,"agent","--workspace",$workspace,"retry prompt"]' > "$TMPROOT/case5b-cmd.json"
{
  printf 'TOOL=cursor\n'
  printf 'TIMEOUT=1\n'
  printf 'CAPTURE_STDOUT_ONLY=true\n'
  printf 'OUTPUT_FILE=%s\n' "$F5B_RETRY"
  printf 'CMD_JSON=%s\n' "$(cat "$TMPROOT/case5b-cmd.json")"
} > "$F5B_RETRY.meta"
PATH="$F5B_BIN:$PATH" "$COLLECTOR" --timeout 30 "$F5B_RETRY" >"$TMPROOT/case5b-retry.stdout" 2>"$TMPROOT/case5b-retry.stderr"
F5B_RETRY_OUTPUT="${F5B_RETRY%.txt}-retry.txt"
echo "=== stdout ==="
cat "$TMPROOT/case5b-retry.stdout"
echo "=== retry file ==="
ls -la "$F5B_RETRY_OUTPUT" || true
cat "$F5B_RETRY_OUTPUT" 2>/dev/null || true
echo "=== grep ==="
grep -A 4 -F "REVIEWER_FILE=$F5B_RETRY_OUTPUT" "$TMPROOT/case5b-retry.stdout" || true
