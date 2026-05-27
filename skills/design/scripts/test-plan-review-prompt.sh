#!/usr/bin/env bash
# Offline regression harness for render-plan-review-prompt.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
RENDERER="$SCRIPT_DIR/render-plan-review-prompt.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-plan-review-prompt-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PLAN_FILE="$TMPROOT/plan.txt"
printf 'Implement reviewer prompt consolidation in skills/design/SKILL.md and scripts/launch-review.sh.\n' > "$PLAN_FILE"
SIMPLE_DT="$TMPROOT/simple-design"
HARD_DT="$TMPROOT/hard-design"
mkdir -p "$SIMPLE_DT" "$HARD_DT"
printf '%s\n' '{"schema_version":2,"design_classification":"SIMPLE","partition_requested":false,"brainstorm_requested":false}' >"$SIMPLE_DT/run-params.json"
printf '%s\n' '{"schema_version":2,"design_classification":"HARD","partition_requested":false,"brainstorm_requested":false}' >"$HARD_DT/run-params.json"

assert_contains() {
    local label="$1"
    local needle="$2"
    local file="$3"
    grep -Fq -- "$needle" "$file" || fail "$label: missing '$needle'"
}

assert_exit_2() {
    local label="$1"
    shift
    local stdout="$TMPROOT/${label}.out"
    local stderr="$TMPROOT/${label}.err"
    local rc
    set +e
    "$@" >"$stdout" 2>"$stderr"
    rc=$?
    set -e
    [[ "$rc" -eq 2 ]] || fail "$label: expected exit 2, got $rc"
    [[ -s "$stderr" ]] || fail "$label: expected stderr diagnostic"
}

assert_count() {
    local label="$1"
    local needle="$2"
    local expected="$3"
    local file="$4"
    local count
    count=$(grep -Fc -- "$needle" "$file" || true)
    [[ "$count" == "$expected" ]] || fail "$label: expected $expected occurrences of '$needle', got $count"
}

archetypes=(arch edge innovation pragmatic requirements)
vendors=(codex cursor)

for archetype in "${archetypes[@]}"; do
    for vendor in "${vendors[@]}"; do
        out="$TMPROOT/${vendor}-${archetype}.txt"
        err="$TMPROOT/${vendor}-${archetype}.err"
        bash "$RENDERER" --archetype "$archetype" --vendor "$vendor" --plan-file "$PLAN_FILE" --design-tmpdir "$HARD_DT" >"$out" 2>"$err" \
            || fail "$vendor/$archetype: renderer exited non-zero: $(cat "$err")"

        assert_contains "$vendor/$archetype focus enum" "code-quality / risk-integration / correctness / architecture / security" "$out"
        assert_contains "$vendor/$archetype sentinel instruction" '{"no_issues_found": true}' "$out"
        assert_contains "$vendor/$archetype plan path" "$PLAN_FILE" "$out"
        assert_contains "$vendor/$archetype plan-vs-current-state guidance" "The plan describes the codebase AFTER this PR lands" "$out"
        # shellcheck disable=SC2016
        assert_contains "$vendor/$archetype heading-format guidance" '`### NEW:` / `### UPDATED:` / `### REWRITTEN:` subsections' "$out"
        assert_contains "$vendor/$archetype read-only" "Do NOT modify files" "$out"

        last_line="$(tail -n 1 "$out")"
        [[ "$last_line" != '{"no_issues_found": true}' ]] \
            || fail "$vendor/$archetype: output ends with only JSON no-findings sentinel"

        assert_contains "$vendor/$archetype TSV header" "schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix" "$out"
        assert_contains "$vendor/$archetype TSV record shape" "1	<scope>	<severity>	<focus_area>	<location>	<what>	<scenario_or_breakage>	<suggested_fix>" "$out"
        assert_contains "$vendor/$archetype file paths wording" "file paths named in the plan" "$out"
        assert_contains "$vendor/$archetype no-findings mutual exclusion" "no TSV records" "$out"
        assert_contains "$vendor/$archetype hard tier emphasis" "Tier emphasis: HARD" "$out"
        assert_count "$vendor/$archetype hard tier emphasis count" "Tier emphasis: HARD" 1 "$out"
    done
done

# Archetype-specific full_role prose check (once per archetype, vendor=codex as the representative)
for _arch_check in "arch:Emphasize maintainability" "edge:boundary conditions" "innovation:Question assumptions" "pragmatic:Minimize scope" "requirements:every stated goal"; do
    _arch="${_arch_check%%:*}"
    _phrase="${_arch_check#*:}"
    _out="$TMPROOT/full-role-${_arch}.txt"
    bash "$RENDERER" --archetype "$_arch" --vendor codex --plan-file "$PLAN_FILE" --design-tmpdir "$HARD_DT" >"$_out"
    assert_contains "$_arch full_role" "$_phrase" "$_out"
done

simple_out="$TMPROOT/simple.txt"
hard_out="$TMPROOT/hard.txt"
bash "$RENDERER" --archetype arch --vendor cursor --plan-file "$PLAN_FILE" --design-tmpdir "$SIMPLE_DT" >"$simple_out"
bash "$RENDERER" --archetype arch --vendor cursor --plan-file "$PLAN_FILE" --design-tmpdir "$HARD_DT" >"$hard_out"
assert_contains "simple emphasis" "Tier emphasis: SIMPLE" "$simple_out"
assert_contains "simple minimum-change lane" "This is a minimum-change review lane." "$simple_out"
assert_contains "simple locked phrase" "Bias your findings toward flagging" "$simple_out"
assert_contains "simple security hardening carve-out" "materially required for correctness, security, or safety hardening" "$simple_out"
assert_contains "simple accept-yes line" "Accept YES only for findings that keep or restore that minimum-change contract." "$simple_out"
assert_count "simple emphasis static count" "Tier emphasis: SIMPLE" 1 "$simple_out"
tail -n +2 "$simple_out" >"$TMPROOT/simple-dynamic-tail.txt"
assert_contains "simple dynamic tail emphasis" "Tier emphasis: SIMPLE" "$TMPROOT/simple-dynamic-tail.txt"
assert_count "simple dynamic tail emphasis count" "Tier emphasis: SIMPLE" 1 "$TMPROOT/simple-dynamic-tail.txt"
assert_contains "hard emphasis" "Tier emphasis: HARD" "$hard_out"
assert_contains "hard locked phrase" "Bias your findings toward **thoroughness**" "$hard_out"
assert_count "hard emphasis static count" "Tier emphasis: HARD" 1 "$hard_out"
tail -n +2 "$hard_out" >"$TMPROOT/hard-dynamic-tail.txt"
assert_contains "hard dynamic tail emphasis" "Tier emphasis: HARD" "$TMPROOT/hard-dynamic-tail.txt"
assert_count "hard dynamic tail emphasis count" "Tier emphasis: HARD" 1 "$TMPROOT/hard-dynamic-tail.txt"

assert_exit_2 invalid-archetype bash "$RENDERER" --archetype bogus --vendor codex --plan-file "$PLAN_FILE" --design-tmpdir "$HARD_DT"
assert_exit_2 invalid-vendor bash "$RENDERER" --archetype arch --vendor claude --plan-file "$PLAN_FILE" --design-tmpdir "$HARD_DT"
assert_exit_2 missing-plan-file bash "$RENDERER" --archetype arch --vendor cursor
assert_exit_2 nonexistent-plan-file bash "$RENDERER" --archetype arch --vendor cursor --plan-file /nonexistent/plan.txt --design-tmpdir "$HARD_DT"

echo "test-plan-review-prompt: ok"
