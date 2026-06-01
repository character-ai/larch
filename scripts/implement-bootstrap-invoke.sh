#!/usr/bin/env bash
# implement-bootstrap-invoke.sh — /implement Step 0 bootstrap wrapper (initial + resume).

set -euo pipefail

usage() {
  printf 'Usage: %s --mode initial|resume\n' "${0##*/}" >&2
  exit 1
}

MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      [ $# -ge 2 ] || usage
      MODE=$2
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

case "$MODE" in
  initial|resume) ;;
  *)
    usage
    ;;
esac

: "${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT must be set}"

if [ "$MODE" = resume ]; then
  [ -n "${IMPLEMENT_TMPDIR:-}" ] || {
    printf '%s\n' 'implement-bootstrap-invoke.sh: --mode resume requires exported IMPLEMENT_TMPDIR' >&2
    exit 1
  }
  export IMPLEMENT_TMPDIR
fi

_ib_caller_env=()
if [ -n "${CALLER_ENV_PATH:-}" ]; then
  _ib_caller_env+=(--caller-env "$CALLER_ENV_PATH")
elif [ -n "${SESSION_ENV_PATH:-}" ]; then
  _ib_caller_env+=(--caller-env "$SESSION_ENV_PATH")
fi

_ib_issue=()
_ib_target_issue="${TARGET_ISSUE_NUMBER:-${ISSUE_NUMBER:-}}"
[ -n "$_ib_target_issue" ] && _ib_issue+=(--issue-number "$_ib_target_issue")

_ib_fork=()
if [ "${forked_target:-false}" = "true" ]; then
  _ib_fork+=(--forked-target true)
  [ -n "${UPSTREAM_REPO:-}" ] && _ib_fork+=(--upstream-repo "$UPSTREAM_REPO")
fi

_ib_run_id=()
[ -n "${RUN_ID:-}" ] && _ib_run_id+=(--run-id "$RUN_ID")

_ib_preflight=()
[ -n "${PREFLIGHT_TMPDIR:-}" ] && _ib_preflight+=(--preflight-tmpdir "$PREFLIGHT_TMPDIR")

_ib_emergency=()
case "${emergency_requested:-}" in
  true|false) _ib_emergency+=(--emergency-requested "$emergency_requested") ;;
esac

_phase_args=()
case "$MODE" in
  initial)
    _phase_args=(--up-to-phase coder)
    [ -n "${coder:-}" ] && _phase_args+=(--coder "$coder")
    ;;
  resume)
    _phase_args=(--up-to-phase plan --resume-plan-tail)
    ;;
esac

set +e
_ib_out=$("${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap.sh" "${_phase_args[@]}" "${_ib_caller_env[@]+"${_ib_caller_env[@]}"}" "${_ib_issue[@]+"${_ib_issue[@]}"}" "${_ib_fork[@]+"${_ib_fork[@]}"}" "${_ib_run_id[@]+"${_ib_run_id[@]}"}" "${_ib_preflight[@]+"${_ib_preflight[@]}"}" "${_ib_emergency[@]+"${_ib_emergency[@]}"}")
_ib_rc=$?
set -e

