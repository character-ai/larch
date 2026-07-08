#!/usr/bin/env bash
# step-5-review.sh — /implement Step 5 bgjob launcher and review-loop entrypoint.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
BGJOB_CHILD=false
while [ $# -gt 0 ]; do
    case "$1" in
        --bgjob-child) BGJOB_CHILD=true; shift ;;
        --help) printf '%s
' 'Usage: step-5-review.sh'; exit 0 ;;
        *) printf '%s
' "step-5-review.sh: unknown argument: $1" >&2; exit 2 ;;
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

read_run_flag_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/run-flags.sh"
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

step5_live_registry_exists() {
    python3 <<'PY'
from pathlib import Path
import os
import sys

plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
sys.path.insert(0, str(plugin_root / "python"))
try:
    from larch.bgjob import registry  # noqa: E402

    path, entry = registry.read_for(tmpdir=Path(os.environ["IMPLEMENT_TMPDIR"]), step="implement-step5-review")
    if entry is None:
        raise SystemExit(1)
    if registry.child_liveness(entry).live and registry.daemon_liveness(entry).live:
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

step5_canonical_result_env_state() {
    python3 <<'PY'
from pathlib import Path
import os
import sys

result_env = Path(os.environ["IMPLEMENT_TMPDIR"]) / "bgjob" / "implement-step5-review.result.env"
required_keys = {
    "STEP5_REVIEW_STATUS",
    "STALL_TRACKING",
    "STALL_REASON",
    "ROUNDS_COMPLETED",
    "FINAL_ROUND_NUM",
    "FINAL_REVIEW_AND_FIX_STATUS",
    "CODER_STATUS",
    "FILES_CHANGED_HINT",
    "EFFECTIVE_ROUND_CAP",
}

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
        if key and key not in rows:
            rows[key] = value
except OSError:
    print("BGJOB_ERROR=registry-check-failed", file=sys.stderr)
    raise SystemExit(2)
status = rows.get("STEP5_REVIEW_STATUS", "")
if rows.get("BGJOB_RC") == "0" and status and required_keys.issubset(rows):
    print("complete")
    raise SystemExit(0)
if status == "stall" and required_keys.issubset(rows):
    print("stall")
    raise SystemExit(0)
print("stale")
raise SystemExit(1)
PY
}

step5_run_child() {
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true
    dynamic_archetypes_cap=""
    if [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        dynamic_archetypes_cap=$(awk 'BEGIN{p="LARCH_DYNAMIC_ARCHETYPES_MAX="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "$dynamic_archetypes_cap" ] && [ -n "${LARCH_DYNAMIC_ARCHETYPES_MAX:-}" ]; then
        dynamic_archetypes_cap="$LARCH_DYNAMIC_ARCHETYPES_MAX"
    fi
    [ -n "$dynamic_archetypes_cap" ] || dynamic_archetypes_cap=1
    case "$dynamic_archetypes_cap" in [0-1]) ;; *) printf 'ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: %s
' "$dynamic_archetypes_cap" >&2; exit 2 ;; esac
    export LARCH_DYNAMIC_ARCHETYPES_MAX="$dynamic_archetypes_cap"
    difficulty_override=$(read_run_flag_key DIFFICULTY_OVERRIDE "")
    case "$difficulty_override" in ""|TRIVIAL|MODERATE|HARD) ;; *) difficulty_override="" ;; esac
    printf '> **🔶 /implement 5: code review — review-and-fix step5 --mode loop, fixed tier cap 2; escalated rounds skip pruning; prune-to-empty converges; no round-5 re-probe; dynamic-archetypes cap=%s**\n' "$dynamic_archetypes_cap" >&2
    if [ -n "$difficulty_override" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
            --implement-tmpdir "$IMPLEMENT_TMPDIR" \
            --mode loop \
            --starting-round 1 \
            --difficulty "$difficulty_override"
    else
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
            --implement-tmpdir "$IMPLEMENT_TMPDIR" \
            --mode loop \
            --starting-round 1
    fi
}

rehydrate_plugin_root
rehydrate_larch_triplet
export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

if [ "$BGJOB_CHILD" = true ]; then
    step5_run_child
    exit $?
fi

if [ -L "$IMPLEMENT_TMPDIR/bgjob" ]; then
    printf '%s
' 'step-5-review.sh: refusing symlinked bgjob directory' >&2
    exit 2
fi
mkdir -p "$IMPLEMENT_TMPDIR/bgjob" "$IMPLEMENT_TMPDIR/.completed"
RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/implement-step5-review.result.env"
if [ -L "$RESULT_ENV" ]; then
    printf '%s
' 'step-5-review.sh: refusing symlinked bgjob result env' >&2
    exit 2
fi
if [ -e "$RESULT_ENV" ] && [ ! -f "$RESULT_ENV" ]; then
    printf '%s
' 'step-5-review.sh: refusing non-regular bgjob result env' >&2
    exit 2
fi
set +e
registry_state=$(step5_live_registry_exists)
registry_rc=$?
set -e
if [ "$registry_rc" -eq 2 ]; then
    exit 2
fi
set +e
result_env_state=$(step5_canonical_result_env_state)
result_env_rc=$?
set -e
if [ "$result_env_rc" -eq 2 ]; then
    exit 2
fi
if [ "$registry_state" = live ]; then
    if [ "$result_env_state" != complete ] && [ "$result_env_state" != stall ]; then
        rm -f "$RESULT_ENV" 2>/dev/null || true
    fi
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step implement-step5-review --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
    exit $?
fi
if [ "$result_env_state" = complete ] || [ "$result_env_state" = stall ]; then
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait --step implement-step5-review --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0
    exit $?
fi
if [ "$result_env_state" = stale ]; then
    rm -f "$RESULT_ENV" 2>/dev/null || true
fi
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/.step5-review-result.env"
[ -L "$MERGE_RESULT_ENV" ] && { printf '%s
' 'step-5-review.sh: refusing symlinked merge-result-env' >&2; exit 2; }
: >"$MERGE_RESULT_ENV"
rm -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal" "$IMPLEMENT_TMPDIR/.step5-wrapper-detached" "$IMPLEMENT_TMPDIR/.step5-reattach-active" 2>/dev/null || true

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step implement-step5-review \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s 21600 \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
    --merge-result-env "$MERGE_RESULT_ENV" \
    --sentinel "$IMPLEMENT_TMPDIR/.completed/step-5-terminal" \
    -- \
    bash "$SCRIPT_DIR/step-5-review.sh" --bgjob-child
