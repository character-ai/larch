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
LAUNCH_HEAD=""
LAUNCH_FP=""
LAUNCH_SCHEMA=""
REPO_ROOT_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --bgjob-child) BGJOB_CHILD="true"; shift ;;
        --site) [ $# -ge 2 ] || exit 2; SITE=$2; shift 2 ;;
        --commit-site) [ $# -ge 2 ] || exit 2; COMMIT_SITE=$2; shift 2 ;;
        --forked-target) [ $# -ge 2 ] || exit 2; FORKED_TARGET=$2; shift 2 ;;
        --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
        --launch-head) [ $# -ge 2 ] || exit 2; LAUNCH_HEAD=$2; shift 2 ;;
        --launch-fp) [ $# -ge 2 ] || exit 2; LAUNCH_FP=$2; shift 2 ;;
        --launch-schema) [ $# -ge 2 ] || exit 2; LAUNCH_SCHEMA=$2; shift 2 ;;
        --repo-root) [ $# -ge 2 ] || exit 2; REPO_ROOT_ARG=$2; shift 2 ;;
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

step_checks_live_registry_exists() {
    python3 <<'PY'
from pathlib import Path
import os
import sys

plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
sys.path.insert(0, str(plugin_root / "python"))
try:
    from larch.bgjob import registry  # noqa: E402

    path, entry = registry.read_for(tmpdir=Path(os.environ["IMPLEMENT_TMPDIR"]), step=os.environ["STEP_CHECKS_STEP"])
    if entry is None:
        raise SystemExit(1)
    if registry.child_liveness(entry).live or registry.daemon_liveness(entry).live:
        print("live")
        raise SystemExit(0)
    registry.unlink_entry(path)
except SystemExit:
    raise
except Exception:
    print("BGJOB_ERROR=registry-check-failed", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(1)
PY
}

kv_value() {
    local key=$1 text=$2
    printf '%s\n' "$text" | awk -F= -v k="$key" '$1 == k { print substr($0, index($0, "=") + 1); exit }'
}

resolve_repo_root() {
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement checks-result-identity resolve-repo-root \
        --implement-tmpdir "$IMPLEMENT_TMPDIR"
}

compute_identity() {
    local root=$1
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement checks-result-identity compute --repo-root "$root"
}

classify_completed() {
    local root=$1 result_env=$2 step=$3
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement checks-result-identity classify \
        --mode completed \
        --repo-root "$root" \
        --result-env "$result_env" \
        --step "$step" \
        --terminal-actions "continue,stall,checks-failed,skip-to-7a"
}

classify_live_seed() {
    local root=$1 merge_env=$2 result_env=$3 step=$4
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement checks-result-identity classify \
        --mode live-seed \
        --repo-root "$root" \
        --result-env "$result_env" \
        --merge-env "$merge_env" \
        --step "$step"
}

validate_child_identity() {
    local root=$1 head=$2 fp=$3 schema=$4
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement checks-result-identity validate-child \
        --repo-root "$root" \
        --expected-head "$head" \
        --expected-fp "$fp" \
        --expected-schema "$schema"
}

post_publish_identity_matches() {
    local checks_out=$1
    # A successful composite intentionally commits or rebases after its checks
    # leg, so its launch identity is no longer the expected final identity.
    if [ -n "$COMMIT_SITE" ] && printf '%s\n' "$checks_out" | grep -Fxq 'COMMIT_ROUTE_OUTCOME=continue'; then
        return 0
    fi
    validate_child_identity "$REPO_ROOT" "$LAUNCH_HEAD" "$LAUNCH_FP" "$LAUNCH_SCHEMA" >/dev/null
}

write_integrity_failure() {
    local out=$1 step=$2 reason=$3
    printf '%s\n' \
        "STEP=${step}" \
        "BGJOB_RC=1" \
        "NEXT_ACTION=identity-integrity-failed" \
        "FAILURE_REASON=${reason}" >"$out"
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
        CHILD_CMD+=(checks run-relevant --site "$SITE" --tmpdir "$IMPLEMENT_TMPDIR" --repo-root "$REPO_ROOT")
    fi
}

merge_result_cleanup() {
    if [ -n "${MERGE_RESULT_ENV_TMP:-}" ]; then
        rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true
    fi
}

if [ "$BGJOB_CHILD" = "true" ]; then
    [ -n "$MERGE_RESULT_ENV" ] || { printf '%s
' 'run-step-checks.sh: --merge-result-env is required in child mode' >&2; exit 2; }
    [ -n "$REPO_ROOT_ARG" ] || { printf '%s
' 'run-step-checks.sh: --repo-root is required in child mode' >&2; exit 2; }
    [ -n "$LAUNCH_HEAD" ] && [ -n "$LAUNCH_FP" ] && [ -n "$LAUNCH_SCHEMA" ] || {
        printf '%s
' 'run-step-checks.sh: launch identity args required in child mode' >&2
        exit 2
    }
    REPO_ROOT="$REPO_ROOT_ARG"
    export REPO_ROOT CLAUDE_PROJECT_DIR="$REPO_ROOT"
    cd "$REPO_ROOT" || exit 2
    MERGE_RESULT_ENV_PARENT="${MERGE_RESULT_ENV%/*}"
    [ -L "$MERGE_RESULT_ENV_PARENT" ] && { printf '%s
' 'run-step-checks.sh: refusing symlinked merge-result-env parent' >&2; exit 2; }
    MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
    trap merge_result_cleanup EXIT
    STEP="implement-checks-$SITE"
    if [ "$SITE" = "step3" ]; then
        STEP="implement-step3-checks"
    elif [ "$SITE" = "step5-self-review" ]; then
        STEP="implement-checks-step5-self-review"
    elif [ "$SITE" = "step6" ]; then
        STEP="implement-step6-checks"
    fi
    if ! validate_child_identity "$REPO_ROOT" "$LAUNCH_HEAD" "$LAUNCH_FP" "$LAUNCH_SCHEMA" >/dev/null; then
        write_integrity_failure "$MERGE_RESULT_ENV_TMP" "$STEP" "pre-checks-identity-mismatch"
        if [ -L "$MERGE_RESULT_ENV" ]; then
            exit 2
        fi
        mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || true
        exit 1
    fi
    build_child_command
    set +e
    CHECKS_OUT="$("${CHILD_CMD[@]}")"
    rc=$?
    set -e
    if ! post_publish_identity_matches "$CHECKS_OUT"; then
        write_integrity_failure "$MERGE_RESULT_ENV_TMP" "$STEP" "pre-publish-identity-mismatch"
        if [ -L "$MERGE_RESULT_ENV" ]; then
            exit 2
        fi
        mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || true
        exit 1
    fi
    {
        printf '%s\n' "$CHECKS_OUT"
        printf '%s\n' "CHECKS_INPUT_HEAD_SHA=${LAUNCH_HEAD}"
        printf '%s\n' "CHECKS_INPUT_TREE_FP=${LAUNCH_FP}"
        printf '%s\n' "CHECKS_INPUT_FP_SCHEMA=${LAUNCH_SCHEMA}"
    } >"$MERGE_RESULT_ENV_TMP"
    if [ -L "$MERGE_RESULT_ENV" ]; then
        exit 2
    fi
    mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || rc=$?
    printf '%s\n' "$CHECKS_OUT"
    exit "$rc"
fi

STEP="implement-checks-$SITE"
BUDGET_S="10800"
if [ "$SITE" = "step3" ]; then
    STEP="implement-step3-checks"
    BUDGET_S="15600"
elif [ "$SITE" = "step5-self-review" ]; then
    STEP="implement-checks-step5-self-review"
    BUDGET_S="14700"
elif [ "$SITE" = "step6" ]; then
    STEP="implement-step6-checks"
fi

if [ -L "$IMPLEMENT_TMPDIR/bgjob" ]; then
    printf '%s
' 'run-step-checks.sh: refusing symlinked bgjob directory' >&2
    exit 2
fi
mkdir -p "$IMPLEMENT_TMPDIR/bgjob"
RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.result.env"
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
if [ -L "$RESULT_ENV" ]; then
    printf '%s
' 'run-step-checks.sh: refusing symlinked bgjob result env' >&2
    exit 2
fi
if [ -e "$RESULT_ENV" ] && [ ! -f "$RESULT_ENV" ]; then
    printf '%s
' 'run-step-checks.sh: refusing non-regular bgjob result env' >&2
    exit 2
fi
if [ -L "$MERGE_RESULT_ENV" ]; then
    printf '%s
' 'run-step-checks.sh: refusing symlinked merge-result-env' >&2
    exit 2
fi

set +e
REPO_ROOT_OUT=$(resolve_repo_root)
resolve_rc=$?
set -e
if [ "$resolve_rc" -ne 0 ]; then
    printf '%s
' 'run-step-checks.sh: failed to resolve persisted REPO_ROOT' >&2
    exit 2
fi
REPO_ROOT=$(kv_value REPO_ROOT "$REPO_ROOT_OUT")
[ -n "$REPO_ROOT" ] || { printf '%s
' 'run-step-checks.sh: empty REPO_ROOT' >&2; exit 2; }
export REPO_ROOT CLAUDE_PROJECT_DIR="$REPO_ROOT"

set +e
IDENTITY_OUT=$(compute_identity "$REPO_ROOT")
identity_rc=$?
set -e
if [ "$identity_rc" -ne 0 ]; then
    printf '%s
' 'run-step-checks.sh: failed to compute checks input identity' >&2
    exit 2
fi
LAUNCH_HEAD=$(kv_value CHECKS_INPUT_HEAD_SHA "$IDENTITY_OUT")
LAUNCH_FP=$(kv_value CHECKS_INPUT_TREE_FP "$IDENTITY_OUT")
LAUNCH_SCHEMA=$(kv_value CHECKS_INPUT_FP_SCHEMA "$IDENTITY_OUT")
[ -n "$LAUNCH_HEAD" ] && [ -n "$LAUNCH_FP" ] && [ -n "$LAUNCH_SCHEMA" ] || {
    printf '%s
' 'run-step-checks.sh: incomplete checks input identity' >&2
    exit 2
}

STEP_CHECKS_STEP="$STEP"
STEP_CHECKS_RESULT_ENV="$RESULT_ENV"
export STEP_CHECKS_STEP STEP_CHECKS_RESULT_ENV
set +e
registry_state=$(step_checks_live_registry_exists)
registry_rc=$?
set -e
if [ "$registry_rc" -eq 2 ]; then
    exit 2
fi

if [ "$registry_state" = live ]; then
    set +e
    live_out=$(classify_live_seed "$REPO_ROOT" "$MERGE_RESULT_ENV" "$RESULT_ENV" "$STEP")
    live_rc=$?
    set -e
    if [ "$live_rc" -eq 2 ]; then
        exit 2
    fi
    live_state=$(kv_value STATE "$live_out")
    if [ "$live_state" != matching ]; then
        printf '%s
' "run-step-checks.sh: live checks job identity mismatch (STATE=${live_state}); refusing duplicate launch" >&2
        exit 2
    fi
    if [ -f "$RESULT_ENV" ]; then
        set +e
        completed_out=$(classify_completed "$REPO_ROOT" "$RESULT_ENV" "$STEP")
        completed_rc=$?
        set -e
        if [ "$completed_rc" -eq 2 ]; then
            exit 2
        fi
        completed_state=$(kv_value STATE "$completed_out")
        if [ "$completed_state" != matching ]; then
            rm -f "$RESULT_ENV" 2>/dev/null || true
        fi
    fi
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
    exit $?
fi

if [ -f "$RESULT_ENV" ]; then
    set +e
    completed_out=$(classify_completed "$REPO_ROOT" "$RESULT_ENV" "$STEP")
    completed_rc=$?
    set -e
    if [ "$completed_rc" -eq 2 ]; then
        exit 2
    fi
    completed_state=$(kv_value STATE "$completed_out")
    if [ "$completed_state" = matching ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
        exit $?
    fi
    rm -f "$RESULT_ENV" 2>/dev/null || true
    rm -f "$MERGE_RESULT_ENV" 2>/dev/null || true
    if [ -e "$RESULT_ENV" ] || [ -e "$MERGE_RESULT_ENV" ]; then
        printf '%s
' 'run-step-checks.sh: failed to clear stale checks result state' >&2
        exit 2
    fi
fi

MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
{
    printf '%s\n' "CHECKS_INPUT_HEAD_SHA=${LAUNCH_HEAD}"
    printf '%s\n' "CHECKS_INPUT_TREE_FP=${LAUNCH_FP}"
    printf '%s\n' "CHECKS_INPUT_FP_SCHEMA=${LAUNCH_SCHEMA}"
} >"$MERGE_RESULT_ENV_TMP"
[ -L "$MERGE_RESULT_ENV" ] && { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; printf '%s
' 'run-step-checks.sh: refusing symlinked merge-result-env' >&2; exit 2; }
mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; exit 2; }

CHILD_ARGS=(
    --bgjob-child
    --site "$SITE"
    --commit-site "$COMMIT_SITE"
    --forked-target "$FORKED_TARGET"
    --merge-result-env "$MERGE_RESULT_ENV"
    --repo-root "$REPO_ROOT"
    --launch-head "$LAUNCH_HEAD"
    --launch-fp "$LAUNCH_FP"
    --launch-schema "$LAUNCH_SCHEMA"
)
if [ "$REBASE_CHECKPOINT_4R" = "true" ]; then
    CHILD_ARGS+=(--rebase-checkpoint-4r)
fi

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step "$STEP" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s "$BUDGET_S" \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
    --merge-result-env "$MERGE_RESULT_ENV" \
    -- \
    bash "$SCRIPT_DIR/run-step-checks.sh" "${CHILD_ARGS[@]}"
