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
{"schema_version":2,"design_classification":"$classification","partition_requested":false,"brainstorm_requested":false}
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

echo "=== tally-error does not consume the pending round ==="
D4="$TMPROOT/tally-error"
write_common_inputs "$D4" HARD
printf '2\n' >"$D4/review-round-count.txt"
write_loop_stub "$D4" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=$D4/voting-tally.md\nVOTER_1_PARSE_RATE_STATUS=ok\n'; exit 2"
run_guard "$D4" >/tmp/larch-step3-cap.guard4.out
driver_out=$(run_driver "$D4")
printf '%s\n' "$driver_out" | grep -q '^TALLY_PLAN_REVIEW_STATUS=tally-error$' || fail "expected tally-error tally status"
[[ "$(cat "$D4/review-round-count.txt")" == "2" ]] || fail "tally-error path must not consume pending round"

echo "PASS: test-step3-review-cap.sh"
