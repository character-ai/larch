#!/usr/bin/env bash
# Assert every /design readability amendment site references the shared preamble.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

usage() {
    printf '%s\n' "Usage: lint-readability-preamble.sh [--root <repo-or-fixture-root>]" >&2
}

take_value() {
    local flag="$1"
    local value="${2:-}"
    if [ -z "$value" ] || [ "${value#--}" != "$value" ]; then
        printf '%s\n' "lint-readability-preamble.sh: $flag requires a value" >&2
        exit 2
    fi
    printf '%s' "$value"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --root)
            ROOT="$(take_value --root "${2:-}")"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "lint-readability-preamble.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

manifest_tsv="$ROOT/scripts/lint-readability-preamble.tsv"
if [ ! -f "$manifest_tsv" ]; then
    printf '%s\n' "lint-readability-preamble.sh: manifest not found: $manifest_tsv" >&2
    exit 2
fi

# shellcheck disable=SC2016 # literal prompt token pattern, not shell expansion.
external_style_line='Style requirements: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal prompt token pattern, not shell expansion.
plan_review_style_line='Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal Markdown/backtick regex, not shell expansion.
orchestrator_style_re='^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: `skills/design/references/readability-style\.md`\.\*\*$'

validate_expected_count() {
    local path="$1"
    local expected_count="$2"
    case "$expected_count" in
        ''|*[!0-9]*)
            printf '%s\n' "lint-readability-preamble.sh: invalid expected_count in $manifest_tsv for row $path" >&2
            exit 2
            ;;
    esac
}

count_sketch_style_lines() {
    local file="$1"
    awk '
        $0 == "Style requirements: <READABILITY_STYLE>." {
            count++
            next
        }
        $0 ~ /\\nStyle requirements: <READABILITY_STYLE>\."`$/ {
            count++
        }
        END {
            print count + 0
        }
    ' "$file"
}

check_step_placement() {
    local file="$1"
    local rel_path="$2"
    local step_markers="$3"
    local step_id

    IFS=',' read -r -a step_ids <<< "$step_markers"
    for step_id in "${step_ids[@]}"; do
        step_id="${step_id#"${step_id%%[![:space:]]*}"}"
        step_id="${step_id%"${step_id##*[![:space:]]}"}"
        [ -n "$step_id" ] || continue
        awk -v step_id="$step_id" -v rel_path="$rel_path" -v style_re="$orchestrator_style_re" '
BEGIN { in_step = 0; count = 0; found_marker = 0 }
{
    if (match($0, "^<!-- step:" step_id "([[:space:]]|—)")) {
        if (in_step && found_marker && count < 1) {
            printf "%s: step \"%s\": expected >=1 orchestrator-inline readability-style directive in step body, found 0\n", rel_path, step_id > "/dev/stderr"
            exit 1
        }
        in_step = 1
        found_marker = 1
        count = 0
        next
    }
    if (in_step && match($0, "^<!-- step:")) {
        if (count < 1) {
            printf "%s: step \"%s\": expected >=1 orchestrator-inline readability-style directive in step body, found 0\n", rel_path, step_id > "/dev/stderr"
            exit 1
        }
        in_step = 0
        count = 0
    }
    if (in_step && $0 ~ style_re) {
        count++
    }
}
END {
    if (!found_marker) {
        printf "%s: step \"%s\": orchestrator-inline step marker not found\n", rel_path, step_id > "/dev/stderr"
        exit 1
    }
    if (in_step && count < 1) {
        printf "%s: step \"%s\": expected >=1 orchestrator-inline readability-style directive in step body, found 0\n", rel_path, step_id > "/dev/stderr"
        exit 1
    }
}
        ' "$file" || return 1
    done
    return 0
}

missing=0

while IFS= read -r row; do
    path="${row%%$'\t'*}"
    rest="${row#*$'\t'}"
    variant="${rest%%$'\t'*}"
    rest="${rest#*$'\t'}"
    expected_count="${rest%%$'\t'*}"
    rest="${rest#*$'\t'}"
    prompt_kind="${rest%%$'\t'*}"
    step_markers="${rest#*$'\t'}"

    validate_expected_count "$path" "$expected_count"

    file="$ROOT/$path"
    ok=false
    count=0
    count_message_emitted=false

    if [ -f "$file" ]; then
        case "$variant" in
            external-prompt)
                case "${prompt_kind:-standard}" in
                    plan-review)
                        count=$(grep -Fxc "$plan_review_style_line" "$file" || true)
                        ;;
                    sketch)
                        count=$(count_sketch_style_lines "$file")
                        ;;
                    *)
                        count=$(grep -Fxc "$external_style_line" "$file" || true)
                        ;;
                esac
                if [ "$count" = "$expected_count" ]; then
                    ok=true
                else
                    printf '%s\n' "$path: expected $expected_count external-prompt readability-style directives, found ${count:-0}" >&2
                    count_message_emitted=true
                fi
                ;;
            orchestrator-inline)
                count=$(grep -Ec "$orchestrator_style_re" "$file" || true)
                if [ "$count" = "$expected_count" ]; then
                    ok=true
                else
                    printf '%s\n' "$path: expected $expected_count orchestrator-inline readability-style directives, found ${count:-0}" >&2
                    count_message_emitted=true
                fi
                if [ "$ok" = true ] && [ -n "$step_markers" ]; then
                    if ! check_step_placement "$file" "$path" "$step_markers"; then
                        ok=false
                    fi
                fi
                ;;
            *)
                printf '%s\n' "lint-readability-preamble.sh: unknown manifest variant: $variant" >&2
                exit 2
                ;;
        esac
    fi

    if [ "$ok" != true ]; then
        if [ "$count_message_emitted" != true ]; then
            printf '%s\n' "$path: missing $variant readability-style directive" >&2
        fi
        missing=1
    fi
done < <(
    awk -F '\t' 'NF >= 1 && $1 !~ /^#/ && $0 != "" {
        printf "%s\t%s\t%s\t%s\t%s\n", $1, $2, $3, $4, $5
    }' "$manifest_tsv"
)

exit "$missing"
