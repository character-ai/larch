#!/usr/bin/env bash
# Offline regression harness for lint-readability-preamble.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
LINT="$SCRIPT_DIR/lint-readability-preamble.sh"

fail() {
    printf '%s\n' "FAIL: $1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-readability-lint-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

external_paths="
skills/design/references/brainstorm-prompts.md
skills/design/references/sketch-prompts.md
skills/design/references/dialectic-debate.md
"

orchestrator_paths="
skills/design/SKILL.md
skills/design/references/design-outline.md
skills/design/references/brainstorm.md
skills/design/references/sketch-launch.md
skills/design/references/dialectic-execution.md
skills/design/references/approval-gates.md
skills/design/references/discussion-rounds.md
"

# shellcheck disable=SC2016 # literal prompt token fixture, not shell expansion.
external_style_line='Style requirements: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal prompt token fixture, not shell expansion.
plan_review_style_line='Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal Markdown/backtick fixture, not shell expansion.
orchestrator_style_line='**MANDATORY — READ ENTIRE FILE before composing fixture text: `skills/design/references/readability-style.md`.**'

write_file() {
    local root="$1"
    local rel="$2"
    local body="$3"
    mkdir -p "$(dirname "$root/$rel")"
    printf '%s\n' "$body" > "$root/$rel"
}

repeat_line() {
    local line="$1"
    local count="$2"
    local i

    for ((i = 0; i < count; i++)); do
        printf '%s\n' "$line"
    done
}

populate_fixture() {
    local root="$1"
    local missing_external="${2:-}"
    local missing_orchestrator="${3:-}"
    local partial_orchestrator="${4:-}"
    local partial_count="${5:-0}"
    local expected_count
    local rel

    for rel in $external_paths; do
        if [ "$rel" = "$missing_external" ]; then
            write_file "$root" "$rel" "External prompt without the token."
        elif [ "$rel" = "skills/design/references/brainstorm-prompts.md" ]; then
            write_file "$root" "$rel" "$(repeat_line "$external_style_line" 3)"
        elif [ "$rel" = "skills/design/references/sketch-prompts.md" ]; then
            write_file "$root" "$rel" "$(repeat_line "$external_style_line" 4)"
        else
            write_file "$root" "$rel" "$(repeat_line "$external_style_line" 2)"
        fi
    done

    write_file "$root" "skills/design/references/plan-review.md" "$plan_review_style_line"

    for rel in $orchestrator_paths; do
        if [ "$rel" = "$missing_orchestrator" ]; then
            write_file "$root" "$rel" "Inline composition without the directive."
        elif [ "$rel" = "$partial_orchestrator" ]; then
            write_file "$root" "$rel" "$(repeat_line "$orchestrator_style_line" "$partial_count")"
        else
            expected_count=1
            if [ "$rel" = "skills/design/SKILL.md" ]; then
                expected_count=4
            fi
            write_file "$root" "$rel" "$(repeat_line "$orchestrator_style_line" "$expected_count")"
        fi
    done
}

assert_lint_ok() {
    local label="$1"
    local root="$2"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    bash "$LINT" --root "$root" >"$out" 2>"$err" || fail "$label: expected lint success: $(cat "$err")"
    [ ! -s "$err" ] || fail "$label: expected empty stderr"
}

assert_lint_fails_for() {
    local label="$1"
    local root="$2"
    local expected="$3"
    local unexpected="${4:-}"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    local rc

    set +e
    bash "$LINT" --root "$root" >"$out" 2>"$err"
    rc=$?
    set -e

    [ "$rc" -ne 0 ] || fail "$label: expected lint failure"
    grep -Fq -- "$expected" "$err" || fail "$label: stderr missing '$expected': $(cat "$err")"
    if [ -n "$unexpected" ]; then
        ! grep -Fq -- "$unexpected" "$err" || fail "$label: stderr included '$unexpected': $(cat "$err")"
    fi
}

compliant="$TMPROOT/compliant"
external_bad="$TMPROOT/external-bad"
orchestrator_bad="$TMPROOT/orchestrator-bad"
orchestrator_partial="$TMPROOT/orchestrator-partial"
orchestrator_missing_file="$TMPROOT/orchestrator-missing-file"

populate_fixture "$compliant"
populate_fixture "$external_bad" "skills/design/references/brainstorm-prompts.md"
populate_fixture "$orchestrator_bad" "" "skills/design/SKILL.md"
populate_fixture "$orchestrator_partial" "" "" "skills/design/SKILL.md" 3
populate_fixture "$orchestrator_missing_file"
rm -f "$orchestrator_missing_file/skills/design/SKILL.md"

write_file "$external_bad" "skills/design/references/brainstorm-prompts.md" "$(repeat_line "$external_style_line" 2)"

assert_lint_ok compliant "$compliant"
assert_lint_fails_for external-bad "$external_bad" "skills/design/references/brainstorm-prompts.md: expected 3 external-prompt readability-style directives, found 2" "skills/design/references/brainstorm-prompts.md: missing external-prompt readability-style directive"
assert_lint_fails_for orchestrator-bad "$orchestrator_bad" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 0" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive"
assert_lint_fails_for orchestrator-partial "$orchestrator_partial" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 3" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive"
assert_lint_fails_for orchestrator-missing-file "$orchestrator_missing_file" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives"

printf '%s\n' "test-lint-readability-preamble: ok"
