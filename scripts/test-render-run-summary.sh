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
TMP_DES_OUT=""
TMP_DES_STD=""
TMP_CU_OUT=""
TMP_CU_STD=""
TMP_ZERO_OUT=""
TMP_CU_NZ_OUT=""
TMP_LINES_NA=""
TMP_LINES_PARTIAL=""
TMP_NO_PATH=""
trap 'rm -f "$TMP" "$notes" "$TMP_DEF" "$TMP_PART" "$TMP_ERR" "$TMP_ERR_STDERR" "$TMP_DES_OUT" "$TMP_DES_STD" "$TMP_CU_OUT" "$TMP_CU_STD" "$TMP_ZERO_OUT" "$TMP_CU_NZ_OUT" "$TMP_LINES_NA" "$TMP_LINES_PARTIAL" "$TMP_NO_PATH"' EXIT
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
    --emergency-requested true \
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
    --code-added 107 \
    --code-deleted 23 \
    --logs-added 50 \
    --logs-deleted 10 \
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
if grep -Fq -- '- **Path**:' "$TMP"; then fail 'implement happy path must omit Path bullet'; fi
grep -Fq -- '- Emergency: true' "$TMP" || fail 'missing emergency line when requested'
grep -Fq '**Note:** fixture note' "$TMP" || fail 'missing appended note'
grep -Fxq -- '- **Lines (PR diff)**: code +107/-23, larch-logs +50/-10' "$TMP" || fail 'missing full Lines (PR diff) bullet'
grep -Fq "TOTAL ~\$5.00" "$TMP" || fail 'missing expected total cost line (approx prefix)'
pass 'render body shape + sentinel + notes + cost + lines'

# Shipped defaults: 1M tokens each lane (aggregate-only) → blended 0.80 + 2.00 + 1.50 = 4.30 USD total.
TMP_DEF="$(mktemp "${TMPDIR:-/tmp}/trs-def.XXXXXX")"
env -u LARCH_CLAUDE_RATE_PER_M -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-DEF \
    --mode '--quick' \
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
if grep -Fq -- '- **Path**:' "$TMP_DEF"; then fail 'implement default path must omit Path bullet'; fi
if grep -Fq 'Emergency: true' "$TMP_DEF"; then fail 'omitted emergency state must not render emergency line'; fi
pass 'all-defaulted cost semantics (shipped blended defaults)'

# Explicit Claude rate only; zero-token lanes show $0.00 (defaults still apply for rates).
TMP_PART="$(mktemp "${TMPDIR:-/tmp}/trs-part.XXXXXX")"
LARCH_CLAUDE_RATE_PER_M=2 env -u LARCH_CODEX_RATE_PER_M -u LARCH_CURSOR_RATE_PER_M -u LARCH_TOKEN_RATE_PER_M \
    "$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-PART \
    --mode '--quick' \
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
if grep -Fq -- '- **Path**:' "$TMP_PART"; then fail 'implement partial path must omit Path bullet'; fi
if grep -Fq 'Emergency: true' "$TMP_PART"; then fail 'explicit non-emergency case must not render emergency line'; fi
pass "priced Claude + zero-token lanes at \$0.00"

# stderr envelope pins (quiet diagnostics; not mixed into markdown file).
TMP_ERR="$(mktemp "${TMPDIR:-/tmp}/trs-err.XXXXXX")"
TMP_ERR_STDERR="$(mktemp "${TMPDIR:-/tmp}/trs-errstderr.XXXXXX")"
TMP_DES_OUT="$(mktemp "${TMPDIR:-/tmp}/trs-des-out.XXXXXX")"
TMP_DES_STD="$(mktemp "${TMPDIR:-/tmp}/trs-des-std.XXXXXX")"
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

TMP_ZERO_OUT="$(mktemp "${TMPDIR:-/tmp}/trs-zero-out.XXXXXX")"
"$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-ZERO \
    --mode N/A \
    --workflow-path N/A \
    --duration N/A \
    --issue-number 0 \
    --issue-url N/A \
    --pr-number 0 \
    --pr-url N/A \
    --plan-review-line N/A \
    --code-review-line N/A \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path N/A \
    --output-file "$TMP_ZERO_OUT" >/dev/null 2>/dev/null
grep -Fq "Claude \$0.00, Codex \$0.00, Cursor \$0.00" "$TMP_ZERO_OUT" || fail 'omitted token flags should retain zero-dollar behavior'
grep -Fxq -- '- **Lines (PR diff)**: N/A' "$TMP_ZERO_OUT" || fail 'omitted line-count flags render N/A'
pass 'omitted token flags render zero-dollar cost'

