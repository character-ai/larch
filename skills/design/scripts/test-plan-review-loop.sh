#!/usr/bin/env bash
# Offline integration tests for plan-review-loop.sh (PATH-style stubs via LARCH_PLAN_REVIEW_*_SH).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

bash -n "$PLR" || fail "bash -n plan-review-loop.sh failed"

set +e
"$PLR" --plan-file "$ROOT/README.md" --codex-present true --cursor-present true 2>/dev/null
rc=$?
set -e
[[ "$rc" == 2 ]] || fail "expected exit 2 when --design-tmpdir missing, got $rc"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-plan-review-loop.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/stub-bin"
mkdir -p "$STUB"

write_scout() {
    cat >"$STUB/scout-plan-archetypes-wrapper.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) out="${2:?}"; shift 2 ;;
        --plan-file|--description-file|--max-archetypes|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$out" ]] || exit 2
printf '%s\n' '{"archetypes":[]}' >"$out"
EOS
    chmod +x "$STUB/scout-plan-archetypes-wrapper.sh"
}

write_dispatch_one_slot() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
PLAN_FILE=""
FEATURE_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file) FEATURE_FILE="${2:?}"; shift 2 ;;
        --codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" && -n "$PLAN_FILE" && -n "$FEATURE_FILE" ]] || exit 2
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
PROMPT="$DESIGN_TMPDIR/render-plan-cursor-arch.prompt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'","prompt_file":"'"$PROMPT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
: >"$PROMPT"
cp "$FEATURE_FILE" "$DESIGN_TMPDIR/feature-file-seen.txt"
printf '%s\n' "$FEATURE_FILE" >"$DESIGN_TMPDIR/feature-file-path.txt"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_three_slots() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
PLAN_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?}"; shift 2 ;;
        --feature-file|--codex-present|--cursor-present|--timeout) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" && -n "$PLAN_FILE" ]] || exit 2
OUT1="$DESIGN_TMPDIR/rv1.txt"
OUT2="$DESIGN_TMPDIR/rv2.txt"
OUT3="$DESIGN_TMPDIR/rv3.txt"
PROMPT1="$DESIGN_TMPDIR/p1.prompt"
PROMPT2="$DESIGN_TMPDIR/p2.prompt"
PROMPT3="$DESIGN_TMPDIR/p3.prompt"
: >"$OUT1"
: >"$OUT2"
: >"$OUT3"
: >"$PROMPT1"
: >"$PROMPT2"
: >"$PROMPT3"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
{
    printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT1"'","prompt_file":"'"$PROMPT1"'"}'
    printf '%s\n' '{"slot":"cursor-plan-edge","tool":"cursor","output":"'"$OUT2"'","prompt_file":"'"$PROMPT2"'"}'
    printf '%s\n' '{"slot":"cursor-plan-innov","tool":"cursor","output":"'"$OUT3"'","prompt_file":"'"$PROMPT3"'"}'
} >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
printf '%s\n' "$OUT1" "$OUT2" "$OUT3" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\nALL_OUTPUT_FILES_PATH=%s\n' "$PATHS" "$PATHS"
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_dispatch_fail() {
    cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
printf 'DISPATCH_OK=false\nFALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=false\n'
EOS
    chmod +x "$STUB/dispatch-plan-review-panel.sh"
}

write_collect() {
    local mode="${1:?}"
    cat >"$STUB/collect-agent-results.sh" <<EOS
#!/usr/bin/env bash
set -euo pipefail
paths=""
while [[ \$# -gt 0 ]]; do
    case "\$1" in
        --paths-file) paths="\${2:?}"; shift 2 ;;
        --timeout) shift 2 ;;
        --substantive-validation|--validation-mode|--structured-reviewer-validation) shift 1 ;;
        *) shift 1 ;;
    esac
done
[[ -n "\$paths" && -f "\$paths" ]] || exit 1
idx=0
while IFS= read -r p || [[ -n "\$p" ]]; do
    [[ -z "\$p" ]] && continue
    tsv="\${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
