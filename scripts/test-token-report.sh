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
contains "claude header row" "| Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output |" "$md"
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

# Pin the Claude body rows from fixture content so a regression that zeros
# the cache columns, swaps cache_read with cache_create, or drops them from
# vrow while keeping the column count would still fail. Fixture has two
# transcript rows: input/cache_read/cache_create/output = 1/2/3/4 (Step 1
# - design, larch:design) and 10/20/30/40 (Step 2 - implement,
# larch:implement). Grand total = 11/22/33/44.
expected_claude_step1="| Step 1 - design | **step total** | 1 | 2 | 3 | 4 |"
if grep -Fq "$expected_claude_step1" <<<"$md"; then pass
else fail "claude step 1 step-total row missing or wrong: expected '$expected_claude_step1'"
fi
expected_claude_step2="| Step 2 - implement | **step total** | 10 | 20 | 30 | 40 |"
if grep -Fq "$expected_claude_step2" <<<"$md"; then pass
else fail "claude step 2 step-total row missing or wrong: expected '$expected_claude_step2'"
fi
expected_claude_grand="| **Grand total** |  | 11 | 22 | 33 | 44 |"
if grep -Fq "$expected_claude_grand" <<<"$md"; then pass
else fail "claude grand-total row missing or wrong: expected '$expected_claude_grand'"
fi

# Negative assertions: deprecated combined / aggregate column names and HTML
# entities must not appear. The "Claude Cache Read" / "Claude Cache Create"
# columns ARE legitimate now, so we only forbid a combined "Claude total"
# column and the legacy "Vendor total" header. Anchor N/A to the old cell
# shape so legitimate labels cannot trip it.
for needle in "Claude total" "Vendor total" "&nbsp;"; do
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

claude_pipes=$(grep -F '| Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output |' <<<"$inj_md" | head -1 | sed 's/\\|//g' | tr -cd '|' | wc -c | tr -d ' ')
vendor_pipes=$(grep -F '| Step | Skill | Input | Output | Total |' <<<"$inj_md" | head -1 | sed 's/\\|//g' | tr -cd '|' | wc -c | tr -d ' ')
mode=""
mismatch=0
# Pipe-parity check: each table's body rows must match its header's pipe count. The Claude table header is now 6 columns (Step | Skill | Claude Input | Claude Cache Read | Claude Cache Create | Claude Output); any other ### heading is a vendor table using the 5-column budget. Both budgets are derived from the live header line above (claude_pipes / vendor_pipes), so this comment documents the shape rather than pinning a magic number. Body rows before a heading fail closed.
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

# Whole-line marker regex parity — a prose line
# that merely *mentions* the marker substring (e.g. inside a backtick
# code span or table cell) MUST NOT be treated as a structural sentinel
# (closes #1511 finding A). Set up a file with a prose mention BEFORE a
# real matched pair; the matched-pair branch must rewrite only the real
# pair and leave the prose line intact.
PROSE_MARKER="$TMP/prose-marker.md"
{
    printf '## Existing\n\n'
    # shellcheck disable=SC2016 # Backticks here are literal markdown code-span delimiters in fixture data, not shell command substitution.
    printf 'See `<!-- token-report-begin -->` for the matched-pair contract; the marker text appears in this prose line.\n'
    printf '\n'
    printf '<!-- token-report-begin -->\n'
    printf '## Token Report\n\nstale body\n'
    printf '<!-- token-report-end -->\n'
    printf '\n## After\n\nkept-suffix\n'
} > "$PROSE_MARKER"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$PROSE_MARKER"
pm_body=$(cat "$PROSE_MARKER")
contains "prose mention preserved (begin)" "the marker text appears in this prose line" "$pm_body"
contains "prose-marker: suffix preserved" "kept-suffix" "$pm_body"
# Exactly one real matched pair after rewrite — the prose mentions inside
# code spans must not bump the count.
pm_real_begin=$(grep -c '^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$' "$PROSE_MARKER")
pm_real_end=$(grep -c '^[[:space:]]*<!-- token-report-end -->[[:space:]]*$' "$PROSE_MARKER")
eq "prose-marker: single whole-line begin" "1" "$pm_real_begin"
eq "prose-marker: single whole-line end" "1" "$pm_real_end"
if grep -q 'stale body' "$PROSE_MARKER"; then
    fail "prose-marker: stale body inside real pair was not rewritten"
