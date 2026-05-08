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
contains "vendor header row" "| Step | Skill | Input | Output | Total |" "$md"
contains "claude skill row"  "larch:implement" "$md"

# Pin the codex step-total and grand-total rows to aggregate-only fixture
# values so total-only rows cannot silently render as all-zero vendor rows.
expected_codex_row="| Step 1 - design | **step total** | 0 | 0 | 100 |"
if grep -Fq "$expected_codex_row" <<<"$md"; then pass
else fail "codex step-total row missing or wrong: expected '$expected_codex_row'"
fi
expected_codex_grand="| **Grand total** |  | 0 | 0 | 100 |"
if grep -Fq "$expected_codex_grand" <<<"$md"; then pass
else fail "codex grand-total row missing or wrong: expected '$expected_codex_grand'"
fi

# Pin the cursor step-total row to a uniquely identified line built from
# fixture values so substring collisions cannot pass silently.
expected_cursor_row="| Step 2 - implement | **step total** | 1 | 2 | 10 |"
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

claude_pipes=$(grep -F '| Step | Skill | Claude Input | Claude Output |' <<<"$inj_md" | head -1 | sed 's/\\|//g' | tr -cd '|' | wc -c | tr -d ' ')
vendor_pipes=$(grep -F '| Step | Skill | Input | Output | Total |' <<<"$inj_md" | head -1 | sed 's/\\|//g' | tr -cd '|' | wc -c | tr -d ' ')
mode=""
mismatch=0
# Pipe-parity check: Claude tables use the Claude header budget (4 columns); any other ### heading is a vendor table using the 5-column budget. Body rows before a heading fail closed.
while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in
        '### Claude'*) mode=claude ;;
        '### '*) mode=vendor ;;
        '|'*)
            case "$line" in
                *'---'*) continue ;;
            esac
            stripped=$(printf '%s' "$line" | sed 's/\\|//g')
            n=$(printf '%s' "$stripped" | tr -cd '|' | wc -c | tr -d ' ')
            case "$mode" in
                claude) [[ "$n" == "$claude_pipes" ]] || mismatch=$((mismatch + 1)) ;;
                vendor) [[ "$n" == "$vendor_pipes" ]] || mismatch=$((mismatch + 1)) ;;
                *) mismatch=$((mismatch + 1)) ;;
            esac
            ;;
    esac
done <<< "$inj_md"
case "$mismatch" in
    0) pass ;;
    *) fail "$mismatch row(s) had wrong separator-pipe count after injection; md_cell escape failed" ;;
esac

# Unknown-vendor heading sanitization: vendor_label's raw fallback routes
# through md_cell so a vendor name containing | or newline cannot break the
# heading line or inject a fake row separator into downstream markdown.
UNK_LEDGER="$TMP/unk-ledger.jsonl"
jq -c -n '{type:"mark",step:"Step 1 - design",ts:"2026-05-06T00:00:00Z"}' > "$UNK_LEDGER"
jq -c -n --arg v 'evil|vendor' '{type:"vendor",vendor:$v,input:1,output:2,total:3,ts:"2026-05-06T00:00:05Z"}' >> "$UNK_LEDGER"
jq -c -n --arg v $'two-line\nvendor' '{type:"vendor",vendor:$v,input:4,output:5,total:9,ts:"2026-05-06T00:00:06Z"}' >> "$UNK_LEDGER"
unk_md=$("$SCRIPT" --ledger "$UNK_LEDGER" --transcript "$TRANSCRIPT" --full --markdown)
contains "unknown vendor pipe escaped (heading)"      'evil\|vendor'  "$unk_md"
contains "unknown vendor newline collapsed (heading)" 'two-line vendor' "$unk_md"

