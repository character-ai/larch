#!/usr/bin/env bash
# Regression harness for dispatch-with-waterfall.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d /tmp/larch-test-dispatch-waterfall-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/codex" <<'STUB'
#!/usr/bin/env bash
out=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then out="$arg"; fi
    last="$arg"
done
[[ -n "$out" ]] || exit 9
if [[ "${CODEX_STUB_FAIL:-false}" == "true" ]]; then
    exit 7
fi
printf 'codex ok\n' > "$out"
STUB
cat > "$STUB_BIN/cursor" <<'STUB'
#!/usr/bin/env bash
if [[ "${CURSOR_STUB_FAIL:-false}" == "true" ]]; then
    exit 8
fi
printf '{"result":"cursor ok","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
if [[ "${CLAUDE_STUB_FAIL:-false}" == "true" ]]; then
    exit 9
fi
printf 'claude ok\n'
STUB
chmod +x "$STUB_BIN/codex" "$STUB_BIN/cursor" "$STUB_BIN/claude"

prompt="$TMPROOT/prompt.txt"
printf 'vote\n' > "$prompt"

assert_line() {
    local expected="$1" output="$2"
    grep -Fxq "$expected" <<< "$output" || { echo "FAIL: missing $expected" >&2; printf '%s\n' "$output" >&2; exit 1; }
}

manifest="$TMPROOT/slots.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/codex-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_FAIL=true "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=0" "$out"
assert_line "ALL_OUTPUT_TOOLS=cursor" "$out"
grep -Fq "cursor ok" "$TMPROOT/codex-slot-phase2.txt" || { echo "FAIL: phase2 cursor output" >&2; exit 1; }

manifest="$TMPROOT/slots-claude.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/claude-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" CODEX_STUB_FAIL=true CURSOR_STUB_FAIL=true "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present true \
    --cursor-present true \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=1" "$out"
assert_line "ALL_OUTPUT_TOOLS=claude" "$out"
grep -Fq "claude ok" "$TMPROOT/claude-slot-phase3.txt" || { echo "FAIL: phase3 claude output" >&2; exit 1; }

manifest="$TMPROOT/slots-absent.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/absent-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=1" "$out"
assert_line "ALL_OUTPUT_TOOLS=claude" "$out"

# Test: Phase-3 hard failure — both external tools absent and Claude stub fails.
# DISPATCH_OK must be false when Phase 3 Claude slot fails.
manifest="$TMPROOT/slots-hardfail.ndjson"
printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/hardfail-slot.txt" "$prompt" > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" CLAUDE_STUB_FAIL=true "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "DISPATCH_OK=false" "$out"
assert_line "FALLBACK_COUNT=1" "$out"

# Test: WARN threshold — fallback count exceeds LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD.
# With threshold=1 and 2 slots both falling through to Claude, WARN must be emitted.
manifest="$TMPROOT/slots-warn.ndjson"
{
    printf '{"slot":"s1","tool":"codex","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/warn-slot1.txt" "$prompt"
    printf '{"slot":"s2","tool":"cursor","output":"%s","prompt_file":"%s"}\n' "$TMPROOT/warn-slot2.txt" "$prompt"
} > "$manifest"
out=$(PATH="$STUB_BIN:$PATH" LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD=1 "$REPO_ROOT/scripts/dispatch-with-waterfall.sh" \
    --slots-file "$manifest" \
    --codex-present false \
    --cursor-present false \
    --mode description \
    --timeout 5)
assert_line "FALLBACK_COUNT=2" "$out"
grep -Fq "WARN=cost-fallback-exceeded-threshold" <<< "$out" || { echo "FAIL: missing WARN=cost-fallback-exceeded-threshold" >&2; printf '%s\n' "$out" >&2; exit 1; }
assert_line "DISPATCH_OK=true" "$out"

echo "PASS: test-dispatch-with-waterfall.sh"
