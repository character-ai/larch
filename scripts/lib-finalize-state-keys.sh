# shellcheck shell=bash
# shellcheck disable=SC2317
# Sourced-only finalize-state key library. Bash 3.2-compatible.
if [ "${LARCH_LIB_FINALIZE_STATE_KEYS_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_FINALIZE_STATE_KEYS_LOADED=1

# shellcheck disable=SC2034
LARCH_FINALIZE_STATE_KEYS=(
    BRANCH_NAME
    PR_NUMBER
    PR_TITLE
    PR_URL
    ISSUE_NUMBER
    REPO
    DRAFT
    MERGE
    DEFERRED
    REPO_UNAVAILABLE
    PR_CLOSED
    DESIGN_ONLY_DONE
    BAIL_NEEDS_USER_INPUT
    STALL_TRACKING
    STALL_STEP
    DONE_RENAME_APPLIED
    RUN_ID
    EXPECTED_SESSION_ID
    EXPECTED_TMPDIR_BASENAME_PREFIX
    NO_LOGS_COMMIT
)

# shellcheck disable=SC2034
LARCH_FINALIZE_STATE_DEFAULT_KEYS=(DESIGN_ONLY_DONE)
# shellcheck disable=SC2034
LARCH_FINALIZE_STATE_DEFAULT_VALUES=(false)

larch_finalize_state_default() {
    local key=$1 index
    index=0
    while [ "$index" -lt "${#LARCH_FINALIZE_STATE_DEFAULT_KEYS[@]}" ]; do
        if [ "${LARCH_FINALIZE_STATE_DEFAULT_KEYS[$index]}" = "$key" ]; then
            printf '%s\n' "${LARCH_FINALIZE_STATE_DEFAULT_VALUES[$index]}"
            return 0
        fi
        index=$((index + 1))
    done
    printf '\n'
}
