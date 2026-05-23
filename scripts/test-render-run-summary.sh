#!/usr/bin/env bash
# test-render-run-summary.sh — offline harness for render-run-summary.sh.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/render-run-summary.sh"
TMP="$(mktemp "${TMPDIR:-/tmp}/trs.XXXXXX")"
TMP_DEF=""
TMP_PART=""
TMP_ERR=""
TMP_ERR_STDERR=""
trap 'rm -f "$TMP" "$notes" "$TMP_DEF" "$TMP_PART" "$TMP_ERR" "$TMP_ERR_STDERR"' EXIT
PASS=0
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; PASS=$((PASS+1)); }

notes=$(mktemp)
printf '%s\n' "**Note:** fixture note" > "$notes"

LARCH_CLAUDE_RATE_PER_M=1 LARCH_CODEX_RATE_PER_M=2 LARCH_CURSOR_RATE_PER_M=3 \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-X \
    --mode '--quick' \
    --workflow-path SIMPLE \
    --duration '00:01:00' \
    --claude-tokens 1000000 \
    --codex-tokens 2000000 \
    --cursor-tokens 0 \
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
    --issue-number 9 \
    --issue-url 'https://github.com/o/r/issues/9' \
    --pr-number 10 \
    --pr-url 'https://github.com/o/r/pull/10' \
    --plan-review-line '1/2 accepted' \
    --code-review-line '3/4 accepted' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 1 \
    --warnings 2 \
    --run-logs-path 'larch-logs/implement/RUN-X/' \
    --note-lines-file "$notes" \
    --output-file "$TMP" >/dev/null 2>/dev/null

grep -Fq '<!-- larch:run-summary v=1 -->' "$TMP" || fail 'missing sentinel'
grep -Fq '## /implement run RUN-X — merged' "$TMP" || fail 'missing title outcome'
if grep -Fq '**Outcome**:' "$TMP"; then fail 'merged run must not emit Outcome bullet'; fi
grep -Fq '**PR**:' "$TMP" || fail 'missing PR bullet when URL known'
grep -Fq '**Note:** fixture note' "$TMP" || fail 'missing appended note'
grep -Fq "TOTAL ~\$5.00" "$TMP" || fail 'missing expected total cost line (approx prefix)'
pass 'render body shape + sentinel + notes + cost'

# Shipped defaults: 1M tokens each lane (aggregate-only) → blended 0.80 + 2.00 + 1.50 = 4.30 USD total.
TMP_DEF="$(mktemp "${TMPDIR:-/tmp}/trs-def.XXXXXX")"
env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-DEF \
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
    --output-file "$TMP_DEF" >/dev/null 2>/dev/null
grep -Fq "TOTAL ~\$4.30" "$TMP_DEF" || fail 'all-defaulted total cost'
grep -Fq "Claude \$0.80" "$TMP_DEF" || fail 'all-defaulted Claude slot'
grep -Fq "Codex \$2.00" "$TMP_DEF" || fail 'all-defaulted Codex slot'
grep -Fq "Cursor \$1.50" "$TMP_DEF" || fail 'all-defaulted Cursor slot'
if grep -Fq '**Tokens**:' "$TMP_DEF"; then fail 'legacy Tokens bullet must not appear'; fi
pass 'all-defaulted cost semantics (shipped blended defaults)'

# Explicit Claude rate only; zero-token lanes show $0.00 (defaults still apply for rates).
TMP_PART="$(mktemp "${TMPDIR:-/tmp}/trs-part.XXXXXX")"
LARCH_CLAUDE_RATE_PER_M=2 env -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-PART \
    --mode '--quick' \
    --workflow-path SIMPLE \
    --duration '00:01:00' \
    --claude-tokens 1000000 \
    --codex-tokens 0 \
    --cursor-tokens 0 \
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
    --output-file "$TMP_PART" >/dev/null 2>/dev/null
grep -Fq "TOTAL ~\$2.00" "$TMP_PART" || fail 'Claude-only priced total'
grep -Fq "Codex \$0.00" "$TMP_PART" || fail 'zero-token codex slot'
grep -Fq "Cursor \$0.00" "$TMP_PART" || fail 'zero-token cursor slot'
pass "priced Claude + zero-token lanes at \$0.00"

# stderr envelope pins (quiet diagnostics; not mixed into markdown file).
TMP_ERR="$(mktemp "${TMPDIR:-/tmp}/trs-err.XXXXXX")"
TMP_ERR_STDERR="$(mktemp "${TMPDIR:-/tmp}/trs-errstderr.XXXXXX")"
env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" \
    --skill implement \
    --outcome pr-open \
    --run-id RUN-ERR \
    --mode '/implement' \
    --workflow-path 'N/A' \
    --duration 'N/A' \
    --claude-tokens 0 \
    --codex-tokens 0 \
    --cursor-tokens 0 \
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
    --output-file "$TMP_ERR" \
    --print-stdout >/dev/null 2>"$TMP_ERR_STDERR"
grep -Fq 'STATUS=ok' "$TMP_ERR_STDERR" || fail 'stderr STATUS=ok'
grep -Fq 'OUTPUT_FILE=' "$TMP_ERR_STDERR" || fail 'stderr OUTPUT_FILE pin'
pass 'stderr STATUS and OUTPUT_FILE pins'

printf 'PASS=%s\n' "$PASS"
