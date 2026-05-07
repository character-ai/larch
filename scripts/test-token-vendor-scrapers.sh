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

# launch-cursor-implement.sh + launch-codex-implement.sh record-vendor smoke
# (issue #1351 Gap 4 — overlaps Gap 1's per-launcher harness coverage). The
# launcher's own scrape path already runs in tests-cursor/codex-implementer.sh;
# this scrapers harness pins that the resulting JSONL row carries
# raw=cursor_implement / raw=codex_implement, which is the contract scraper
# consumers (token-report) depend on for the "vendor:cursor_implement" /
# "vendor:codex_implement" attribution.
if command -v jq >/dev/null 2>&1; then
    LCI_BIN="$TMP/lci-bin"
    mkdir -p "$LCI_BIN"
    cat > "$LCI_BIN/cursor" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf '{"result":"stub","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}\n'
STUB_EOF
    chmod +x "$LCI_BIN/cursor"

    cat > "$LCI_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'stub codex transcript payload\n' > "$output_path"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'tokens used\n7,777\n'
STUB_EOF
    chmod +x "$LCI_BIN/codex"

    LCI_SCRATCH="$TMP/lci-scratch"
    mkdir -p "$LCI_SCRATCH"
    printf 'plan\n' > "$LCI_SCRATCH/plan.md"
    printf 'feature\n' > "$LCI_SCRATCH/feature.txt"

    # Per-launcher invocation, with a unique session id so each ledger is
    # isolated and the dump-and-assert step reads the correct file.
    for variant in cursor codex; do
        LCI_SESSION="lci-${variant}-$$"
        case "$variant" in
            cursor)
                AGENT_PROMPT="$REPO_ROOT/agents/cursor-implementer.md"
                LAUNCHER="$REPO_ROOT/scripts/launch-cursor-implement.sh"
                EXPECTED_RAW="cursor_implement"
                EXPECTED_TOTAL=10
                ;;
            codex)
                AGENT_PROMPT="$REPO_ROOT/agents/codex-implementer.md"
                LAUNCHER="$REPO_ROOT/scripts/launch-codex-implement.sh"
                EXPECTED_RAW="codex_implement"
                EXPECTED_TOTAL=7777
                ;;
        esac

        if [[ ! -f "$AGENT_PROMPT" ]]; then
            fail "$variant agent prompt missing: $AGENT_PROMPT"
            continue
        fi

        TR="$LCI_SCRATCH/$variant-transcript.txt"
        SC="$LCI_SCRATCH/$variant-sidecar.log"
        MF="$LCI_SCRATCH/$variant-manifest.json"
        QA="$LCI_SCRATCH/$variant-qa.json"

        LARCH_TOKEN_SESSION_ID="$LCI_SESSION" \
        PATH="$LCI_BIN:$PATH" \
        RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
        LARCH_CURSOR_MODEL="stub-model" \
        LARCH_CODEX_MODEL="stub-codex-model" \
        STUB_MANIFEST_PATH="$MF" \
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
            "$LAUNCHER" \
                --transcript-path "$TR" \
                --sidecar-log "$SC" \
                --manifest-path "$MF" \
                --qa-pending-path "$QA" \
                --plan-file "$LCI_SCRATCH/plan.md" \
                --feature-file "$LCI_SCRATCH/feature.txt" \
                --agent-prompt "$AGENT_PROMPT" \
                --timeout 30 >/dev/null 2>&1 || true

        LCI_LEDGER=$(LARCH_TOKEN_SESSION_ID="$LCI_SESSION" "$REPO_ROOT/scripts/token-ledger.sh" dump | sed -n '1p')
        if [[ -f "$LCI_LEDGER" ]] && jq -e --arg raw "$EXPECTED_RAW" --argjson total "$EXPECTED_TOTAL" \
            'select(.type=="vendor" and .raw==$raw and .total==$total)' "$LCI_LEDGER" >/dev/null 2>&1; then
            pass
        else
            fail "launch-${variant}-implement.sh did not record-vendor raw=$EXPECTED_RAW total=$EXPECTED_TOTAL; ledger=$LCI_LEDGER content=$(cat "$LCI_LEDGER" 2>/dev/null)"
        fi
        rm -f "$LCI_LEDGER"
    done
else
    pass  # jq absent — skip per launcher runtime guard parallel
fi

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-vendor-scrapers.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-vendor-scrapers.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
