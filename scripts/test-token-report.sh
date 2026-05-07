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
contains "claude heading"  "### Claude"  "$md"
contains "codex heading"   "### Codex"   "$md"
contains "cursor heading"  "### Cursor"  "$md"
contains "claude header row" "| Step | Skill | Claude Input | Claude Output |" "$md"
contains "vendor header row" "| Step | Skill | Input | Output |" "$md"
contains "claude skill row"  "larch:implement" "$md"

# Pin the cursor step-total row to a uniquely identified line built from
# fixture values so substring collisions cannot pass silently.
expected_cursor_row="| Step 2 - implement | **step total** | 1 | 2 |"
if grep -Fq "$expected_cursor_row" <<<"$md"; then pass
else fail "cursor step-total row missing or wrong: expected '$expected_cursor_row'"
fi

# Negative assertions: old columns and HTML entities must not appear. Anchor
# N/A to the old cell shape so legitimate labels cannot trip it.
for needle in "Cache read" "Cache create" "Claude total" "Vendor total" "&nbsp;"; do
    if grep -Fq "$needle" <<<"$md"; then
        fail "rendered markdown must not contain '$needle'"
    else
        pass
    fi
done
if grep -Fq '| N/A |' <<<"$md"; then
    fail "rendered markdown must not contain old md_na_row cells (\`| N/A |\`)"
else
    pass
fi

# Per-heading existence plus per-block grand-total presence. Compute the
# expected vendor-table count from fixture content rather than a magic number.
codex_present=0
cursor_present=0
grep -F '"vendor":"codex"' "$LEDGER" >/dev/null 2>&1 && codex_present=1
grep -F '"vendor":"cursor"' "$LEDGER" >/dev/null 2>&1 && cursor_present=1
expected_gt=$((1 + codex_present + cursor_present))
gt_count=$(grep -c '\*\*Grand total\*\*' <<<"$md" || true)
if [[ "$gt_count" == "$expected_gt" ]]; then pass
else fail "expected $expected_gt grand-total rows; got $gt_count (codex_present=$codex_present cursor_present=$cursor_present)"
fi

INJ_LEDGER="$TMP/inj-ledger.jsonl"
INJ_TRANSCRIPT="$TMP/inj-transcript.jsonl"
# Build with jq so embedded pipes and newlines round-trip safely as JSON.
jq -c -n --arg s 'Step | with pipe' '{type:"mark",step:$s,ts:"2026-05-06T00:00:00Z"}' > "$INJ_LEDGER"
jq -c -n --arg s $'Step\nnewline mark' '{type:"mark",step:$s,ts:"2026-05-06T00:00:30Z"}' >> "$INJ_LEDGER"
jq -c -n '{type:"vendor",vendor:"cursor",input:1,output:2,total:3,ts:"2026-05-06T00:00:05Z"}' >> "$INJ_LEDGER"
jq -c -n --arg sk 'a|b' '{type:"assistant",timestamp:"2026-05-06T00:00:03.100Z",attributionSkill:$sk,message:{usage:{input_tokens:1,output_tokens:2,cache_read_input_tokens:0,cache_creation_input_tokens:0}}}' > "$INJ_TRANSCRIPT"
jq -c -n --arg sk $'two-line\nskill' '{type:"assistant",timestamp:"2026-05-06T00:00:31.100Z",attributionSkill:$sk,message:{usage:{input_tokens:5,output_tokens:6,cache_read_input_tokens:0,cache_creation_input_tokens:0}}}' >> "$INJ_TRANSCRIPT"
inj_md=$("$SCRIPT" --ledger "$INJ_LEDGER" --transcript "$INJ_TRANSCRIPT" --full --markdown)

contains "injection escaped pipe (step cell)"   'Step \| with pipe' "$inj_md"
contains "injection escaped pipe (skill cell)"  'a\|b'               "$inj_md"
contains "injection newline collapsed (step)"   "Step newline mark" "$inj_md"
contains "injection newline collapsed (skill)"  "two-line skill"    "$inj_md"

hdr_pipes=$(grep -F '| Step | Skill | Claude Input | Claude Output |' <<<"$inj_md" | head -1 | sed 's/\\|//g' | tr -cd '|' | wc -c | tr -d ' ')
mismatch=0
while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in
        '|'*)
            stripped=$(printf '%s' "$line" | sed 's/\\|//g')
            n=$(printf '%s' "$stripped" | tr -cd '|' | wc -c | tr -d ' ')
            case "$line" in
                *'---'*) continue ;;
            esac
            if [[ "$n" != "$hdr_pipes" ]]; then mismatch=$((mismatch + 1)); fi
            ;;
    esac
done <<< "$inj_md"
case "$mismatch" in
    0) pass ;;
    *) fail "$mismatch row(s) had wrong separator-pipe count after injection; md_cell escape failed" ;;
esac

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

# Malformed transcript JSONL routes through render_jq's jq parse failure to
# RENDER_FAIL_REASON="failed to parse token sources" (issue #1351 Gap 3).
MALFORMED_TRANSCRIPT="$TMP/malformed-transcript.jsonl"
printf 'this is not json\n{also not json\n' > "$MALFORMED_TRANSCRIPT"
malformed=$("$SCRIPT" --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse)
contains "malformed transcript reason" "Token report unavailable: failed to parse token sources" "$malformed"

# Ledger with vendor-only entries (no "mark" rows) hits the in-jq error("no
# step marks in ledger") branch, which also surfaces as
# RENDER_FAIL_REASON="failed to parse token sources" (issue #1351 Gap 3).
LEDGER_NO_MARKS="$TMP/no-marks.jsonl"
cat > "$LEDGER_NO_MARKS" <<'JSONL'
{"type":"vendor","vendor":"codex","total":5,"ts":"2026-05-06T00:00:00Z"}
JSONL
no_marks=$("$SCRIPT" --ledger "$LEDGER_NO_MARKS" --transcript "$TRANSCRIPT" --since-last-mark --terse)
contains "no-step-marks reason" "Token report unavailable: failed to parse token sources" "$no_marks"

BIG="$TMP/big-run-statistics.md"
for i in $(seq 1 250); do printf '| old | row %s |\n' "$i" >> "$BIG"; done
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-run-statistics "$BIG"
big_body=$(cat "$BIG")
contains "oversized sentinel"     "<!-- token-report-begin -->" "$big_body"
contains "oversized claude head"  "### Claude"  "$big_body"
contains "oversized codex head"   "### Codex"   "$big_body"
contains "oversized cursor head"  "### Cursor"  "$big_body"

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-report.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-report.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
