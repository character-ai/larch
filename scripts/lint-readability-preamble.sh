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
    "skills/design/SKILL.md:orchestrator-inline"
    "skills/design/references/design-outline.md:orchestrator-inline"
    "skills/design/references/brainstorm.md:orchestrator-inline"
    "skills/design/references/sketch-launch.md:orchestrator-inline"
    "skills/design/references/dialectic-execution.md:orchestrator-inline"
    "skills/design/references/approval-gates.md:orchestrator-inline"
    "skills/design/references/discussion-rounds.md:orchestrator-inline"
    "skills/design/references/brainstorm-prompts.md:external-prompt"
    "skills/design/references/sketch-prompts.md:external-prompt"
    "skills/design/references/dialectic-debate.md:external-prompt"
    "skills/design/references/plan-review.md:external-prompt"
)

# shellcheck disable=SC2016 # literal prompt token pattern, not shell expansion.
external_style_line='Style requirements: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal prompt token pattern, not shell expansion.
plan_review_style_line='Style requirements for finding text and OOS Descriptions: `<READABILITY_STYLE>`.'
# shellcheck disable=SC2016 # literal Markdown/backtick regex, not shell expansion.
orchestrator_style_re='^\*\*MANDATORY — READ ENTIRE FILE before [^:]+: `skills/design/references/readability-style\.md`\.\*\*$'

missing=0

for row in "${manifest_rows[@]}"; do
    path="${row%:*}"
    variant="${row##*:}"
    file="$ROOT/$path"
    ok=false

    if [ -f "$file" ]; then
        case "$variant" in
            external-prompt)
                if grep -Fxq "$external_style_line" "$file" \
                    || grep -Fxq "$plan_review_style_line" "$file"; then
                    ok=true
                fi
                ;;
            orchestrator-inline)
                if grep -Eq "$orchestrator_style_re" "$file"; then
                    ok=true
                fi
                ;;
            *)
                printf '%s\n' "lint-readability-preamble.sh: unknown manifest variant: $variant" >&2
                exit 2
                ;;
        esac
    fi

    if [ "$ok" != true ]; then
        printf '%s\n' "$path: missing $variant readability-style directive" >&2
        missing=1
    fi
done

exit "$missing"
