#!/usr/bin/env bash
# Regression harness for /design Step 3 review-round cap handling.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

extract_block() {
    local anchor="$1"
    awk -v anchor="$anchor" '
        index($0, anchor) { found=1; next }
        found && /^```bash$/ { in_block=1; next }
        found && in_block && /^```$/ { exit }
        found && in_block { print }
    ' "$SKILL_MD"
}

guard_block="$(extract_block '**Review-round cap entry guard**:')"
[[ -n "$guard_block" ]] || fail "could not extract Step 3 cap guard block"

driver_block="$(extract_block "### Plan review driver (\`plan-review-loop.sh\`)")"
[[ -n "$driver_block" ]] || fail "could not extract Step 3 plan-review driver block"

grep -Fq 'The Step 3.5 continuation block below is bypassed on this path.' "$SKILL_MD" \
    || fail "SKILL missing explicit Step 3.5 bypass prose"
grep -Fq "including \`LOOP_STATUS=panel-failed\`" "$SKILL_MD" \
    || fail "SKILL missing panel-failed counter-consumption prose"
grep -Fq "MUST NOT persist when \`TALLY_PLAN_REVIEW_STATUS=tally-error\`" "$SKILL_MD" \
    || fail "SKILL missing tally-error non-consumption prose"
# shellcheck disable=SC2016 # ${...} tokens are literal markdown/code pins.
grep -Fq '**⚠ Step 3: review-round cap (${_round_cap}) reached for ${_tier}; skipping panel and continuing to Step 3b, Step 4, then Gate C.**' "$SKILL_MD" \
    || fail "SKILL missing exact review-round cap breadcrumb"
grep -Fq 'WARN=Step 3: refusing to clean symlinked plan-review directory' "$SKILL_MD" \
    || fail "SKILL missing symlinked plan-review cleanup warning"

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-step3-cap-test.XXXXXX")"
TEST_HOME="$TMPROOT/home"
ENV_FILE="$TEST_HOME/.cache/larch/sessions/current-design-env-$$.sh"
trap 'rm -rf "$TMPROOT"; rm -f "$ENV_FILE"' EXIT
mkdir -p "$(dirname "$ENV_FILE")"

rewrite_env_source() {
    perl -0pe 's{\[ -f ~/.cache/larch/sessions/current-design-env-\$PPID\.sh \] && source ~/.cache/larch/sessions/current-design-env-\$PPID\.sh}{source "'"$ENV_FILE"'"}g'
}

guard_block="$(printf '%s\n' "$guard_block" | rewrite_env_source)"
driver_block="$(printf '%s\n' "$driver_block" | rewrite_env_source)"

run_guard() {
    local design_tmpdir="$1"
    cat >"$ENV_FILE" <<EOF
DESIGN_TMPDIR=$(printf '%q' "$design_tmpdir")
CLAUDE_PLUGIN_ROOT=$(printf '%q' "$design_tmpdir")
EOF
    HOME="$TEST_HOME" bash -lc "$guard_block"
}

run_driver() {
    local design_tmpdir="$1"
    cat >"$ENV_FILE" <<EOF
DESIGN_TMPDIR=$(printf '%q' "$design_tmpdir")
CLAUDE_PLUGIN_ROOT=$(printf '%q' "$design_tmpdir")
CODEX_PRESENT=true
CURSOR_PRESENT=true
EOF
    HOME="$TEST_HOME" bash -lc "$driver_block
printf 'LOOP_STATUS=%s\n' \"\${LOOP_STATUS:-}\"
printf 'TALLY_PLAN_REVIEW_STATUS=%s\n' \"\${TALLY_PLAN_REVIEW_STATUS:-}\"
"
}

write_common_inputs() {
    local dir="$1" classification="$2"
    mkdir -p "$dir/scripts" "$dir/skills/design/scripts"
    cat >"$dir/run-params.json" <<EOF
{"schema_version":2,"design_classification":"$classification","workflow_path":"$classification","partition_requested":false,"brainstorm_requested":false}
EOF
    printf '# Plan\n\ndiff_lines: 1\n' >"$dir/plan.txt"
    printf 'feature\n' >"$dir/feature-description.txt"
    ln -sf "$ROOT/scripts/read-design-classification.sh" "$dir/scripts/read-design-classification.sh"
}

write_loop_stub() {
    local dir="$1" body="$2"
    mkdir -p "$dir/skills/design/scripts"
    cat >"$dir/skills/design/scripts/plan-review-loop.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
$body
EOF
    chmod +x "$dir/skills/design/scripts/plan-review-loop.sh"
}

write_snapshot_stub() {
    local dir="$1"
    mkdir -p "$dir/skills/design/scripts"
    cat >"$dir/skills/design/scripts/snapshot-plan-round.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
subcmd="${1:?}"
shift
design_tmpdir=""
round=""
value=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir) design_tmpdir="${2:?}"; shift 2 ;;
        --round) round="${2:?}"; shift 2 ;;
        --value) value="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
