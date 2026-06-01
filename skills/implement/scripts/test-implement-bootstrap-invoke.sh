#!/usr/bin/env bash
# test-implement-bootstrap-invoke.sh — offline harness for implement-bootstrap-invoke.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REAL_WRAPPER="$REPO_ROOT/scripts/implement-bootstrap-invoke.sh"
REAL_REDACT_SECRETS="$REPO_ROOT/scripts/redact-secrets.sh"
REAL_REDACT_TMPDIR="$REPO_ROOT/scripts/redact-tmpdir-paths.sh"
REAL_LIB_QUIET="$REPO_ROOT/scripts/lib-quiet.sh"

[ -x "$REAL_WRAPPER" ] || { echo "FAIL: $REAL_WRAPPER not executable"; exit 1; }

PASS=0
FAIL=0

assert_contains() {
  local needle=$1 haystack=$2 label=$3
  if printf '%s' "$haystack" | grep -qF -- "$needle"; then
    PASS=$((PASS + 1))
    echo "PASS: $label"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $label"
    echo "  expected to contain: $needle"
    printf '%s\n' "$haystack" | sed 's/^/    /'
  fi
}

assert_not_contains() {
  local needle=$1 haystack=$2 label=$3
  if printf '%s' "$haystack" | grep -qF -- "$needle"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: $label"
    echo "  did not expect: $needle"
  else
    PASS=$((PASS + 1))
    echo "PASS: $label"
  fi
}

assert_rc() {
  local actual=$1 expected=$2 label=$3
  if [ "$actual" -eq "$expected" ]; then
    PASS=$((PASS + 1))
    echo "PASS: $label"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $label (expected rc=$expected got rc=$actual)"
  fi
}

assert_empty() {
  local value=$1 label=$2
  if [ -z "$value" ]; then
    PASS=$((PASS + 1))
    echo "PASS: $label"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $label"
    printf '%s\n' "$value" | sed 's/^/    /'
  fi
}

build_sandbox() {
  SANDBOX=$(mktemp -d /tmp/larch-ibi-test.XXXXXX)
  mkdir -p "$SANDBOX/scripts"
  cp "$REAL_WRAPPER" "$SANDBOX/scripts/implement-bootstrap-invoke.sh"
  cp "$REAL_REDACT_SECRETS" "$SANDBOX/scripts/redact-secrets.sh"
  cp "$REAL_REDACT_TMPDIR" "$SANDBOX/scripts/redact-tmpdir-paths.sh"
  cp "$REAL_LIB_QUIET" "$SANDBOX/scripts/lib-quiet.sh"
  chmod +x "$SANDBOX/scripts/"*.sh

  cat >"$SANDBOX/scripts/implement-bootstrap.sh" <<'STUB'
#!/usr/bin/env bash
printf 'stub argv: %s\n' "$*" >>"${STUB_LOG:-/dev/null}"
printf 'stub-env IMPLEMENT_TMPDIR=%s\n' "${IMPLEMENT_TMPDIR:-}" >>"${STUB_LOG:-/dev/null}"
case "${STUB_MODE:-success}" in
  success)
    printf 'IMPLEMENT_TMPDIR=%s\n' "${STUB_TMPDIR:-/tmp/larch-stub-tmpdir}"
    printf 'IMPLEMENT_BAIL_REASON=\n'
    printf 'STALL_TRACKING=false\n'
    printf 'PLAN_FILE=%s/plan.txt\n' "${STUB_TMPDIR:-/tmp/larch-stub-tmpdir}"
    printf 'coder=codex\n'
    printf 'coder_fallback=false\n'
    printf 'REPO_UNAVAILABLE=false\n'
    printf 'DEFERRED=false\n'
    printf 'ISSUE_NUMBER=42\n'
    printf 'REPO=owner/repo\n'
    printf 'CODEX_PRESENT=true\n'
    printf 'CURSOR_PRESENT=true\n'
    printf 'CODEX_BINARY_FOUND=true\n'
    printf 'CURSOR_BINARY_FOUND=true\n'
    printf 'codex_available=true\n'
    printf 'cursor_available=true\n'
    printf 'RUN_ID=stub-run\n'
    printf 'BRANCH_NAME=feature/stub\n'
    printf 'BRANCH_ACTION=created\n'
  ;;
  exit2)
    printf 'IMPLEMENT_TMPDIR=%s\n' "${STUB_TMPDIR:-/tmp/larch-stub-tmpdir}"
    printf 'STEP_FAILED=%s\n' "${STUB_STEP_FAILED:-session-setup}"
    [ -n "${STUB_GATE_ERROR:-}" ] && printf 'GATE_ERROR=%s\n' "$STUB_GATE_ERROR"
    [ -n "${STUB_PREFLIGHT_ERROR:-}" ] && printf 'PREFLIGHT_ERROR=%s\n' "$STUB_PREFLIGHT_ERROR"
    exit 2
    ;;
  *)
    exit 1
    ;;
