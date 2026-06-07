#!/usr/bin/env bash
# test-render-cost-line.sh — offline harness for scripts/render-cost-line.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd -P)"
RCL="$SCRIPT_DIR/render-cost-line.sh"
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { PASS=$((PASS + 1)); }

want_line="💰 Cost: TOTAL ~\$9.30 — Claude \$0.80, Codex \$4.00, Cursor \$4.50, Claude (subprocess) \$0.00  |  Tokens: 6000k"

# (a) all rates defaulted (unset vendor rate env)
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 1000000 --codex-tokens 2000000 --cursor-tokens 3000000)
test "$out" = "$want_line" || fail "default-rate line mismatch: got $out"
pass "all-defaulted exact line"

# (b) explicit rates
out=$(LARCH_CLAUDE_RATE_PER_M=1 LARCH_CODEX_RATE_PER_M=2 LARCH_CURSOR_RATE_PER_M=3 \
    "$RCL" --claude-tokens 1000000 --codex-tokens 2000000 --cursor-tokens 0)
test "$out" = "💰 Cost: TOTAL ~\$5.00 — Claude \$1.00, Codex \$4.00, Cursor \$0.00, Claude (subprocess) \$0.00  |  Tokens: 3000k" || fail "explicit rates: $out"
pass "explicit rates line"

# (c) one vendor zero tokens still emits $0.00
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0)
test "$out" = "💰 Cost: TOTAL ~\$2.00 — Claude \$0.00, Codex \$2.00, Cursor \$0.00, Claude (subprocess) \$0.00  |  Tokens: 1000k" || fail "zero vendor: $out"
pass "zero-token vendor shows 0.00"

# (c2) claude_sub lane priced at Claude rates and summed into the total (issue #3637)
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 0 --codex-tokens 0 --cursor-tokens 0 \
    --claude-sub-input-tokens 1000000 --claude-sub-output-tokens 1000000)
test "$out" = "💰 Cost: TOTAL ~\$30.00 — Claude \$0.00, Codex \$0.00, Cursor \$0.00, Claude (subprocess) \$30.00  |  Tokens: 2000k" || fail "claude_sub lane: $out"
pass "claude_sub lane priced at Claude rates"

# (c3) --quiet-on-empty stays quiet when only claude_sub tokens are also zero
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 0 --codex-tokens 0 --cursor-tokens 0 --claude-sub-tokens 0 --quiet-on-empty)
test -z "$out" || fail "quiet-on-empty with claude_sub should print nothing, got: $out"
pass "quiet-on-empty honors claude_sub"

# (c4) --quiet-on-empty still prints when only claude_sub has tokens
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-sub-input-tokens 1000000 --quiet-on-empty)
test -n "$out" || fail "quiet-on-empty must still emit when claude_sub has tokens"
pass "quiet-on-empty emits for claude_sub-only usage"

# (d) --quiet-on-empty all zero
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 0 --codex-tokens 0 --cursor-tokens 0 --quiet-on-empty)
test -z "$out" || fail "quiet-on-empty should print nothing, got: $out"
pass "quiet-on-empty"

# (e) byte-pin punctuation (emoji, em dash, double-space, pipe)
case "$want_line" in
    *'💰 Cost: TOTAL ~$'*) ;;
    *) fail "missing cost prefix / emoji" ;;
esac
case "$want_line" in
    *' — Claude $'*) ;;
    *) fail "missing em dash segment" ;;
esac
case "$want_line" in
    *'  |  Tokens:'*) ;;
    *) fail "missing double-spaced pipe segment" ;;
esac
pass "byte-pin punctuation"

# (f) per-bucket Codex flags route through token-cost without blended warning
stderr_file=$(mktemp "${TMPDIR:-/tmp}/render-cost-line-stderr.XXXXXX")
cost_kv=$("$SCRIPT_DIR/token-cost.sh" \
    --codex-input-tokens 1000000 \
    --codex-cached-input-tokens 9000000 \
    --codex-output-tokens 500000)
read_kv() {
    local key=$1
    printf '%s\n' "$cost_kv" | awk -F= -v k="$key" '$1==k{print $2; exit}'
}
total_cost=$(read_kv TOTAL_COST)
claude_cost=$(read_kv CLAUDE_COST)
codex_cost=$(read_kv CODEX_COST)
cursor_cost=$(read_kv CURSOR_COST)
claude_sub_cost=$(read_kv CLAUDE_SUB_COST)
total_tokens_k=$(($(read_kv TOTAL_TOKENS) / 1000))
expected_line="💰 Cost: TOTAL ~\$$total_cost — Claude \$$claude_cost, Codex \$$codex_cost, Cursor \$$cursor_cost, Claude (subprocess) \$$claude_sub_cost  |  Tokens: ${total_tokens_k}k"
out=$("$RCL" --codex-input-tokens 1000000 --codex-cached-input-tokens 9000000 --codex-output-tokens 500000 2>"$stderr_file")
test "$out" = "$expected_line" \
    || fail "per-bucket codex flags line mismatch: got $out"
if grep -Eq 'BLENDED_WARN|blended rate' "$stderr_file"; then
    fail "per-bucket codex flags should not warn: $(cat "$stderr_file")"
fi
rm -f "$stderr_file"
pass "per-bucket codex flags"

printf 'PASS: test-render-cost-line.sh — %s checks\n' "$PASS"
