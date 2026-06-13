#!/usr/bin/env bash
# test-render-review-phase-detail.sh — harness for render-review-phase-detail.sh (issue #3774).
set -euo pipefail
export LARCH_QUIET_DISABLE=1
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
HELPER="$REPO/scripts/render-review-phase-detail.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

assert_ascii_chart_invariants() {
    local file="$1"
    python3 - "$file" <<'PYCHART'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read().splitlines()
in_fence = False
chart = []
charts = []
for line in text:
    if line == "```":
        if in_fence:
            charts.append(chart)
            chart = []
            in_fence = False
        else:
            in_fence = True
        continue
    if in_fence:
        chart.append(line)
if not charts:
    raise SystemExit("no plain fenced charts found")
for chart in charts:
    borders = [line for line in chart if "┌" in line or "└" in line]
    rows = [line for line in chart if "│" in line]
    if not borders or not rows:
        continue
    left = borders[0].find("┌") if "┌" in borders[0] else borders[0].find("└")
    right = borders[0].find("┐") if "┐" in borders[0] else borders[0].find("┘")
    for line in borders:
        l = line.find("┌") if "┌" in line else line.find("└")
        r = line.find("┐") if "┐" in line else line.find("┘")
        assert l == left, line
        assert r == right, line
    axis = chart[1] if len(chart) > 1 else ""
    assert axis.find("0:00") == left + 1, axis
    for line in rows:
        assert line.find("│") == left, line
        assert line.rfind("│") == right, line
        track = line[left + 1:right]
        assert set(track) <= {" ", "█"}, track
        assert not re.search(r"█+ +█+", track), track
PYCHART
}

command -v jq >/dev/null 2>&1 || { printf 'SKIP: jq unavailable\n'; exit 0; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/trrpd.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

ROOT="$WORK/run"
mkdir -p "$ROOT/round-1" "$ROOT/round-2" "$ROOT/round-3"

# round 1: 4 suggestions (2 acc, 1 rej, 1 exon), 2 OOS proposed (1 acc), 6 reviewers,
# one failed slot (codex generalist STATUS=ERROR).
cat >"$ROOT/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"1","EXONERATED_COUNT":"1","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"1","OOS_REJECTED_COUNT":"1"},"summary":{"panel":{"static_slot_count":5,"dynamic_slot_count":1,"total_slot_count":6},"finding_counts":{"total_accepted":2,"total_rejected":1,"total_exonerated":1,"total_neutral":0}},"collector":"REVIEWER_FILE=/t/round-1/cursor-specialist-structure-output.txt\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\nREVIEWER_FILE=/t/round-1/codex-generalist-output.txt\nTOOL=codex\nSTATUS=ERROR\nEXIT_CODE=1\nFAILURE_REASON=timeout\n"}
JSON
cat >"$ROOT/round-1/panel-manifest.ndjson" <<'JSON'
{"slot":"structure","tool":"cursor","output":"/t/round-1/cursor-specialist-structure-output.txt"}
{"slot":"correctness","tool":"cursor","output":"/t/round-1/cursor-specialist-correctness-output.txt"}
{"slot":"generic","tool":"codex","output":"/t/round-1/codex-generalist-output.txt"}
JSON

# round 2: 3 suggestions (all accepted), 0 OOS, reviewers via static+dynamic fallback (3+1=4), no failures.
cat >"$ROOT/round-2/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"3","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"static_slot_count":3,"dynamic_slot_count":1}},"collector":""}
JSON
cat >"$ROOT/round-2/panel-manifest.ndjson" <<'JSON'
{"slot":"correctness","tool":"cursor","output":"/t/round-2/cursor-specialist-correctness-output.txt"}
JSON

# round 3: dir present but NO round-meta.json -> must be skipped entirely.
: >"$ROOT/round-3/placeholder"