esac
STUB
  chmod +x "$SANDBOX/scripts/implement-bootstrap.sh"
}

run_wrapper() {
  (
    cd "$SANDBOX"
    export CLAUDE_PLUGIN_ROOT="$SANDBOX"
    export STUB_LOG="$SANDBOX/stub-invoke.log"
    "$@"
  )
}

run_exit2_case() {
  local step=$1 label=$2 expected=$3
  build_sandbox
  STUB_TMPDIR=$(mktemp -d /tmp/larch-ibi-exit2.XXXXXX)
  export STUB_TMPDIR
  export STUB_MODE=exit2
  export STUB_STEP_FAILED="$step"
  stderr_file=$(mktemp /tmp/larch-ibi-stderr.XXXXXX)
  stdout_file=$(mktemp /tmp/larch-ibi-stdout.XXXXXX)
  set +e
  run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode initial >"$stdout_file" 2>"$stderr_file"
  rc=$?
  set -e
  assert_rc "$rc" 2 "$label rc"
  stderr=$(cat "$stderr_file")
  stdout=$(cat "$stdout_file")
  assert_contains "$expected" "$stderr" "$label message on stderr"
  assert_empty "$stdout" "$label stdout empty"
  rm -f "$stderr_file" "$stdout_file"
  rm -rf "$SANDBOX" "$STUB_TMPDIR"
  unset STUB_TMPDIR STUB_MODE STUB_STEP_FAILED STUB_GATE_ERROR STUB_PREFLIGHT_ERROR
}

# --- initial mode argv ---
build_sandbox
export coder=codex
export RUN_ID=run-1
export PREFLIGHT_TMPDIR=/tmp/preflight-1
export TARGET_ISSUE_NUMBER=99
export CALLER_ENV_PATH=/tmp/caller-env-test
export emergency_requested=true
export forked_target=true
export UPSTREAM_REPO=up/repo
STUB_TMPDIR=$(mktemp -d /tmp/larch-ibi-tmp.XXXXXX)
export STUB_TMPDIR
out=$(run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode initial 2>/dev/null) || true
stub_log=$(cat "$SANDBOX/stub-invoke.log" 2>/dev/null || true)
assert_contains '--up-to-phase coder' "$stub_log" 'initial mode uses coder phase'
assert_contains '--coder codex' "$stub_log" 'initial mode passes --coder when set'
assert_not_contains '--resume-plan-tail' "$stub_log" 'initial mode omits resume tail'
assert_contains '--caller-env' "$stub_log" 'initial wires caller-env when set'
assert_contains '--issue-number 99' "$stub_log" 'initial wires issue number'
assert_contains '--forked-target true' "$stub_log" 'initial wires forked target'
assert_contains '--upstream-repo up/repo' "$stub_log" 'initial wires upstream repo'
assert_contains '--run-id run-1' "$stub_log" 'initial wires run id'
assert_contains '--preflight-tmpdir /tmp/preflight-1' "$stub_log" 'initial wires preflight tmpdir'
assert_contains '--emergency-requested true' "$stub_log" 'initial wires emergency flag'
assert_contains 'IMPLEMENT_TMPDIR=' "$out" 'initial stdout envelope has IMPLEMENT_TMPDIR'
assert_contains 'REPO=owner/repo' "$out" 'initial stdout envelope has REPO'
assert_contains 'CODEX_PRESENT=true' "$out" 'initial stdout envelope has presence keys'
[ -f "$STUB_TMPDIR/bootstrap-routing.env" ] && assert_contains 'BRANCH_NAME=feature/stub' "$(cat "$STUB_TMPDIR/bootstrap-routing.env")" 'routing env file has BRANCH_NAME'
rm -rf "$SANDBOX" "$STUB_TMPDIR"