LEGACY_LEDGER="$TMP/legacy-ledger.jsonl"
jq -c -n '{type:"mark",step:"Step 1 - design",ts:"2026-05-06T00:00:00Z"}' > "$LEGACY_LEDGER"
jq -c -n '{type:"vendor",vendor:"cursor",input:1,output:2,cache_read:3,cache_create:4,ts:"2026-05-06T00:00:05Z"}' >> "$LEGACY_LEDGER"
legacy_md=$("$SCRIPT" --ledger "$LEGACY_LEDGER" --transcript "$TRANSCRIPT" --full --markdown)
contains "legacy vendor total synthesized" "| Step 1 - design | **step total** | 1 | 2 | 10 |" "$legacy_md"

TOKEN_REPORT="$TMP/token-report.md"
printf '## Existing\n\nkept\n' > "$TOKEN_REPORT"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$TOKEN_REPORT"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$TOKEN_REPORT"
begin_count=$(grep -c '<!-- token-report-begin -->' "$TOKEN_REPORT")
end_count=$(grep -c '<!-- token-report-end -->' "$TOKEN_REPORT")
heading_count=$(grep -c '^## Token Report$' "$TOKEN_REPORT")
eq "single begin sentinel" "1" "$begin_count"
eq "single end sentinel" "1" "$end_count"
eq "single heading" "1" "$heading_count"
contains "existing content preserved" "kept" "$(cat "$TOKEN_REPORT")"

# Lone-begin marker normalization: a half-written prior run leaves only the
# begin sentinel and partial body. The replace path must drop the lone marker
# (and everything after it) before appending the fresh block, leaving exactly
# one begin/end pair and one ## Token Report heading. Without this, the legacy
# else-branch would append a second block over the broken prefix.
LONE_BEGIN="$TMP/lone-begin.md"
{
    printf '## Existing\n\nkept-prefix\n'
    printf '<!-- token-report-begin -->\n'
    printf 'partial broken body\n'
} > "$LONE_BEGIN"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$LONE_BEGIN" 2>"$TMP/lone-begin.stderr"
lb_begin=$(grep -c '<!-- token-report-begin -->' "$LONE_BEGIN")
lb_end=$(grep -c '<!-- token-report-end -->' "$LONE_BEGIN")
lb_heading=$(grep -c '^## Token Report$' "$LONE_BEGIN")
eq "lone-begin: single begin marker" "1" "$lb_begin"
eq "lone-begin: single end marker" "1" "$lb_end"
eq "lone-begin: single heading" "1" "$lb_heading"
contains "lone-begin: warning emitted" "lone <!-- token-report-begin -->" "$(cat "$TMP/lone-begin.stderr")"
contains "lone-begin: prefix preserved" "kept-prefix" "$(cat "$LONE_BEGIN")"
if grep -q 'partial broken body' "$LONE_BEGIN"; then
    fail "lone-begin: broken body was not stripped"
else
    pass
fi

# Lone-end marker normalization: only the end sentinel survives. The replace
# path drops content from the head through the marker, then appends a fresh
# block. The result keeps exactly one begin/end pair and one heading; any
# pre-marker body is intentionally discarded since it cannot be reattributed.
LONE_END="$TMP/lone-end.md"
{
    printf 'orphan body before lone end\n'
    printf '<!-- token-report-end -->\n'
    printf '## After\n\nkept-suffix\n'
} > "$LONE_END"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$LONE_END" 2>"$TMP/lone-end.stderr"
le_begin=$(grep -c '<!-- token-report-begin -->' "$LONE_END")
le_end=$(grep -c '<!-- token-report-end -->' "$LONE_END")
le_heading=$(grep -c '^## Token Report$' "$LONE_END")
eq "lone-end: single begin marker" "1" "$le_begin"
eq "lone-end: single end marker" "1" "$le_end"
eq "lone-end: single heading" "1" "$le_heading"
contains "lone-end: warning emitted" "lone <!-- token-report-end -->" "$(cat "$TMP/lone-end.stderr")"
contains "lone-end: suffix preserved" "kept-suffix" "$(cat "$LONE_END")"
if grep -q 'orphan body before lone end' "$LONE_END"; then
    fail "lone-end: orphan head was not stripped"
else
    pass
fi

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

