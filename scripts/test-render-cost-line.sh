#!/usr/bin/env bash
# test-render-cost-line.sh — offline harness for scripts/render-cost-line.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd -P)"
RCL="$SCRIPT_DIR/render-cost-line.sh"
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { PASS=$((PASS + 1)); }

want_line="💰 Cost: TOTAL ~\$9.30 — Claude \$0.80, Codex \$4.00, Cursor \$4.50  |  Tokens: 6000k"

# (a) all rates defaulted (unset vendor rate env)
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 1000000 --codex-tokens 2000000 --cursor-tokens 3000000)
test "$out" = "$want_line" || fail "default-rate line mismatch: got $out"
pass "all-defaulted exact line"

# (b) explicit rates
out=$(LARCH_CLAUDE_RATE_PER_M=1 LARCH_CODEX_RATE_PER_M=2 LARCH_CURSOR_RATE_PER_M=3 \
    "$RCL" --claude-tokens 1000000 --codex-tokens 2000000 --cursor-tokens 0)
test "$out" = "💰 Cost: TOTAL ~\$5.00 — Claude \$1.00, Codex \$4.00, Cursor \$0.00  |  Tokens: 3000k" || fail "explicit rates: $out"
pass "explicit rates line"

# (c) one vendor zero tokens still emits $0.00
out=$(env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$RCL" --claude-tokens 0 --codex-tokens 1000000 --cursor-tokens 0)
test "$out" = "💰 Cost: TOTAL ~\$2.00 — Claude \$0.00, Codex \$2.00, Cursor \$0.00  |  Tokens: 1000k" || fail "zero vendor: $out"
pass "zero-token vendor shows 0.00"

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

printf 'PASS: test-render-cost-line.sh — %s checks\n' "$PASS"
