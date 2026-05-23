#!/usr/bin/env bash
# test-render-cost-line-realism.sh — optional ±10% check vs hand reference (DE-2622).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
FX="$REPO/scripts/fixtures/token-cost-realism-2026-05.jsonl"
RCL="$REPO/scripts/render-cost-line.sh"
TC="$REPO/scripts/token-cost.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

if [[ ! -f "$FX" ]]; then
    printf 'SKIP: test-render-cost-line-realism.sh (fixture absent: %s)\n' "$FX"
    exit 0
fi

probe=$(jq -c 'select(.kind=="cost_probe")' "$FX" | head -1)
[[ -n "$probe" ]] || fail "fixture missing cost_probe record"

ref=$(jq -r '.ref_usd' <<<"$probe")
[[ -n "$ref" && "$ref" != "null" ]] || fail "fixture missing ref_usd"

ci=$(jq -r '.claude.input // 0' <<<"$probe")
ccr=$(jq -r '.claude.cache_read // 0' <<<"$probe")
cc5=$(jq -r '.claude.cache_write_5m // 0' <<<"$probe")
cc1=$(jq -r '.claude.cache_write_1h // 0' <<<"$probe")
co=$(jq -r '.claude.output // 0' <<<"$probe")
d_tot=$(jq -r '.codex.aggregate_tokens // 0' <<<"$probe")
u_tot=$(jq -r '.cursor.aggregate_tokens // 0' <<<"$probe")

clr='env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M'

cost_kv=$($clr "$TC" \
    --claude-input-tokens "$ci" \
    --claude-cache-read-tokens "$ccr" \
    --claude-cache-write-5m-tokens "$cc5" \
    --claude-cache-write-1h-tokens "$cc1" \
    --claude-output-tokens "$co" \
    --codex-tokens "$d_tot" \
    --cursor-tokens "$u_tot")
ref_tc=$(printf '%s\n' "$cost_kv" | awk -F= '$1=="TOTAL_COST"{print $2; exit}')
[[ -n "$ref_tc" ]] || fail "token-cost did not emit TOTAL_COST="

awk -v r="$ref" -v t="$ref_tc" 'BEGIN {
  if (r + 0 == 0) exit 1
  d = (t > r) ? (t - r) / r : (r - t) / r
  exit !(d < 1e-6)
}' </dev/null || fail "fixture ref_usd $ref mismatches token-cost TOTAL_COST=$ref_tc"

line=$($clr "$RCL" \
    --claude-input-tokens "$ci" \
    --claude-cache-read-tokens "$ccr" \
    --claude-cache-write-5m-tokens "$cc5" \
    --claude-cache-write-1h-tokens "$cc1" \
    --claude-output-tokens "$co" \
    --codex-tokens "$d_tot" \
    --cursor-tokens "$u_tot")
rest="${line#*TOTAL ~\$}"
got="${rest%% —*}"
[[ -n "$got" ]] || fail "could not parse TOTAL from cost line: $line"

awk -v r="$ref_tc" -v g="$got" 'BEGIN {
  if (r + 0 <= 0) exit 1
  d = (g > r) ? (g - r) / r : (r - g) / r
  exit !(d <= 0.10 + 1e-9)
}' </dev/null || fail "render-cost-line total $got not within ±10% of token-cost TOTAL_COST=$ref_tc"

pass "realism: render-cost-line within ±10% of token-cost for fixture probe"
printf 'PASS: test-render-cost-line-realism.sh\n'
