#!/usr/bin/env bash
# test-token-cost-per-bucket.sh — per-bucket arithmetic + env precedence (DE-2622).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd -P)"
HELPER="$SCRIPT_DIR/token-cost.sh"
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS + 1)); }

read_kv() {
    local key=$1 data
    data=$(printf '%s\n' "$2" | awk -F= -v k="$key" '$1==k{print $2; exit}')
    printf '%s\n' "${data:-}"
}

with_rates_cleared() {
    env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
        -u LARCH_CLAUDE_INPUT_RATE_PER_M -u LARCH_CLAUDE_CACHE_READ_RATE_PER_M -u LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M \
        -u LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M -u LARCH_CLAUDE_OUTPUT_RATE_PER_M \
        -u LARCH_CODEX_INPUT_RATE_PER_M -u LARCH_CODEX_CACHED_INPUT_RATE_PER_M -u LARCH_CODEX_OUTPUT_RATE_PER_M \
        -u LARCH_CURSOR_INPUT_RATE_PER_M -u LARCH_CURSOR_CACHE_READ_RATE_PER_M -u LARCH_CURSOR_OUTPUT_RATE_PER_M \
        "$@"
}

# (a) Plan acceptance: hand-computed CLAUDE_COST=5.75 at default Opus 4.7 rates.
out=$(with_rates_cleared "$HELPER" \
    --claude-input-tokens 100 \
    --claude-cache-read-tokens 10000000 \
    --claude-cache-write-5m-tokens 100000 \
    --claude-output-tokens 5000 \
    --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "5.75" || fail "per-bucket Claude reference total"
pass "CLAUDE_COST=5.75 reference mix"

# (b) Per-bucket env override beats default for one bucket.
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M \
    -u LARCH_CLAUDE_CACHE_READ_RATE_PER_M -u LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M \
    -u LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M -u LARCH_CLAUDE_OUTPUT_RATE_PER_M \
    -u LARCH_CODEX_INPUT_RATE_PER_M -u LARCH_CODEX_CACHED_INPUT_RATE_PER_M -u LARCH_CODEX_OUTPUT_RATE_PER_M \
    -u LARCH_CURSOR_INPUT_RATE_PER_M -u LARCH_CURSOR_CACHE_READ_RATE_PER_M -u LARCH_CURSOR_OUTPUT_RATE_PER_M \
    LARCH_CLAUDE_INPUT_RATE_PER_M=10 \
    "$HELPER" --claude-input-tokens 1000000 --claude-cache-read-tokens 0 \
        --claude-cache-write-5m-tokens 0 --claude-cache-write-1h-tokens 0 --claude-output-tokens 0 \
        --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "10.00" || fail "per-bucket env override"
pass "LARCH_CLAUDE_INPUT_RATE_PER_M override"

# (c) Legacy blended env still applies when per-bucket unset (stderr warning expected).
stderrf=$(mktemp "${TMPDIR:-/tmp}/tcpb-err.XXXXXX")
trap 'rm -f "$stderrf"' EXIT
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    -u LARCH_CODEX_INPUT_RATE_PER_M -u LARCH_CODEX_CACHED_INPUT_RATE_PER_M -u LARCH_CODEX_OUTPUT_RATE_PER_M \
    -u LARCH_CLAUDE_INPUT_RATE_PER_M -u LARCH_CLAUDE_CACHE_READ_RATE_PER_M -u LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M \
    -u LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M -u LARCH_CLAUDE_OUTPUT_RATE_PER_M \
    -u LARCH_CURSOR_INPUT_RATE_PER_M -u LARCH_CURSOR_CACHE_READ_RATE_PER_M -u LARCH_CURSOR_OUTPUT_RATE_PER_M \
    LARCH_CODEX_RATE_PER_M=9 \
    "$HELPER" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0 2>"$stderrf")
grep -q 'blended rate' "$stderrf" || fail 'expected blended-fallback stderr warning'
test "$(read_kv CODEX_COST "$out")" = "9.00" || fail "legacy Codex blended env"
pass "legacy blended env + stderr warning"

# (d) Malformed per-bucket env → default constant for that bucket.
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M \
    -u LARCH_CLAUDE_INPUT_RATE_PER_M -u LARCH_CLAUDE_CACHE_READ_RATE_PER_M -u LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M \
    -u LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M \
    -u LARCH_CODEX_INPUT_RATE_PER_M -u LARCH_CODEX_CACHED_INPUT_RATE_PER_M -u LARCH_CODEX_OUTPUT_RATE_PER_M \
    -u LARCH_CURSOR_INPUT_RATE_PER_M -u LARCH_CURSOR_CACHE_READ_RATE_PER_M -u LARCH_CURSOR_OUTPUT_RATE_PER_M \
    LARCH_CLAUDE_OUTPUT_RATE_PER_M=xyzzy \
    "$HELPER" --claude-input-tokens 0 --claude-cache-read-tokens 0 --claude-cache-write-5m-tokens 0 \
        --claude-cache-write-1h-tokens 0 --claude-output-tokens 1000000 \
        --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "25.00" || fail "malformed output rate falls back to default 25/M"
pass "malformed per-bucket env uses default"

printf 'PASS: test-token-cost-per-bucket.sh — %s checks\n' "$PASS"
