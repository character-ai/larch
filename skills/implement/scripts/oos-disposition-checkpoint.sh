#!/usr/bin/env bash
# oos-disposition-checkpoint.sh — Step 8+ OOS disposition input plumbing + gate invocation.
#
# Exit 0: gate passed or skipped (fork / repo-unavailable).
# Exit 1: disposition gap (gate exit 1).
# Exit 2: validation/setup (gate exit 2 or pre-gate input-resolution failure).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

IMPLEMENT_TMPDIR=""
DESIGN_TMPDIR_ARG=""
_chk_log=""

usage() {
  printf 'usage: oos-disposition-checkpoint.sh --implement-tmpdir DIR [--design-tmpdir DIR]\n' >&2
}

log_checkpoint_failure() {
  local saved_rc=$1 site=$2 output_file=$3
  [ -f "$output_file" ] || : >"$output_file" 2>/dev/null || true
  "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
    --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
    --site "$site" \
    --tool oos-disposition-checkpoint.sh \
    --exit-code "$saved_rc" \
    --category "Tool Failures" \
    --output-file "$output_file" \
    --redact || true
  exit "$saved_rc"
}

prescan_implement_tmpdir() {
  local arg
  while [ $# -gt 0 ]; do
    arg=$1
    shift
    case "$arg" in
      --implement-tmpdir)
        if [ $# -gt 0 ]; then
          case "$1" in
            --*) ;;
            *) IMPLEMENT_TMPDIR=$1 ;;
          esac
        fi
        return 0
        ;;
    esac
  done
  return 0
}

