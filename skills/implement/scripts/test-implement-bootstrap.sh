#!/usr/bin/env bash
# test-implement-bootstrap.sh — offline harness for scripts/implement-bootstrap.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REAL_SCRIPT="$REPO_ROOT/scripts/implement-bootstrap.sh"

[ -x "$REAL_SCRIPT" ] || { echo "FAIL: $REAL_SCRIPT not executable"; exit 1; }

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
        printf '%s\n' "$haystack" | sed 's/^/    /'
    else
        PASS=$((PASS + 1))
        echo "PASS: $label"
    fi
}

assert_line() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s\n' "$haystack" | grep -qxF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected exact line: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
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

build_sandbox() {
    SANDBOX=$(mktemp -d /tmp/larch-ib-test.XXXXXX)
    mkdir -p "$SANDBOX/scripts" "$SANDBOX/skills/implement/scripts" "$SANDBOX_TMP"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$SANDBOX/scripts/"
    cp "$REPO_ROOT/scripts/lib-execution-issues.sh" "$SANDBOX/scripts/"
    cp "$REAL_SCRIPT" "$SANDBOX/scripts/implement-bootstrap.sh"
    cp "$REPO_ROOT/scripts/write-session-env.sh" "$SANDBOX/scripts/"
    cp "$REPO_ROOT/scripts/read-session-env-key.sh" "$SANDBOX/scripts/"
    chmod +x "$SANDBOX/scripts/implement-bootstrap.sh" "$SANDBOX/scripts/write-session-env.sh" "$SANDBOX/scripts/read-session-env-key.sh"

    cat >"$SANDBOX/scripts/create-branch.sh" <<'STUB'
#!/usr/bin/env bash
echo CURRENT_BRANCH=main
echo IS_MAIN=true
echo IS_USER_BRANCH=false
echo USER_PREFIX=testuser
exit 0
STUB
    chmod +x "$SANDBOX/scripts/create-branch.sh"

    cat >"$SANDBOX/scripts/session-entry-gate.sh" <<'STUB'
#!/usr/bin/env bash
echo ENTRY_GATE=strict
echo SKIP_BRANCH_CHECK=false
exit 0
STUB
    chmod +x "$SANDBOX/scripts/session-entry-gate.sh"

    cat >"$SANDBOX/scripts/write-session-id.sh" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$@" >>"$SANDBOX/invoke-log.txt"
while [ \$# -gt 0 ]; do
  case "\$1" in
    --output) mkdir -p "\$(dirname "\$2")"; printf 'sessstub\\n' > "\$2"; shift 2 ;;
    *) shift ;;
  esac
done
exit 0
STUB
    chmod +x "$SANDBOX/scripts/write-session-id.sh"

    cat >"$SANDBOX/scripts/token-claude-source.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
    chmod +x "$SANDBOX/scripts/token-claude-source.sh"

    cat >"$SANDBOX/scripts/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
log=""
site=""
while [ $# -gt 0 ]; do
  case "$1" in
    --log) log=$2; shift 2 ;;
    --site) site=$2; shift 2 ;;
    *) shift ;;
  esac
done
[ -n "$log" ] && { mkdir -p "$(dirname "$log")"; printf '%s\n' "$site" >> "$log"; }
exit 0
STUB
    chmod +x "$SANDBOX/scripts/append-tool-failure.sh"

    cat >"$SANDBOX/scripts/token-ledger.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'token-ledger %s\n' "$*" >>"$script_dir/../invoke-log.txt"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/token-ledger.sh"

    cat >"$SANDBOX/scripts/timing-ledger.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'timing-ledger %s\n' "$*" >>"$script_dir/../invoke-log.txt"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/timing-ledger.sh"

    cat >"$SANDBOX/scripts/tracking-issue-read.sh" <<'STUB'
#!/usr/bin/env bash
sentinel=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sentinel) sentinel=$2; shift 2 ;;
    *) shift ;;
  esac