else
    pass
fi

# Whole-line begin marker + prose-only end mention. Under the round-1
# review consensus (closes #1511 round-1 FINDING — substring grep + whole
# line awk = data loss), the matched-pair branch must NOT silently drop
# trailing content because of an inline mention of the end marker. With
# whole-line presence probes, has_end stays 0 and the file routes to the
# lone-begin recovery path: content from the whole-line begin marker
# through EOF is dropped (intentional lone-marker semantics), the prose
# end mention sits BEFORE the begin marker so it is preserved, and a
# fresh block is appended.
WHOLE_BEGIN_PROSE_END="$TMP/whole-begin-prose-end.md"
{
    printf '## Existing\n\n'
    # shellcheck disable=SC2016 # Backticks are literal markdown code-span delimiters in fixture data.
    printf 'See `<!-- token-report-end -->` mentioned in this prose line; not a real sentinel.\n'
    printf '\n'
    printf '<!-- token-report-begin -->\n'
    printf 'this would be deleted by lone-begin recovery\n'
} > "$WHOLE_BEGIN_PROSE_END"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$WHOLE_BEGIN_PROSE_END" 2>"$TMP/whole-begin-prose-end.stderr"
wbpe_body=$(cat "$WHOLE_BEGIN_PROSE_END")
contains "whole-begin/prose-end: prose end mention preserved" "mentioned in this prose line" "$wbpe_body"
contains "whole-begin/prose-end: lone-begin warning emitted" "lone <!-- token-report-begin -->" "$(cat "$TMP/whole-begin-prose-end.stderr")"
wbpe_real_begin=$(grep -c '^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$' "$WHOLE_BEGIN_PROSE_END")
wbpe_real_end=$(grep -c '^[[:space:]]*<!-- token-report-end -->[[:space:]]*$' "$WHOLE_BEGIN_PROSE_END")
eq "whole-begin/prose-end: single whole-line begin" "1" "$wbpe_real_begin"
eq "whole-begin/prose-end: single whole-line end" "1" "$wbpe_real_end"
if grep -q 'this would be deleted by lone-begin recovery' "$WHOLE_BEGIN_PROSE_END"; then
    fail "whole-begin/prose-end: post-begin content was not stripped"
else
    pass
fi

# Prose-only mentions of BOTH markers, no whole-line markers anywhere.
# Substring grep would have selected the matched-pair branch, then the
# whole-line awk would have silently no-op'd the replacement (file
# unchanged → append succeeded with no new block, an invisible failure).
# With whole-line presence probes, has_begin and has_end both stay 0 and
# the file routes to the no-marker append path: existing content is
# preserved verbatim and a fresh block is appended at EOF.
PROSE_BOTH_NO_WHOLE_LINE="$TMP/prose-both-no-whole-line.md"
{
    printf '## Existing\n\n'
    # shellcheck disable=SC2016 # Backticks are literal markdown code-span delimiters in fixture data.
    printf 'Both `<!-- token-report-begin -->` and `<!-- token-report-end -->` mentioned only in prose.\n'
    printf '\nkept-content\n'
} > "$PROSE_BOTH_NO_WHOLE_LINE"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --append-token-report "$PROSE_BOTH_NO_WHOLE_LINE"
pbnwl_body=$(cat "$PROSE_BOTH_NO_WHOLE_LINE")
contains "prose-both: existing content preserved" "kept-content" "$pbnwl_body"
contains "prose-both: prose mentions preserved" "mentioned only in prose" "$pbnwl_body"
pbnwl_real_begin=$(grep -c '^[[:space:]]*<!-- token-report-begin -->[[:space:]]*$' "$PROSE_BOTH_NO_WHOLE_LINE")
pbnwl_real_end=$(grep -c '^[[:space:]]*<!-- token-report-end -->[[:space:]]*$' "$PROSE_BOTH_NO_WHOLE_LINE")
eq "prose-both: fresh whole-line begin appended" "1" "$pbnwl_real_begin"
eq "prose-both: fresh whole-line end appended" "1" "$pbnwl_real_end"