fail_validation() {
  local msg=$1
  [ -f "$_chk_log" ] || : >"$_chk_log" 2>/dev/null || true
  printf '%s\n' "$msg" >>"$_chk_log" 2>/dev/null || true
  printf '%s\n' "$msg" >&2
  log_checkpoint_failure 2 step-8-oos-checkpoint-validation "$_chk_log"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --implement-tmpdir)
      if [ $# -lt 2 ] || [ "${2#--}" != "$2" ]; then
        IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-/nonexistent}"
        _chk_log="$IMPLEMENT_TMPDIR/oos-disposition-checkpoint.stderr.log"
        fail_validation 'oos-disposition-checkpoint: --implement-tmpdir requires a value'
      fi
      IMPLEMENT_TMPDIR="$2"
      shift 2
      ;;
    --design-tmpdir)
      if [ $# -lt 2 ] || [ "${2#--}" != "$2" ]; then
        [ -n "$IMPLEMENT_TMPDIR" ] || prescan_implement_tmpdir "$@"
        _chk_log="${IMPLEMENT_TMPDIR:-/tmp}/oos-disposition-checkpoint.stderr.log"
        fail_validation 'oos-disposition-checkpoint: --design-tmpdir requires a value'
      fi
      DESIGN_TMPDIR_ARG="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      if [ -z "$IMPLEMENT_TMPDIR" ]; then
        IMPLEMENT_TMPDIR="/nonexistent"
      fi
      _chk_log="$IMPLEMENT_TMPDIR/oos-disposition-checkpoint.stderr.log"
      fail_validation "oos-disposition-checkpoint: unknown argument: $1"
      ;;
  esac
done

if [ -z "$IMPLEMENT_TMPDIR" ]; then
  IMPLEMENT_TMPDIR="/nonexistent"
  _chk_log="$IMPLEMENT_TMPDIR/oos-disposition-checkpoint.stderr.log"
  usage
  fail_validation 'oos-disposition-checkpoint: --implement-tmpdir is required'
fi

_chk_log="$IMPLEMENT_TMPDIR/oos-disposition-checkpoint.stderr.log"
_gate_log="$IMPLEMENT_TMPDIR/oos-disposition-gate.stderr.log"
[ -f "$_chk_log" ] || : >"$_chk_log" 2>/dev/null || true

_forked=false
_repo_unavail=false
if [ -f "$IMPLEMENT_TMPDIR/ship-pr-state.sh" ]; then
  _forked=$(grep '^FORKED_TARGET=' "$IMPLEMENT_TMPDIR/ship-pr-state.sh" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r')
  _repo_unavail=$(grep '^REPO_UNAVAILABLE=' "$IMPLEMENT_TMPDIR/ship-pr-state.sh" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r')
fi
if [ -z "$_forked" ] && [ -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then
  _forked=$(grep '^FORKED_TARGET=' "$IMPLEMENT_TMPDIR/finalize-state.sh" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r')
fi
if [ -z "$_repo_unavail" ] && [ -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then
  _repo_unavail=$(grep '^REPO_UNAVAILABLE=' "$IMPLEMENT_TMPDIR/finalize-state.sh" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r')
fi

_repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
_oos_mb=""
_oos_range="HEAD"
if [ -n "$_repo_root" ] && git -C "$_repo_root" rev-parse -q --verify origin/main >/dev/null 2>&1; then
  _oos_mb=$(git -C "$_repo_root" merge-base HEAD origin/main 2>/dev/null || true)
  if [ -n "$_oos_mb" ]; then
    _oos_range="${_oos_mb}..HEAD"
  else
    _oos_range="origin/main..HEAD"
  fi
fi

_RUN_ID=""
if [ -f "$IMPLEMENT_TMPDIR/ship-pr-state.sh" ]; then
  _RUN_ID=$(grep '^RUN_ID=' "$IMPLEMENT_TMPDIR/ship-pr-state.sh" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r')
fi
if [ -z "$_RUN_ID" ] && [ -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then
  _RUN_ID=$(grep '^RUN_ID=' "$IMPLEMENT_TMPDIR/finalize-state.sh" 2>/dev/null | tail -n 1 | cut -d= -f2- | tr -d '\r')
fi
if [ -z "$_RUN_ID" ]; then
  _RUN_ID=$(tr -d '\r\n' <"$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)
fi
_oos_ndjson=""
if [ -n "$_RUN_ID" ]; then
  _oos_ndjson="$IMPLEMENT_TMPDIR/larch-logs/implement/$_RUN_ID/oos-issues.ndjson"
fi
if [ -z "$_RUN_ID" ]; then
  _oos_list=$(find "$IMPLEMENT_TMPDIR/larch-logs/implement" -mindepth 2 -maxdepth 2 -name oos-issues.ndjson -type f 2>/dev/null | LC_ALL=C sort || true)
  _oos_n=$(printf '%s\n' "$_oos_list" | sed '/^$/d' | wc -l | tr -d '[:space:]')
  if [ "${_oos_n:-0}" -eq 1 ]; then
    _oos_ndjson=$(printf '%s\n' "$_oos_list" | sed '/^$/d' | head -n 1)
  elif [ "${_oos_n:-0}" -gt 1 ]; then
    fail_validation 'implement: ambiguous oos-issues.ndjson without session-id; cannot pass --oos-issues-ndjson'
  fi
fi

_design_tmpdir="${DESIGN_TMPDIR_ARG:-${DESIGN_TMPDIR:-}}"
_oos_design_path="$IMPLEMENT_TMPDIR/oos-accepted-design.md"
if [ -n "$_design_tmpdir" ] && [ -f "$_design_tmpdir/oos-accepted-design.md" ]; then
  _oos_design_path="$_design_tmpdir/oos-accepted-design.md"
elif [ -f "$IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md" ]; then
  _oos_design_path="$IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md"
fi

_oos_accepted_csv="$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md,$_oos_design_path,$IMPLEMENT_TMPDIR/oos-accepted-review.md"
_non_sec_oos=0
_oos_blk_awk="$SCRIPT_DIR/oos-non-security-block-count.awk"
while IFS= read -r _acc; do
  [ -z "$_acc" ] && continue
  [ -f "$_acc" ] || continue
  _n=$(awk -f "$_oos_blk_awk" "$_acc" 2>/dev/null | tr -d '[:space:]' || printf '0')
  _non_sec_oos=$((_non_sec_oos + _n))
done <<EOF
$(printf '%s' "$_oos_accepted_csv" | tr ',' '\n')
EOF

if [ "${_forked:-false}" != "true" ] && [ "${_repo_unavail:-false}" != "true" ]; then
  if [ "${_non_sec_oos:-0}" -gt 0 ]; then
    if [ -z "$_oos_ndjson" ] || [ ! -f "$_oos_ndjson" ]; then
      fail_validation 'implement: non-security accepted OOS requires a resolved oos-issues.ndjson path for disposition gate (--oos-issues-ndjson); batch missing or undiscoverable'
    fi
  fi
fi

_gate_extra=()
[ "${_forked:-false}" = "true" ] && _gate_extra+=(--fork-mode)
[ "${_repo_unavail:-false}" = "true" ] && _gate_extra+=(--repo-unavailable)
if [ -n "$_oos_ndjson" ] && [ -f "$_oos_ndjson" ]; then
  _gate_extra+=(--oos-issues-ndjson "$_oos_ndjson")
fi

: >"$_gate_log" 2>/dev/null || true
set +e
"$SCRIPT_DIR/oos-disposition-gate.sh" \
  "${_gate_extra[@]+"${_gate_extra[@]}"}" \
  --accepted-files "$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md,$_oos_design_path,$IMPLEMENT_TMPDIR/oos-accepted-review.md" \
  --filed-urls-file "$IMPLEMENT_TMPDIR/oos-issues-created.md" \
  --filed-urls-strict-file "$_oos_design_path" \
  --commit-range "$_oos_range" 2>"$_gate_log"
_oos_gate_rc=$?
set -e

if [ "$_oos_gate_rc" -eq 0 ]; then
  exit 0
fi
if [ "$_oos_gate_rc" -eq 1 ]; then
  log_checkpoint_failure 1 step-8-oos-checkpoint "$_gate_log"
fi
if [ "$_oos_gate_rc" -eq 2 ]; then
  log_checkpoint_failure 2 step-8-oos-checkpoint-validation "$_gate_log"
fi
log_checkpoint_failure "$_oos_gate_rc" step-8-oos-checkpoint-validation "$_gate_log"
