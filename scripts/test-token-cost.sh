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

# (a) defaults when no rate env set (blended aggregate path)
out=$($clr "$HELPER" --claude-tokens 1000000 --codex-tokens 1000000 --cursor-tokens 1000000)
test "$(read_kv CLAUDE_COST "$out")" = "0.80" || fail "default Claude blended cost"
test "$(read_kv CODEX_COST "$out")" = "2.00" || fail "default Codex blended cost"
test "$(read_kv CURSOR_COST "$out")" = "1.50" || fail "default Cursor blended cost"
test "$(read_kv TOTAL_COST "$out")" = "4.30" || fail "default TOTAL_COST sum"
pass "defaults when unset"

# (b) env override (blended)
out=$(LARCH_CLAUDE_RATE_PER_M=2 env -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "2.00" || fail "Claude override"
pass "explicit override"

# (c) zero → default
out=$(LARCH_CLAUDE_RATE_PER_M=0 env -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "0.80" || fail "Claude zero falls back to default blended"
pass "zero env uses default"

# (d) empty string → default
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    LARCH_CODEX_RATE_PER_M='' "$HELPER" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0)
test "$(read_kv CODEX_COST "$out")" = "2.00" || fail "empty Codex rate uses default"
pass "empty string uses default"

# (e) malformed → default
out=$(LARCH_CODEX_RATE_PER_M=abc env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0)
test "$(read_kv CODEX_COST "$out")" = "2.00" || fail "malformed Codex rate uses default"
pass "malformed uses default"

# (f) LARCH_TOKEN_RATE_PER_M wins over Claude default
out=$(LARCH_TOKEN_RATE_PER_M=7 env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 0 --cursor-tokens 0)
test "$(read_kv CLAUDE_COST "$out")" = "7.00" || fail "LARCH_TOKEN_RATE_PER_M fallback"
pass "LARCH_TOKEN_RATE_PER_M precedence over Claude default"

# (g) TOTAL sums all three with mixed TOKEN_RATE and defaults
out=$(LARCH_TOKEN_RATE_PER_M=5 env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M \
    "$HELPER" --claude-tokens 1000000 --codex-tokens 1000000 --cursor-tokens 1000000)
test "$(read_kv TOTAL_COST "$out")" = "8.50" || fail "TOTAL sums three numeric lanes"
pass "TOTAL sums three numeric lanes"

# (h) malformed token count exits 2 (does not silently coerce to zero)
if $clr "$HELPER" --claude-tokens not-a-number --codex-tokens 0 --cursor-tokens 0 >/dev/null 2>&1; then
    fail "expected non-zero exit for invalid token count"
fi
pass "invalid token count rejected"

# (i) claude_sub priced at Claude rates (issue #3637): input 1M=$5, output 1M=$25
out=$($clr "$HELPER" --claude-sub-input-tokens 1000000 --claude-sub-output-tokens 1000000)
test "$(read_kv CLAUDE_SUB_COST "$out")" = "30.00" || fail "claude_sub per-bucket priced at Claude rates: $(read_kv CLAUDE_SUB_COST "$out")"
test "$(read_kv CLAUDE_SUB_TOKENS "$out")" = "2000000" || fail "claude_sub per-bucket token count"
pass "claude_sub per-bucket Claude rates"

# (j) claude_sub aggregate uses the Claude blended rate ($0.80/M)
out=$($clr "$HELPER" --claude-sub-tokens 1000000)
test "$(read_kv CLAUDE_SUB_COST "$out")" = "0.80" || fail "claude_sub aggregate blended cost"
pass "claude_sub aggregate blended"

# (k) TOTAL_COST and TOTAL_TOKENS include the claude_sub lane
out=$($clr "$HELPER" --claude-tokens 1000000 --codex-tokens 1000000 --cursor-tokens 1000000 --claude-sub-tokens 1000000)
# claude 0.80 + codex 2.00 + cursor 1.50 + claude_sub 0.80 = 5.10
test "$(read_kv TOTAL_COST "$out")" = "5.10" || fail "TOTAL_COST includes claude_sub: $(read_kv TOTAL_COST "$out")"
test "$(read_kv TOTAL_TOKENS "$out")" = "4000000" || fail "TOTAL_TOKENS includes claude_sub"
pass "TOTAL includes claude_sub lane"

# (l) claude_sub rates are independent of CLAUDE_BUCKET: a claude_sub-only
# per-bucket invocation must use per-bucket Claude rates, not the blended
# fallback (regression guard for the rate-resolution gating).
out=$($clr "$HELPER" --claude-sub-input-tokens 1000000 2>/dev/null)
test "$(read_kv CLAUDE_SUB_COST "$out")" = "5.00" || fail "claude_sub-only per-bucket must price input at \$5/M, got $(read_kv CLAUDE_SUB_COST "$out")"
pass "claude_sub-only per-bucket uses per-bucket Claude rates"

printf 'PASS: test-token-cost.sh — %s checks\n' "$PASS"
