#!/usr/bin/env bash
# token-cost.sh — per-vendor token cost (per-bucket or blended fallback).
#
# Stateless; reads token counts from CLI and rates from env.
# Output: KEY=value lines on stdout (one per line).
# Blended fallback emits a one-line warning on stderr when used.
set -euo pipefail

# Anthropic Claude Opus 4.7 (verified 2026-05-22 against
# https://platform.claude.com/docs/en/about-claude/pricing).
DEFAULT_CLAUDE_INPUT_RATE_PER_M=5.00
DEFAULT_CLAUDE_CACHE_READ_RATE_PER_M=0.50
DEFAULT_CLAUDE_CACHE_WRITE_5M_RATE_PER_M=6.25
DEFAULT_CLAUDE_CACHE_WRITE_1H_RATE_PER_M=10.00
DEFAULT_CLAUDE_OUTPUT_RATE_PER_M=25.00

# OpenAI GPT-5.3-Codex (verified 2026-05-22 against
# https://developers.openai.com/codex/pricing).
DEFAULT_CODEX_INPUT_RATE_PER_M=0.44
DEFAULT_CODEX_CACHED_INPUT_RATE_PER_M=0.04
DEFAULT_CODEX_OUTPUT_RATE_PER_M=3.50

# Cursor Auto mode (verified 2026-05-22 against
# https://cursor.com/docs/models-and-pricing). MAX mode passes
# through the underlying model's rate.
DEFAULT_CURSOR_INPUT_RATE_PER_M=1.25
DEFAULT_CURSOR_CACHE_READ_RATE_PER_M=0.25
DEFAULT_CURSOR_OUTPUT_RATE_PER_M=6.00

# Conservative cache-heavy blended defaults when only aggregate counts are provided.
DEFAULT_CLAUDE_BLENDED_PER_M=0.80
DEFAULT_CODEX_BLENDED_PER_M=2.00
DEFAULT_CURSOR_BLENDED_PER_M=1.50

usage() {
    printf 'Usage: token-cost.sh [--per-bucket flags...] [--claude-tokens N --codex-tokens N --cursor-tokens N]\n' >&2
    printf 'Per-bucket: --claude-input-tokens N ... --claude-output-tokens N\n' >&2
    printf '            --codex-input-tokens N --codex-cached-input-tokens N --codex-output-tokens N\n' >&2
    printf '            --cursor-input-tokens N --cursor-cache-read-tokens N --cursor-output-tokens N\n' >&2
}

num() {
    case "${1:-}" in
        '') printf '0\n' ;;
        *[!0-9]*)
            printf '%s\n' "token-cost.sh: invalid non-integer token count: ${1:-}" >&2
            exit 2
            ;;
        *) printf '%s\n' "$1" ;;
    esac
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

cost_bucket() {
    local tokens="$1" rate="$2"
    if [ -z "$tokens" ] || [ "$tokens" -eq 0 ] 2>/dev/null; then
        printf '0\n'
        return 0
    fi
    awk -v t="$tokens" -v r="$rate" 'BEGIN { printf "%.6f\n", (t/1000000)*r }'
}

sum_money() {
    awk -v a="${1:-0}" -v b="${2:-0}" -v c="${3:-0}" -v d="${4:-0}" -v e="${5:-0}" 'BEGIN {
      printf "%.2f\n", (a+0)+(b+0)+(c+0)+(d+0)+(e+0)
    }'
}

# --- Arg parse ---
CLAUDE_T=0 CODEX_T=0 CURSOR_T=0
C_IN=0 C_CR=0 C_CW5=0 C_CW1=0 C_OUT=0
D_IN=0 D_CACHED=0 D_OUT=0
U_IN=0 U_CR=0 U_OUT=0

CLAUDE_BUCKET=false CODEX_BUCKET=false CURSOR_BUCKET=false

while [ $# -gt 0 ]; do
    case "$1" in
        --claude-tokens)           CLAUDE_T=$(num "${2:-0}"); shift 2 ;;
        --codex-tokens)            CODEX_T=$(num "${2:-0}"); shift 2 ;;
        --cursor-tokens)           CURSOR_T=$(num "${2:-0}"); shift 2 ;;
        --claude-input-tokens)     CLAUDE_BUCKET=true; C_IN=$(num "${2:-0}"); shift 2 ;;
        --claude-cache-read-tokens) CLAUDE_BUCKET=true; C_CR=$(num "${2:-0}"); shift 2 ;;
        --claude-cache-write-5m-tokens) CLAUDE_BUCKET=true; C_CW5=$(num "${2:-0}"); shift 2 ;;
        --claude-cache-write-1h-tokens) CLAUDE_BUCKET=true; C_CW1=$(num "${2:-0}"); shift 2 ;;
        --claude-output-tokens)    CLAUDE_BUCKET=true; C_OUT=$(num "${2:-0}"); shift 2 ;;
        --codex-input-tokens)      CODEX_BUCKET=true; D_IN=$(num "${2:-0}"); shift 2 ;;
        --codex-cached-input-tokens) CODEX_BUCKET=true; D_CACHED=$(num "${2:-0}"); shift 2 ;;
        --codex-output-tokens)     CODEX_BUCKET=true; D_OUT=$(num "${2:-0}"); shift 2 ;;
        --cursor-input-tokens)     CURSOR_BUCKET=true; U_IN=$(num "${2:-0}"); shift 2 ;;
        --cursor-cache-read-tokens) CURSOR_BUCKET=true; U_CR=$(num "${2:-0}"); shift 2 ;;
        --cursor-output-tokens)    CURSOR_BUCKET=true; U_OUT=$(num "${2:-0}"); shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