TMP_NO_PATH="$(mktemp "${TMPDIR:-/tmp}/trs-no-path.XXXXXX")"
"$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-NO-PATH \
    --mode N/A \
    --duration N/A \
    --issue-number 0 \
    --issue-url N/A \
    --pr-number 0 \
    --pr-url N/A \
    --plan-review-line N/A \
    --code-review-line N/A \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path N/A \
    --output-file "$TMP_NO_PATH" >/dev/null 2>/dev/null
if grep -Fq -- '- **Path**:' "$TMP_NO_PATH"; then fail 'implement without workflow path must omit Path bullet'; fi
pass 'implement without workflow path omits Path bullet'

TMP_LINES_NA="$(mktemp "${TMPDIR:-/tmp}/trs-lines-na.XXXXXX")"
"$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-LINES-NA \
    --mode N/A \
    --workflow-path N/A \
    --duration N/A \
    --issue-number 0 \
    --issue-url N/A \
    --pr-number 0 \
    --pr-url N/A \
    --plan-review-line N/A \
    --code-review-line N/A \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path N/A \
    --output-file "$TMP_LINES_NA" >/dev/null 2>/dev/null
grep -Fxq -- '- **Lines (PR diff)**: N/A' "$TMP_LINES_NA" || fail 'implement without line flags renders N/A'
pass 'implement no line-count data renders N/A'

TMP_LINES_PARTIAL="$(mktemp "${TMPDIR:-/tmp}/trs-lines-partial.XXXXXX")"
"$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-LINES-PARTIAL \
    --mode N/A \
    --workflow-path N/A \
    --duration N/A \
    --issue-number 0 \
    --issue-url N/A \
    --pr-number 0 \
    --pr-url N/A \
    --plan-review-line N/A \
    --code-review-line N/A \
    --code-added 107 \
    --code-deleted 23 \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path N/A \
    --output-file "$TMP_LINES_PARTIAL" >/dev/null 2>/dev/null
grep -Fxq -- '- **Lines (PR diff)**: N/A' "$TMP_LINES_PARTIAL" || fail 'partial line-count flags render N/A'
pass 'partial line-count data renders N/A'

TMP_CU_OUT="$(mktemp "${TMPDIR:-/tmp}/trs-cu-out.XXXXXX")"
TMP_CU_STD="$(mktemp "${TMPDIR:-/tmp}/trs-cu-std.XXXXXX")"
"$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-CU \
    --mode N/A \
    --workflow-path N/A \
    --duration N/A \
    --cost-unavailable \
    --issue-number 0 \
    --issue-url N/A \
    --pr-number 0 \
    --pr-url N/A \
    --plan-review-line N/A \
    --code-review-line N/A \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path N/A \
    --output-file "$TMP_CU_OUT" \
    --print-stdout >"$TMP_CU_STD" 2>/dev/null
grep -Fxq -- '- **Cost**: N/A' "$TMP_CU_OUT" || fail '--cost-unavailable output file cost'
grep -Fxq -- '- **Cost**: N/A' "$TMP_CU_STD" || fail '--cost-unavailable stdout cost'
cmp -s "$TMP_CU_OUT" "$TMP_CU_STD" || fail '--cost-unavailable stdout/file identity'
pass '--cost-unavailable renders N/A'

TMP_CU_NZ_OUT="$(mktemp "${TMPDIR:-/tmp}/trs-cu-nz-out.XXXXXX")"
"$HELPER" \
    --skill implement \
    --outcome merged \
    --run-id RUN-CU-NZ \
    --mode N/A \
    --workflow-path N/A \
    --duration N/A \
    --cost-unavailable \
    --claude-tokens 111 \
    --codex-tokens 222 \
    --cursor-tokens 333 \
    --claude-input-tokens 1 \
    --claude-cache-read-tokens 2 \
    --claude-cache-write-5m-tokens 3 \
    --claude-cache-write-1h-tokens 4 \
    --claude-output-tokens 5 \
    --codex-input-tokens 6 \
    --codex-cached-input-tokens 7 \
    --codex-output-tokens 8 \
    --cursor-input-tokens 9 \
    --cursor-cache-read-tokens 10 \
    --cursor-output-tokens 11 \
    --issue-number 0 \
    --issue-url N/A \
    --pr-number 0 \
    --pr-url N/A \
    --plan-review-line N/A \
    --code-review-line N/A \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path N/A \
    --output-file "$TMP_CU_NZ_OUT" >/dev/null 2>/dev/null