case "$subcmd" in
    read-cursor)
        current=1
        [[ -f "$design_tmpdir/plan-review-round-cursor.txt" ]] && current="$(cat "$design_tmpdir/plan-review-round-cursor.txt")"
        printf 'ROUND_CURSOR=%s\n' "$current"
        ;;
    write-cursor)
        printf '%s\n' "$value" >"$design_tmpdir/plan-review-round-cursor.txt"
        printf 'write-cursor:%s\n' "$value" >>"$design_tmpdir/snapshot.log"
        ;;
    *)
        echo "unexpected snapshot subcmd: $subcmd" >&2
        exit 2
        ;;
esac
EOF
    chmod +x "$dir/skills/design/scripts/snapshot-plan-round.sh"
}

echo "=== missing counter starts at round 1 ==="
D1="$TMPROOT/round1"
write_common_inputs "$D1" SIMPLE
run_guard "$D1" >/tmp/larch-step3-cap.guard1.out
grep -Fq 'STEP3_REVIEW_CAP_REACHED=false' "$D1/.step3-review-cap.env" || fail "expected cap false on first entry"
grep -Fq 'STEP3_REVIEW_ROUND_NUM=1' "$D1/.step3-review-cap.env" || fail "expected first entry round number 1"

echo "=== cap reached bypasses loop ==="
D2="$TMPROOT/cap-reached"
write_common_inputs "$D2" SIMPLE
printf '3\n' >"$D2/review-round-count.txt"
write_loop_stub "$D2" 'exit 97'
run_guard "$D2" >/tmp/larch-step3-cap.guard2.out
grep -Fq 'STEP3_REVIEW_CAP_REACHED=true' "$D2/.step3-review-cap.env" || fail "expected cap reached env"
driver_out=$(run_driver "$D2")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=cap-reached$' || fail "expected cap-reached loop status"
printf '%s\n' "$driver_out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached$' || fail "expected skipped-cap-reached tally status"
[[ "$(cat "$D2/review-round-count.txt")" == "3" ]] || fail "cap-reached path must leave counter unchanged"

echo "=== panel-failed consumes the pending round ==="
D3="$TMPROOT/panel-failed"
write_common_inputs "$D3" SIMPLE
printf '1\n' >"$D3/review-round-count.txt"
write_loop_stub "$D3" "printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=panel-failed\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\nVOTER_1_PARSE_RATE_STATUS=SKIPPED\n'; exit 1"
run_guard "$D3" >/tmp/larch-step3-cap.guard3.out
driver_out=$(run_driver "$D3")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=panel-failed$' || fail "expected panel-failed loop status"
[[ "$(cat "$D3/review-round-count.txt")" == "2" ]] || fail "panel-failed path should consume pending round"

echo "=== unrecognized loop status still consumes the pending round ==="
D3B="$TMPROOT/unrecognized-status"
write_common_inputs "$D3B" SIMPLE
printf '1\n' >"$D3B/review-round-count.txt"
write_loop_stub "$D3B" "printf 'LOOP_STATUS=weird-status\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\nVOTER_1_PARSE_RATE_STATUS=SKIPPED\n'; exit 1"
run_guard "$D3B" >/tmp/larch-step3-cap.guard3b.out
driver_out=$(run_driver "$D3B")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=panel-failed$' || fail "invalid loop status should be normalized to panel-failed"
[[ "$(cat "$D3B/review-round-count.txt")" == "2" ]] || fail "unrecognized post-launch status should keep pending round consumed"

