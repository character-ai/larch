#!/usr/bin/env bash
# render-cost-line.sh — single-line terminal cost + token summary for /design.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TOKEN_COST_SH="$SCRIPT_DIR/token-cost.sh"
# shellcheck source=scripts/lib-cost-line-format.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-cost-line-format.sh"

usage() {
    printf 'Usage: render-cost-line.sh [--per-bucket flags] [--claude-tokens N ...] [--quiet-on-empty]\n' >&2
}

CLAUDE_T=0 CODEX_T=0 CURSOR_T=0
C_IN=0 C_CR=0 C_CW5=0 C_CW1=0 C_OUT=0
D_IN=0 D_CACHED=0 D_OUT=0
U_IN=0 U_CR=0 U_OUT=0
QUIET_ON_EMPTY=false

while [ $# -gt 0 ]; do
    case "$1" in
        --claude-tokens)  CLAUDE_T=${2:-0}; shift 2 ;;
        --codex-tokens)   CODEX_T=${2:-0}; shift 2 ;;
        --cursor-tokens)  CURSOR_T=${2:-0}; shift 2 ;;
        --claude-input-tokens)     C_IN=${2:-0}; shift 2 ;;
        --claude-cache-read-tokens) C_CR=${2:-0}; shift 2 ;;
        --claude-cache-write-5m-tokens) C_CW5=${2:-0}; shift 2 ;;
        --claude-cache-write-1h-tokens) C_CW1=${2:-0}; shift 2 ;;
        --claude-output-tokens)    C_OUT=${2:-0}; shift 2 ;;
        --codex-input-tokens)      D_IN=${2:-0}; shift 2 ;;
        --codex-cached-input-tokens) D_CACHED=${2:-0}; shift 2 ;;
        --codex-output-tokens)     D_OUT=${2:-0}; shift 2 ;;
        --cursor-input-tokens)     U_IN=${2:-0}; shift 2 ;;
        --cursor-cache-read-tokens) U_CR=${2:-0}; shift 2 ;;
        --cursor-output-tokens)    U_OUT=${2:-0}; shift 2 ;;
        --quiet-on-empty) QUIET_ON_EMPTY=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

case "$CLAUDE_T$CODEX_T$CURSOR_T$C_IN$C_CR$C_CW5$C_CW1$C_OUT$D_IN$D_CACHED$D_OUT$U_IN$U_CR$U_OUT" in *[!0-9]*)
    usage
    exit 2
    ;;
esac

if "$QUIET_ON_EMPTY" && [ "$CLAUDE_T" -eq 0 ] && [ "$CODEX_T" -eq 0 ] && [ "$CURSOR_T" -eq 0 ] \
    && [ "$C_IN" -eq 0 ] && [ "$C_CR" -eq 0 ] && [ "$C_CW5" -eq 0 ] && [ "$C_CW1" -eq 0 ] && [ "$C_OUT" -eq 0 ] \
    && [ "$D_IN" -eq 0 ] && [ "$D_CACHED" -eq 0 ] && [ "$D_OUT" -eq 0 ] \
    && [ "$U_IN" -eq 0 ] && [ "$U_CR" -eq 0 ] && [ "$U_OUT" -eq 0 ]; then
    exit 0
fi

read_kv() {
    local key=$1 v
    v=$(printf '%s\n' "$cost_lines" | awk -F= -v k="$key" '$1==k{print $2; exit}')
    [ -n "$v" ] && printf '%s\n' "$v" || printf '0.00\n'
}

cost_errf=$(mktemp "${TMPDIR:-/tmp}/rcl-err.XXXXXX")
trap 'rm -f "$cost_errf"' EXIT

codex_args=(--codex-input-tokens "$D_IN" --codex-cached-input-tokens "$D_CACHED" --codex-output-tokens "$D_OUT")
if [ "$((D_IN + D_CACHED + D_OUT))" -eq 0 ] && [ "$CODEX_T" -gt 0 ]; then
    codex_args=(--codex-tokens "$CODEX_T")
fi
cursor_args=(--cursor-input-tokens "$U_IN" --cursor-cache-read-tokens "$U_CR" --cursor-output-tokens "$U_OUT")
if [ "$((U_IN + U_CR + U_OUT))" -eq 0 ] && [ "$CURSOR_T" -gt 0 ]; then
    cursor_args=(--cursor-tokens "$CURSOR_T")
fi

if [ "$((C_IN + C_CR + C_CW5 + C_CW1 + C_OUT))" -gt 0 ]; then
    claude_args=(
        --claude-input-tokens "$C_IN"
        --claude-cache-read-tokens "$C_CR"
        --claude-cache-write-5m-tokens "$C_CW5"
        --claude-cache-write-1h-tokens "$C_CW1"
        --claude-output-tokens "$C_OUT"
    )
else
    claude_args=(--claude-tokens "$CLAUDE_T")
fi
cost_lines=$("$TOKEN_COST_SH" \
    "${claude_args[@]}" \
    "${codex_args[@]}" \
    "${cursor_args[@]}" \
    2>"$cost_errf") || cost_lines=""
if [ -s "$cost_errf" ]; then
    cat "$cost_errf" >&2
fi

tc=$(read_kv TOTAL_COST)
cc=$(read_kv CLAUDE_COST)
dc=$(read_kv CODEX_COST)
uc=$(read_kv CURSOR_COST)
tt=$(read_kv TOTAL_TOKENS)

larch_emit_cost_line "$tc" "$cc" "$dc" "$uc" "$tt"