# --- initial mode omits unset coder ---
build_sandbox
unset coder
STUB_TMPDIR=$(mktemp -d /tmp/larch-ibi-tmp.XXXXXX)
export STUB_TMPDIR
out=$(run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode initial 2>/dev/null) || true
stub_log=$(cat "$SANDBOX/stub-invoke.log" 2>/dev/null || true)
assert_contains '--up-to-phase coder' "$stub_log" 'initial mode still uses coder phase when coder unset'
assert_not_contains '--coder' "$stub_log" 'initial mode omits --coder when unset'
assert_contains 'IMPLEMENT_TMPDIR=' "$out" 'initial unset coder stdout envelope has IMPLEMENT_TMPDIR'
rm -rf "$SANDBOX" "$STUB_TMPDIR"

# --- resume mode argv + IMPLEMENT_TMPDIR pass-through ---
build_sandbox
RESUME_TMP=$(mktemp -d /tmp/larch-ibi-resume.XXXXXX)
mkdir -p "$RESUME_TMP"
touch "$RESUME_TMP/session-env.sh"
export IMPLEMENT_TMPDIR="$RESUME_TMP"
export STUB_TMPDIR="$RESUME_TMP"
unset coder
out=$(run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode resume 2>/dev/null) || true
stub_log=$(cat "$SANDBOX/stub-invoke.log" 2>/dev/null || true)
assert_contains '--up-to-phase plan' "$stub_log" 'resume mode uses plan phase'
assert_contains '--resume-plan-tail' "$stub_log" 'resume mode passes resume tail'
assert_not_contains '--coder' "$stub_log" 'resume mode omits --coder'
assert_contains "stub-env IMPLEMENT_TMPDIR=$RESUME_TMP" "$stub_log" 'resume passes IMPLEMENT_TMPDIR to stub env'
assert_contains "IMPLEMENT_TMPDIR=$RESUME_TMP" "$out" 'resume envelope includes IMPLEMENT_TMPDIR'
rm -rf "$SANDBOX" "$RESUME_TMP"

# --- handled exit 2 cases: stderr / empty stdout ---
export STUB_GATE_ERROR=contract-breach
run_exit2_case session-entry-gate 'session-entry-gate exit 2' 'internal Step 0 contract violation'
export STUB_PREFLIGHT_ERROR=dirty-main
run_exit2_case session-setup 'session-setup exit 2' '/implement requires clean main to start'
run_exit2_case get-issue-state 'get-issue-state exit 2' 'could not verify the adopted issue state'
run_exit2_case issue-number-required-for-resume 'issue-number-required-for-resume exit 2' '--issue-number is required to resume an adopted tracking sentinel'
run_exit2_case resume-plan-tail-sentinel 'resume-plan-tail-sentinel exit 2' 'resume tail could not validate tracking state'

# --- copy-plan exit 2 redaction pipe ---
build_sandbox
STUB_TMPDIR=$(mktemp -d /tmp/larch-implement-copy.XXXXXX)
printf 'copy failed with sk-abcdefghijklmnopqrstuvwxyz123456 at %s/private\n' "$STUB_TMPDIR" >"$STUB_TMPDIR/copy-plan.stderr.log"
export STUB_TMPDIR STUB_MODE=exit2 STUB_STEP_FAILED=copy-plan
stderr_file=$(mktemp /tmp/larch-ibi-stderr.XXXXXX)
stdout_file=$(mktemp /tmp/larch-ibi-stdout.XXXXXX)
set +e
run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode initial >"$stdout_file" 2>"$stderr_file"
rc=$?
set -e
stderr=$(cat "$stderr_file")
stdout=$(cat "$stdout_file")
assert_rc "$rc" 2 'copy-plan exit 2 rc'
assert_contains 'could not copy the preflight plan' "$stderr" 'copy-plan operator message'
assert_contains '<REDACTED-TOKEN>' "$stderr" 'copy-plan redacts token'
assert_contains '<TMPDIR>' "$stderr" 'copy-plan redacts tmpdir path'
assert_not_contains 'sk-abcdefghijklmnopqrstuvwxyz123456' "$stderr" 'copy-plan suppresses raw token'
assert_not_contains "$STUB_TMPDIR" "$stderr" 'copy-plan suppresses raw tmpdir path'
assert_empty "$stdout" 'copy-plan stdout empty'
rm -f "$stderr_file" "$stdout_file"
rm -rf "$SANDBOX" "$STUB_TMPDIR"
unset STUB_TMPDIR STUB_MODE STUB_STEP_FAILED

