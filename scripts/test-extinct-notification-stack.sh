#!/usr/bin/env bash
# test-extinct-notification-stack.sh — ensure the retired notification guard stack stays removed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

check_absent() {
  local token="$1" label="$2" tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/larch-extinct.XXXXXX")
  if git grep -n -F -- "$token" -- . ':!larch-logs' ':!docs/workflow-lifecycle.md' >"$tmp"; then
    cat "$tmp" >&2
    rm -f "$tmp"
    fail "$label is extinct outside larch-logs"
  fi
  rm -f "$tmp"
}

check_absent "hook-bg-poll-""guard" 'bg poll guard hook'
check_absent "hook-no-progress-""guard" 'no-progress guard hook'
check_absent ".bg-wait-""active" 'bg wait marker'
check_absent "no-progress-turns"".count" 'no-progress sidecar'
check_absent "no-progress-circuit-""breaker-armed" 'no-progress circuit sidecar'
check_absent "no-progress-stop-""block-emitted" 'no-progress stop sidecar'
check_absent "no-progress-task-output-""clamped" 'no-progress clamp sidecar'
check_absent "bg-poll-guard-task-output-""read." 'task-output poll counter'
check_absent "bg-poll-guard-probe-""denials." 'probe-denial poll counter'
check_absent ".step3-terminal-persisted-""this-run" 'Step 3 terminal sidecar'
check_absent "design-background-""wait" 'retired design wait doc'
check_absent "task-""notification" 'Claude background notification token'
check_absent "step-3-""terminal" 'retired Step 3 terminal sentinel'
check_absent "step-5c-""terminal" 'retired Step 5c terminal sentinel'
check_absent "step-5-""terminal" 'retired Step 5 terminal sentinel'
check_absent "step-5-resume-""terminal" 'retired Step 5 resume terminal sentinel'
check_absent "step-5-self-review-""terminal" 'retired self-review terminal sentinel'
check_absent "step-6-""terminal" 'retired Step 6 terminal sentinel'
check_absent "step-7a-""terminal" 'retired Step 7a terminal sentinel'
check_absent "lint-bg-wait-writer-""parity" 'retired writer parity lint'
check_absent "test-implement-anti-polling-""rule" 'retired anti-polling harness'
check_absent "test-hook-clone-ownership-""parity" 'retired clone ownership harness'

pass 'retired notification guard stack tokens are absent'