# findings: accepted attribution -> cursor/correctness x4, cursor/structure x1.
cat >"$ROOT/review-findings-full.jsonl" <<'JSON'
{"id":"FINDING_1","outcome":"accepted","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1"}
{"id":"FINDING_2","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1"}
{"id":"OOS_C1_1","outcome":"out_of_scope","reviewer_slots":["codex-generalist-output.txt"],"round_num":"1"}
{"id":"REJ_C1_1","outcome":"rejected","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1"}
{"id":"FINDING_3","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"2"}
{"id":"FINDING_4","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"2"}
{"id":"FINDING_5","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"2"}
JSON

# timing ledger: round 1 = 300s (5m), round 2 = 120s (2m), plus vendor tasks.
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000300\t300\t2\t1\t2\t-\n'
    printf 'v1\tround\t1700001000\timplement\tStep 5 — code review\t2\t1700001000\t1700001120\t120\t3\t0\t0\t-\n'
    printf 'v1\tvendor\t1700000010\timplement\t-\tcursor\treview\t1700000000\t1700000120\t120\tcursor-specialist-structure-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000020\timplement\t-\tcodex\treview\t1700000060\t1700000200\t140\tReviewer:Unsafe,Name-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000025\timplement\t-\tclaude\tvendor-misc\t1700000025\t1700000040\t15\taggregator-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000030\timplement\t-\tcodex\tvendor-misc\t1700000030\t1700000050\t20\tscout-plan-manifest.json.raw\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000040\timplement\t-\tcodex\tcodex-plan-autofix\t1700000040\t1700000070\t30\tcodex-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000050\timplement\t-\tcursor\tcursor-plan-autofix\t1700000050\t1700000080\t30\tcursor-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700001010\timplement\t-\tcursor\treview\t1700001010\t1700001100\t90\tcursor-specialist-correctness-output.txt\t0\tcomplete\n'
} >"$ROOT/timing-ledger.tsv"

OUT="$WORK/section.md"
"$HELPER" --rounds-root "$ROOT" --findings-file "$ROOT/review-findings-full.jsonl" \
    --timing-ledger "$ROOT/timing-ledger.tsv" --skill implement --output "$OUT"

# --- Test 1: header + per-round rows + totals ---
grep -Fq -- '| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |' "$OUT" \
    || fail 'missing table header'
grep -Fq -- '| 1 | 4 | 2 | 2 | 1 | 5m 00s | — | 6 |' "$OUT" || fail "round-1 row wrong: $(grep -F '| 1 |' "$OUT" || true)"
grep -Fq -- '| 2 | 3 | 3 | 0 | 0 | 2m 00s | — | 4 |' "$OUT" || fail "round-2 row wrong: $(grep -F '| 2 |' "$OUT" || true)"
grep -Fq -- '| **Total** | **7** | **5** | **2** | **1** | **7m 00s** | **—** | **10** |' "$OUT" \
    || fail "total row wrong: $(grep -F 'Total' "$OUT" || true)"
pass 'per-round table + totals'

# --- Test 2: round-3 (no round-meta.json) is skipped ---
if grep -Eq '^\| 3 \|' "$OUT"; then fail 'round-3 without round-meta.json must be skipped'; fi
pass 'round dir without round-meta.json skipped'

# --- Test 3: top reviewers attributed by vendor/archetype ---
grep -Fq -- '1. cursor/correctness — 4' "$OUT" || fail "top reviewer #1 wrong: $(grep -F 'cursor/correctness' "$OUT" || true)"
grep -Fq -- 'cursor/structure — 1' "$OUT" || fail 'cursor/structure not attributed'
pass 'top reviewers by suggestions accepted'

# --- Test 4: failed reviewer slots by vendor/archetype ---
grep -Fq -- '**Reviewer slot failures**: 1' "$OUT" || fail "failure count wrong: $(grep -F 'failures' "$OUT" || true)"
grep -Fq -- '- codex/generic: 1' "$OUT" || fail 'failed slot not attributed to codex/generic'
pass 'reviewer slot failures attributed'

# --- Test 5: no token ledger -> cost cells are em dashes (no $); never the dollar-primary emoji ---
if grep -Fq -- '$' "$OUT"; then fail 'without a token ledger, cost cells must be em dashes (no dollar figures)'; fi
if grep -Fq -- '💰' "$OUT"; then fail 'output must not contain the dollar-primary cost emoji'; fi
grep -Fq -- 'per-round vendor cost' "$OUT" || fail 'missing vendor-cost footnote'
pass 'no-token-ledger cost cells are em dashes; footnote present'

# --- Test 5b: reviewer timing ASCII Gantt charts render after table and before top reviewers ---
total_line=$(grep -nF '| **Total** |' "$OUT" | head -1 | cut -d: -f1 || true)
gantt_line=$(grep -nF '### Round 1 reviewer timing' "$OUT" | head -1 | cut -d: -f1 || true)
top_line=$(grep -nF '**Top reviewers**' "$OUT" | head -1 | cut -d: -f1 || true)
[[ -n "$total_line" && -n "$gantt_line" && -n "$top_line" && "$total_line" -lt "$gantt_line" && "$gantt_line" -lt "$top_line" ]] \
    || fail 'Gantt chart must render after Total row and before Top reviewers'
grep -Fq -- '```' "$OUT" || fail 'ASCII chart missing plain fence'
if grep -Fq -- '```mermaid' "$OUT"; then fail 'ASCII chart must not use Mermaid fence'; fi
if grep -Fq -- 'dateFormat X' "$OUT" || grep -Fq -- 'axisFormat %H:%M:%S' "$OUT"; then fail 'ASCII chart must not contain Mermaid directives'; fi
grep -Fq -- 'Round 1 reviewer timing  ·  window 0:00-5:00 (300s)' "$OUT" || fail 'ASCII chart title must use m:ss span'
grep -Fq -- 'cursor/structure' "$OUT" || fail 'ASCII label must use slot_map when available'
grep -Fq -- 'unknown/reviewer:unsafe,name' "$OUT" || fail 'ASCII fallback label must preserve punctuation'
grep -Fq -- 'aggregator ' "$OUT" || fail 'ASCII fallback label must render aggregator'
grep -Fq -- 'scout ' "$OUT" || fail 'ASCII fallback label must render scout-plan-manifest as scout'
grep -Fq -- 'codex/codex-plan-autofix' "$OUT" || fail 'ASCII bare codex output must use task kind'
grep -Fq -- 'cursor/cursor-plan-autofix' "$OUT" || fail 'ASCII bare cursor output must use task kind'
grep -Fq -- 'cursor/correctness' "$OUT" || fail 'ASCII chart must render round 2 task'
grep -Fq -- '### Round 2 reviewer timing' "$OUT" || fail 'ASCII chart must render round 2 heading'
grep -Fq -- '120s' "$OUT" || fail 'ASCII chart must include bare duration suffix'
if grep -Eq '\([0-9]+-[0-9]+\)' "$OUT"; then fail 'ASCII chart must not include parenthesized ranges'; fi
assert_ascii_chart_invariants "$OUT"
pass 'reviewer timing ASCII charts render with raw labels and invariants'

NO_GANTT_OUT="$WORK/no-gantt.md"
"$HELPER" --rounds-root "$ROOT" --findings-file "$ROOT/review-findings-full.jsonl" \
    --timing-ledger "$ROOT/timing-ledger.tsv" --skill implement --no-gantt --output "$NO_GANTT_OUT"
grep -Fq -- '| 1 | 4 | 2 | 2 | 1 | 5m 00s | — | 6 |' "$NO_GANTT_OUT" || fail '--no-gantt must keep table rows'
if grep -Fq -- '```' "$NO_GANTT_OUT"; then fail '--no-gantt must suppress ASCII fences'; fi
if grep -Fq -- '### Round 1 reviewer timing' "$NO_GANTT_OUT"; then fail '--no-gantt must suppress timing headings'; fi
pass '--no-gantt suppresses charts only'

# --- Test 6: singular "reviewer" schema fallback ---
OLD="$WORK/old"
mkdir -p "$OLD/round-1"
cat >"$OLD/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"1","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}
JSON
cat >"$OLD/findings.jsonl" <<'JSON'
{"id":"FINDING_1","outcome":"accepted","reviewer":"cursor-specialist-edge-cases-output.txt","round_num":"1"}
JSON
OUT_OLD="$WORK/old-section.md"
"$HELPER" --rounds-root "$OLD" --findings-file "$OLD/findings.jsonl" --skill implement --output "$OUT_OLD"
grep -Fq -- 'cursor/edge-cases — 1' "$OUT_OLD" || fail "singular reviewer fallback wrong: $(cat "$OUT_OLD")"
# No timing ledger -> Time column is an em dash for the round.
grep -Fq -- '| 1 | 1 | 1 | 0 | 0 | — | — | 2 |' "$OUT_OLD" || fail "old-schema row wrong: $(grep -F '| 1 |' "$OUT_OLD" || true)"
pass 'singular reviewer fallback + missing-timing em dash'

# --- Test 7: no completed rounds -> explicit no-round message, exit 0 ---
EMPTY="$WORK/empty"
mkdir -p "$EMPTY"
EOUT="$WORK/empty.md"
"$HELPER" --rounds-root "$EMPTY" --skill implement --output "$EOUT"
[ -s "$EOUT" ] || fail 'no-rounds case must produce non-empty output'
grep -Fq -- '## Review Phase Detail' "$EOUT" || fail 'no-rounds case missing section heading'
grep -Fq -- 'No review rounds completed.' "$EOUT" || fail 'no-rounds case missing no-completed-rounds message'
pass 'no completed rounds -> no-round message'

INFLIGHT="$WORK/inflight"
mkdir -p "$INFLIGHT/round-1"
: >"$INFLIGHT/round-1/panel-manifest.ndjson"
IOUT="$WORK/inflight.md"
"$HELPER" --rounds-root "$INFLIGHT" --skill implement --output "$IOUT"
[ -s "$IOUT" ] || fail 'in-flight-only case must produce non-empty output'
grep -Fq -- 'No review rounds completed.' "$IOUT" || fail 'in-flight-only case missing no-completed-rounds message'
pass 'in-flight round dirs only -> no-round message'

# --- Test 8: usage errors exit 2 ---
rc=0; "$HELPER" --skill implement >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "missing --rounds-root should exit 2 (got $rc)"
rc=0; "$HELPER" --rounds-root "$ROOT" --skill bogus >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "invalid --skill should exit 2 (got $rc)"
pass 'usage errors exit 2'

# --- Test 9: stdout mode (no --output) prints the section ---
"$HELPER" --rounds-root "$ROOT" --findings-file "$ROOT/review-findings-full.jsonl" --skill implement \
    | grep -Fq -- '## Review Phase Detail' || fail 'stdout mode missing section heading'
pass 'stdout mode'

# --- Test 10: per-round VENDOR cost from token-ledger timestamp window (#3774 clarification) ---
# Guard: only run if jq supports fromdateiso8601. ISO timestamps are hardcoded
# (epoch→ISO was previously done via python3 -c '...', which caused flaky
# set -e exits when python3 failed to fork under CI process-limit pressure).
if echo '"2023-11-14T22:15:00Z"' | jq -e 'fromdateiso8601 | numbers' >/dev/null 2>&1; then
    CR="$WORK/cost-run"; mkdir -p "$CR/round-1" "$CR/round-2"
    cat >"$CR/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"1","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}
