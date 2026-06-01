#!/usr/bin/env bash
# parse-bootstrap-routing-envelope.sh — shared /implement Step 0 routing envelope parse.
#
# Source after implement-bootstrap-invoke.sh succeeds (_inv_rc=0). Requires _inv_out
# (wrapper stdout capture). Optional IMPLEMENT_TMPDIR may be preset.
#
#   . "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh"
#   . "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh" --preserve-coder
#
# File-first: $IMPLEMENT_TMPDIR/bootstrap-routing.env when a regular file (symlinks skipped).
# Stdout fallback fills keys still empty after file parse.

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  printf '%s\n' 'parse-bootstrap-routing-envelope.sh: source this script; do not execute directly' >&2
  exit 1
fi

_preserve_coder=false
while [ $# -gt 0 ]; do
  case "$1" in
    --preserve-coder)
      _preserve_coder=true
      shift
      ;;
    *)
      printf '%s\n' "parse-bootstrap-routing-envelope.sh: unknown argument: $1" >&2
      return 1
      ;;
  esac
done

_inv_routing_keys='IMPLEMENT_TMPDIR IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback REPO_UNAVAILABLE DEFERRED ISSUE_NUMBER REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION'

_inv_routing_key_allowed() {
  _inv_key=$1
  [ -n "$_inv_key" ] || return 1
  case "$_inv_key" in
    *[!a-zA-Z0-9_]*)
      return 1
      ;;
  esac
  case " $_inv_routing_keys " in
    *" $_inv_key "*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ "$_preserve_coder" = true ]; then
  unset IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE REPO_UNAVAILABLE DEFERRED REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION
else
  unset IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback REPO_UNAVAILABLE DEFERRED REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION
fi

IMPLEMENT_TMPDIR=$(printf '%s\n' "${_inv_out:-}" | grep '^IMPLEMENT_TMPDIR=' | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)

_inv_apply_routing_line() {
  [ -z "$_inv_line" ] && return 0
  _inv_key="${_inv_line%%=*}"
  _inv_value="${_inv_line#*=}"
  _inv_routing_key_allowed "$_inv_key" || return 0
  if [ "$_preserve_coder" = true ]; then
    case "$_inv_key" in
      coder|coder_fallback) return 0 ;;
    esac
  fi
  case "$_inv_key" in
    coder|coder_fallback) [ -n "$_inv_value" ] || return 0 ;;
  esac
  printf -v "$_inv_key" '%s' "$_inv_value"
}

_inv_apply_routing_line_if_empty() {
  [ -z "$_inv_line" ] && return 0
  _inv_key="${_inv_line%%=*}"
  _inv_value="${_inv_line#*=}"
  _inv_routing_key_allowed "$_inv_key" || return 0
  if [ "$_preserve_coder" = true ]; then
    case "$_inv_key" in
      coder|coder_fallback) return 0 ;;
    esac
  fi
  case "$_inv_key" in
    coder|coder_fallback) [ -n "$_inv_value" ] || return 0 ;;
  esac
  case "$_inv_key" in
    IMPLEMENT_TMPDIR) [ -z "${IMPLEMENT_TMPDIR:-}" ] && IMPLEMENT_TMPDIR="$_inv_value" ;;
    IMPLEMENT_BAIL_REASON) [ -z "${IMPLEMENT_BAIL_REASON:-}" ] && IMPLEMENT_BAIL_REASON="$_inv_value" ;;
    STALL_TRACKING) [ -z "${STALL_TRACKING:-}" ] && STALL_TRACKING="$_inv_value" ;;
    PLAN_FILE) [ -z "${PLAN_FILE:-}" ] && PLAN_FILE="$_inv_value" ;;
    REPO_UNAVAILABLE) [ -z "${REPO_UNAVAILABLE:-}" ] && REPO_UNAVAILABLE="$_inv_value" ;;
    DEFERRED) [ -z "${DEFERRED:-}" ] && DEFERRED="$_inv_value" ;;
    ISSUE_NUMBER) [ -z "${ISSUE_NUMBER:-}" ] && ISSUE_NUMBER="$_inv_value" ;;
    REPO) [ -z "${REPO:-}" ] && REPO="$_inv_value" ;;
    CODEX_PRESENT) [ -z "${CODEX_PRESENT:-}" ] && CODEX_PRESENT="$_inv_value" ;;
    CURSOR_PRESENT) [ -z "${CURSOR_PRESENT:-}" ] && CURSOR_PRESENT="$_inv_value" ;;
    CODEX_BINARY_FOUND) [ -z "${CODEX_BINARY_FOUND:-}" ] && CODEX_BINARY_FOUND="$_inv_value" ;;
    CURSOR_BINARY_FOUND) [ -z "${CURSOR_BINARY_FOUND:-}" ] && CURSOR_BINARY_FOUND="$_inv_value" ;;
    codex_available) [ -z "${codex_available:-}" ] && codex_available="$_inv_value" ;;
    cursor_available) [ -z "${cursor_available:-}" ] && cursor_available="$_inv_value" ;;
    RUN_ID) [ -z "${RUN_ID:-}" ] && RUN_ID="$_inv_value" ;;
    BRANCH_NAME) [ -z "${BRANCH_NAME:-}" ] && BRANCH_NAME="$_inv_value" ;;
    BRANCH_ACTION) [ -z "${BRANCH_ACTION:-}" ] && BRANCH_ACTION="$_inv_value" ;;
  esac
}

if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/bootstrap-routing.env" ] && [ ! -L "$IMPLEMENT_TMPDIR/bootstrap-routing.env" ]; then
  while IFS= read -r _inv_line || [ -n "$_inv_line" ]; do
    _inv_apply_routing_line
  done <"$IMPLEMENT_TMPDIR/bootstrap-routing.env"
fi
while IFS= read -r _inv_line || [ -n "$_inv_line" ]; do
  _inv_apply_routing_line_if_empty
done <<EOF
$(printf '%s\n' "${_inv_out:-}")
EOF
export IMPLEMENT_TMPDIR IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback REPO_UNAVAILABLE DEFERRED ISSUE_NUMBER REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION
