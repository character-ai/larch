#!/usr/bin/env bash
# run-step-checks.sh — launch /implement checks legs through bgjob.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
SITE=""
COMMIT_SITE=""
FORKED_TARGET="false"
REBASE_CHECKPOINT_4R="false"
BGJOB_CHILD="false"
MERGE_RESULT_ENV=""
while [ $# -gt 0 ]; do
    case "$1" in
        --bgjob-child) BGJOB_CHILD="true"; shift ;;
        --site) [ $# -ge 2 ] || exit 2; SITE=$2; shift 2 ;;
        --commit-site) [ $# -ge 2 ] || exit 2; COMMIT_SITE=$2; shift 2 ;;
        --forked-target) [ $# -ge 2 ] || exit 2; FORKED_TARGET=$2; shift 2 ;;
        --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
        --rebase-checkpoint-4r) REBASE_CHECKPOINT_4R="true"; shift ;;
        --help) printf '%s
' 'Usage: run-step-checks.sh --site SITE [--commit-site SITE] [--rebase-checkpoint-4r] [--forked-target true|false]'; exit 0 ;;
        *) printf '%s
' "run-step-checks.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -n "$SITE" ] || { printf '%s
' 'run-step-checks.sh: --site is required' >&2; exit 2; }
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

rehydrate_plugin_root
rehydrate_larch_triplet
export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

build_child_command() {
    CHILD_CMD=(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py")
    if [ -n "$COMMIT_SITE" ]; then
        CHILD_CMD+=(implement checks-commit-route --checks-site "$SITE" --commit-site "$COMMIT_SITE")
        if [ "$REBASE_CHECKPOINT_4R" = "true" ]; then
            CHILD_CMD+=(--rebase-checkpoint-4r)
        fi
        CHILD_CMD+=(--forked-target "$FORKED_TARGET")
    else
        CHILD_CMD+=(checks run-relevant --site "$SITE" --tmpdir "$IMPLEMENT_TMPDIR")
    fi
}

if [ "$BGJOB_CHILD" = "true" ]; then
    [ -n "$MERGE_RESULT_ENV" ] || { printf '%s
' 'run-step-checks.sh: --merge-result-env is required in child mode' >&2; exit 2; }
    build_child_command
    set +e
    "${CHILD_CMD[@]}" | tee "$MERGE_RESULT_ENV"
    pipe_status=("${PIPESTATUS[@]}")
    set -e
    rc=${pipe_status[0]}
    tee_rc=${pipe_status[1]}
    if [ "$tee_rc" -ne 0 ]; then
        rc=$tee_rc
    fi
    exit "$rc"
fi

STEP="implement-checks-$SITE"
BUDGET_S="10800"
SENTINEL_ARGS=()
if [ "$SITE" = "step3" ]; then
    STEP="implement-step3-checks"
    BUDGET_S="15600"
    rm -f "$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-3-terminal.count" "$IMPLEMENT_TMPDIR/.completed/step-3-terminal" 2>/dev/null || true
    SENTINEL_ARGS=(--sentinel "$IMPLEMENT_TMPDIR/.completed/step-3-terminal")
elif [ "$SITE" = "step6" ]; then
    STEP="implement-step6-checks"
    SENTINEL_ARGS=(--sentinel "$IMPLEMENT_TMPDIR/.completed/step-6-terminal")
fi

mkdir -p "$IMPLEMENT_TMPDIR/bgjob"
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
: >"$MERGE_RESULT_ENV"
CHILD_ARGS=(--bgjob-child --site "$SITE" --commit-site "$COMMIT_SITE" --forked-target "$FORKED_TARGET" --merge-result-env "$MERGE_RESULT_ENV")
if [ "$REBASE_CHECKPOINT_4R" = "true" ]; then
    CHILD_ARGS+=(--rebase-checkpoint-4r)
fi

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step "$STEP" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s "$BUDGET_S" \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
    --merge-result-env "$MERGE_RESULT_ENV" \
    "${SENTINEL_ARGS[@]}" \
    -- \
    bash "$SCRIPT_DIR/run-step-checks.sh" "${CHILD_ARGS[@]}"
