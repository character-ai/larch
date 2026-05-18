#!/usr/bin/env bash
# persist-post-plan-keys.sh — Persist PLAN_FILE, FEATURE_FILE, and POST_PLAN_WORKFLOW_PATH
# to $IMPLEMENT_TMPDIR/session-env.sh, then verify the write.
#
# Replaces the inline grep-v / append / mv shell snippets that the /implement
# orchestrator used to emit at the Step 1 post-plan router. The orchestrator-side
# pattern was load-bearing but failed silently when any of the three writes was
# skipped or the snippet was elided — leaving session-env.sh with a stable but
# half-baked content that Step 5's launchers (run-step1-plan-log.sh /
# run-step5-review.sh) only flagged minutes later as "PLAN_FILE missing from
# session-env" (see issue #2326).
#
# Usage:
#   persist-post-plan-keys.sh --implement-tmpdir PATH \
#                              --plan-file PATH \
#                              --feature-file PATH \
#                              --workflow-path SIMPLE|HARD
#
# Behavior:
#   - Validates inputs (paths exist, workflow-path is SIMPLE or HARD).
#   - Filters anchored ^PLAN_FILE= / ^FEATURE_FILE= / ^POST_PLAN_WORKFLOW_PATH=
#     lines from a copy of $IMPLEMENT_TMPDIR/session-env.sh, appends the three
#     new lines, and atomically `mv` the result into place.
#   - Post-condition: re-reads the file via read-session-env-key.sh and asserts
#     each of the three keys returns the expected value. Mismatch is a fatal
#     exit-2 with an actionable error naming the bad key.
#
# Exit codes:
#   0 — all three keys persisted and verified.
#   2 — usage error, validation failure, write failure, or post-condition failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

fail() {
    printf 'persist-post-plan-keys.sh: %s\n' "$1" >&2
    exit 2
}

usage() {
    printf 'Usage: persist-post-plan-keys.sh --implement-tmpdir PATH --plan-file PATH --feature-file PATH --workflow-path SIMPLE|HARD\n' >&2
}

IMPLEMENT_TMPDIR_ARG=""
PLAN_FILE_ARG=""
FEATURE_FILE_ARG=""
WORKFLOW_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail "--implement-tmpdir requires a value"
            IMPLEMENT_TMPDIR_ARG="$2"
            shift 2
            ;;
        --plan-file)
            [[ $# -ge 2 ]] || fail "--plan-file requires a value"
            PLAN_FILE_ARG="$2"
            shift 2
            ;;
        --feature-file)
            [[ $# -ge 2 ]] || fail "--feature-file requires a value"
            FEATURE_FILE_ARG="$2"
            shift 2
            ;;
        --workflow-path)
            [[ $# -ge 2 ]] || fail "--workflow-path requires a value"
            WORKFLOW_PATH="$2"
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

[[ -n "$IMPLEMENT_TMPDIR_ARG" ]]  || { usage; fail "--implement-tmpdir is required"; }
[[ -n "$PLAN_FILE_ARG" ]]         || { usage; fail "--plan-file is required"; }
[[ -n "$FEATURE_FILE_ARG" ]]      || { usage; fail "--feature-file is required"; }
[[ -n "$WORKFLOW_PATH" ]]         || { usage; fail "--workflow-path is required"; }

[[ -d "$IMPLEMENT_TMPDIR_ARG" ]]  || fail "--implement-tmpdir not a directory: $IMPLEMENT_TMPDIR_ARG"

# Reject control characters / newlines that would corrupt KEY=VALUE lines.
for value in "$PLAN_FILE_ARG" "$FEATURE_FILE_ARG" "$WORKFLOW_PATH"; do
    case "$value" in
        *$'\n'*|*$'\r'*) fail "argument contains newline; refusing to write session-env" ;;
    esac
done

case "$WORKFLOW_PATH" in
    SIMPLE|HARD) ;;
    *) fail "--workflow-path must be SIMPLE or HARD, got: $WORKFLOW_PATH" ;;
esac

[[ -f "$PLAN_FILE_ARG" ]]    || fail "--plan-file not found: $PLAN_FILE_ARG"
[[ -s "$PLAN_FILE_ARG" ]]    || fail "--plan-file is empty: $PLAN_FILE_ARG"
[[ -f "$FEATURE_FILE_ARG" ]] || fail "--feature-file not found: $FEATURE_FILE_ARG"

IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
SESSION_ENV_PATH="$IMPLEMENT_TMPDIR/session-env.sh"
[[ -f "$SESSION_ENV_PATH" ]] || fail "session-env not found: $SESSION_ENV_PATH"
[[ -r "$SESSION_ENV_PATH" ]] || fail "session-env not readable: $SESSION_ENV_PATH"
[[ -w "$SESSION_ENV_PATH" ]] || fail "session-env not writable: $SESSION_ENV_PATH"

READER="$SCRIPT_DIR/read-session-env-key.sh"
[[ -x "$READER" ]] || fail "read-session-env-key.sh not executable: $READER"

TMPFILE="$(mktemp "${SESSION_ENV_PATH}.tmp.XXXXXX")"
cleanup() {
    rm -f "$TMPFILE"
}
trap cleanup EXIT

{
    grep -v '^PLAN_FILE=' "$SESSION_ENV_PATH" \
        | grep -v '^FEATURE_FILE=' \
        | grep -v '^POST_PLAN_WORKFLOW_PATH=' || true
    printf 'PLAN_FILE=%s\n' "$PLAN_FILE_ARG"
    printf 'FEATURE_FILE=%s\n' "$FEATURE_FILE_ARG"
    printf 'POST_PLAN_WORKFLOW_PATH=%s\n' "$WORKFLOW_PATH"
} > "$TMPFILE"

mv "$TMPFILE" "$SESSION_ENV_PATH"
trap - EXIT

# Post-condition assertion: re-read the file and assert each key matches.
verify_key() {
    local key="$1" expected="$2" got
    got="$("$READER" --file "$SESSION_ENV_PATH" --key "$key" --default "")"
    if [[ "$got" != "$expected" ]]; then
        fail "post-condition: $key not persisted (expected=$expected got=${got:-<empty>}); session-env=$SESSION_ENV_PATH"
    fi
}

verify_key PLAN_FILE "$PLAN_FILE_ARG"
verify_key FEATURE_FILE "$FEATURE_FILE_ARG"
verify_key POST_PLAN_WORKFLOW_PATH "$WORKFLOW_PATH"

printf 'POST_PLAN_KEYS_PERSISTED=true\n'
printf 'PLAN_FILE=%s\n' "$PLAN_FILE_ARG"
printf 'FEATURE_FILE=%s\n' "$FEATURE_FILE_ARG"
printf 'POST_PLAN_WORKFLOW_PATH=%s\n' "$WORKFLOW_PATH"