JSON
    cat >"$CR/round-2/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}
JSON
    # Round 1 window [1700000000,1700000300]; round 2 window [1700001000,1700001300].
    {
        printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000300\t300\t1\t0\t0\t-\n'
        printf 'v1\tround\t1700001000\timplement\tStep 5 — code review\t2\t1700001000\t1700001300\t300\t0\t0\t0\t-\n'
    } >"$CR/timing-ledger.tsv"
    # codex + claude_sub land in round-1 window; cursor is outside both (must be excluded).
    # Timestamps are hardcoded UTC ISO strings (epoch 1700000100, 1700000160, 1700002800)
    # to avoid spawning python3 subprocesses under CI process-limit pressure (#3781).
    {
        printf '{"type":"vendor","vendor":"codex","input":5000,"cache_read":20000,"cache_create":0,"output":3000,"total":28000,"ts":"2023-11-14T22:15:00Z"}\n'
        printf '{"type":"vendor","vendor":"claude_sub","input":3,"cache_read":48773,"cache_create":36197,"output":2724,"total":87697,"ts":"2023-11-14T22:16:00Z"}\n'
        printf '{"type":"vendor","vendor":"cursor","input":9999,"cache_read":99999,"cache_create":0,"output":9999,"total":119997,"ts":"2023-11-14T23:00:00Z"}\n'
    } >"$CR/token-ledger.jsonl"
    # Guard token cost CLI: split producer from post-processor so pipefail cannot mask which side failed.
    if ! _tc_out="$(python3 "$REPO/python/cli.py" token cost --codex-input-tokens 5000 --codex-cached-input-tokens 20000 --codex-output-tokens 3000 --claude-sub-input-tokens 3 --claude-sub-cache-read-tokens 48773 --claude-sub-cache-write-5m-tokens 36197 --claude-sub-output-tokens 2724 2>/dev/null)"; then
        fail "python3 python/cli.py token cost failed (rc=$?)"
    fi
    exp1="$(printf '%s\n' "$_tc_out" | awk -F= '$1=="TOTAL_COST"{print $2; exit}')"
    COUT="$WORK/cost-section.md"
    # Guard renderer call.
    "$HELPER" --rounds-root "$CR" --timing-ledger "$CR/timing-ledger.tsv" --token-ledger "$CR/token-ledger.jsonl" --skill implement --output "$COUT" || fail "render-review-phase-detail.sh failed (rc=$?)"
    grep -Fq -- "| 1 | 1 | 1 | 0 | 0 | 5m 00s | \$$exp1 | 2 |" "$COUT" || fail "round-1 vendor cost wrong (exp \$$exp1): $(grep -F '| 1 |' "$COUT" || true)"
    grep -Fq -- "| 2 | 0 | 0 | 0 | 0 | 5m 00s | \$0.00 | 2 |" "$COUT" || fail "round-2 empty-window cost should be \$0.00: $(grep -F '| 2 |' "$COUT" || true)"
    exptot="$(awk -v a="$exp1" 'BEGIN{printf "%.2f", a+0}')"
    grep -Fq -- "| **Total** | **1** | **1** | **0** | **0** | **10m 00s** | **\$$exptot** | **4** |" "$COUT" || fail "total vendor cost wrong (exp \$$exptot): $(grep -F 'Total' "$COUT" || true)"
    pass "per-round VENDOR cost: in-window priced, out-of-window excluded, empty window = \$0.00"
    # Regression: forced token cost CLI failure must emit FAIL:, not bare abort (#3781).
    _bad_repo="$WORK/bad-repo"; mkdir -p "$_bad_repo/python"
    printf 'raise SystemExit(1)\n' > "$_bad_repo/python/cli.py"
    _reg_out="$WORK/reg-fail.txt"
    set +e
    (
        if ! _tc_out="$(python3 "$_bad_repo/python/cli.py" token cost 2>/dev/null)"; then
            fail "python3 python/cli.py token cost failed (rc=$?)"
        fi
    ) >"$_reg_out" 2>&1
    _reg_rc=$?
    set -e
    command grep -Fq 'FAIL:' "$_reg_out" || fail "regression: forced subprocess failure must produce FAIL: diagnostic (got rc=$_reg_rc)"
    pass "regression: forced subprocess failure surfaces FAIL: diagnostic"