echo "=== passive-summary statuses parse and persist across Step 3 entries ==="
DP="$TMPROOT/passive-summary"
write_common_inputs "$DP" HARD
write_snapshot_stub "$DP"
mkdir -p "$DP/plan-review/round-1" "$DP/plan-review/round-2"
printf 'stale\n' >"$DP/plan-review/round-1/stale.txt"
printf 'stale\n' >"$DP/plan-review/round-2/stale.txt"
write_loop_stub "$DP" "mkdir -p \"$DP/plan-review/round-1\"; printf 'fresh\n' >\"$DP/plan-review/round-1/new.txt\"; printf 'LOOP_STATUS=converged\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nREASON=streak\nREVISE_STATUS=ok\nCONVERGENCE_STREAK=2\nCOLLECT_OK_COUNT=1\nCOLLECT_FAILURE_COUNT=0\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=$DP/voting-tally.md\nVOTER_1_PARSE_RATE_STATUS=ok\n'; exit 0"
run_guard "$DP" >/tmp/larch-step3-cap.guardp1.out
driver_out=$(run_driver "$DP")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=converged$' || fail "expected converged passive-summary status"
[[ "$(cat "$DP/review-round-count.txt")" == "1" ]] || fail "first passive-summary entry should persist round 1"
[[ -f "$DP/plan-review/round-1/new.txt" ]] || fail "fresh round-1 artifact missing after first entry"
[[ ! -e "$DP/plan-review/round-1/stale.txt" ]] || fail "stale round-1 artifact should be cleaned before launch"
[[ ! -e "$DP/plan-review/round-2/stale.txt" ]] || fail "stale round-2 artifact should be cleaned before launch"
write_loop_stub "$DP" "mkdir -p \"$DP/plan-review/round-2\"; printf 'fresh\n' >\"$DP/plan-review/round-2/new.txt\"; printf 'LOOP_STATUS=cap-hit\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=2\nREASON=cap-hit\nREVISE_STATUS=ok\nCONVERGENCE_STREAK=1\nCOLLECT_OK_COUNT=1\nCOLLECT_FAILURE_COUNT=0\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=$DP/voting-tally.md\nVOTER_1_PARSE_RATE_STATUS=ok\n'; exit 0"
run_guard "$DP" >/tmp/larch-step3-cap.guardp2.out
driver_out=$(run_driver "$DP")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=cap-hit$' || fail "expected cap-hit passive-summary status"
[[ "$(cat "$DP/review-round-count.txt")" == "2" ]] || fail "second passive-summary entry should persist round 2"
[[ -f "$DP/plan-review/round-2/new.txt" ]] || fail "fresh round-2 artifact missing after second entry"

echo "=== hard path advances round 2 after successful round-1 snapshot ==="
DH="$TMPROOT/hard-round2"
write_common_inputs "$DH" HARD
printf '1\n' >"$DH/review-round-count.txt"
printf '1\n' >"$DH/plan-review-round-cursor.txt"
printf 'round1 snapshot\n' >"$DH/plan-after-round-1.txt"
write_snapshot_stub "$DH"
mkdir -p "$DH/skills/design/scripts"
cat >"$DH/skills/design/scripts/plan-review-loop.sh" <<'STUBEOF'
#!/usr/bin/env bash
set -euo pipefail
round_num=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --round-num) round_num="${2:?}"; shift 2 ;;
        *) shift ;;
    esac
done
STUBEOF
cat >>"$DH/skills/design/scripts/plan-review-loop.sh" <<STUBEOF
printf "%s\n" "\$round_num" >"$DH/round-num-seen.txt"
printf "LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=%s\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nVOTER_1_PARSE_RATE_STATUS=ok\n" "\$round_num"
STUBEOF
chmod +x "$DH/skills/design/scripts/plan-review-loop.sh"
run_guard "$DH" >/tmp/larch-step3-cap.guardh.out
driver_out=$(run_driver "$DH")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=complete$' || fail "hard round-2 path should still complete"
[[ "$(cat "$DH/round-num-seen.txt")" == "2" ]] || fail "hard round-2 path must pass --round-num 2 to plan-review-loop.sh"
[[ "$(cat "$DH/plan-review-round-cursor.txt")" == "2" ]] || fail "hard round-2 path must persist cursor 2 before launch"
grep -Fqx 'write-cursor:2' "$DH/snapshot.log" || fail "hard round-2 path must advance cursor via snapshot helper"

echo "=== tally-error does not consume the pending round ==="
D4="$TMPROOT/tally-error"
write_common_inputs "$D4" HARD
write_snapshot_stub "$D4"
printf '2\n' >"$D4/review-round-count.txt"
write_loop_stub "$D4" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=$D4/voting-tally.md\nVOTER_1_PARSE_RATE_STATUS=ok\n'; exit 2"
run_guard "$D4" >/tmp/larch-step3-cap.guard4.out
driver_out=$(run_driver "$D4")
printf '%s\n' "$driver_out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=tally-error$' || fail "expected tally-error tally status"
[[ "$(cat "$D4/review-round-count.txt")" == "2" ]] || fail "tally-error path must not consume pending round"

echo "=== hard cap blocks the sixth review round ==="
D5="$TMPROOT/hard-cap"
write_common_inputs "$D5" HARD
printf '5\n' >"$D5/review-round-count.txt"
write_loop_stub "$D5" 'exit 97'
run_guard "$D5" >/tmp/larch-step3-cap.guard5.out
grep -Fq 'STEP3_REVIEW_CAP_REACHED=true' "$D5/.step3-review-cap.env" || fail "expected HARD cap reached env"
driver_out=$(run_driver "$D5")
printf '%s\n' "$driver_out" | grep -q '^LOOP_STATUS=cap-reached$' || fail "expected HARD cap-reached loop status"
printf '%s\n' "$driver_out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached$' || fail "expected HARD skipped-cap-reached tally status"
[[ "$(cat "$D5/review-round-count.txt")" == "5" ]] || fail "HARD cap path must leave counter unchanged"

echo "PASS: test-step3-review-cap.sh"
