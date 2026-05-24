#!/usr/bin/env bash
# compose-plan-goals-test.sh — compose the implement plan-goals-test log batch.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    while IFS= read -r line; do larch_err "$line"; done <<'USAGE'
Usage:
  compose-plan-goals-test.sh --plan-file PATH [--goal-text TEXT]
USAGE
}

fail() {
    larch_err "ERROR=$1"
    exit 2
}

PLAN_FILE=""
GOAL_TEXT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --plan-file)
            PLAN_FILE="${2:?--plan-file requires a value}"
            shift 2
            ;;
        --goal-text)
            GOAL_TEXT="${2:?--goal-text requires a value}"
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

[ -n "$PLAN_FILE" ] || {
    usage
    fail "--plan-file is required"
}
[ -f "$PLAN_FILE" ] || fail "plan file not found: $PLAN_FILE"
[ -s "$PLAN_FILE" ] || fail "plan file is empty: $PLAN_FILE"

plan_bytes="$(wc -c < "$PLAN_FILE" | tr -d ' ')"
[ "$plan_bytes" -ge 64 ] || fail "plan file is too short: $PLAN_FILE ($plan_bytes bytes)"

# Reject if first non-blank line matches a pointer-only placeholder.
first_nonblank="$(awk 'NF { gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0); print tolower($0); exit }' "$PLAN_FILE")"
if printf '%s\n' "$first_nonblank" | grep -Eiq "^(see plan\.txt|see attached|see linked|tbd|todo)\.?$"; then
    fail "plan file is a pointer-only placeholder: $PLAN_FILE"
fi

# Extract test plan section (any level-1/2/3 recognized test/verification heading).
test_plan="$(
    awk '
        found {
            if (/^#{1,3}[[:space:]]/) exit
            print
            next
        }
        /^#{1,3}[[:space:]]+([Tt]est[[:space:]][Pp]lan|[Tt]ests|[Tt]esting|[Vv]erification|[Tt]est[[:space:]][Ss]trategy|[Vv]erification[[:space:]][Ss]trategy)[[:space:]]*$/ { found = 1 }
    ' "$PLAN_FILE"
)"

if [ -z "$test_plan" ]; then
    test_plan="(no test plan section in plan-file)"
fi

output=$(
    printf '## Goal\n'
    printf '%s\n\n' "$GOAL_TEXT"
    printf '## Implementation Plan\n'
    # Stop before any test plan section to avoid duplicating content under ## Test plan below.
    # Strip the first source "Implementation Plan" heading (wrapper supplies it), then drop a
    # immediately-following alternate "## Plan" heading and any intervening blank lines so the
    # payload does not show back-to-back plan section titles.
    awk '
        /^#{1,3}[[:space:]]+[Ii]mplementation[[:space:]][Pp]lan[[:space:]]*$/ && !seen_impl++ {
            pending_alt = 1
            next
        }
        pending_alt {
            if (/^[[:space:]]*$/) next
            if (/^#{1,3}[[:space:]]+[Pp]lan[[:space:]]*$/) {
                pending_alt = 0
                next
            }
            pending_alt = 0
        }
        /^#{1,3}[[:space:]]+([Tt]est[[:space:]][Pp]lan|[Tt]ests|[Tt]esting|[Vv]erification|[Tt]est[[:space:]][Ss]trategy|[Vv]erification[[:space:]][Ss]trategy)[[:space:]]*$/ { exit }
        { print }
    ' "$PLAN_FILE"
    printf '\n## Test plan\n'
    printf '%s\n' "$test_plan"
)
emit "$output"