# LARCH_DEBUG_TOKEN_REPORT — opt-in jq-stderr capture path. With the env
# var set to a truthy spelling, render failure surfaces a "(jq stderr at
# <path>)" suffix in the unavailable message and the stderr file holds the
# captured jq diagnostics. Falsy / unset values preserve the default silent
# behavior. Closes #1466 sub-item A; tests re-use the malformed-transcript
# fixture above to provoke a render failure.
# Truthy spellings — full enumerated allowlist from scripts/token-report.sh
# (round-2 review FINDING_3: tests covered only `1` and `true`; documented
# allowlist also includes case variants of yes/on). Each entry must surface
# the "(jq stderr at <path>)" suffix and produce a non-empty stderr file.
for truthy_value in "1" "true" "TRUE" "True" "yes" "YES" "Yes" "on" "ON" "On"; do
    debug_out=$(LARCH_DEBUG_TOKEN_REPORT="$truthy_value" "$SCRIPT" \
        --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse)
    case "$debug_out" in
        *"(jq stderr at "*) pass ;;
        *) fail "truthy env value '$truthy_value' should enable debug path: '$debug_out'" ;;
    esac
    debug_path=$(printf '%s' "$debug_out" | sed -n 's/.*jq stderr at \([^)]*\)).*/\1/p')
    if [[ -n "$debug_path" && -s "$debug_path" ]]; then
        pass
    else
        fail "truthy env value '$truthy_value' stderr file empty or missing: '$debug_path'"
    fi
    [[ -n "$debug_path" ]] && rm -f "$debug_path"
done

# Negative spellings (`no`, `off`, `0`, `false`, empty) MUST NOT enable
# the debug path — the gate is an explicit allowlist, not "non-empty
# non-zero" (round-1 review FINDING_1 — over-broad falsy list).
# Use env -u for the genuinely-unset case so the harness is hermetic and
# does not inherit a caller-supplied LARCH_DEBUG_TOKEN_REPORT (round-3
# review codex finding — without `env -u` running the harness with
# LARCH_DEBUG_TOKEN_REPORT=1 in the caller's env would flake the
# "unset" assertion). The empty-value case is exercised separately.
out=$(env -u LARCH_DEBUG_TOKEN_REPORT "$SCRIPT" \
    --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse)
case "$out" in
    *"jq stderr at "*) fail "<unset> env should not enable debug path: '$out'" ;;
    *) pass ;;
esac

for negative_value in "" "0" "false" "FALSE" "no" "NO" "off" "OFF" "disabled"; do
    out=$(LARCH_DEBUG_TOKEN_REPORT="$negative_value" "$SCRIPT" \
        --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse)
    case "$out" in
        *"jq stderr at "*) fail "negative env value '$negative_value' should not enable debug path: '$out'" ;;
        *) pass ;;
    esac
done

# Successful render with debug enabled MUST clean up the stderr temp
# (round-1 review FINDING_7 — empty stderr files cluttering $TMPDIR on
# every successful run). Use a per-test isolated TMPDIR so a parallel job
# touching the shared system /tmp cannot flake the before/after count
# (round-2 review FINDING_6).
isolated_tmp="$TMP/leak-check-tmp"
mkdir -p "$isolated_tmp"
before_count=$(find "$isolated_tmp" -maxdepth 1 -name 'larch-token-report-jq-stderr-*' 2>/dev/null | wc -l | tr -d ' ')
TMPDIR="$isolated_tmp" LARCH_DEBUG_TOKEN_REPORT=1 "$SCRIPT" \
    --ledger "$LEDGER" --transcript "$TRANSCRIPT" --since-last-mark --terse > /dev/null
after_count=$(find "$isolated_tmp" -maxdepth 1 -name 'larch-token-report-jq-stderr-*' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$before_count" == "$after_count" ]]; then pass
else fail "debug=1 successful render leaked stderr temp file (before=$before_count after=$after_count)"
fi

BIG="$TMP/big-token-report.md"
for i in $(seq 1 250); do printf '| old | row %s |\n' "$i" >> "$BIG"; done
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$BIG"
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