else
    printf 'SKIP: jq fromdateiso8601 unavailable; per-round vendor cost test skipped\n'
fi

DR="$WORK/design-run"
mkdir -p "$DR/round-1"
cat >"$DR/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"1","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"1","OOS_ACCEPTED_COUNT":"1","OOS_REJECTED_COUNT":"1"},"summary":{"panel":{"total_slot_count":1}},"collector":"TOOL=unknown\nSTATUS=FAILED\nREVIEWER_FILE=collector-failure-1.txt\n"}
JSON
cat >"$DR/round-1/panel-manifest.ndjson" <<'JSON'
{"slot":"claude-plan-generic","tool":"claude_sub","output":"/t/design/claude-plan-generic-output.txt"}
JSON
cat >"$DR/review-findings-full.jsonl" <<'JSON'
{"id":"FINDING_D1","outcome":"accepted","reviewer_slots":["claude-plan-generic-output.txt"],"round_num":""}
{"id":"FINDING_D2","outcome":"accepted","reviewer_slots":["claude-plan-generic-output.txt"],"round_num":""}
JSON
printf 'v1\tround\t1700000000\tdesign\tdesign Step 3 — plan review\t1\t1700000000\t1700000065\t65\t2\t1\t1\t-\n' >"$DR/timing-ledger.tsv"
printf 'v1\tvendor\t1700000010\timplement\t-\tclaude\treview\t1700000010\t1700000060\t50\tclaude-plan-generic-output.txt\t0\tcomplete\n' >>"$DR/timing-ledger.tsv"
DOUT="$WORK/design-section.md"
"$HELPER" --rounds-root "$DR" --findings-file "$DR/review-findings-full.jsonl" \
    --timing-ledger "$DR/timing-ledger.tsv" --skill design --output "$DOUT"
