#!/usr/bin/env bash
# test-render-run-summary.sh — offline harness for render-run-summary.sh.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/render-run-summary.sh"
TMP="$(mktemp "${TMPDIR:-/tmp}/trs.XXXXXX")"
TMP_NA=""
TMP_PART=""
TMP_ERR=""
TMP_ERR_STDERR=""
trap 'rm -f "$TMP" "$notes" "$TMP_NA" "$TMP_PART" "$TMP_ERR" "$TMP_ERR_STDERR"' EXIT
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

# All vendor costs N/A (zero rates: totals stay N/A even with non-zero tokens).
TMP_NA="$(mktemp "${TMPDIR:-/tmp}/trs-na.XXXXXX")"
LARCH_CLAUDE_RATE_PER_M=0 LARCH_CODEX_RATE_PER_M=0 LARCH_CURSOR_RATE_PER_M=0 LARCH_TOKEN_RATE_PER_M=0 \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-NA \
    --mode '--quick' \
    --workflow-path SIMPLE \
    --duration '00:01:00' \
    --claude-tokens 1000 \
    --codex-tokens 1000 \
    --cursor-tokens 1000 \
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
    --output-file "$TMP_NA" >/dev/null 2>/dev/null
grep -Fq 'TOTAL N/A' "$TMP_NA" || fail 'all-N/A cost line'
grep -Fq 'Claude N/A' "$TMP_NA" || fail 'all-N/A claude slot'
if grep -Fq '**PR**:' "$TMP_NA"; then fail 'PR bullet omitted when display is N/A'; fi
pass 'all-N/A cost semantics'

# Partial N/A: one priced lane + others N/A.
TMP_PART="$(mktemp "${TMPDIR:-/tmp}/trs-part.XXXXXX")"
LARCH_CLAUDE_RATE_PER_M=1 LARCH_CODEX_RATE_PER_M=0 LARCH_CURSOR_RATE_PER_M=0 LARCH_TOKEN_RATE_PER_M='' \
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
grep -Fq 'TOTAL ~' "$TMP_PART" || fail 'partial-N/A total missing tilde prefix'
cost_needle="\$1.00"
grep -Fq "$cost_needle" "$TMP_PART" || fail 'partial-N/A total missing amount'
grep -Fq 'Codex N/A' "$TMP_PART" || fail 'partial-N/A codex slot'
pass 'partial-N/A cost semantics'

# stderr envelope pins (quiet diagnostics; not mixed into markdown file).
TMP_ERR="$(mktemp "${TMPDIR:-/tmp}/trs-err.XXXXXX")"
TMP_ERR_STDERR="$(mktemp "${TMPDIR:-/tmp}/trs-errstderr.XXXXXX")"
LARCH_CLAUDE_RATE_PER_M=1 LARCH_CODEX_RATE_PER_M=0 LARCH_CURSOR_RATE_PER_M=0 LARCH_TOKEN_RATE_PER_M='' \
    "$HELPER" \
    --skill fix-issue \
    --outcome pr-open \
    --run-id RUN-ERR \
    --mode '/fix-issue' \
    --workflow-path 'N/A' \
    --duration 'N/A' \
    --claude-tokens 0 \
    --codex-tokens 0 \
    --cursor-tokens 0 \
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