# --- gh-issue-view exit 2 redaction pipe ---
build_sandbox
STUB_TMPDIR=$(mktemp -d /tmp/larch-implement-gh.XXXXXX)
printf 'gh failed with ghp_abcdefghijklmnopqrstuvwxyz123456 at %s/issue\n' "$STUB_TMPDIR" >"$STUB_TMPDIR/gh-issue-view.stderr.log"
export STUB_TMPDIR STUB_MODE=exit2 STUB_STEP_FAILED=gh-issue-view
stderr_file=$(mktemp /tmp/larch-ibi-stderr.XXXXXX)
stdout_file=$(mktemp /tmp/larch-ibi-stdout.XXXXXX)
set +e
run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode initial >"$stdout_file" 2>"$stderr_file"
rc=$?
set -e
stderr=$(cat "$stderr_file")
stdout=$(cat "$stdout_file")
assert_rc "$rc" 2 'gh-issue-view exit 2 rc'
assert_contains 'could not read the issue title/body' "$stderr" 'gh-issue-view operator message'
assert_contains '<REDACTED-TOKEN>' "$stderr" 'gh-issue-view redacts token'
assert_contains '<TMPDIR>' "$stderr" 'gh-issue-view redacts tmpdir path'
assert_not_contains 'ghp_abcdefghijklmnopqrstuvwxyz123456' "$stderr" 'gh-issue-view suppresses raw token'
assert_not_contains "$STUB_TMPDIR" "$stderr" 'gh-issue-view suppresses raw tmpdir path'
assert_empty "$stdout" 'gh-issue-view stdout empty'
rm -f "$stderr_file" "$stdout_file"
rm -rf "$SANDBOX" "$STUB_TMPDIR"
unset STUB_TMPDIR STUB_MODE STUB_STEP_FAILED

# --- usage errors ---
build_sandbox
set +e
run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode bogus >/dev/null 2>&1
rc=$?
set -e
assert_rc "$rc" 1 'invalid mode usage exit'
rm -rf "$SANDBOX"

build_sandbox
set +e
run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" >/dev/null 2>&1
rc=$?
set -e
assert_rc "$rc" 1 'absent mode usage exit'
rm -rf "$SANDBOX"

build_sandbox
set +e
run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode >/dev/null 2>&1
rc=$?
set -e
assert_rc "$rc" 1 'missing mode value usage exit'
rm -rf "$SANDBOX"

build_sandbox
unset IMPLEMENT_TMPDIR
set +e
run_wrapper "$SANDBOX/scripts/implement-bootstrap-invoke.sh" --mode resume >/dev/null 2>&1
rc=$?
set -e
assert_rc "$rc" 1 'resume without IMPLEMENT_TMPDIR usage exit'
rm -rf "$SANDBOX"

# --- NEVER #14 ---
# shellcheck disable=SC2016 # literal source grep, not shell.
if grep -Fq '>> "$IMPLEMENT_TMPDIR/session-env.sh"' "$REAL_WRAPPER"; then
  FAIL=$((FAIL + 1))
  echo "FAIL: NEVER14 append redirect in wrapper"
else
  PASS=$((PASS + 1))
  echo "PASS: NEVER14 no session-env append"
fi
# shellcheck disable=SC2016
if grep -Fq 'cat > "$IMPLEMENT_TMPDIR/session-env.sh"' "$REAL_WRAPPER"; then
  FAIL=$((FAIL + 1))
  echo "FAIL: NEVER14 heredoc redirect in wrapper"
else
  PASS=$((PASS + 1))
  echo "PASS: NEVER14 no session-env heredoc"
fi

# --- wrapper routing key set in source ---
_wrapper_src=$(cat "$REAL_WRAPPER")
assert_contains 'BRANCH_NAME' "$_wrapper_src" 'wrapper source includes BRANCH_NAME routing key'
assert_contains 'PLAN_FILE' "$_wrapper_src" 'wrapper source includes PLAN_FILE routing key'
assert_contains 'coder_fallback' "$_wrapper_src" 'wrapper source includes coder_fallback routing key'

echo "---"
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