grep -Fq -- '## Review Phase Detail' "$DOUT" || fail 'design fixture missing Review Phase Detail heading'
grep -Fq -- '| 1 | 4 | 2 | 2 | 1 | 1m 05s | — | 1 |' "$DOUT" \
    || fail "design fixture row wrong: $(grep -F '| 1 |' "$DOUT" || true)"
grep -Fq -- '1. claude_sub/claude-plan-generic — 2' "$DOUT" \
    || fail "design top reviewer attribution wrong: $(grep -F 'claude' "$DOUT" || true)"
grep -Fq -- '**Reviewer slot failures**: 1' "$DOUT" || fail 'design collector placeholder failure count missing'
grep -Fq -- '- unknown/collector-failure-1: 1' "$DOUT" \
    || fail "design collector placeholder failure attribution wrong: $(grep -F 'collector-failure' "$DOUT" || true)"
grep -Fq -- '### Round 1 reviewer timing' "$DOUT" || fail 'design skill fixture missing reviewer timing despite vendor skill mismatch'
grep -Fq -- 'claude_sub/claude-plan-generic' "$DOUT" || fail 'design skill fixture must join vendor row to slot_map despite vendor skill mismatch'
assert_ascii_chart_invariants "$DOUT"
pass 'design skill fixture renders counts, attribution, collector failures, and timing'