if [ "$_ib_rc" -eq 2 ]; then
  _ib_tmpdir=$(printf '%s\n' "$_ib_out" | grep '^IMPLEMENT_TMPDIR=' | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)
  [ -n "$_ib_tmpdir" ] && IMPLEMENT_TMPDIR=$_ib_tmpdir
  _ib_sf=$(printf '%s\n' "$_ib_out" | grep '^STEP_FAILED=' | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)
  # shellcheck disable=SC2016 # operator-facing literals; backticks are markdown, not shell.
  case "$_ib_sf" in
    session-entry-gate)
      { printf '%s\n' "$_ib_out" | grep '^GATE_ERROR=' || true; printf '%s\n' '**⚠ /implement: internal Step 0 contract violation in session-entry-gate.sh. Aborting.**'; } >&2
      ;;
    session-setup)
      { printf '%s\n' "$_ib_out" | grep '^PREFLIGHT_ERROR=' || true; printf '%s\n' '**⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run; (c) commit or stash uncommitted changes on `main` first.**'; } >&2
      ;;
    get-issue-state)
      { printf '%s\n' "$_ib_out" | grep '^STEP_FAILED=' || true; printf '%s\n' '**⚠ /implement Step 0 tracking: could not verify the adopted issue state. Aborting.**'; } >&2
      ;;
    issue-number-required-for-resume)
      { printf '%s\n' "$_ib_out" | grep '^STEP_FAILED=' || true; printf '%s\n' '**⚠ /implement Step 0 tracking: --issue-number is required to resume an adopted tracking sentinel. Re-run `/implement <issue-N>` for the sentinel'\''s issue.**'; } >&2
      ;;
    copy-plan)
      if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/copy-plan.stderr.log" ]; then
        _ib_redacted_err=$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-copy-plan.XXXXXX")
        if "${CLAUDE_PLUGIN_ROOT}/scripts/redact-secrets.sh" <"$IMPLEMENT_TMPDIR/copy-plan.stderr.log" | "${CLAUDE_PLUGIN_ROOT}/scripts/redact-tmpdir-paths.sh" >"$_ib_redacted_err"; then
          cat "$_ib_redacted_err" >&2
        else
          printf '%s\n' '**⚠ /implement Step 0 plan materialization: copy-plan stderr redaction failed; raw stderr suppressed. See execution issues / local logs.**' >&2
        fi
        rm -f "$_ib_redacted_err"
      fi
      printf '%s\n' '**⚠ /implement Step 0 plan materialization: could not copy the preflight plan into the implement session. Aborting.**' >&2
      ;;
    gh-issue-view)
      if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/gh-issue-view.stderr.log" ]; then
        _ib_redacted_err=$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-gh-issue-view.XXXXXX")
        if "${CLAUDE_PLUGIN_ROOT}/scripts/redact-secrets.sh" <"$IMPLEMENT_TMPDIR/gh-issue-view.stderr.log" | "${CLAUDE_PLUGIN_ROOT}/scripts/redact-tmpdir-paths.sh" >"$_ib_redacted_err"; then
          cat "$_ib_redacted_err" >&2
        else
          printf '%s\n' '**⚠ /implement Step 0 plan materialization: gh-issue-view stderr redaction failed; raw stderr suppressed. See execution issues / local logs.**' >&2
        fi
        rm -f "$_ib_redacted_err"
      fi
      printf '%s\n' '**⚠ /implement Step 0 plan materialization: could not read the issue title/body. Aborting.**' >&2
      ;;
    resume-plan-tail-sentinel)
      { printf '%s\n' "$_ib_out" | grep '^STEP_FAILED=' || true; printf '%s\n' '**⚠ /implement Step 0 dirty-tree recovery: the resume tail could not validate tracking state from the existing session artifacts. Restore or inspect `$IMPLEMENT_TMPDIR`, then restart `/implement`.**'; } >&2
      ;;
  esac
  exit 2
fi

if [ "$_ib_rc" -ne 0 ]; then
  exit "$_ib_rc"
fi

_inv_routing_keys='IMPLEMENT_TMPDIR IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback REPO_UNAVAILABLE DEFERRED ISSUE_NUMBER REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION'

_inv_emit_routing_kv() {
  _inv_line=$1
  [ -z "$_inv_line" ] && return 0
  _inv_key="${_inv_line%%=*}"
  _inv_value="${_inv_line#*=}"
  case " $_inv_routing_keys " in
    *" $_inv_key "*) printf '%s=%s\n' "$_inv_key" "$_inv_value" ;;
  esac
}

_inv_tmpdir=$(printf '%s\n' "$_ib_out" | grep '^IMPLEMENT_TMPDIR=' | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)
[ -n "$_inv_tmpdir" ] || {
  printf '%s\n' 'implement-bootstrap-invoke.sh: bootstrap success missing IMPLEMENT_TMPDIR' >&2
  exit 1
}

_inv_routing_buf=$(mktemp "${TMPDIR:-/tmp}/implement-bootstrap-routing.XXXXXX")
while IFS= read -r _inv_line || [ -n "$_inv_line" ]; do
  _inv_emit_routing_kv "$_inv_line" >>"$_inv_routing_buf"
done <<EOF
$(printf '%s\n' "$_ib_out")
EOF

cat "$_inv_routing_buf" >"$_inv_tmpdir/bootstrap-routing.env"
cat "$_inv_routing_buf"
rm -f "$_inv_routing_buf"
