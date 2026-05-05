#!/usr/bin/env bash
# session-entry-gate.sh — Shared clean-main entry gate policy.

set -euo pipefail

fail() {
    printf 'GATE_ERROR=%s\n' "$1" >&2
    exit 4
}

require_value() {
    local flag="$1"
    local argc="$2"
    local value="${3-}"
    if (( argc < 2 )); then
        fail "missing value for $flag"
    fi
    if [[ "$value" == --* ]]; then
        fail "missing value for $flag"
    fi
}

valid_bool() {
    [[ "$1" == "true" || "$1" == "false" ]]
}

MODE=""
CURRENT_BRANCH=""
IS_MAIN=""
IS_USER_BRANCH=""
USER_PREFIX=""
BRANCH_INFO_SUPPLIED=""

MODE_SUPPLIED=false
CURRENT_BRANCH_SUPPLIED=false
IS_MAIN_SUPPLIED=false
IS_USER_BRANCH_SUPPLIED=false
USER_PREFIX_SUPPLIED=false
BRANCH_INFO_SUPPLIED_FLAG=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            require_value "$1" "$#" "${2-}"
            MODE="$2"
            MODE_SUPPLIED=true
            shift 2
            ;;
        --current-branch)
            require_value "$1" "$#" "${2-}"
            # shellcheck disable=SC2034 # audit-only echo from create-branch.sh --check; see sibling contract.
            CURRENT_BRANCH="$2"
            CURRENT_BRANCH_SUPPLIED=true
            shift 2
            ;;
        --is-main)
            require_value "$1" "$#" "${2-}"
            IS_MAIN="$2"
            IS_MAIN_SUPPLIED=true
            shift 2
            ;;
        --is-user-branch)
            require_value "$1" "$#" "${2-}"
            IS_USER_BRANCH="$2"
            IS_USER_BRANCH_SUPPLIED=true
            shift 2
            ;;
        --user-prefix)
            require_value "$1" "$#" "${2-}"
            USER_PREFIX="$2"
            USER_PREFIX_SUPPLIED=true
            shift 2
            ;;
        --branch-info-supplied)
            require_value "$1" "$#" "${2-}"
            BRANCH_INFO_SUPPLIED="$2"
            BRANCH_INFO_SUPPLIED_FLAG=true
            shift 2
            ;;
        --*)
            fail "unknown flag: $1"
            ;;
        *)
            fail "unknown argument: $1"
            ;;
    esac
done

[[ "$MODE_SUPPLIED" == "true" ]] || fail "missing required flag --mode"
[[ "$CURRENT_BRANCH_SUPPLIED" == "true" ]] || fail "missing required flag --current-branch"
[[ "$USER_PREFIX_SUPPLIED" == "true" ]] || fail "missing required flag --user-prefix"
[[ "$IS_MAIN_SUPPLIED" == "true" ]] || fail "missing required flag --is-main"
[[ "$IS_USER_BRANCH_SUPPLIED" == "true" ]] || fail "missing required flag --is-user-branch"

[[ "$MODE" == "implement" || "$MODE" == "design" ]] || fail "invalid mode: $MODE"
[[ -n "$USER_PREFIX" ]] || fail "--user-prefix must be non-empty"
valid_bool "$IS_MAIN" || fail "invalid value for --is-main: $IS_MAIN"
valid_bool "$IS_USER_BRANCH" || fail "invalid value for --is-user-branch: $IS_USER_BRANCH"

if [[ "$MODE" == "implement" && "$BRANCH_INFO_SUPPLIED_FLAG" == "true" ]]; then
    fail "--branch-info-supplied not allowed for mode=implement"
fi

if [[ "$BRANCH_INFO_SUPPLIED_FLAG" == "true" ]]; then
    valid_bool "$BRANCH_INFO_SUPPLIED" || fail "invalid value for --branch-info-supplied: $BRANCH_INFO_SUPPLIED"
else
    BRANCH_INFO_SUPPLIED=false
fi

ENTRY_GATE="strict"
SKIP_BRANCH_CHECK="false"

if [[ "$MODE" == "design" && "$BRANCH_INFO_SUPPLIED" == "true" ]]; then
    ENTRY_GATE="continue"
    SKIP_BRANCH_CHECK="true"
elif [[ "$IS_USER_BRANCH" == "true" ]]; then
    ENTRY_GATE="continue"
    SKIP_BRANCH_CHECK="true"
fi

printf 'ENTRY_GATE=%s\n' "$ENTRY_GATE"
printf 'SKIP_BRANCH_CHECK=%s\n' "$SKIP_BRANCH_CHECK"