EOS
    if [[ "$mode" == "empty" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    } >"$tsv"
EOS
    elif [[ "$mode" == "three_distinct" ]]; then
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    idx=$((idx + 1))
        case "$idx" in
            1)
                printf '%s\n' "in_scope	important	correctness	src/a	Alpha zqf9m planreview distinct finding	scenario one	fix one"
                printf '%s\n' "out_of_scope	important	correctness	src/oos1	Beta kjp2x planreview distinct oos	scenario oos	fix oos"
                ;;
            2)
                printf '%s\n' "in_scope	important	correctness	src/b	Gamma nmr7w planreview distinct finding	scenario two	fix two"
                printf '%s\n' "out_of_scope	important	correctness	src/oos2	Delta hxp4q planreview distinct oos	scenario oos2	fix oos2"
                ;;
            3)
                printf '%s\n' "in_scope	important	correctness	src/c	Epsilon wvt8r planreview distinct finding	scenario three	fix three"
                printf '%s\n' "out_of_scope	important	correctness	src/oos3	Zeta mlb3s planreview distinct oos	scenario oos3	fix oos3"
                ;;
            *) printf '%s\n' "in_scope	important	correctness	src/x	unexpected row	scen	fix" ;;
        esac
    } >"$tsv"
EOS
    else
        cat >>"$STUB/collect-agent-results.sh" <<'EOS'
        printf '%s\n' "in_scope	important	correctness	src/a	Alpha concern text goes here	scenario one	fix one"
    } >"$tsv"
EOS
    fi
    cat >>"$STUB/collect-agent-results.sh" <<'EOS'
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
    chmod +x "$STUB/collect-agent-results.sh"
}

write_voters_three() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/vstub1.txt"
v2="$DESIGN_TMPDIR/vstub2.txt"
v3="$DESIGN_TMPDIR/vstub3.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
for f in "$v1" "$v2" "$v3"; do
    cat >"$f" <<'INNER'
FINDING_1: YES
INNER
done
printf '%s\n' "$v1" "$v2" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

write_voters_slot2_failed() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/claude-vote-output.txt"
v3="$DESIGN_TMPDIR/cursor-vote-output.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
for f in "$v1" "$v3"; do
    cat >"$f" <<'INNER'
FINDING_1: YES
INNER
done
printf '%s\n' "$v1" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=failed\n' "$DESIGN_TMPDIR/codex-vote-output.txt"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

# Plan ballot after dedup: three FINDING_* and three OOS_* blocks (tally needs one line per id per voter).
write_voters_plan_six() {
    cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;;
        --ballot-file|--codex-available|--cursor-available|--session-env-path) shift 2 ;;
        *) shift 1 ;;
    esac
done
[[ -n "$DESIGN_TMPDIR" ]] || exit 2
v1="$DESIGN_TMPDIR/vstub1.txt"
v2="$DESIGN_TMPDIR/vstub2.txt"
v3="$DESIGN_TMPDIR/vstub3.txt"
vp="$DESIGN_TMPDIR/voter-paths.list"
_vote_body=$'FINDING_1: YES\nFINDING_2: YES\nFINDING_3: YES\nOOS_1: YES\nOOS_2: YES\nOOS_3: YES\n'
for f in "$v1" "$v2" "$v3"; do
    printf '%s' "$_vote_body" >"$f"
done
printf '%s\n' "$v1" "$v2" "$v3" >"$vp"
printf 'DISPATCH_OK=true\nVOTER_PATHS_FILE=%s\nVOTER_1_PARSE_RATE_STATUS=ok\n' "$vp"
printf 'VOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\n' "$v1"
printf 'VOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v2"
printf 'VOTER_3_PATH=%s\nVOTER_3_TOOL=cursor\nVOTER_3_STATUS=launched\n' "$v3"
EOS
    chmod +x "$STUB/dispatch-plan-voters.sh"
}

write_tally_fail() {
    cat >"$STUB/tally-plan-review.sh" <<'EOS'
#!/usr/bin/env bash
echo "tally stub failure" >&2
exit 2
EOS
    chmod +x "$STUB/tally-plan-review.sh"
}

run_loop() {
    local d="$1"
    local round_num="${2:-1}"
    export CLAUDE_PLUGIN_ROOT="$ROOT"
    export LARCH_QUIET_DISABLE=1
    export LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh"
    export LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh"
    export LARCH_PLAN_REVIEW_TALLY_SH="${LARCH_PLAN_REVIEW_TALLY_SH:-$ROOT/skills/design/scripts/tally-plan-review.sh}"
    export LARCH_AGGREGATOR_DISABLED=1
    bash "$PLR" \
        --design-tmpdir "$d" \
        --plan-file "$d/plan.txt" \
        --feature-file "$d/feature-description.txt" \
        --codex-present true \
        --cursor-present true \
        --round-num "$round_num"
}