done
if [ -z "$sentinel" ] || [ ! -f "$sentinel" ]; then
  echo FAILED=true
  echo ERROR=sentinel-not-found
  exit 1
fi
issue=$(awk -F= '$1=="ISSUE_NUMBER"{print substr($0,index($0,"=")+1); exit}' "$sentinel")
run_id=$(awk -F= '$1=="RUN_ID"{print substr($0,index($0,"=")+1); exit}' "$sentinel")
adopted=$(awk -F= '$1=="ADOPTED"{print substr($0,index($0,"=")+1); exit}' "$sentinel")
case "$adopted" in
  ""|true|false) ;;
  *) echo FAILED=true; echo "ERROR=invalid ADOPTED value"; exit 1 ;;
esac
echo "ISSUE_NUMBER=$issue"
echo "RUN_ID=$run_id"
echo "ADOPTED=$adopted"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/tracking-issue-read.sh"

    cat >"$SANDBOX/scripts/get-issue-state.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${LARCH_TEST_GET_ISSUE_FAILED:-false}" = "true" ]; then
  echo FAILED=true
  echo "ERROR=failed=value"
  exit 1
fi
echo "STATE=${LARCH_TEST_ISSUE_STATE:-OPEN}"
echo "URL=https://example.test/${LARCH_TEST_URL_KIND:-issues}/123"
echo "IS_PR=${LARCH_TEST_IS_PR:-false}"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/get-issue-state.sh"

    cat >"$SANDBOX/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${LARCH_TEST_LARCH_LOG_FAIL:-false}" = "true" ]; then
  echo LOG_WRITTEN=false
  echo LOG_PATH=
  echo BYTES=0
  echo SHA256=
  echo COMMIT_SHA=
  echo UNCHANGED=false
  echo "ERROR=init failed"
  exit 1
fi
run_id=""
log_root=""
skill=""
while [ $# -gt 0 ]; do
  case "$1" in
    --log-root) log_root=$2; shift 2 ;;
    --skill) skill=$2; shift 2 ;;
    --run-id) run_id=$2; shift 2 ;;
    *) shift ;;
  esac
done
path="$log_root/$skill/$run_id/manifest.json"
mkdir -p "$(dirname "$path")"
printf '{}\n' > "$path"
echo LOG_WRITTEN=true
echo "LOG_PATH=$path"
echo BYTES=3
echo SHA256=dummy
echo COMMIT_SHA=
echo UNCHANGED=false
exit 0
STUB
    chmod +x "$SANDBOX/scripts/larch-log.sh"

    cat >"$SANDBOX/skills/implement/scripts/post-tracking-issue.sh" <<'STUB'
#!/usr/bin/env bash
tmpdir=""
issue=""
run_id=""
adopted="true"
while [ $# -gt 0 ]; do
  case "$1" in
    --implement-tmpdir) tmpdir=$2; shift 2 ;;
    --issue-number) issue=$2; shift 2 ;;
    --run-id) run_id=$2; shift 2 ;;
    --adopted) adopted=$2; shift 2 ;;
    *) shift ;;
  esac
done
if [ "${LARCH_TEST_POSTED:-true}" != "true" ]; then
  echo POSTED=false
  echo COMMENT_URL=
  echo "ERROR=post failed"
  exit 1
fi
printf 'ISSUE_NUMBER=%s\nRUN_ID=%s\nADOPTED=%s\n' "$issue" "$run_id" "$adopted" > "$tmpdir/parent-issue.md"
echo POSTED=true
echo COMMENT_URL=https://example.test/comment
exit 0
STUB
    chmod +x "$SANDBOX/skills/implement/scripts/post-tracking-issue.sh"

    cat >"$SANDBOX/scripts/tracking-issue-write.sh" <<'STUB'
