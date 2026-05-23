#!/usr/bin/env bash
# render-cost-line.sh — single-line terminal cost + token summary for /design.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TOKEN_COST_SH="$SCRIPT_DIR/token-cost.sh"

usage() {
    printf 'Usage: render-cost-line.sh --claude-tokens N --codex-tokens N --cursor-tokens N [--quiet-on-empty]\n' >&2
}

CLAUDE_T=0
CODEX_T=0
CURSOR_T=0
QUIET_ON_EMPTY=false

while [ $# -gt 0 ]; do
    case "$1" in
        --claude-tokens)  CLAUDE_T=${2:-0}; shift 2 ;;
        --codex-tokens)   CODEX_T=${2:-0}; shift 2 ;;
        --cursor-tokens)  CURSOR_T=${2:-0}; shift 2 ;;
        --quiet-on-empty) QUIET_ON_EMPTY=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

case "$CLAUDE_T$CODEX_T$CURSOR_T" in *[!0-9]*)
    usage
    exit 2
    ;;
esac

if "$QUIET_ON_EMPTY" && [ "$CLAUDE_T" -eq 0 ] && [ "$CODEX_T" -eq 0 ] && [ "$CURSOR_T" -eq 0 ]; then
    exit 0
fi

read_kv() {
    local key=$1 v
    v=$(printf '%s\n' "$cost_lines" | awk -F= -v k="$key" '$1==k{print $2; exit}')
    [ -n "$v" ] && printf '%s\n' "$v" || printf '0.00\n'
}

cost_lines=$("$TOKEN_COST_SH" \
    --claude-tokens "$CLAUDE_T" \
    --codex-tokens "$CODEX_T" \
    --cursor-tokens "$CURSOR_T" 2>/dev/null || true)

tc=$(read_kv TOTAL_COST)
cc=$(read_kv CLAUDE_COST)
dc=$(read_kv CODEX_COST)
uc=$(read_kv CURSOR_COST)

fmt_usd() {
    awk -v x="${1:-0}" 'BEGIN { printf "$%.2f\n", x+0 }' | tr -d '\n'
}

total_disp=$(fmt_usd "$tc")
c_disp=$(fmt_usd "$cc")
d_disp=$(fmt_usd "$dc")
u_disp=$(fmt_usd "$uc")

tok_k=$(awk -v n="$((CLAUDE_T + CODEX_T + CURSOR_T))" 'BEGIN {
  if (n == "") n = 0
  printf "%d\n", int((n+500)/1000)
}')

printf '💰 Cost: TOTAL ~%s — Claude %s, Codex %s, Cursor %s  |  Tokens: %sk\n' \
    "$total_disp" "$c_disp" "$d_disp" "$u_disp" "$tok_k"