echo "=== stubbed driver: zero findings (empty TSV) ==="
D0="$TMP/z0"
mkdir -p "$D0"
printf 'plan\n' >"$D0/plan.txt"
printf 'feat\n' >"$D0/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect empty
write_voters_three
out0=$(run_loop "$D0")
printf '%s\n' "$out0" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings$' || fail "expected skipped-empty-findings TALLY kv"
printf '%s\n' "$out0" | grep -q '^WARN=plan-review-tsv:' || fail "expected WARN for empty TSV path"
[[ -f "$D0/ballot.txt" ]] || fail "ballot.txt missing on zero-findings path"
grep -q 'No findings were raised' "$D0/voting-tally.md" || fail "expected zero-findings tally prose"
[[ -f "$D0/plan-review/round-1/findings-classification.tsv" ]] || fail "zero-findings classification TSV missing"
[[ "$(wc -l < "$D0/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "zero-findings classification TSV should contain header only"

echo "=== stubbed driver: one finding + real tally ==="
D1="$TMP/z1"
mkdir -p "$D1"
printf 'plan\n' >"$D1/plan.txt"
printf 'feat\n' >"$D1/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out1=$(run_loop "$D1")
printf '%s\n' "$out1" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status"
printf '%s\n' "$out1" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete loop"
grep -q 'FINDING_1' "$D1/accepted-plan-findings.md" || fail "accepted finding missing"
[[ -f "$D1/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV missing for real tally"

echo "=== stubbed driver: round-2 artifacts honor --round-num ==="
D1R2="$TMP/z1r2"
mkdir -p "$D1R2"
printf 'plan\n' >"$D1R2/plan.txt"
printf 'feat\n' >"$D1R2/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
out1r2=$(run_loop "$D1R2" 2)
printf '%s\n' "$out1r2" | grep -q '^ROUNDS_COMPLETED=2$' || fail "expected round-2 ROUNDS_COMPLETED kv"
[[ -f "$D1R2/plan-review/round-2/findings-classification.tsv" ]] || fail "round-2 classification TSV missing"
[[ ! -e "$D1R2/plan-review/round-1/findings-classification.tsv" ]] || fail "round-2 run must not write round-1 TSV"

echo "=== panel-failed path writes header-only classification TSV ==="
D1P="$TMP/z1p"
mkdir -p "$D1P"
printf 'plan\n' >"$D1P/plan.txt"
printf 'feat\n' >"$D1P/feature-description.txt"
write_scout
write_dispatch_fail
write_collect one
write_voters_three
set +e
out1p=$(run_loop "$D1P")
rc1p=$?
set -e
[[ "$rc1p" -eq 1 ]] || fail "panel-failed path should exit 1"
printf '%s\n' "$out1p" | grep -q '^LOOP_STATUS=panel-failed$' || fail "expected panel-failed loop status"
[[ -f "$D1P/plan-review/round-1/findings-classification.tsv" ]] || fail "panel-failed classification TSV missing"
[[ "$(wc -l < "$D1P/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "panel-failed TSV should contain header only"

echo "=== stubbed driver: failed middle voter preserves canonical tally slot ==="
D1B="$TMP/z1b"
mkdir -p "$D1B"
printf 'plan\n' >"$D1B/plan.txt"
printf 'feat\n' >"$D1B/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_slot2_failed
out1b=$(run_loop "$D1B")
printf '%s\n' "$out1b" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status with failed middle voter"
python3 - "$D1B/plan-review/round-1/findings-classification.tsv" <<'PY'
import csv, sys
with open(sys.argv[1], newline="", encoding="utf-8") as fh:
    row = next(csv.DictReader(fh, delimiter="\t"))
assert row["finding_id"] == "FINDING_1"
assert row["v1_tool"] == "Claude"
assert row["v2_tool"] == ""
assert row["v3_tool"] == "Cursor"
PY

echo "=== brainstorm context merges into feature file before dispatch ==="
DB="$TMP/zb"
mkdir -p "$DB"
printf 'plan\n' >"$DB/plan.txt"
printf 'feat base\n' >"$DB/feature-description.txt"
cat >"$DB/brainstorm.md" <<'EOS'
## Brainstorm Synthesis

### Idea
**Source:** claude-brainstorm
extra context
EOS
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
outb=$(run_loop "$DB")
printf '%s\n' "$outb" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status with brainstorm merge"
grep -Fq '## Feature / issue context (base)' "$DB/feature-file-seen.txt" || fail "merged feature file missing base header"
grep -Fq 'feat base' "$DB/feature-file-seen.txt" || fail "merged feature file missing base content"
grep -Fq '## Brainstorm synthesis (additive; optional)' "$DB/feature-file-seen.txt" || fail "merged feature file missing brainstorm header"
grep -Fq 'extra context' "$DB/feature-file-seen.txt" || fail "merged feature file missing brainstorm content"

echo "=== stubbed tally failure still emits loop KVs ==="
D2="$TMP/z2"
mkdir -p "$D2"
cp "$D1/plan.txt" "$D2/plan.txt"
cp "$D1/feature-description.txt" "$D2/feature-description.txt"
write_scout
write_dispatch_one_slot
write_collect one
write_voters_three
write_tally_fail
_prev_tally="${LARCH_PLAN_REVIEW_TALLY_SH:-}"
export LARCH_PLAN_REVIEW_TALLY_SH="$STUB/tally-plan-review.sh"
out2=$(run_loop "$D2")
if [[ -n "$_prev_tally" ]]; then
    export LARCH_PLAN_REVIEW_TALLY_SH="$_prev_tally"
else
    unset LARCH_PLAN_REVIEW_TALLY_SH
fi
printf '%s\n' "$out2" | grep -q '^TALLY_PLAN_REVIEW_STATUS=tally-error$' || fail "expected tally-error after stub tally rc=2"
printf '%s\n' "$out2" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete loop after tally failure"
printf '%s\n' "$out2" | grep -q '^WARN=plan-review-tally:' || fail "expected tally WARN"
[[ -f "$D2/voting-tally.md" ]] || fail "voting-tally.md missing after stub tally failure"
[[ -s "$D2/voting-tally.md" ]] || fail "voting-tally.md empty after stub tally failure"
grep -q 'Tally aborted' "$D2/voting-tally.md" || fail "stub tally banner missing in voting-tally.md"
[[ -f "$D2/plan-review/round-1/findings-classification.tsv" ]] || fail "classification TSV missing after stub tally failure"
[[ "$(wc -l < "$D2/plan-review/round-1/findings-classification.tsv" | tr -d ' ')" == "1" ]] || fail "tally-error TSV should contain header only"

echo "=== stubbed driver: three reviewers each OOS_1 + FINDING_1 (dedup + tally) ==="
D3="$TMP/z3"
mkdir -p "$D3"
printf 'plan\n' >"$D3/plan.txt"
printf 'feat\n' >"$D3/feature-description.txt"
write_scout
write_dispatch_three_slots
write_collect three_distinct
write_voters_plan_six
out3=$(run_loop "$D3")
printf '%s\n' "$out3" | grep -q '^TALLY_PLAN_REVIEW_STATUS=ok$' || fail "expected ok tally status (three-reviewer case)"
printf '%s\n' "$out3" | grep -q '^LOOP_STATUS=complete$' || fail "expected complete loop (three-reviewer case)"
[[ -s "$D3/ballot.txt" ]] || fail "ballot.txt missing or empty (three-reviewer case)"
for _h in "### OOS_1:" "### OOS_2:" "### OOS_3:"; do
    _c=$(grep -cF "$_h" "$D3/findings.md" 2>/dev/null || true)
    [[ "$_c" -eq 1 ]] || fail "expected exactly one $_h in findings.md, got $_c"
    _b=$(grep -cF "$_h" "$D3/ballot.txt" 2>/dev/null || true)
    [[ "$_b" -eq 1 ]] || fail "expected exactly one $_h in ballot.txt, got $_b"
done
python3 - "$D3/findings.md" <<'PY' || fail "FINDING heading ids not strictly increasing from 1 in findings.md"
import re, sys

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
nums = [int(m.group(1)) for m in re.finditer(r"^### FINDING_(\d+):", text, re.M)]
if not nums:
    print("no FINDING headings", file=sys.stderr)
    sys.exit(1)
if nums[0] != 1:
    print("FINDING ids must start at 1", file=sys.stderr)
    sys.exit(1)
for a, b in zip(nums, nums[1:]):
    if b <= a:
        print(f"not strictly increasing: {nums}", file=sys.stderr)
        sys.exit(1)
PY

printf '%s\n' "test-plan-review-loop: ok"