CAP="$WORK/cap-run"
mkdir -p "$CAP/round-1"
cat >"$CAP/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":30}}}
JSON
printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700001000\t1000\t0\t0\t0\t-\n' >"$CAP/timing-ledger.tsv"
for i in $(seq 1 30); do
    start=$((1700000000 + i))
    end=$((start + 10))
    printf 'v1\tvendor\t%s\timplement\t-\tcodex\treview\t%s\t%s\t10\tcodex-specialist-cap-%02d-output.txt\t0\tcomplete\n' "$start" "$start" "$end" "$i" >>"$CAP/timing-ledger.tsv"
done
CAP_OUT="$WORK/cap.md"
"$HELPER" --rounds-root "$CAP" --timing-ledger "$CAP/timing-ledger.tsv" --skill implement --output "$CAP_OUT"
cap_tasks=$(grep -Ec '^codex/cap-[0-9][0-9]' "$CAP_OUT" || true)
[ "$cap_tasks" -eq 25 ] || fail "Gantt task cap must render 25 tasks (got $cap_tasks)"
assert_ascii_chart_invariants "$CAP_OUT"
pass 'Gantt task cap limits each round to 25 tasks'

SORT_RUN="$WORK/sort-run"
mkdir -p "$SORT_RUN/round-1"
cat >"$SORT_RUN/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":3}}}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000100\t100\t0\t0\t0\t-\n'
    printf 'v1\tvendor\t1700000000\timplement\t-\tcodex\treview\t1700000050\t1700000060\t10\tz label-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000000\timplement\t-\tcodex\treview\t1700000010\t1700000020\t10\tlabel with spaces-output.txt\t0\tcomplete\n'
    printf 'v1\tvendor\t1700000000\timplement\t-\tcodex\treview\t1700000010\t1700000015\t5\ta label-output.txt\t0\tcomplete\n'
} >"$SORT_RUN/timing-ledger.tsv"
SORT_OUT="$WORK/sort.md"
"$HELPER" --rounds-root "$SORT_RUN" --timing-ledger "$SORT_RUN/timing-ledger.tsv" --skill implement --output "$SORT_OUT"
a_line=$(grep -n '^unknown/a label ' "$SORT_OUT" | cut -d: -f1)
spaces_line=$(grep -n '^unknown/label with spaces ' "$SORT_OUT" | cut -d: -f1)
z_line=$(grep -n '^unknown/z label ' "$SORT_OUT" | cut -d: -f1)
[[ -n "$a_line" && -n "$spaces_line" && -n "$z_line" && "$a_line" -lt "$spaces_line" && "$spaces_line" -lt "$z_line" ]] \
    || fail 'ASCII rows must sort by absolute start, end, then label with tab delimiter'
pass 'ASCII rows sort by absolute start, end, then label'

MAL="$WORK/malformed-run"
mkdir -p "$MAL/round-1"
cat >"$MAL/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"1","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":1}}}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000100\t100\t1\t0\t0\t-\n'
    printf 'malformed\n'
    printf 'v1\tvendor\tbad\timplement\t-\tcodex\treview\tbad\trow\t0\tbad-output.txt\t0\tcomplete\n'
} >"$MAL/timing-ledger.tsv"
MAL_OUT="$WORK/malformed.md"
"$HELPER" --rounds-root "$MAL" --timing-ledger "$MAL/timing-ledger.tsv" --skill implement --output "$MAL_OUT" \
    || fail 'malformed timing rows must not fail rendering'
grep -Fq -- '| 1 | 1 | 1 | 0 | 0 | 1m 40s | — | 1 |' "$MAL_OUT" || fail 'malformed timing rows must keep the table'
grep -Fq -- 'No reviewer timing tasks overlapped this round.' "$MAL_OUT" || fail 'malformed timing rows should render no-task note'
pass 'malformed timing rows are best-effort'

