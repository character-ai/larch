#!/usr/bin/env bash
# test-token-vendor-scrapers.sh — offline regression harness for vendor token extraction.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }
eq() {
    if [[ "$2" == "$3" ]]; then pass; else fail "$1 expected '$2' got '$3'"; fi
}

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-token-vendor.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

codex_scrape() {
    awk '/^tokens used$/ { getline n; gsub(",","",n); last=n } END { print last }' "$1" 2>/dev/null || true
}

cat > "$TMP/codex.sidecar" <<'EOF'
noise
tokens used
1,234
more noise
tokens used
5,678
EOF
eq "codex last block" "5678" "$(codex_scrape "$TMP/codex.sidecar")"

cat > "$TMP/codex-bad.sidecar" <<'EOF'
tokens used
123
tokens used
not numeric
EOF
n=$(codex_scrape "$TMP/codex-bad.sidecar")
if [[ "$n" =~ ^[0-9]+$ ]]; then fail "codex non-numeric trailing value should be rejected by caller"; else pass; fi

cat > "$TMP/cursor.json" <<'JSON'
{"result":"plain reviewer prose","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}
JSON
read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$TMP/cursor.json")
eq "cursor input" "1" "$INP"
eq "cursor total" "10" "$((INP + OUT + CR + CW))"

bad=$(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$TMP/nope.json" 2>/dev/null || echo "0 0 0 0")
eq "cursor malformed fallback" "0 0 0 0" "$bad"

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '{"result":"reviewer prose only","usage":{"inputTokens":5,"outputTokens":6,"cacheReadTokens":7,"cacheWriteTokens":8}}\n'
EOF
chmod +x "$STUB_BIN/cursor"

OUT_FILE="$TMP/cursor-review.txt"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
PATH="$STUB_BIN:$PATH" \
LARCH_CURSOR_MODEL=stub-model \
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$REPO_ROOT/scripts/launch-cursor-review.sh" --output "$OUT_FILE" --timeout 30 --prompt "review" >/dev/null

eq "cursor review prose output" "reviewer prose only" "$(cat "$OUT_FILE")"
if jq -e '.usage.inputTokens == 5' "${OUT_FILE}.json" >/dev/null; then pass; else fail "cursor review raw JSON sidecar missing usage"; fi

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-vendor-scrapers.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-vendor-scrapers.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