grep -Fxq -- '- **Cost**: N/A' "$TMP_CU_NZ_OUT" || fail '--cost-unavailable must override explicit token args'
pass '--cost-unavailable overrides explicit non-zero token args'

# --- --skill design ---
LARCH_CLAUDE_RATE_PER_M=1 LARCH_CODEX_RATE_PER_M=2 LARCH_CURSOR_RATE_PER_M=3 \
    "$HELPER" \
    --skill design \
    --outcome approved \
    --run-id RUN-D1 \
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
    --pr-number 0 \
    --pr-url 'N/A' \
    --plan-review-line '2 accepted (0 critical / 1 high / 1 medium / 0 low)' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'larch-logs/design/RUN-D1/' \
    --output-file "$TMP_DES_OUT" \
    --print-stdout >"$TMP_DES_STD" 2>/dev/null
grep -Fq '## /design run RUN-D1 — approved' "$TMP_DES_OUT" || fail 'design title'
grep -Fq -- '- **Cost**:' "$TMP_DES_OUT" || fail 'design cost bullet'
grep -Fq -- '- **Plan review**:' "$TMP_DES_OUT" || fail 'design plan review'
grep -Fq -- '- **OOS filed**:' "$TMP_DES_OUT" || fail 'design oos'
grep -Fq '<!-- larch:run-summary v=1 -->' "$TMP_DES_OUT" || fail 'design sentinel'
if grep -Fq -- '- **PR**:' "$TMP_DES_OUT"; then fail 'design must not emit PR'; fi
if grep -Fq -- '- **Code review**:' "$TMP_DES_OUT"; then fail 'design must not emit code review'; fi
if grep -Fq -- '- **Lines (PR diff)**:' "$TMP_DES_OUT"; then fail 'design must not emit Lines (PR diff)'; fi
if grep -Fq -- '- **Outcome**:' "$TMP_DES_OUT"; then fail 'approved design must not emit Outcome'; fi
if grep -Fq -- '- **Mode**:' "$TMP_DES_OUT"; then fail 'design must not emit Mode'; fi
if grep -Fq -- '- **Path**:' "$TMP_DES_OUT"; then fail 'design must not emit Path'; fi
cmp -s "$TMP_DES_OUT" "$TMP_DES_STD" || fail 'design stdout must match --output-file byte-for-byte'
pass 'design skill schema + cmp byte identity'

"$HELPER" \
    --skill design \
    --outcome cancelled-clarify \
    --run-id RUN-D2 \
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
    --plan-review-line '0 findings' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'N/A' \
    --output-file "$TMP_DES_OUT" >/dev/null 2>/dev/null
grep -Fq -- '- **Outcome**: cancelled-clarify' "$TMP_DES_OUT" || fail 'design cancelled outcome bullet'
pass 'design intermediate outcome'


"$HELPER" \
    --skill design \
    --outcome publish-skipped \
    --run-id unknown \
    --duration 'N/A' \
    --cost-unavailable \
    --issue-number 9 \
    --issue-url 'https://github.com/o/r/issues/9' \
    --pr-number 0 \
    --pr-url 'N/A' \
    --plan-review-line '0 findings' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'N/A' \
    --output-file "$TMP_DES_OUT" >/dev/null 2>/dev/null
grep -Fq -- '- **Outcome**: publish-skipped' "$TMP_DES_OUT" || fail 'publish-skipped outcome bullet'
# shellcheck disable=SC2016 # literal markdown with backticks is intentionally single-quoted.
grep -Fq -- '- **Run logs**: `N/A`' "$TMP_DES_OUT" || fail 'unknown run-id must keep Run logs N/A'
if grep -Fq 'larch-logs/design/unknown/' "$TMP_DES_OUT"; then fail 'unknown run-id must not synthesize run-log path'; fi
pass 'publish-skipped unknown run keeps logs N/A'

"$HELPER" \
    --skill design \
    --outcome publish-skipped \
    --run-id RUN-D-SKIP \
    --duration 'N/A' \
    --cost-unavailable \
    --issue-number 9 \
    --issue-url 'https://github.com/o/r/issues/9' \
    --pr-number 0 \
    --pr-url 'N/A' \
    --plan-review-line '0 findings' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'N/A' \
    --output-file "$TMP_DES_OUT" >/dev/null 2>/dev/null