#!/usr/bin/env bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'tracking-issue-write %s\n' "$*" >>"$script_dir/../invoke-log.txt"
if [ "${LARCH_TEST_RENAME_FAILED:-false}" = "true" ]; then
  echo FAILED=true
  echo "ERROR=rename failed"
  exit 1
fi
echo RENAMED=true
echo "NEW_TITLE=[IMPLEMENTING] test"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/tracking-issue-write.sh"

    cat >"$SANDBOX/scripts/get-issue-context.sh" <<'STUB'
#!/usr/bin/env bash
tmpdir=""
raw_args="$*"
while [ $# -gt 0 ]; do
  case "$1" in
    --tmpdir) tmpdir=$2; shift 2 ;;
    --issue|--repo) shift 2 ;;
    *) shift ;;
  esac
done
if [ "${GET_ISSUE_CONTEXT_EXIT:-0}" -ne 0 ]; then
  printf 'simulated upstream context failure\n' >&2
  exit "$GET_ISSUE_CONTEXT_EXIT"
fi
mkdir -p "$tmpdir"
printf 'title\n' > "$tmpdir/upstream-issue-title.txt"
printf 'body\n' > "$tmpdir/upstream-issue-body.txt"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf 'get-issue-context %s\n' "$raw_args" >>"$script_dir/../invoke-log.txt"
echo "TITLE_FILE=$tmpdir/upstream-issue-title.txt"
echo "BODY_FILE=$tmpdir/upstream-issue-body.txt"
exit 0
STUB
    chmod +x "$SANDBOX/scripts/get-issue-context.sh"

    : >"$SANDBOX/invoke-log.txt"
}

write_gp1_session_setup() {
    cat >"$SANDBOX/scripts/session-setup.sh" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=owner/repo
echo REPO_UNAVAILABLE=false
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
    chmod +x "$SANDBOX/scripts/session-setup.sh"
}

run_bootstrap() {
    (
        cd "$SANDBOX" || exit 1
        env \
            CLAUDE_PLUGIN_ROOT="$SANDBOX" \
            LARCH_BREADCRUMB_STREAM= \
            LARCH_QUIET_BREADCRUMBS="${LARCH_QUIET_BREADCRUMBS:-}" \
            LARCH_QUIET_BREADCRUMB_FD="${LARCH_QUIET_BREADCRUMB_FD:-}" \
            bash "$SANDBOX/scripts/implement-bootstrap.sh" "$@"
    )
}

SANDBOX_TMP=""
SANDBOX=""

