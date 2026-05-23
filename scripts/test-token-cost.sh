#!/usr/bin/env bash
# test-token-cost.sh — offline harness for scripts/token-cost.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd -P)"
HELPER="$SCRIPT_DIR/token-cost.sh"
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { PASS=$((PASS + 1)); }

read_kv() {
    local key=$1 data
    data=$(printf '%s\n' "$2" | awk -F= -v k="$key" '$1==k{print $2; exit}')
    printf '%s\n' "${data:-}"
}

clr='env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M'

# (a) defaults when no rate env set
out=$($clr "$HELPER" --claude-tokens 1000000 --codex-tokens 1000000 --cursor-tokens 1000000)
test "$(read_kv CLAUDE_COST "$out")" = "6.00" || fail "default Claude cost"
test "$(read_kv CODEX_COST "$out")" = "10.00" || fail "default Codex cost"
test "$(read_kv CURSOR_COST "$out")" = "10.00" || fail "default Cursor cost"
test "$(read_kv TOTAL_COST "$out")" = "26.00" || fail "default TOTAL_COST sum"
pass "defaults when unset"

# (b) env override
out=$(LARCH_CLAUDE_RATE_PER_M=2 env -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "2.00" || fail "Claude override"
pass "explicit override"

# (c) zero → default
out=$(LARCH_CLAUDE_RATE_PER_M=0 env -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "6.00" || fail "Claude zero falls back to default"
pass "zero env uses default"

# (d) empty string → default
out=$(env LARCH_CODEX_RATE_PER_M='' -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0)
test "$(read_kv CODEX_COST "$out")" = "10.00" || fail "empty Codex rate uses default"
pass "empty string uses default"

# (e) malformed → default
out=$(LARCH_CODEX_RATE_PER_M=abc env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0)
test "$(read_kv CODEX_COST "$out")" = "10.00" || fail "malformed Codex rate uses default"
pass "malformed uses default"

# (f) LARCH_TOKEN_RATE_PER_M wins over Claude default
out=$(LARCH_TOKEN_RATE_PER_M=7 env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "7.00" || fail "LARCH_TOKEN_RATE_PER_M fallback"
pass "LARCH_TOKEN_RATE_PER_M precedence over Claude default"

# (g) TOTAL sums all three with mixed TOKEN_RATE and defaults
out=$(LARCH_TOKEN_RATE_PER_M=5 env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 1000000 --cursor-tokens 1000000)
test "$(read_kv TOTAL_COST "$out")" = "25.00" || fail "TOTAL 5+10+10"
pass "TOTAL sums three numeric lanes"

printf 'PASS: test-token-cost.sh — %s checks\n' "$PASS"