# --- Test 11: skill-window contamination — table Time/Cost ignore other-skill round rows ---
CONT="$WORK/contamination"
mkdir -p "$CONT/round-1"
cat >"$CONT/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"1","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}
JSON
cat >"$CONT/round-1/panel-manifest.ndjson" <<'JSON'
{"slot":"correctness","tool":"cursor","output":"/t/cont/cursor-specialist-correctness-output.txt"}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000100\t100\t1\t0\t0\t-\n'
    printf 'v1\tround\t1700000000\tdesign\tdesign Step 3 — plan review\t1\t1700000000\t1700001800\t1800\t1\t0\t0\t-\n'
} >"$CONT/timing-ledger.tsv"
if echo '"2023-11-14T22:18:20Z"' | jq -e 'fromdateiso8601 | numbers' >/dev/null 2>&1; then
        printf '{"type":"vendor","vendor":"codex","input":5000,"cache_read":20000,"cache_create":0,"output":3000,"total":28000,"ts":"2023-11-14T22:21:40Z"}\n' >"$CONT/token-ledger.jsonl"
    if ! _tc_cont="$(python3 "$REPO/python/cli.py" token cost --codex-input-tokens 5000 --codex-cached-input-tokens 20000 --codex-output-tokens 3000 2>/dev/null)"; then
        fail "python3 python/cli.py token cost failed for contamination fixture (rc=$?)"
    fi
    exp_cont="$(printf '%s\n' "$_tc_cont" | awk -F= '$1=="TOTAL_COST"{print $2; exit}')"
    CONT_OUT="$WORK/contamination.md"
    "$HELPER" --rounds-root "$CONT" --timing-ledger "$CONT/timing-ledger.tsv" \
        --token-ledger "$CONT/token-ledger.jsonl" --skill implement --no-gantt --output "$CONT_OUT"
    grep -Fq -- "| 1 | 1 | 1 | 0 | 0 | 1m 40s | \$0.00 | 2 |" "$CONT_OUT" \
        || fail "skill-window Time must use implement window only: $(grep -F '| 1 |' "$CONT_OUT" || true)"
    if grep -Fq -- '30m' "$CONT_OUT" || grep -Fq -- '16m' "$CONT_OUT"; then
        fail 'skill-window Time must not use wider design round window'
    fi
    if grep -Fq -- "\$$exp_cont" "$CONT_OUT"; then
        fail "implement round Cost must exclude design-only token-ledger record (exp excluded \$$exp_cont)"
    fi
    grep -Fq -- "| **Total** | **1** | **1** | **0** | **0** | **1m 40s** | **\$0.00** | **2** |" "$CONT_OUT" \
        || fail "Total cost must exclude design-only token record: $(grep -F 'Total' "$CONT_OUT" || true)"
    pass 'skill-window contamination: table Time/Cost ignore other-skill round rows'
else
    printf 'SKIP: jq fromdateiso8601 unavailable; skill-window contamination test skipped\n'
fi

# --- Test 12: Gantt preservation — vendor rows join by unfiltered round overlap ---
GANTT_PRES="$WORK/gantt-preservation"
mkdir -p "$GANTT_PRES/round-1"
cat >"$GANTT_PRES/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":1}}}
JSON
cat >"$GANTT_PRES/round-1/panel-manifest.ndjson" <<'JSON'
{"slot":"structure","tool":"cursor","output":"/t/gp/cursor-specialist-structure-output.txt"}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000100\t100\t0\t0\t0\t-\n'
    printf 'v1\tround\t1700000000\tdesign\tdesign Step 3 — plan review\t1\t1700000000\t1700001800\t1800\t0\t0\t0\t-\n'
    printf 'v1\tvendor\t1700000500\timplement\t-\tcursor\treview\t1700000500\t1700000600\t100\tcursor-specialist-structure-output.txt\t0\tcomplete\n'
} >"$GANTT_PRES/timing-ledger.tsv"
GP_OUT="$WORK/gantt-preservation.md"
"$HELPER" --rounds-root "$GANTT_PRES" --timing-ledger "$GANTT_PRES/timing-ledger.tsv" --skill implement --output "$GP_OUT"
grep -Fq -- '### Round 1 reviewer timing' "$GP_OUT" || fail 'Gantt preservation fixture missing timing heading'
grep -Fq -- 'cursor/structure' "$GP_OUT" \
    || fail 'Gantt must include vendor row overlapping wider unfiltered round window'
assert_ascii_chart_invariants "$GP_OUT"
pass 'Gantt preservation: vendor rows join by unfiltered round overlap'

FAIL_RENDER="$WORK/fail-render"
mkdir -p "$FAIL_RENDER/round-1"
cat >"$FAIL_RENDER/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":1}}}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000060\t60\t0\t0\t0\t-\n'
    printf 'v1\tvendor\t1700000001\timplement\t-\tcodex\treview\t1700000001\t1700000010\t9\tcodex-review-output.txt\t0\tcomplete\n'
} >"$FAIL_RENDER/timing-ledger.tsv"
FAIL_BIN="$WORK/fail-bin"; mkdir -p "$FAIL_BIN"
printf '#!/usr/bin/env bash\nexit 1\n' >"$FAIL_BIN/python3"; chmod +x "$FAIL_BIN/python3"
FAIL_OUT="$WORK/fail-render.md"
PATH="$FAIL_BIN:$PATH" "$HELPER" --rounds-root "$FAIL_RENDER" --timing-ledger "$FAIL_RENDER/timing-ledger.tsv" --skill implement --output "$FAIL_OUT" \
    || fail 'renderer failure must not abort helper'
