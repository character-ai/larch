#!/usr/bin/env bash
# Offline regression harness for lint-readability-preamble.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
LINT="$SCRIPT_DIR/lint-readability-preamble.sh"
MANIFEST_TSV="$SCRIPT_DIR/lint-readability-preamble.tsv"

fail() {
    printf '%s\n' "FAIL: $1" >&2
    exit 1
}

TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-readability-lint-test.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

# shellcheck disable=SC2016 # literal prompt token fixture, not shell expansion.
external_style_line='Style requirements: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal prompt token fixture, not shell expansion.
plan_review_style_line='Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal prompt token fixture, not shell expansion.
sketch_style_line='Style requirements: <READABILITY_STYLE>.'
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

validate_expected_count() {
    local manifest="$1"
    local path="$2"
    local expected_count="$3"
    case "$expected_count" in
        ''|*[!0-9]*)
            printf '%s\n' "test-lint-readability-preamble.sh: invalid expected_count in $manifest for row $path" >&2
            exit 2
            ;;
    esac
}

read_manifest_rows() {
    local tsv="$1"
    awk -F '\t' 'NF >= 1 && $1 !~ /^#/ && $0 != "" {
        printf "%s\t%s\t%s\t%s\t%s\n", $1, $2, $3, $4, $5
    }' "$tsv"
}

stage_manifest() {
    local root="$1"
    local src="${2:-$MANIFEST_TSV}"
    mkdir -p "$root/scripts"
    cp "$src" "$root/scripts/lint-readability-preamble.tsv"
}

write_skill_md_with_steps() {
    local root="$1"
    local count_per_step="$2"
    local body=""
    local step
    local i

    for step in 2b 3b 4 5; do
        body="${body}<!-- step:${step} — fixture -->
"
        for ((i = 0; i < count_per_step; i++)); do
            body="${body}${orchestrator_style_line}
"
        done
    done
    write_file "$root" "skills/design/SKILL.md" "$body"
}

populate_fixture() {
    local root="$1"
    local manifest_src="${MANIFEST_TSV}"
    local missing_external="${2:-}"
    local missing_orchestrator="${3:-}"
    local partial_orchestrator="${4:-}"
    local partial_count="${5:-0}"
    local row path variant expected_count prompt_kind step_markers
    local rel body

    stage_manifest "$root" "$manifest_src"

    while IFS= read -r row; do
        path="${row%%$'\t'*}"
        rest="${row#*$'\t'}"
        variant="${rest%%$'\t'*}"
        rest="${rest#*$'\t'}"
        expected_count="${rest%%$'\t'*}"
        rest="${rest#*$'\t'}"
        prompt_kind="${rest%%$'\t'*}"
        step_markers="${rest#*$'\t'}"
        validate_expected_count "$manifest_src" "$path" "$expected_count"

        rel="$path"
        if [ "$variant" = "external-prompt" ]; then
            if [ "$rel" = "$missing_external" ]; then
                write_file "$root" "$rel" "External prompt without the token."
                continue
            fi
            case "${prompt_kind:-standard}" in
                plan-review)
                    write_file "$root" "$rel" "$plan_review_style_line"
                    ;;
                sketch)
                    write_file "$root" "$rel" "$(repeat_line "$sketch_style_line" "$expected_count")"
                    ;;
                *)
                    write_file "$root" "$rel" "$(repeat_line "$external_style_line" "$expected_count")"
                    ;;
            esac
            continue
        fi

        if [ "$variant" = "orchestrator-inline" ]; then
            if [ "$rel" = "$missing_orchestrator" ]; then
                write_file "$root" "$rel" "Inline composition without the directive."
                continue
            fi
            if [ "$rel" = "$partial_orchestrator" ]; then
                if [ "$rel" = "skills/design/SKILL.md" ] && [ -n "$step_markers" ]; then
                    write_skill_md_with_steps "$root" "$partial_count"
                else
                    write_file "$root" "$rel" "$(repeat_line "$orchestrator_style_line" "$partial_count")"
                fi
                continue
            fi
            if [ "$rel" = "skills/design/SKILL.md" ] && [ -n "$step_markers" ]; then
                write_skill_md_with_steps "$root" 1
                continue
            fi
            write_file "$root" "$rel" "$(repeat_line "$orchestrator_style_line" "$expected_count")"
        fi
    done < <(read_manifest_rows "$manifest_src")
}