# --- GP1-infra ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP1-infra exit 0"
assert_contains "IMPLEMENT_TMPDIR=$SANDBOX_TMP" "$out" "GP1 IMPLEMENT_TMPDIR"
assert_contains "SESSION_ID=sessstub" "$out" "GP1 SESSION_ID"
assert_contains "codex_available=true" "$out" "GP1 codex_available"
assert_contains "IMPLEMENT_BAIL_REASON=" "$out" "GP1 IMPLEMENT_BAIL_REASON tail present"
assert_not_contains "STEP_FAILED=" "$out" "GP1 no STEP_FAILED"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-adopt ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runA 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-adopt exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "GP-adopt branch"
assert_contains "ISSUE_NUMBER=123" "$out" "GP-adopt issue"
assert_contains "RUN_ID=runA" "$out" "GP-adopt run id"
assert_contains "DEFERRED=false" "$out" "GP-adopt not deferred"
assert_contains "STALL_TRACKING=false" "$out" "GP-adopt no stall"
assert_contains "RUN_ID=runA" "$(cat "$SANDBOX_TMP/parent-issue.md")" "GP-adopt sentinel run id"
assert_contains "FORKED_TARGET=false" "$(cat "$SANDBOX_TMP/session-env.sh")" "GP-adopt session-env fork default"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains 'token-ledger mark Step 0 — tracking issue' "$invoke" "GP-adopt no bootstrap token mark"
assert_not_contains 'timing-ledger mark Step 0 — tracking issue' "$invoke" "GP-adopt no bootstrap timing mark"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-adopt-session-id ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-adopt-session-id exit 0"
assert_contains "RUN_ID=sessstub" "$out" "GP-adopt-session-id run id"
assert_contains "RUN_ID=sessstub" "$(cat "$SANDBOX_TMP/parent-issue.md")" "GP-adopt-session-id sentinel run id"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2 sentinel resume ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume1\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2 exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "GP2 branch"
assert_contains "ISSUE_NUMBER=123" "$out" "GP2 issue"
assert_contains "RUN_ID=resume1" "$out" "GP2 run id"
assert_contains "DEFERRED=false" "$out" "GP2 not deferred"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP3 forked_target ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --forked-target true --upstream-repo upstream/repo 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP3 exit 0"
assert_contains "BRANCH_SELECTED=forked-target-skip" "$out" "GP3 branch"
assert_line "ISSUE_NUMBER=" "$out" "GP3 empty issue"
assert_contains "DEFERRED=true" "$out" "GP3 deferred"
assert_contains "FORKED_TARGET=true" "$(cat "$SANDBOX_TMP/session-env.sh")" "GP3 session-env fork true"
assert_contains "TITLE_FILE=$SANDBOX_TMP/upstream-issue-title.txt" "$(cat "$SANDBOX_TMP/upstream-context.out")" "GP3 upstream title artifact"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_contains 'get-issue-context --issue 123 --repo upstream/repo' "$invoke" "GP3 upstream context invoked"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP3-upstream-context-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
export GET_ISSUE_CONTEXT_EXIT=7
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --forked-target true --upstream-repo upstream/repo 2>/dev/null) && rc=$? || rc=$?
unset GET_ISSUE_CONTEXT_EXIT
assert_rc "$rc" 0 "GP3-upstream-context-fail exit 0"
assert_contains "BRANCH_SELECTED=forked-target-skip" "$out" "GP3-upstream-context-fail branch"
assert_contains "Step 0 tracking adoption — forked target upstream context" "$(cat "$SANDBOX_TMP/execution-issues.md")" "GP3-upstream-context-fail execution issues"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-repo-unavail-tracking ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/scripts/session-setup.sh" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=
echo REPO_UNAVAILABLE=true
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/scripts/session-setup.sh"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-repo-unavail-tracking exit 0"
assert_contains "BRANCH_SELECTED=repo-unavailable-skip" "$out" "GP-repo-unavail-tracking branch"
assert_line "ISSUE_NUMBER=" "$out" "GP-repo-unavail-tracking empty issue"
assert_contains "DEFERRED=true" "$out" "GP-repo-unavail-tracking deferred"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP4 repo_unavailable ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/scripts/session-setup.sh" <<STUB
#!/usr/bin/env bash
echo SESSION_TMPDIR=$SANDBOX_TMP
echo SESSION_ID=sessstub
echo REPO=
echo REPO_UNAVAILABLE=true
echo CODEX_PRESENT=true
echo CURSOR_PRESENT=true
echo CODEX_BINARY_FOUND=true
echo CURSOR_BINARY_FOUND=true
exit 0
STUB
chmod +x "$SANDBOX/scripts/session-setup.sh"
stderrf=$(mktemp "${TMPDIR:-/tmp}/larch-ib-gp4.XXXXXX")
out=$(run_bootstrap --up-to-phase infra 2>"$stderrf") && rc=$? || rc=$?
err=$(cat "$stderrf")
rm -f "$stderrf"
assert_rc "$rc" 0 "GP4 exit 0"
assert_contains "REPO_UNAVAILABLE=true" "$out" "GP4 REPO_UNAVAILABLE in stdout"
assert_contains "**⚠ Could not determine repository name." "$err" "GP4 repo warning on stderr"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B1 sentinel mismatch fall-through ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=999\nRUN_ID=oldrun\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runB 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B1 exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B1 fall-through branch"
assert_contains "RUN_ID=runB" "$out" "B1 fresh run id"
assert_contains "ISSUE_NUMBER=123" "$(cat "$SANDBOX_TMP/parent-issue.md")" "B1 sentinel replaced"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B2 CLOSED bail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_ISSUE_STATE=CLOSED run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B2 exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-closed" "$out" "B2 bail reason"
assert_line "BRANCH_SELECTED=" "$out" "B2 no branch"
assert_line "ISSUE_NUMBER=" "$out" "B2 empty issue tail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B2-plan CLOSED bail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_ISSUE_STATE=CLOSED run_bootstrap --up-to-phase plan --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B2-plan exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-closed" "$out" "B2-plan bail reason"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B2-plan no phase-3 overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B3 IS_PR bail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_IS_PR=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B3 exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=adopted-issue-is-pr" "$out" "B3 bail reason"
assert_line "BRANCH_SELECTED=" "$out" "B3 no branch"
assert_line "ISSUE_NUMBER=" "$out" "B3 empty issue tail"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4 POSTED=false deferred ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=999\nRUN_ID=stale\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runD 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4 exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B4 branch"
assert_contains "DEFERRED=true" "$out" "B4 deferred"
assert_not_contains "STALL_TRACKING=true" "$out" "B4 no stall"
assert_not_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B4 no tracking-init-failed bail"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "tracking-issue-write rename --issue 123 --state implementing" "$invoke" "B4 no rename"
if [ ! -f "$SANDBOX_TMP/parent-issue.md" ]; then
    PASS=$((PASS + 1))
    echo "PASS: B4 no sentinel"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: B4 sentinel should not exist"