OUT="$TMP/table.md"
"$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --full --markdown --output "$OUT"
if [[ -s "$OUT" ]]; then pass; else fail "--output did not write table"; fi

missing=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TMP/missing.jsonl" --since-last-mark --terse 2>&1)
contains "missing transcript" "Token report unavailable:" "$missing"

# Malformed transcript JSONL routes through render_jq's jq parse failure to
# RENDER_FAIL_REASON="failed to parse token sources" (issue #1351 Gap 3).
MALFORMED_TRANSCRIPT="$TMP/malformed-transcript.jsonl"
printf 'this is not json\n{also not json\n' > "$MALFORMED_TRANSCRIPT"
malformed=$("$SCRIPT" --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse 2>&1)
contains "malformed transcript reason" "Token report unavailable: failed to parse token sources" "$malformed"

# Ledger with vendor-only entries (no "mark" rows) hits the in-jq error("no
# step marks in ledger") branch, which also surfaces as
# RENDER_FAIL_REASON="failed to parse token sources" (issue #1351 Gap 3).
LEDGER_NO_MARKS="$TMP/no-marks.jsonl"
cat > "$LEDGER_NO_MARKS" <<'JSONL'
{"type":"vendor","vendor":"codex","total":5,"ts":"2026-05-06T00:00:00Z"}
JSONL
no_marks=$("$SCRIPT" --ledger "$LEDGER_NO_MARKS" --transcript "$TRANSCRIPT" --since-last-mark --terse 2>&1)
contains "no-step-marks reason" "Token report unavailable: failed to parse token sources" "$no_marks"

# LARCH_DEBUG_TOKEN_REPORT — opt-in jq-stderr capture path. With the env
# var set to a truthy spelling, render failure surfaces a fixed
# "(jq stderr captured; debug)" suffix in the unavailable message
# (stderr, since unavailable() routes to stderr) and emits the actual
# captured stderr file path on the script's own stderr
# ("token-report.sh: jq stderr captured at <path>") so the absolute
# TMPDIR/username-bearing path never reaches the published surface
# (anchor / PR body). Falsy / unset values preserve the default silent
# behavior. Closes #1466 sub-item A and #1511 sub-item B; tests re-use
# the malformed-transcript fixture above to provoke a render failure.
# Truthy spellings — full enumerated allowlist from scripts/token-report.sh
# (round-2 review FINDING_3: tests covered only `1` and `true`; documented
# allowlist also includes case variants of yes/on). Each entry must surface
# the fixed-phrase suffix on stderr, the stderr path line, and a non-empty
# stderr file.
for truthy_value in "1" "true" "TRUE" "True" "yes" "YES" "Yes" "on" "ON" "On"; do
    debug_stderr_file="$TMP/debug-stderr-$truthy_value.txt"
    debug_out=$(LARCH_DEBUG_TOKEN_REPORT="$truthy_value" "$SCRIPT" \
        --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse \
        2>"$debug_stderr_file")
    debug_stderr_body=$(cat "$debug_stderr_file")
    case "$debug_stderr_body" in
        *"(jq stderr captured; debug)"*) pass ;;
        *) fail "truthy env value '$truthy_value' should surface fixed-phrase suffix on stderr: '$debug_stderr_body'" ;;
    esac
    case "$debug_out" in
        *"jq stderr at "*) fail "truthy env value '$truthy_value' MUST NOT leak absolute path on stdout: '$debug_out'" ;;
        *) pass ;;
    esac
    case "$debug_stderr_body" in
        *"token-report.sh: jq stderr captured at "*) pass ;;
        *) fail "truthy env value '$truthy_value' should emit captured-path line on stderr: '$debug_stderr_body'" ;;
    esac
    # Extract the path on the script's stderr — greedy on both ends so a
    # path containing a `)` (unlikely under mktemp but defensive) is not
    # silently truncated.
    debug_path_line="${debug_stderr_body##*jq stderr captured at }"
    debug_path="${debug_path_line%%$'\n'*}"
    if [[ -n "$debug_path" && -s "$debug_path" ]]; then
        pass
    else
        fail "truthy env value '$truthy_value' stderr file empty or missing: '$debug_path'"
    fi
    [[ -n "$debug_path" ]] && rm -f "$debug_path"
    rm -f "$debug_stderr_file"
