#!/usr/bin/env bash
# compose-pr-summary.sh — emit 1-3 Markdown summary bullets for the PR body.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage:
  compose-pr-summary.sh --plan-goals-file PATH
USAGE
}

fail() {
    larch_err "ERROR=$1"
    exit 2
}

PLAN_GOALS_FILE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --plan-goals-file)
            PLAN_GOALS_FILE="${2:?--plan-goals-file requires a value}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[ -n "$PLAN_GOALS_FILE" ] || { usage; fail "--plan-goals-file is required"; }
if ! [ -f "$PLAN_GOALS_FILE" ] || ! [ -s "$PLAN_GOALS_FILE" ]; then
    fail "plan-goals file missing or empty: $PLAN_GOALS_FILE"
fi

# Bullet 1: first non-blank line of the ## Goal section (stop at next heading).
goal_line=$(awk '/^## Goal/{found=1; next} found && /^#/{exit} found && NF{print; exit}' "$PLAN_GOALS_FILE")
[ -n "$goal_line" ] || fail "no Goal line found in $PLAN_GOALS_FILE"

summary=$(printf -- '- %s\n' "$goal_line")

# Derive changed-file list against merge-base.
merge_base=$(git merge-base HEAD origin/main 2>/dev/null) || merge_base=""
changed_files=""
if [ -n "$merge_base" ]; then
    changed_files=$(git diff --name-only "$merge_base..HEAD" 2>/dev/null) || changed_files=""
fi

# Bullet 2: test files changed.
if [ -n "$changed_files" ]; then
    test_count=$(printf '%s\n' "$changed_files" | grep -cE '(^|/)test-[^/]+\.sh$' || true)
    if [ "${test_count:-0}" -gt 0 ]; then
        summary="$summary"$'\n'"$(printf -- '- Added or updated %s test file(s).' "$test_count")"
    fi
fi

# Bullet 3: cross-cutting changes (>2 distinct top-level dirs).
if [ -n "$changed_files" ]; then
    dir_count=$(printf '%s\n' "$changed_files" | awk -F/ 'NF>1{print $1} NF==1{print "."}' | sort -u | grep -c '.' || true)
    if [ "${dir_count:-0}" -gt 2 ]; then
        cross_dirs=$(printf '%s\n' "$changed_files" | awk -F/ 'NF>1{print $1} NF==1{print "."}' | sort -u | tr '\n' ',' | sed 's/,$//')
        summary="$summary"$'\n'"$(printf -- '- Cross-cutting changes across: %s.' "$cross_dirs")"
    fi
fi

emit "$summary"