fi
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4-plan POSTED=false deferred guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase plan --issue-number 123 --run-id runD 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4-plan exit 0"
assert_contains "DEFERRED=true" "$out" "B4-plan deferred"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B4-plan no phase-3 overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B4-all POSTED=false deferred guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_POSTED=false run_bootstrap --up-to-phase all --issue-number 123 --run-id runD 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B4-all exit 0"
assert_contains "DEFERRED=true" "$out" "B4-all deferred"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B4-all no phase-3 overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-4" "$out" "B4-all no phase-4 overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5 larch-log init fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runE 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5 exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5 bail reason"
assert_contains "STALL_TRACKING=true" "$out" "B5 stall"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B5 branch"
assert_contains "ISSUE_NUMBER=123" "$out" "B5 preserves issue"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-all larch-log init fail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase all --issue-number 123 --run-id runE 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-all exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5-all bail reason"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B5-all no phase-3 overwrite"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-4" "$out" "B5-all no phase-4 overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-plan larch-log init fail guard ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase plan --issue-number 123 --run-id runE 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-plan exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5-plan bail reason"
assert_not_contains "IMPLEMENT_BAIL_REASON=not-yet-implemented-phase-3" "$out" "B5-plan no phase-3 overwrite"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B5-branch1 larch-log init fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume-fail\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_LARCH_LOG_FAIL=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B5-branch1 exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "B5-branch1 branch"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B5-branch1 bail reason"
assert_contains "STALL_TRACKING=true" "$out" "B5-branch1 stall"
assert_contains "RUN_ID=resume-fail" "$out" "B5-branch1 preserves run id"
assert_contains "ISSUE_NUMBER=123" "$out" "B5-branch1 preserves issue"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B6 get-issue-state FAILED=true ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(LARCH_TEST_GET_ISSUE_FAILED=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B6 exit 2"
assert_contains "STEP_FAILED=get-issue-state" "$out" "B6 STEP_FAILED"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B7 unexpected issue state ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(LARCH_TEST_ISSUE_STATE=MERGED run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B7-non-open-state exit 2"
assert_contains "STEP_FAILED=get-issue-state" "$out" "B7-non-open-state STEP_FAILED"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-sentinel-malformed ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=bad1\nADOPTED=yes\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runF 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B-sentinel-malformed exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B-sentinel-malformed fall-through branch"
assert_contains "RUN_ID=runF" "$out" "B-sentinel-malformed fresh run id"
assert_contains "RUN_ID=runF" "$(cat "$SANDBOX_TMP/parent-issue.md")" "B-sentinel-malformed sentinel replaced"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-sentinel-invalid-run-id ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=bad run\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runG 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B-sentinel-invalid-run-id exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "B-sentinel-invalid-run-id fall-through branch"
assert_contains "RUN_ID=runG" "$out" "B-sentinel-invalid-run-id fresh run id"
assert_contains "RUN_ID=runG" "$(cat "$SANDBOX_TMP/parent-issue.md")" "B-sentinel-invalid-run-id sentinel replaced"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-empty-run-id-derivation ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
cat >"$SANDBOX/scripts/write-session-id.sh" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in
    --output) mkdir -p "$(dirname "$2")"; : > "$2"; shift 2 ;;
    *) shift ;;
  esac
