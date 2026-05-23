#!/usr/bin/env bash
# test-render-run-summary-format.sh — bug-4: single Cost bullet, no Tokens bullet (DE-2622).
set -euo pipefail
export LARCH_QUIET_DISABLE=1
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
HELPER="$REPO/scripts/render-run-summary.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

TMP="$(mktemp "${TMPDIR:-/tmp}/trsf.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-FMT \
    --mode '--quick' \
    --workflow-path SIMPLE \
    --duration '00:01:00' \
    --claude-tokens 1000000 \
    --codex-tokens 1000000 \
    --cursor-tokens 1000000 \
    --claude-input-tokens 0 \
    --claude-cache-read-tokens 0 \
    --claude-cache-write-5m-tokens 0 \
    --claude-cache-write-1h-tokens 0 \
    --claude-output-tokens 0 \
    --codex-input-tokens 0 \
    --codex-cached-input-tokens 0 \
    --codex-output-tokens 0 \
    --cursor-input-tokens 0 \
    --cursor-cache-read-tokens 0 \
    --cursor-output-tokens 0 \
    --issue-number 0 \
    --issue-url 'N/A' \
    --pr-number 0 \
    --pr-url 'N/A' \
    --plan-review-line 'N/A' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'N/A' \
    --output-file "$TMP" >/dev/null 2>/dev/null

grep -Fq -- '- **Cost**: 💰 TOTAL ~$' "$TMP" || fail 'missing dollar-primary Cost bullet prefix'
grep -Fq -- 'Claude $' "$TMP" || fail 'missing Claude vendor dollars'
grep -Fq -- 'Codex $' "$TMP" || fail 'missing Codex vendor dollars'
grep -Fq -- 'Cursor $' "$TMP" || fail 'missing Cursor vendor dollars'
grep -Fq -- '  |  Tokens:' "$TMP" || fail 'missing token suffix on Cost line'
if grep -Fq -- '**Tokens**:' "$TMP"; then fail 'standalone Tokens bullet must not appear'; fi
pass 'render-run-summary markdown cost shape'

printf 'PASS: test-render-run-summary-format.sh\n'