done

# Negative spellings (`no`, `off`, `0`, `false`, empty) MUST NOT enable
# the debug path — the gate is an explicit allowlist, not "non-empty
# non-zero" (round-1 review FINDING_1 — over-broad falsy list). The
# "must not leak" assertion is keyed on either spelling of the legacy /
# fixed phrase since the negative path emits no debug suffix at all.
# Use env -u for the genuinely-unset case so the harness is hermetic and
# does not inherit a caller-supplied LARCH_DEBUG_TOKEN_REPORT (round-3
# review codex finding — without `env -u` running the harness with
# LARCH_DEBUG_TOKEN_REPORT=1 in the caller's env would flake the
# "unset" assertion). The empty-value case is exercised separately.
out=$(env -u LARCH_DEBUG_TOKEN_REPORT "$SCRIPT" \
    --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse)
case "$out" in
    *"jq stderr captured"*|*"jq stderr at "*) fail "<unset> env should not enable debug path: '$out'" ;;
    *) pass ;;
esac

for negative_value in "" "0" "false" "FALSE" "no" "NO" "off" "OFF" "disabled"; do
    out=$(LARCH_DEBUG_TOKEN_REPORT="$negative_value" "$SCRIPT" \
        --ledger "$LEDGER" --transcript "$MALFORMED_TRANSCRIPT" --since-last-mark --terse)
    case "$out" in
        *"jq stderr captured"*|*"jq stderr at "*) fail "negative env value '$negative_value' should not enable debug path: '$out'" ;;
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

# --- Inferred-skill attribution fixtures ---

# Case A: null-attributionSkill row within a step-mark window →
# rendered Skill cell contains "inferred:" prefix.
INFER_LEDGER="$TMP/infer-ledger.jsonl"
INFER_TRANSCRIPT="$TMP/infer-transcript.jsonl"
cat > "$INFER_LEDGER" <<'JSONL'
{"type":"mark","step":"Step 1 - design","ts":"2026-05-06T00:00:00Z"}
{"type":"mark","step":"Step 2 - implement","ts":"2026-05-06T00:01:00Z"}
JSONL
# Row at 00:00:30 has no attributionSkill — falls in Step 1 window [00:00:00, 00:01:00)
jq -c -n '{type:"assistant",timestamp:"2026-05-06T00:00:30.000Z",message:{usage:{input_tokens:5,cache_read_input_tokens:0,cache_creation_input_tokens:0,output_tokens:7}}}' > "$INFER_TRANSCRIPT"
infer_md=$("$SCRIPT" --ledger "$INFER_LEDGER" --transcript "$INFER_TRANSCRIPT" --full --markdown)
contains "case-A inferred prefix" "inferred:Step 1 - design" "$infer_md"

# Case B: null-attributionSkill row BEFORE the first mark → row excluded
# from the rendered table (claude_table renders only rows at or after the
# first mark; such rows do not appear as "unattributed" in the output).
PRE_MARK_TRANSCRIPT="$TMP/pre-mark-transcript.jsonl"
# Row at 1999-01-01 is before any mark in INFER_LEDGER (first mark at 2026-05-06T00:00:00Z)
jq -c -n '{type:"assistant",timestamp:"1999-01-01T00:00:00.000Z",message:{usage:{input_tokens:99,cache_read_input_tokens:0,cache_creation_input_tokens:0,output_tokens:99}}}' > "$PRE_MARK_TRANSCRIPT"
pre_md=$("$SCRIPT" --ledger "$INFER_LEDGER" --transcript "$PRE_MARK_TRANSCRIPT" --full --markdown)
# Grand total must be 0 (pre-mark row excluded entirely)
if grep -Fq '| **Grand total** |  | 0 | 0 | 0 | 0 |' <<<"$pre_md"; then pass
else fail "case-B: pre-mark null row should be excluded from grand total; got: $pre_md"
fi