grep -Fq -- '| 1 | 0 | 0 | 0 | 0 | 1m 00s | — | 1 |' "$FAIL_OUT" || fail 'renderer failure must preserve table'
grep -Fq -- 'Reviewer timing chart unavailable.' "$FAIL_OUT" || fail 'renderer failure must emit neutral unavailable note'
if grep -Fq -- 'No reviewer timing tasks overlapped this round.' "$FAIL_OUT"; then fail 'renderer failure with rows must not emit no-task note'; fi
pass 'renderer failure is best-effort and not misreported as no tasks'

FAIL_EXTRACT="$WORK/fail-extract"
mkdir -p "$FAIL_EXTRACT/round-1"
cat >"$FAIL_EXTRACT/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"0","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":1}}}
JSON
{
    printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000060\t60\t0\t0\t0\t-\n'
    printf 'v1\tvendor\t1700000001\timplement\t-\tcodex\treview\t1700000001\t1700000010\t9\tcodex-review-output.txt\t0\tcomplete\n'
} >"$FAIL_EXTRACT/timing-ledger.tsv"
FAIL_SORT_BIN="$WORK/fail-sort-bin"; mkdir -p "$FAIL_SORT_BIN"
cat >"$FAIL_SORT_BIN/sort" <<'SH'
#!/usr/bin/env bash
for arg in "$@"; do
    case "$arg" in
        -k2,2n) exit 1 ;;
    esac
done
exec /usr/bin/sort "$@"
SH
chmod +x "$FAIL_SORT_BIN/sort"
FAIL_EXTRACT_OUT="$WORK/fail-extract.md"
PATH="$FAIL_SORT_BIN:$PATH" "$HELPER" --rounds-root "$FAIL_EXTRACT" --timing-ledger "$FAIL_EXTRACT/timing-ledger.tsv" --skill implement --output "$FAIL_EXTRACT_OUT" \
    || fail 'extraction failure must not abort helper'
grep -Fq -- 'Reviewer timing chart unavailable.' "$FAIL_EXTRACT_OUT" || fail 'extraction failure must emit unavailable note'
if grep -Fq -- 'No reviewer timing tasks overlapped this round.' "$FAIL_EXTRACT_OUT"; then fail 'extraction failure with overlapping vendor rows must not emit no-task note'; fi
pass 'extraction failure is not misreported as no tasks'

CWD_OUT="$WORK/cwd.md"
( cd "$WORK" && "$HELPER" --rounds-root "$GANTT_PRES" --timing-ledger "$GANTT_PRES/timing-ledger.tsv" --skill implement --output "$CWD_OUT" )
grep -Fq -- 'cursor/structure' "$CWD_OUT" || fail 'renderer must launch when cwd is outside repo root'
pass 'renderer launches via SCRIPT_DIR outside repo root'

ROUND_META="$REPO/scripts/write-design-round-meta.sh"
TSV_SEC="$WORK/tsv-fallback-security-oos"
mkdir -p "$TSV_SEC"
cat >"$TSV_SEC/findings-classification.tsv" <<'TSV'
finding_id	finding_reviewers	voting_result	v1_vote	v1_correctness	v1_severity	v1_quality	v1_uncertain	v1_tool
OOS_1	Codex-Security	accepted
OOS_2	Codex-Security	rejected
TSV
cat >"$TSV_SEC/findings-oos.md" <<'MD'
### OOS_1: Security hardening note
- **Reviewer**: Codex-Security
- focus-area = security
- Concern: rotate keys.

### OOS_2: Security rejected note
- **Reviewer**: Codex-Security
- focus-area = security
- Concern: audit logging.
MD
printf '{"slot":"security","tool":"codex","output":"/t/sec-output.txt"}\n' >"$TSV_SEC/plan-review-slots.ndjson"
"$ROUND_META" --round-dir "$TSV_SEC"
jq -e '.tally.OOS_ACCEPTED_COUNT == "0" and .tally.OOS_REJECTED_COUNT == "0"' \
    "$TSV_SEC/round-meta.json" >/dev/null \
    || fail "TSV fallback should exclude security-tagged OOS counts"
pass 'write-design-round-meta TSV fallback security OOS adjustment'

printf 'PASS: test-render-review-phase-detail.sh\n'
