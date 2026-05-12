#!/usr/bin/env bash
# Offline regression harness for render-plan-review-prompt.sh.

set -euo pipefail

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

archetypes=(arch edge innovation pragmatic requirements)
vendors=(codex cursor)

for archetype in "${archetypes[@]}"; do
    for vendor in "${vendors[@]}"; do
        out="$TMPROOT/${vendor}-${archetype}.txt"
        err="$TMPROOT/${vendor}-${archetype}.err"
        bash "$RENDERER" --archetype "$archetype" --vendor "$vendor" --plan-file "$PLAN_FILE" >"$out" 2>"$err" \
            || fail "$vendor/$archetype: renderer exited non-zero: $(cat "$err")"

        assert_contains "$vendor/$archetype focus enum" "code-quality / risk-integration / correctness / architecture / security" "$out"
        assert_contains "$vendor/$archetype sentinel instruction" "NO_ISSUES_FOUND" "$out"
        assert_contains "$vendor/$archetype plan path" "$PLAN_FILE" "$out"
        assert_contains "$vendor/$archetype read-only" "Do NOT modify files" "$out"

        last_line="$(tail -n 1 "$out")"
        [[ "$last_line" != "NO_ISSUES_FOUND" ]] \
            || fail "$vendor/$archetype: output ends with only NO_ISSUES_FOUND"

        assert_contains "$vendor/$archetype TSV header" "schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix" "$out"
        assert_contains "$vendor/$archetype TSV record shape" "1	<scope>	<severity>	<focus_area>	<location>	<what>	<scenario_or_breakage>	<suggested_fix>" "$out"
        assert_contains "$vendor/$archetype file paths wording" "file paths named in the plan" "$out"
        assert_contains "$vendor/$archetype no-findings mutual exclusion" "do NOT include a TSV block" "$out"
    done
done

# Archetype-specific full_role prose check (once per archetype, vendor=codex as the representative)
for _arch_check in "arch:Emphasize maintainability" "edge:boundary conditions" "innovation:Question assumptions" "pragmatic:Minimize scope" "requirements:every stated goal"; do
    _arch="${_arch_check%%:*}"
    _phrase="${_arch_check#*:}"
    _out="$TMPROOT/full-role-${_arch}.txt"
    bash "$RENDERER" --archetype "$_arch" --vendor codex --plan-file "$PLAN_FILE" >"$_out"
    assert_contains "$_arch full_role" "$_phrase" "$_out"
done

assert_exit_2 invalid-archetype bash "$RENDERER" --archetype bogus --vendor codex --plan-file "$PLAN_FILE"
assert_exit_2 invalid-vendor bash "$RENDERER" --archetype arch --vendor claude --plan-file "$PLAN_FILE"
assert_exit_2 missing-plan-file bash "$RENDERER" --archetype arch --vendor cursor
assert_exit_2 nonexistent-plan-file bash "$RENDERER" --archetype arch --vendor cursor --plan-file /nonexistent/plan.txt

echo "test-plan-review-prompt: ok"
