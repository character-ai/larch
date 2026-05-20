#!/usr/bin/env bash
# test-render-run-summary.sh — offline harness for render-run-summary.sh.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/render-run-summary.sh"
TMP="$(mktemp "${TMPDIR:-/tmp}/trs.XXXXXX")"
trap 'rm -f "$TMP" "$notes"' EXIT
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
    --output-file "$TMP" >/dev/null

grep -Fq '<!-- larch:run-summary v=1 -->' "$TMP" || fail 'missing sentinel'
grep -Fq '**Outcome**: merged' "$TMP" || fail 'missing outcome'
grep -Fq '**Note:** fixture note' "$TMP" || fail 'missing appended note'
grep -Fq "TOTAL \$5.00" "$TMP" || fail 'missing expected total cost line'
pass 'render body shape + sentinel + notes + cost'

printf 'PASS=%s\n' "$PASS"
