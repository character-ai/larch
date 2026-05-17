#!/usr/bin/env bash
# Regression harness for dispatch-panel.sh waterfall wiring.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/dispatch-panel.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-panel.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
unset CLAUDE_PLUGIN_ROOT

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""; last=""
for arg in "$@"; do [[ "$last" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
printf 'codex review\n' > "$out"
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
printf '{"result":"cursor review","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
printf 'claude review\n'
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

plan_file="$TMP/plan.md"
printf '# plan\n' > "$plan_file"

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/simple" \
    --codex-available true \
    --cursor-available true \
    --panel simple \
    --plan-file "$plan_file")
grep -Fq 'PANEL_MODE=waterfall' <<< "$out"
grep -Fq 'PANEL_SHAPE=simple' <<< "$out"
grep -Fq 'SLOT_COUNT=7' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
[[ -s "$TMP/simple/cursor-specialist-structure-output.txt" ]]
[[ -s "$TMP/simple/codex-generalist-output.txt" ]]

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/hard" \
    --codex-available true \
    --cursor-available true \
    --panel hard \
    --plan-file "$plan_file")
grep -Fq 'PANEL_SHAPE=hard' <<< "$out"
grep -Fq 'SLOT_COUNT=12' <<< "$out"
[[ -s "$TMP/hard/cursor-specialist-structure-output.txt" ]]
[[ -s "$TMP/hard/codex-specialist-structure-output.txt" ]]

out=$(PATH="$STUB_BIN:$PATH" "$SCRIPT" \
    --mode diff \
    --review-tmpdir "$TMP/both-down" \
    --codex-available false \
    --cursor-available false \
    --panel simple \
    --plan-file "$plan_file")
grep -Fq 'DISPATCH_OK=true' <<< "$out"
claude_count=$(find "$TMP/both-down" -name '*phase3.txt' | wc -l | tr -d ' ')
[[ "$claude_count" -ge 7 ]] || { echo "FAIL: expected Claude phase3 outputs for both-down panel" >&2; exit 1; }

echo "All assertions passed."