# Case C: null-attributionSkill row at exactly a mark boundary ts → falls
# in the mark whose ts equals row.ts (half-open interval: mark.ts <= row.ts
# < next_mark.ts, so the boundary belongs to the opening mark).
BOUNDARY_TRANSCRIPT="$TMP/boundary-transcript.jsonl"
# Row timestamp equals Step 2 mark ts exactly → should be inferred as Step 2, not Step 1
jq -c -n '{type:"assistant",timestamp:"2026-05-06T00:01:00.000Z",message:{usage:{input_tokens:3,cache_read_input_tokens:0,cache_creation_input_tokens:0,output_tokens:4}}}' > "$BOUNDARY_TRANSCRIPT"
boundary_md=$("$SCRIPT" --ledger "$INFER_LEDGER" --transcript "$BOUNDARY_TRANSCRIPT" --full --markdown)
contains "case-C boundary in step2 window" "inferred:Step 2 - implement" "$boundary_md"
if grep -Fq "inferred:Step 1 - design" <<<"$boundary_md"; then
    fail "case-C: boundary row must NOT be in Step 1 window"
else
    pass
fi

# --- --summary mode ---

# Case 1: normal summary — Total: prefix + correct claude grand total + vendor parenthetical.
# Fixture: LEDGER (codex=100, cursor=10) + TRANSCRIPT (claude input/cache_read/cache_create/output = 11/22/33/44 grand totals).
summary=$("$SCRIPT" --ledger "$LEDGER" --transcript "$TRANSCRIPT" --summary)
contains "summary Total prefix"          "Total:"                            "$summary"
contains "summary claude grand total"    "claude=110 tokens"                 "$summary"
contains "summary vendor parenthetical"  "(codex=100, cursor=10)"            "$summary"

# Case 2: zero-vendor run — vendor=0 with no parenthetical.
# Build a mark-only ledger so the vendor total is 0; the existing TRANSCRIPT
# still contributes Claude usage, confirming the claude portion renders normally.
SUMMARY_NO_VENDOR_LEDGER="$TMP/summary-no-vendor-ledger.jsonl"
cat > "$SUMMARY_NO_VENDOR_LEDGER" <<'JSONL'
{"type":"mark","step":"Step 1 - design","ts":"2026-05-06T00:00:00Z"}
JSONL
summary_no_vendor=$("$SCRIPT" --ledger "$SUMMARY_NO_VENDOR_LEDGER" --transcript "$TRANSCRIPT" --summary)
contains "summary zero-vendor Total prefix" "Total:"    "$summary_no_vendor"
contains "summary zero-vendor vendor=0"     "vendor=0"  "$summary_no_vendor"
case "$summary_no_vendor" in
    *"vendor=0 ("*) fail "zero-vendor summary must not include parenthetical: $summary_no_vendor" ;;
    *) pass ;;
esac

# Case 3: no-marks ledger — prints unavailable warning and exits 0.
# Reuse LEDGER_NO_MARKS (vendor-only rows, no marks).
no_marks_summary=$("$SCRIPT" --ledger "$LEDGER_NO_MARKS" --transcript "$TRANSCRIPT" --summary 2>&1)
contains "summary no-marks unavailable" "Token report unavailable:" "$no_marks_summary"

total=$((PASS + FAIL))
if (( FAIL == 0 )); then
    echo "PASS: test-token-report.sh — $PASS/$total assertions"
else
    echo "FAIL: test-token-report.sh — $FAIL/$total assertions failed" >&2
    exit 1
fi