done
exit 0
STUB
chmod +x "$SANDBOX/scripts/write-session-id.sh"
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "B-empty-run-id-derivation exit 0"
assert_contains "IMPLEMENT_BAIL_REASON=tracking-init-failed" "$out" "B-empty-run-id-derivation bail reason"
assert_contains "STALL_TRACKING=true" "$out" "B-empty-run-id-derivation stall"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP-adopt-rename-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
out=$(LARCH_TEST_RENAME_FAILED=true run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runRename 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP-adopt-rename-fail exit 0"
assert_contains "BRANCH_SELECTED=branch-2-adopt" "$out" "GP-adopt-rename-fail branch"
assert_contains "Step 0 tracking adoption — Branch 2 adopt rename to implementing" "$(cat "$SANDBOX_TMP/execution-issues.md")" "GP-adopt-rename-fail execution issues"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- GP2-rename-fail ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume-rename\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
out=$(LARCH_TEST_RENAME_FAILED=true run_bootstrap --up-to-phase tracking --issue-number 123 2>/dev/null) && rc=$? || rc=$?
assert_rc "$rc" 0 "GP2-rename-fail exit 0"
assert_contains "BRANCH_SELECTED=branch-1-resume" "$out" "GP2-rename-fail branch"
assert_contains "Step 0 tracking adoption — Branch 1 resume rename to implementing" "$(cat "$SANDBOX_TMP/execution-issues.md")" "GP2-rename-fail execution issues"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-preflight ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
cat >"$SANDBOX/scripts/session-setup.sh" <<'STUB'
#!/usr/bin/env bash
echo PREFLIGHT_ERROR=Not on main branch
exit 1
STUB
chmod +x "$SANDBOX/scripts/session-setup.sh"
set +e
out=$(run_bootstrap --up-to-phase infra 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B-preflight exit 2"
assert_contains "PREFLIGHT_ERROR=Not on main branch" "$out" "B-preflight PREFLIGHT_ERROR"
assert_contains "STEP_FAILED=session-setup" "$out" "B-preflight STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "write-session-id" "$invoke" "B-preflight no write-session-id"
rm -rf "$SANDBOX" "$SANDBOX_TMP"

# --- B-gate ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
cat >"$SANDBOX/scripts/session-entry-gate.sh" <<'STUB'
#!/usr/bin/env bash
echo "GATE_ERROR=internal contract violation" >&2
exit 1
STUB
chmod +x "$SANDBOX/scripts/session-entry-gate.sh"
set +e
out=$(run_bootstrap --up-to-phase infra 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B-gate exit 2"
assert_contains "GATE_ERROR=internal contract violation" "$out" "B-gate GATE_ERROR forwarded"
assert_contains "STEP_FAILED=session-entry-gate" "$out" "B-gate STEP_FAILED"
invoke=$(cat "$SANDBOX/invoke-log.txt" 2>/dev/null || true)
assert_not_contains "write-session-id" "$invoke" "B-gate no write-session-id"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-issue-required-for-resume ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
printf 'ISSUE_NUMBER=123\nRUN_ID=resume-guard\nADOPTED=true\n' > "$SANDBOX_TMP/parent-issue.md"
set +e
out=$(run_bootstrap --up-to-phase tracking 2>/dev/null)
rc=$?
set -e
assert_rc "$rc" 2 "B-issue-required-for-resume exit 2"
assert_contains "STEP_FAILED=issue-number-required-for-resume" "$out" "B-issue-required-for-resume STEP_FAILED"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-fork-missing-issue ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --forked-target true --upstream-repo upstream/repo 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-fork-missing-issue exit 2"
assert_contains "--issue-number is required with --upstream-repo" "$out" "B-fork-missing-issue usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-invalid-run-id-arg ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id 'bad run' 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-invalid-run-id-arg exit 2"
assert_contains "--run-id must match ^[A-Za-z0-9._-]+$" "$out" "B-invalid-run-id-arg usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- B-invalid-upstream-repo-arg ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
set +e
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --forked-target true --upstream-repo bad/repo/extra 2>&1)
rc=$?
set -e
assert_rc "$rc" 2 "B-invalid-upstream-repo-arg exit 2"
assert_contains "--upstream-repo must be OWNER/REPO" "$out" "B-invalid-upstream-repo-arg usage"
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-NEVER14 ---
# Patterns are literal (grep -F); $ in the pattern is not shell expansion.
# shellcheck disable=SC2016
if grep -Fq '>> "$IMPLEMENT_TMPDIR/session-env.sh"' "$REAL_SCRIPT"; then
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-NEVER14 found append redirect to session-env.sh"
else
    pat='cat > "$IMPLEMENT_TMPDIR/session-env.sh" <<'
    if grep -Fq "$pat" "$REAL_SCRIPT"; then
        FAIL=$((FAIL + 1))
        echo "FAIL: Edge-NEVER14 found cat heredoc redirect to session-env.sh"
    else
        PASS=$((PASS + 1))
        echo "PASS: Edge-NEVER14 no forbidden direct session-env write patterns"
    fi
fi

# --- Edge-breadcrumb-count ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
bc=$(mktemp "${TMPDIR:-/tmp}/larch-ib-bc.XXXXXX")
export LARCH_QUIET_BREADCRUMBS=1
export LARCH_QUIET_BREADCRUMB_FD=1
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
unset LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD
n=$(printf '%s\n' "$out" | grep -cF '→ step0: infra ready' || true)
rm -f "$bc"
assert_rc "$rc" 0 "Edge-breadcrumb-count exit 0"
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count exactly one breadcrumb"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

# --- Edge-breadcrumb-count-adopt ---
SANDBOX_TMP=$(mktemp -d /tmp/larch-ib-sess.XXXXXX)
build_sandbox
write_gp1_session_setup
export LARCH_QUIET_BREADCRUMBS=1
export LARCH_QUIET_BREADCRUMB_FD=1
out=$(run_bootstrap --up-to-phase tracking --issue-number 123 --run-id runBreadcrumb 2>/dev/null) && rc=$? || rc=$?
unset LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD
n=$(printf '%s\n' "$out" | grep -cF '→ step0: tracking adopted' || true)
assert_rc "$rc" 0 "Edge-breadcrumb-count-adopt exit 0"
if [ "$n" -eq 1 ]; then
    PASS=$((PASS + 1))
    echo "PASS: Edge-breadcrumb-count-adopt exactly one breadcrumb"
else
    FAIL=$((FAIL + 1))
    echo "FAIL: Edge-breadcrumb-count-adopt expected 1 got $n"
fi
rm -rf "$SANDBOX_TMP" "$SANDBOX"

echo "---"
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
