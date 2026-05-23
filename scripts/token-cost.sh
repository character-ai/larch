#!/usr/bin/env bash
# token-cost.sh — per-vendor token cost (implement / fix-issue final summary).
#
# Stateless; reads token counts from CLI and rates from env.
# Output: KEY=value lines on stdout (one per line).
set -euo pipefail

# USD per 1M total tokens (blended estimate defaults when env rates are unset,
# empty, zero, or malformed). Explicit LARCH_*_RATE_PER_M overrides these.
DEFAULT_CLAUDE_RATE_PER_M=6.00
DEFAULT_CODEX_RATE_PER_M=10.00
DEFAULT_CURSOR_RATE_PER_M=10.00

usage() {
    printf 'Usage: token-cost.sh --claude-tokens N --codex-tokens N --cursor-tokens N\n' >&2
}

num() {
    case "${1:-}" in ''|*[!0-9]*) printf '0\n' ;; *) printf '%s\n' "$1" ;; esac
}

# Valid positive decimal: optional fraction; empty / zero / malformed → use default.
rate_or_default() {
    local raw="$1" default="$2"
    case "$raw" in
        ''|0) printf '%s\n' "$default" ;;
        *)
            if printf '%s' "$raw" | grep -Eq '^[0-9]+(\.[0-9]+)?$'; then
                case "$raw" in
                    0|0.0+) printf '%s\n' "$default" ;;
                    *) printf '%s\n' "$raw" ;;
                esac
            else
                printf '%s\n' "$default"
            fi
            ;;
    esac
}

cost_for() {
    local tokens="$1" rate="$2"
    local c
    if [ -z "$tokens" ] || [ "$tokens" -eq 0 ] 2>/dev/null; then
        printf '0.00\n'
        return 0
    fi
    c=$(awk -v t="$tokens" -v r="$rate" 'BEGIN { printf "%.2f\n", (t/1000000)*r }')
    printf '%s\n' "$c"
}

CLAUDE_T=0
CODEX_T=0
CURSOR_T=0

while [ $# -gt 0 ]; do
    case "$1" in
        --claude-tokens)  CLAUDE_T=$(num "${2:-0}");  shift 2 ;;
        --codex-tokens)   CODEX_T=$(num "${2:-0}");   shift 2 ;;
        --cursor-tokens)  CURSOR_T=$(num "${2:-0}");  shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

claude_rate_raw="${LARCH_CLAUDE_RATE_PER_M:-}"
[ -z "$claude_rate_raw" ] || [ "$claude_rate_raw" = "0" ] && claude_rate_raw="${LARCH_TOKEN_RATE_PER_M:-}"

codex_rate_raw="${LARCH_CODEX_RATE_PER_M:-}"
cursor_rate_raw="${LARCH_CURSOR_RATE_PER_M:-}"

claude_r=$(rate_or_default "$claude_rate_raw" "$DEFAULT_CLAUDE_RATE_PER_M")
codex_r=$(rate_or_default "$codex_rate_raw" "$DEFAULT_CODEX_RATE_PER_M")
cursor_r=$(rate_or_default "$cursor_rate_raw" "$DEFAULT_CURSOR_RATE_PER_M")

claude_c=$(cost_for "$CLAUDE_T" "$claude_r")
codex_c=$(cost_for "$CODEX_T" "$codex_r")
cursor_c=$(cost_for "$CURSOR_T" "$cursor_r")

total=$(awk -v a="$claude_c" -v b="$codex_c" -v c="$cursor_c" 'BEGIN {
  printf "%.2f\n", (a+0)+(b+0)+(c+0)
}')

printf 'CLAUDE_COST=%s\n' "$claude_c"
printf 'CODEX_COST=%s\n' "$codex_c"
printf 'CURSOR_COST=%s\n' "$cursor_c"
printf 'TOTAL_COST=%s\n' "$total"
printf 'CLAUDE_TOKENS=%s\n' "$CLAUDE_T"
printf 'CODEX_TOKENS=%s\n' "$CODEX_T"
printf 'CURSOR_TOKENS=%s\n' "$CURSOR_T"
printf 'TOTAL_TOKENS=%s\n' "$((CLAUDE_T + CODEX_T + CURSOR_T))"
