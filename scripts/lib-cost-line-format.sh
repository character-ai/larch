#!/usr/bin/env bash
# lib-cost-line-format.sh — shared dollar-primary cost line (stdout, single line + newline).
# Sourced by token-report / render-cost-line / render-run-summary; no side effects when sourced.
set -euo pipefail

# Args: total_usd claude_usd codex_usd cursor_usd total_tokens_int
# Emits: 💰 Cost: TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k
larch_emit_cost_line() {
    local tc="${1:-0}" cc="${2:-0}" dc="${3:-0}" uc="${4:-0}" n="${5:-0}"
    local total_disp c_disp d_disp u_disp tok_k
    total_disp=$(awk -v x="$tc" 'BEGIN { printf "$%.2f\n", x+0 }' | tr -d '\n')
    c_disp=$(awk -v x="$cc" 'BEGIN { printf "$%.2f\n", x+0 }' | tr -d '\n')
    d_disp=$(awk -v x="$dc" 'BEGIN { printf "$%.2f\n", x+0 }' | tr -d '\n')
    u_disp=$(awk -v x="$uc" 'BEGIN { printf "$%.2f\n", x+0 }' | tr -d '\n')
    tok_k=$(awk -v n="$n" 'BEGIN {
      if (n == "") n = 0
      printf "%d\n", int((n+500)/1000)
    }')
    printf '💰 Cost: TOTAL ~%s — Claude %s, Codex %s, Cursor %s  |  Tokens: %sk\n' \
        "$total_disp" "$c_disp" "$d_disp" "$u_disp" "$tok_k"
}
