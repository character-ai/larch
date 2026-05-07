#!/usr/bin/env bash
# test-token-report.sh — offline regression harness for token-report.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/token-report.sh"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }
contains() {
    case "$3" in
        *"$2"*) pass ;;
        *) fail "$1 missing '$2': $3" ;;
    esac
}
eq() {
    if [[ "$2" == "$3" ]]; then pass; else fail "$1 expected '$2' got '$3'"; fi
}

ROOT="${TMPDIR:-/tmp}"
TMP=$(mktemp -d "$ROOT/test-token-report.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

LEDGER="$TMP/ledger.jsonl"
TRANSCRIPT="$TMP/transcript.jsonl"
cat > "$LEDGER" <<'JSONL'
{"type":"mark","step":"Step 1 - design","ts":"2026-05-06T00:00:00Z"}
{"type":"vendor","vendor":"codex","total":100,"ts":"2026-05-06T00:00:05Z"}
{"type":"mark","step":"Step 2 - implement","ts":"2026-05-06T00:01:00Z"}
{"type":"vendor","vendor":"cursor","input":1,"output":2,"cache_read":3,"cache_create":4,"total":10,"ts":"2026-05-06T00:01:03Z"}
JSONL
cat > "$TRANSCRIPT" <<'JSONL'
{"type":"assistant","timestamp":"2026-05-06T00:00:03.100Z","attributionSkill":"larch:design","message":{"usage":{"input_tokens":1,"cache_read_input_tokens":2,"cache_creation_input_tokens":3,"output_tokens":4}}}
{"type":"assistant","timestamp":"2026-05-06T00:01:03.100Z","attributionSkill":"larch:implement","message":{"usage":{"input_tokens":10,"cache_read_input_tokens":20,"cache_creation_input_tokens":30,"output_tokens":40}}}
JSONL

terse=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --since-last-mark --terse)
contains "terse step" "Step 2 - implement: claude=100 tokens" "$terse"
contains "terse vendor" "vendor=10 (cursor=10)" "$terse"

md=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --full --markdown)
contains "markdown header" "| Step | Skill | Claude input" "$md"
contains "skill row" "&nbsp;&nbsp;larch:implement" "$md"
contains "vendor row" "&nbsp;&nbsp;vendor:codex" "$md"
contains "grand total" "**Grand total**" "$md"

RUN_STATS="$TMP/run-statistics.md"
printf '## Existing\n\nkept\n' > "$RUN_STATS"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-run-statistics "$RUN_STATS"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-run-statistics "$RUN_STATS"
begin_count=$(grep -c '<!-- token-report-begin -->' "$RUN_STATS")
end_count=$(grep -c '<!-- token-report-end -->' "$RUN_STATS")
heading_count=$(grep -c '^## Token Report$' "$RUN_STATS")
eq "single begin sentinel" "1" "$begin_count"
eq "single end sentinel" "1" "$end_count"
eq "single heading" "1" "$heading_count"
contains "existing content preserved" "kept" "$(cat "$RUN_STATS")"

OUT="$TMP/table.md"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --full --markdown --output "$OUT"
if [[ -s "$OUT" ]]; then pass; else fail "--output did not write table"; fi

missing=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TMP/missing.jsonl" --since-last-mark --terse)
contains "missing transcript" "Token report unavailable:" "$missing"

BIG="$TMP/big-run-statistics.md"
for i in $(seq 1 250); do printf '| old | row %s |\n' "$i" >> "$BIG"; done
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-run-statistics "$BIG"
contains "oversized sentinel" "<!-- token-report-begin -->" "$(cat "$BIG")"

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-report.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-report.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