done

BLENDED_WARN=false

# --- Resolve rates ---
# Aggregate/blended path: per-bucket env > legacy blended env > per-bucket default.
# Per-bucket invocation path: per-bucket env > per-bucket default (legacy blended env applies
# only to aggregate lanes — see branch above).
claude_blended_raw="${LARCH_CLAUDE_RATE_PER_M:-}"
if [ -z "$claude_blended_raw" ] || [ "$claude_blended_raw" = "0" ]; then
    claude_blended_raw="${LARCH_TOKEN_RATE_PER_M:-}"
fi
codex_blended_raw="${LARCH_CODEX_RATE_PER_M:-}"
cursor_blended_raw="${LARCH_CURSOR_RATE_PER_M:-}"

# Per-bucket rate resolution: per-bucket env > per-bucket default only (legacy blended env vars
# apply to aggregate/blended paths only — avoids mis-pricing individual buckets when an
# operator keeps LARCH_*_RATE_PER_M overrides from the pre-bucket era).
if [ "$CLAUDE_BUCKET" = true ]; then
    R_C_IN=$(rate_or_default "${LARCH_CLAUDE_INPUT_RATE_PER_M:-}" "$DEFAULT_CLAUDE_INPUT_RATE_PER_M")
    R_C_CR=$(rate_or_default "${LARCH_CLAUDE_CACHE_READ_RATE_PER_M:-}" "$DEFAULT_CLAUDE_CACHE_READ_RATE_PER_M")
    R_C_CW5=$(rate_or_default "${LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M:-}" "$DEFAULT_CLAUDE_CACHE_WRITE_5M_RATE_PER_M")
    R_C_CW1=$(rate_or_default "${LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M:-}" "$DEFAULT_CLAUDE_CACHE_WRITE_1H_RATE_PER_M")
    R_C_OUT=$(rate_or_default "${LARCH_CLAUDE_OUTPUT_RATE_PER_M:-}" "$DEFAULT_CLAUDE_OUTPUT_RATE_PER_M")
else
    R_C_IN=$(rate_or_default "${LARCH_CLAUDE_INPUT_RATE_PER_M:-}" "$(rate_or_default "$claude_blended_raw" "$DEFAULT_CLAUDE_INPUT_RATE_PER_M")")
    R_C_CR=$(rate_or_default "${LARCH_CLAUDE_CACHE_READ_RATE_PER_M:-}" "$(rate_or_default "$claude_blended_raw" "$DEFAULT_CLAUDE_CACHE_READ_RATE_PER_M")")
    R_C_CW5=$(rate_or_default "${LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M:-}" "$(rate_or_default "$claude_blended_raw" "$DEFAULT_CLAUDE_CACHE_WRITE_5M_RATE_PER_M")")
    R_C_CW1=$(rate_or_default "${LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M:-}" "$(rate_or_default "$claude_blended_raw" "$DEFAULT_CLAUDE_CACHE_WRITE_1H_RATE_PER_M")")
    R_C_OUT=$(rate_or_default "${LARCH_CLAUDE_OUTPUT_RATE_PER_M:-}" "$(rate_or_default "$claude_blended_raw" "$DEFAULT_CLAUDE_OUTPUT_RATE_PER_M")")
fi
if [ "$CODEX_BUCKET" = true ]; then
    R_D_IN=$(rate_or_default "${LARCH_CODEX_INPUT_RATE_PER_M:-}" "$DEFAULT_CODEX_INPUT_RATE_PER_M")
    R_D_CACHED=$(rate_or_default "${LARCH_CODEX_CACHED_INPUT_RATE_PER_M:-}" "$DEFAULT_CODEX_CACHED_INPUT_RATE_PER_M")
    R_D_OUT=$(rate_or_default "${LARCH_CODEX_OUTPUT_RATE_PER_M:-}" "$DEFAULT_CODEX_OUTPUT_RATE_PER_M")
else
    R_D_IN=$(rate_or_default "${LARCH_CODEX_INPUT_RATE_PER_M:-}" "$(rate_or_default "$codex_blended_raw" "$DEFAULT_CODEX_INPUT_RATE_PER_M")")
    R_D_CACHED=$(rate_or_default "${LARCH_CODEX_CACHED_INPUT_RATE_PER_M:-}" "$(rate_or_default "$codex_blended_raw" "$DEFAULT_CODEX_CACHED_INPUT_RATE_PER_M")")
    R_D_OUT=$(rate_or_default "${LARCH_CODEX_OUTPUT_RATE_PER_M:-}" "$(rate_or_default "$codex_blended_raw" "$DEFAULT_CODEX_OUTPUT_RATE_PER_M")")