assert_lint_ok() {
    local label="$1"
    local root="$2"
    local out="$TMPROOT/${label}.out"
    local err="$TMPROOT/${label}.err"
    bash "$LINT" --root "$root" >"$out" 2>"$err" || fail "$label: expected lint success: $(cat "$err")"
    [ ! -s "$err" ] || fail "$label: expected empty stderr -- got: $(cat "$err")"
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

assert_lint_exit_eq() {
    local label="$1"
    local root="$2"
    local want="$3"
    local err="$TMPROOT/${label}.err"
    local rc

    set +e
    bash "$LINT" --root "$root" >"$TMPROOT/${label}.out" 2>"$err"
    rc=$?
    set -e
    [ "$rc" -eq "$want" ] || fail "$label: expected exit $want, got $rc: $(cat "$err")"
}

compliant="$TMPROOT/compliant"
external_bad="$TMPROOT/external-bad"
orchestrator_bad="$TMPROOT/orchestrator-bad"
orchestrator_partial="$TMPROOT/orchestrator-partial"
orchestrator_missing_file="$TMPROOT/orchestrator-missing-file"
sketch_bare="$TMPROOT/sketch-bare-token-rejected"
sketch_escaped="$TMPROOT/sketch-escaped"
placement_missing="$TMPROOT/placement-missing-step"
placement_ok="$TMPROOT/placement-correct"
b6_extended="$TMPROOT/b6-extended"
b6_negative="$TMPROOT/b6-negative"
sketch_substring="$TMPROOT/sketch-substring"

populate_fixture "$compliant"
populate_fixture "$external_bad" "skills/design/references/brainstorm-prompts.md"
populate_fixture "$orchestrator_bad" "" "skills/design/SKILL.md"
populate_fixture "$orchestrator_partial" "" "" "skills/design/SKILL.md" 0
populate_fixture "$orchestrator_missing_file"
rm -f "$orchestrator_missing_file/skills/design/SKILL.md"

write_file "$external_bad" "skills/design/references/brainstorm-prompts.md" "$(repeat_line "$external_style_line" 2)"

# orchestrator-partial: three directives all in step 2b (file count 3/4, placement ok per step)
{
    printf '%s\n' '<!-- step:2b — fixture -->'
    repeat_line "$orchestrator_style_line" 3
    printf '%s\n' '<!-- step:3b — fixture -->' '<!-- step:4 — fixture -->' '<!-- step:5 — fixture -->'
} > "$orchestrator_partial/skills/design/SKILL.md"

populate_fixture "$sketch_bare"
write_file "$sketch_bare" "skills/design/references/sketch-prompts.md" "$(repeat_line '<READABILITY_STYLE>' 4)"

populate_fixture "$sketch_escaped"
write_file "$sketch_escaped" "skills/design/references/sketch-prompts.md" "$(repeat_line '"Prompt body.\nStyle requirements: <READABILITY_STYLE>."`' 4)"

populate_fixture "$placement_missing"
{
    printf '%s\n' "$orchestrator_style_line"
    printf '%s\n' '<!-- step:2b — fixture -->' "$orchestrator_style_line"
    printf '%s\n' '<!-- step:3b — fixture -->' "$orchestrator_style_line"
    printf '%s\n' '<!-- step:4 — fixture -->' 'step four body without readability directive'
    printf '%s\n' '<!-- step:5 — fixture -->' "$orchestrator_style_line"
} > "$placement_missing/skills/design/SKILL.md"

populate_fixture "$placement_ok"
write_skill_md_with_steps "$placement_ok" 1

populate_fixture "$b6_extended"
extra_tsv="$TMPROOT/extra-manifest.tsv"
cp "$MANIFEST_TSV" "$extra_tsv"
printf '%s\n' 'skills/design/references/extra-fixture.md	external-prompt	1	standard	' >> "$extra_tsv"
stage_manifest "$b6_extended" "$extra_tsv"
write_file "$b6_extended" "skills/design/references/extra-fixture.md" "$external_style_line"

populate_fixture "$b6_negative"
stage_manifest "$b6_negative" "$extra_tsv"
# Deliberately omit skills/design/references/extra-fixture.md despite the extra TSV row.

populate_fixture "$sketch_substring"
write_file "$sketch_substring" "skills/design/references/sketch-prompts.md" "$(repeat_line "Prefix Style requirements: <READABILITY_STYLE>. suffix" 4)"

malformed_tsv_file="$TMPROOT/bad-manifest.tsv"
malformed_tsv_root="$TMPROOT/malformed-tsv-root"
cp "$MANIFEST_TSV" "$malformed_tsv_file"
printf '%s\n' 'skills/design/references/broken.md	external-prompt		standard	' >> "$malformed_tsv_file"
populate_fixture "$malformed_tsv_root"
stage_manifest "$malformed_tsv_root" "$malformed_tsv_file"

assert_lint_ok compliant "$compliant"
assert_lint_fails_for external-bad "$external_bad" "skills/design/references/brainstorm-prompts.md: expected 3 external-prompt readability-style directives, found 2" "skills/design/references/brainstorm-prompts.md: missing external-prompt readability-style directive"
assert_lint_fails_for orchestrator-bad "$orchestrator_bad" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 0" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive"
assert_lint_fails_for orchestrator-partial "$orchestrator_partial" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives, found 3" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive"
assert_lint_fails_for orchestrator-missing-file "$orchestrator_missing_file" "skills/design/SKILL.md: missing orchestrator-inline readability-style directive" "skills/design/SKILL.md: expected 4 orchestrator-inline readability-style directives"
assert_lint_fails_for sketch-bare-token-rejected "$sketch_bare" "skills/design/references/sketch-prompts.md: expected 4 external-prompt readability-style directives, found 0"
assert_lint_ok sketch-escaped "$sketch_escaped"
assert_lint_fails_for sketch-substring "$sketch_substring" "skills/design/references/sketch-prompts.md: expected 4 external-prompt readability-style directives, found 0"
assert_lint_fails_for placement-missing-step "$placement_missing" 'skills/design/SKILL.md: step "4": expected >=1 orchestrator-inline readability-style directive in step body, found 0'
assert_lint_ok placement-correct "$placement_ok"

# B6: row-count parity — harness reads same awk filter as lint
manifest_rows=0
while IFS= read -r _row; do
    manifest_rows=$((manifest_rows + 1))
done < <(read_manifest_rows "$MANIFEST_TSV")
[ "$manifest_rows" -eq 11 ] || fail "expected 11 manifest rows from repo TSV, got $manifest_rows"
assert_lint_ok b6-extended "$b6_extended"
assert_lint_fails_for b6-negative "$b6_negative" "skills/design/references/extra-fixture.md: missing external-prompt readability-style directive"
assert_lint_exit_eq malformed-tsv "$malformed_tsv_root" 2

printf '%s\n' "test-lint-readability-preamble: ok"
