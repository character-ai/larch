#!/usr/bin/env bash
# step-6-entry.sh — /implement Step 6 bgjob launcher and composite entrypoint.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
BGJOB_CHILD="false"
MERGE_RESULT_ENV=""
ORIGINAL_ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --bgjob-child) BGJOB_CHILD="true"; shift ;;
        --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
        *) ORIGINAL_ARGS+=("$1"); shift ;;
    esac
done

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

step6_cleanup() {
    mkdir -p "$IMPLEMENT_TMPDIR/.completed" 2>/dev/null || true
    printf '' >"$IMPLEMENT_TMPDIR/.completed/step-6-terminal" 2>/dev/null || true
}

step6_merge_cleanup() {
    if [ -n "${MERGE_RESULT_ENV_TMP:-}" ]; then
        rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true
    fi
    step6_cleanup
}

rehydrate_plugin_root
rehydrate_larch_triplet
if [ "$BGJOB_CHILD" = "true" ]; then
    [ -n "$MERGE_RESULT_ENV" ] || { printf '%s
' 'step-6-entry.sh: --merge-result-env is required in child mode' >&2; exit 2; }
    MERGE_RESULT_ENV_PARENT="${MERGE_RESULT_ENV%/*}"
    [ -L "$MERGE_RESULT_ENV_PARENT" ] && { printf '%s
' 'step-6-entry.sh: refusing symlinked merge-result-env parent' >&2; exit 2; }
    MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
    trap step6_merge_cleanup EXIT
    set +e
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement step-6-entry "${ORIGINAL_ARGS[@]}" | tee "$MERGE_RESULT_ENV_TMP"
    pipe_status=("${PIPESTATUS[@]}")
    set -e
    rc=${pipe_status[0]}
    tee_rc=${pipe_status[1]}
    if [ "$tee_rc" -ne 0 ]; then
        rc=$tee_rc
    fi
    if [ -L "$MERGE_RESULT_ENV" ]; then
        exit 2
    fi
    mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || rc=$?
    exit "$rc"
fi

if [ -L "$IMPLEMENT_TMPDIR/bgjob" ]; then
    printf '%s
' 'step-6-entry.sh: refusing symlinked bgjob directory' >&2
    exit 2
fi
mkdir -p "$IMPLEMENT_TMPDIR/bgjob"
STEP="implement-step6-checks"
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
: >"$MERGE_RESULT_ENV_TMP"
[ -L "$MERGE_RESULT_ENV" ] && { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; printf '%s
' 'step-6-entry.sh: refusing symlinked merge-result-env' >&2; exit 2; }
mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; exit 2; }
rm -f "$IMPLEMENT_TMPDIR/.completed/step-6-terminal" 2>/dev/null || true

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step "$STEP" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s 15600 \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
    --merge-result-env "$MERGE_RESULT_ENV" \
    --sentinel "$IMPLEMENT_TMPDIR/.completed/step-6-terminal" \
    -- \
    bash "$SCRIPT_DIR/step-6-entry.sh" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV" "${ORIGINAL_ARGS[@]}"
