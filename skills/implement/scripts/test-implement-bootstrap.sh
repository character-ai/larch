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
    mkdir -p "$SANDBOX/scripts" "$SANDBOX_TMP"
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
exit 0
STUB
    chmod +x "$SANDBOX/scripts/append-tool-failure.sh"

    cat >"$SANDBOX/scripts/token-ledger.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
    chmod +x "$SANDBOX/scripts/token-ledger.sh"

    cat >"$SANDBOX/scripts/timing-ledger.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
    chmod +x "$SANDBOX/scripts/timing-ledger.sh"

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
        export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
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
exec 9>"$bc"
export LARCH_QUIET_BREADCRUMBS=1
export LARCH_QUIET_BREADCRUMB_FD=9
out=$(run_bootstrap --up-to-phase infra 2>/dev/null) && rc=$? || rc=$?
unset LARCH_QUIET_BREADCRUMBS LARCH_QUIET_BREADCRUMB_FD
exec 9>&-
n=$(grep -cF '→ step0: infra ready' "$bc" 2>/dev/null || true)
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

echo "---"
echo "PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
