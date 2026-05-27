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

manifest_rows=(
    "skills/design/SKILL.md:orchestrator-inline:4"
    "skills/design/references/design-outline.md:orchestrator-inline:1"
    "skills/design/references/brainstorm.md:orchestrator-inline:1"
    "skills/design/references/sketch-launch.md:orchestrator-inline:1"
    "skills/design/references/dialectic-execution.md:orchestrator-inline:1"
    "skills/design/references/approval-gates.md:orchestrator-inline:1"
    "skills/design/references/discussion-rounds.md:orchestrator-inline:1"
    "skills/design/references/brainstorm-prompts.md:external-prompt:3:standard"
    "skills/design/references/sketch-prompts.md:external-prompt:4:sketch"
    "skills/design/references/dialectic-debate.md:external-prompt:2:standard"
    "skills/design/references/plan-review.md:external-prompt:1:plan-review"
)

# shellcheck disable=SC2016 # literal prompt token pattern, not shell expansion.
external_style_line='Style requirements: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal prompt token pattern, not shell expansion.
plan_review_style_line='Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal Markdown/backtick regex, not shell expansion.
orchestrator_style_re='^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: `skills/design/references/readability-style\.md`\.\*\*$'

missing=0

for row in "${manifest_rows[@]}"; do
    IFS=':' read -r path variant expected_count prompt_kind <<EOF
$row
EOF
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
                        count=$(grep -Foc '<READABILITY_STYLE>' "$file" || true)
                        ;;
                    *)
                        count=$(grep -Fxc "$external_style_line" "$file" || true)
                        ;;
                esac
                if [ "$count" = "${expected_count:-1}" ]; then
                    ok=true
                fi
                ;;
            orchestrator-inline)
                count=$(grep -Ec "$orchestrator_style_re" "$file" || true)
                if [ "$count" = "${expected_count:-1}" ]; then
                    ok=true
                else
                    printf '%s\n' "$path: expected ${expected_count:-1} orchestrator-inline readability-style directives, found ${count:-0}" >&2
                    count_message_emitted=true
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
done

exit "$missing"