fi
if [ "$CURSOR_BUCKET" = true ]; then
    R_U_IN=$(rate_or_default "${LARCH_CURSOR_INPUT_RATE_PER_M:-}" "$DEFAULT_CURSOR_INPUT_RATE_PER_M")
    R_U_CR=$(rate_or_default "${LARCH_CURSOR_CACHE_READ_RATE_PER_M:-}" "$DEFAULT_CURSOR_CACHE_READ_RATE_PER_M")
    R_U_OUT=$(rate_or_default "${LARCH_CURSOR_OUTPUT_RATE_PER_M:-}" "$DEFAULT_CURSOR_OUTPUT_RATE_PER_M")
else
    R_U_IN=$(rate_or_default "${LARCH_CURSOR_INPUT_RATE_PER_M:-}" "$(rate_or_default "$cursor_blended_raw" "$DEFAULT_CURSOR_INPUT_RATE_PER_M")")
    R_U_CR=$(rate_or_default "${LARCH_CURSOR_CACHE_READ_RATE_PER_M:-}" "$(rate_or_default "$cursor_blended_raw" "$DEFAULT_CURSOR_CACHE_READ_RATE_PER_M")")
    R_U_OUT=$(rate_or_default "${LARCH_CURSOR_OUTPUT_RATE_PER_M:-}" "$(rate_or_default "$cursor_blended_raw" "$DEFAULT_CURSOR_OUTPUT_RATE_PER_M")")
fi

# Blended-only rates (aggregate path)
R_C_BLEND=$(rate_or_default "$claude_blended_raw" "$DEFAULT_CLAUDE_BLENDED_PER_M")
R_D_BLEND=$(rate_or_default "$codex_blended_raw" "$DEFAULT_CODEX_BLENDED_PER_M")
R_U_BLEND=$(rate_or_default "$cursor_blended_raw" "$DEFAULT_CURSOR_BLENDED_PER_M")

cost_for_blend() {
    local tokens="$1" rate="$2"
    if [ -z "$tokens" ] || [ "$tokens" -eq 0 ] 2>/dev/null; then
        printf '0.00\n'
        return 0
    fi
    awk -v t="$tokens" -v r="$rate" 'BEGIN { printf "%.2f\n", (t/1000000)*r }'
}

# --- Claude cost ---
if [ "$CLAUDE_BUCKET" = true ]; then
    p1=$(cost_bucket "$C_IN" "$R_C_IN")
    p2=$(cost_bucket "$C_CR" "$R_C_CR")
    p3=$(cost_bucket "$C_CW5" "$R_C_CW5")
    p4=$(cost_bucket "$C_CW1" "$R_C_CW1")
    p5=$(cost_bucket "$C_OUT" "$R_C_OUT")
    claude_c=$(sum_money "$p1" "$p2" "$p3" "$p4" "$p5")
    CLAUDE_T=$((C_IN + C_CR + C_CW5 + C_CW1 + C_OUT))
else
    if [ "${CLAUDE_T:-0}" -gt 0 ] 2>/dev/null; then
        BLENDED_WARN=true
    fi
    claude_c=$(cost_for_blend "$CLAUDE_T" "$R_C_BLEND")
fi

# --- Codex cost ---
if [ "$CODEX_BUCKET" = true ]; then
    q1=$(cost_bucket "$D_IN" "$R_D_IN")
    q2=$(cost_bucket "$D_CACHED" "$R_D_CACHED")
    q3=$(cost_bucket "$D_OUT" "$R_D_OUT")
    codex_c=$(sum_money "$q1" "$q2" "$q3" 0 0)
    CODEX_T=$((D_IN + D_CACHED + D_OUT))
else
    if [ "${CODEX_T:-0}" -gt 0 ] 2>/dev/null; then
        BLENDED_WARN=true
    fi
    codex_c=$(cost_for_blend "$CODEX_T" "$R_D_BLEND")
fi

# --- Cursor cost ---
if [ "$CURSOR_BUCKET" = true ]; then
    r1=$(cost_bucket "$U_IN" "$R_U_IN")
    r2=$(cost_bucket "$U_CR" "$R_U_CR")
    r3=$(cost_bucket "$U_OUT" "$R_U_OUT")
    cursor_c=$(sum_money "$r1" "$r2" "$r3" 0 0)
    CURSOR_T=$((U_IN + U_CR + U_OUT))
else
    if [ "${CURSOR_T:-0}" -gt 0 ] 2>/dev/null; then
        BLENDED_WARN=true
    fi
    cursor_c=$(cost_for_blend "$CURSOR_T" "$R_U_BLEND")
fi

if [ "$BLENDED_WARN" = true ]; then
    printf '%s\n' "token-cost.sh: WARNING: per-bucket counts unavailable; using blended rate (may overstate by ~3-10x)" >&2
fi

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