# shellcheck disable=SC2016 # literal markdown with backticks is intentionally single-quoted.
grep -Fq -- '- **Run logs**: `N/A`' "$TMP_DES_OUT" || fail 'publish-skipped real run-id must keep Run logs N/A'
if grep -Fq 'larch-logs/design/RUN-D-SKIP/' "$TMP_DES_OUT"; then fail 'publish-skipped real run-id must not synthesize run-log path'; fi
pass 'publish-skipped real run keeps logs N/A'

"$HELPER" \
    --skill design \
    --outcome approved \
    --run-id RUN-D3 \
    --duration 'N/A' \
    --cost-unavailable \
    --issue-number 9 \
    --issue-url 'https://github.com/o/r/issues/9' \
    --pr-number 0 \
    --pr-url 'N/A' \
    --plan-review-line '0 findings' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'N/A' \
    --output-file "$TMP_DES_OUT" >/dev/null 2>/dev/null
# shellcheck disable=SC2016 # literal markdown with backticks is intentionally single-quoted.
grep -Fq -- '- **Run logs**: `larch-logs/design/RUN-D3/`' "$TMP_DES_OUT" || fail 'approved real run-id should synthesize Run logs path'
pass 'approved real run-id logs fallback'

"$HELPER" \
    --skill design \
    --outcome failed-publish \
    --run-id RUN-D4 \
    --duration 'N/A' \
    --cost-unavailable \
    --issue-number 9 \
    --issue-url 'https://github.com/o/r/issues/9' \
    --pr-number 0 \
    --pr-url 'N/A' \
    --plan-review-line '0 findings' \
    --code-review-line 'N/A' \
    --oos-count 0 \
    --oos-urls '' \
    --exec-issues 0 \
    --warnings 0 \
    --run-logs-path 'N/A' \
    --output-file "$TMP_DES_OUT" >/dev/null 2>/dev/null
grep -Fq -- '- **Outcome**: failed-publish' "$TMP_DES_OUT" || fail 'failed-publish outcome bullet'
# shellcheck disable=SC2016 # literal markdown with backticks is intentionally single-quoted.
grep -Fq -- '- **Run logs**: `N/A`' "$TMP_DES_OUT" || fail 'failed-publish must keep Run logs N/A'
if grep -Fq 'larch-logs/design/RUN-D4/' "$TMP_DES_OUT"; then fail 'failed-publish must not synthesize run-log path'; fi
pass 'failed-publish real run keeps logs N/A'

set +e
"$HELPER" --skill foo --outcome approved --run-id X --mode m --workflow-path w --duration d \
    --claude-tokens 0 --codex-tokens 0 --cursor-tokens 0 \
    --claude-input-tokens 0 --claude-cache-read-tokens 0 --claude-cache-write-5m-tokens 0 --claude-cache-write-1h-tokens 0 --claude-output-tokens 0 \
    --codex-input-tokens 0 --codex-cached-input-tokens 0 --codex-output-tokens 0 \
    --cursor-input-tokens 0 --cursor-cache-read-tokens 0 --cursor-output-tokens 0 \
    --issue-number 0 --issue-url N/A --pr-number 0 --pr-url N/A \
    --plan-review-line N/A --code-review-line N/A --oos-count 0 --oos-urls '' \
    --exec-issues 0 --warnings 0 --run-logs-path N/A --output-file "$TMP_DES_OUT" >/dev/null 2>&1
sk=$?
set -e
test "$sk" -eq 2 || fail '--skill foo must exit 2'
pass 'reject unknown --skill'

set +e
"$HELPER" --skill implement --outcome approved --run-id X --mode m --workflow-path w --duration d \
    --emergency-requested maybe \
    --claude-tokens 0 --codex-tokens 0 --cursor-tokens 0 \
    --claude-input-tokens 0 --claude-cache-read-tokens 0 --claude-cache-write-5m-tokens 0 --claude-cache-write-1h-tokens 0 --claude-output-tokens 0 \
    --codex-input-tokens 0 --codex-cached-input-tokens 0 --codex-output-tokens 0 \
    --cursor-input-tokens 0 --cursor-cache-read-tokens 0 --cursor-output-tokens 0 \
    --issue-number 0 --issue-url N/A --pr-number 0 --pr-url N/A \
    --plan-review-line N/A --code-review-line N/A --oos-count 0 --oos-urls '' \
    --exec-issues 0 --warnings 0 --run-logs-path N/A --output-file "$TMP_DES_OUT" >/dev/null 2>&1
sk=$?
set -e
test "$sk" -eq 2 || fail '--emergency-requested maybe must exit 2'
pass 'reject invalid --emergency-requested'

printf 'PASS=%s\n' "$PASS"
