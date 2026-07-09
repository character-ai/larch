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

step_checks_result_env_state() {
    python3 <<'PY'
from pathlib import Path
import os
import sys

result_env = Path(os.environ["STEP_CHECKS_RESULT_ENV"])
step = os.environ["STEP_CHECKS_STEP"]
if result_env.is_symlink() or (result_env.exists() and not result_env.is_file()):
    print("BGJOB_ERROR=registry-check-failed", file=sys.stderr)
    raise SystemExit(2)
if not result_env.exists():
    raise SystemExit(1)
try:
    rows: dict[str, str] = {}
    for line in result_env.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        rows.setdefault(key, value)
except OSError:
    print("BGJOB_ERROR=registry-check-failed", file=sys.stderr)
    raise SystemExit(2)
if rows.get("STEP") == step and rows.get("BGJOB_RC") == "0" and rows.get("NEXT_ACTION"):
    print("complete")
    raise SystemExit(0)
print("stale")
raise SystemExit(1)
PY
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

merge_result_cleanup() {
    if [ -n "${MERGE_RESULT_ENV_TMP:-}" ]; then
        rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true
    fi
}

if [ "$BGJOB_CHILD" = "true" ]; then
    [ -n "$MERGE_RESULT_ENV" ] || { printf '%s
' 'run-step-checks.sh: --merge-result-env is required in child mode' >&2; exit 2; }
    MERGE_RESULT_ENV_PARENT="${MERGE_RESULT_ENV%/*}"
    [ -L "$MERGE_RESULT_ENV_PARENT" ] && { printf '%s
' 'run-step-checks.sh: refusing symlinked merge-result-env parent' >&2; exit 2; }
    MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
    trap merge_result_cleanup EXIT
    build_child_command
    set +e
    "${CHILD_CMD[@]}" | tee "$MERGE_RESULT_ENV_TMP"
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
set +e
result_env_state=$(step_checks_result_env_state)
result_env_rc=$?
set -e
if [ "$result_env_rc" -eq 2 ]; then
    exit 2
fi
if [ "$registry_state" = live ]; then
    if [ "$result_env_state" != complete ]; then
        rm -f "$RESULT_ENV" 2>/dev/null || true
    fi
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
    exit $?
fi
if [ "$result_env_state" = complete ]; then
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
    exit $?
fi
rm -f "$RESULT_ENV" 2>/dev/null || true
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
: >"$MERGE_RESULT_ENV_TMP"
[ -L "$MERGE_RESULT_ENV" ] && { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; printf '%s
' 'run-step-checks.sh: refusing symlinked merge-result-env' >&2; exit 2; }
mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; exit 2; }
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
    -- \
    bash "$SCRIPT_DIR/run-step-checks.sh" "${CHILD_ARGS[@]}"
