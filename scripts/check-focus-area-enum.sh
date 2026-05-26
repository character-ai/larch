#!/usr/bin/env bash
# Assert canonical reviewer focus-area enum surfaces include security.

set -euo pipefail

BACKTICKED_FILES=(
    skills/shared/reviewer-templates.md
    agents/code-reviewer.md
    agents/reviewer-structure.md
    agents/reviewer-correctness.md
    agents/reviewer-testing.md
    agents/reviewer-security.md
    agents/reviewer-edge-cases.md
    agents/reviewer-plan-fidelity.md
    agents/reviewer-code-robustness.md
    skills/shared/focus-area-prompt.md
    docs/review-agents.md
)

UNQUOTED_FILES=(
    skills/review/SKILL.md
    skills/review/scripts/dispatch-panel.sh
    skills/design/SKILL.md
)

exit_code=0
hits_file=$(mktemp "${TMPDIR:-/tmp}/focus-area-enum.XXXXXX")
trap 'rm -f "$hits_file"' EXIT

for f in "${BACKTICKED_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "::error file=$f::expected file is missing"
        exit_code=1
        continue
    fi
    # shellcheck disable=SC2016 # Literal backticks are part of the markdown pattern.
    if grep -n '`code-quality`.*`risk-integration`.*`correctness`.*`architecture`' "$f" >"$hits_file" 2>/dev/null; then
        while IFS= read -r hit || [[ -n "$hit" ]]; do
            line_no="${hit%%:*}"
            line_text="${hit#*:}"
            if ! printf '%s\n' "$line_text" | grep -q 'security'; then
                echo "::error file=$f,line=$line_no::backticked focus-area enumeration does not include 'security': $line_text"
                exit_code=1
            fi
        done <"$hits_file"
    else
        echo "::error file=$f::no backticked focus-area enumeration found"
        exit_code=1
    fi
done

for f in "${UNQUOTED_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "::error file=$f::expected file is missing"
        exit_code=1
        continue
    fi
    if grep -n 'code-quality / risk-integration / correctness / architecture' "$f" >"$hits_file" 2>/dev/null; then
        while IFS= read -r hit || [[ -n "$hit" ]]; do
            line_no="${hit%%:*}"
            line_text="${hit#*:}"
            if ! printf '%s\n' "$line_text" | grep -q 'security'; then
                echo "::error file=$f,line=$line_no::unquoted focus-area enumeration does not include 'security': $line_text"
                exit_code=1
            fi
        done <"$hits_file"
    else
        echo "::error file=$f::no unquoted focus-area enumeration found"
        exit_code=1
    fi
done

exit "$exit_code"
