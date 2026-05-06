#!/usr/bin/env bash
# Regression harness for .claude/skills/relevant-checks/scripts/run-checks.sh.
#
# Black-box contract test: invoke run-checks.sh inside disposable git repos
# with a controlled PATH so host pre-commit / agent-lint installs cannot change
# the documented exit-code behavior.
#
# Usage:
#   bash .claude/skills/relevant-checks/scripts/test-run-checks.sh
#
# Exit codes:
#   0 - all assertions passed
#   1 - at least one assertion failed

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
SCRIPT="$REPO_ROOT/.claude/skills/relevant-checks/scripts/run-checks.sh"

if [[ ! -f "$SCRIPT" ]]; then
    echo "ERROR: required script not found: $SCRIPT" >&2
    exit 1
fi

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-run-checks-XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

export HOME="$TMPROOT/fakehome"
mkdir -p "$HOME"
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null

REAL_GIT=$(command -v git)
REAL_GIT_DIR=$(dirname "$REAL_GIT")
PATH_GIT_DIR="$REAL_GIT_DIR"
if [[ "$REAL_GIT_DIR" == "/usr/local/bin" || -x "$REAL_GIT_DIR/agent-lint" || -x "$REAL_GIT_DIR/pre-commit" ]]; then
    PATH_GIT_DIR=""
fi

PASS=0
FAIL=0
FAILED_TESTS=()
RUN_OUT=""
RUN_EXIT=0

fail() {
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$1")
    echo "FAIL: $1" >&2
}

pass() {
    PASS=$((PASS + 1))
}

assert_stdout_contains() {
    local label="$1" stdout="$2" needle="$3"
    if [[ "$stdout" == *"$needle"* ]]; then
        pass
    else
        fail "$label: expected stdout to contain '$needle'; got: ${stdout:0:400}"
    fi
}

assert_exit_eq() {
    local label="$1" got="$2" want="$3"
    if [[ "$got" -eq "$want" ]]; then
        pass
    else
        fail "$label: expected exit $want, got $got"
    fi
}

setup_git_repo() {
    local dir="$1"
    mkdir -p "$dir"
    (
        cd "$dir"
        git init -q -b main
        git config user.email "test@example.com"
        git config user.name "Test"
        printf '%s\n' "initial content" > tracked.txt
        git add tracked.txt
        git commit -q -m "initial commit"
    )
}

setup_deletion_only_repo() {
    local dir="$1"
    setup_git_repo "$dir"
    (
        cd "$dir"
        git checkout -q -b deletion-only
        git rm -q tracked.txt
        git commit -q -m "delete tracked file"
    )
}

setup_changed_file_repo() {
    local dir="$1"
    setup_git_repo "$dir"
    (
        cd "$dir"
        git checkout -q -b changed-file
        printf '%s\n' "changed content" > tracked.txt
        git add tracked.txt
        git commit -q -m "change tracked file"
    )
}

make_stub_dir() {
    local dir="$1" pre_commit="$2" agent_rc="${3:-absent}"
    mkdir -p "$dir"

    cat > "$dir/git" <<EOF
#!/usr/bin/env bash
exec "$REAL_GIT" "\$@"
EOF
    chmod +x "$dir/git"

    if [[ "$pre_commit" == "present" ]]; then
        cat > "$dir/pre-commit" <<'EOF'
#!/usr/bin/env bash
echo "pre-commit stub: $*"
exit 0
EOF
        chmod +x "$dir/pre-commit"
    fi

    if [[ "$agent_rc" != "absent" ]]; then
        cat > "$dir/agent-lint" <<EOF
#!/usr/bin/env bash
echo "agent-lint stub: \$*"
exit "$agent_rc"
EOF
        chmod +x "$dir/agent-lint"
    fi
}

controlled_path() {
    local stub_dir="$1"
    if [[ -n "$PATH_GIT_DIR" ]]; then
        printf '%s:%s:/usr/bin:/bin\n' "$stub_dir" "$PATH_GIT_DIR"
    else
        printf '%s:/usr/bin:/bin\n' "$stub_dir"
    fi
}

run_checks() {
    local repo="$1" path_value="$2"
    set +e
    RUN_OUT=$(cd "$repo" && PATH="$path_value" /bin/bash "$SCRIPT" 2>&1)
    RUN_EXIT=$?
    set -e
}

echo "=== Section 1: zero-phase paths ==="

REPO_1A="$TMPROOT/repo-empty-no-agent"
STUB_1A="$TMPROOT/stub-empty-no-agent"
setup_git_repo "$REPO_1A"
make_stub_dir "$STUB_1A" present absent
run_checks "$REPO_1A" "$(controlled_path "$STUB_1A")"
assert_exit_eq "1a: empty modified files + agent-lint absent" "$RUN_EXIT" 2
assert_stdout_contains "1a: zero-phase error banner" "$RUN_OUT" "ERROR: no validation phases ran"

REPO_1B="$TMPROOT/repo-deletion-only-no-agent"
STUB_1B="$TMPROOT/stub-deletion-only-no-agent"
setup_deletion_only_repo "$REPO_1B"
make_stub_dir "$STUB_1B" present absent
run_checks "$REPO_1B" "$(controlled_path "$STUB_1B")"
assert_exit_eq "1b: deletions-only + agent-lint absent" "$RUN_EXIT" 2
assert_stdout_contains "1b: zero-phase error banner" "$RUN_OUT" "ERROR: no validation phases ran"

echo "=== Section 2: agent-lint propagation ==="

REPO_2A="$TMPROOT/repo-empty-agent-zero"
STUB_2A="$TMPROOT/stub-empty-agent-zero"
setup_git_repo "$REPO_2A"
make_stub_dir "$STUB_2A" present 0
run_checks "$REPO_2A" "$(controlled_path "$STUB_2A")"
assert_exit_eq "2a: empty modified files + agent-lint rc=0" "$RUN_EXIT" 0
assert_stdout_contains "2a: agent-lint invoked" "$RUN_OUT" "agent-lint stub:"

REPO_2B="$TMPROOT/repo-empty-agent-seven"
STUB_2B="$TMPROOT/stub-empty-agent-seven"
setup_git_repo "$REPO_2B"
make_stub_dir "$STUB_2B" present 7
run_checks "$REPO_2B" "$(controlled_path "$STUB_2B")"
assert_exit_eq "2b: empty modified files + agent-lint rc=7" "$RUN_EXIT" 7
assert_stdout_contains "2b: agent-lint invoked" "$RUN_OUT" "agent-lint stub:"

echo "=== Section 3: changed-file pre-commit path ==="

REPO_3A="$TMPROOT/repo-changed-file-no-agent"
STUB_3A="$TMPROOT/stub-changed-file-no-agent"
setup_changed_file_repo "$REPO_3A"
make_stub_dir "$STUB_3A" present absent
run_checks "$REPO_3A" "$(controlled_path "$STUB_3A")"
assert_exit_eq "3a: changed file + pre-commit success + agent-lint absent" "$RUN_EXIT" 0
assert_stdout_contains "3a: pre-commit stub invoked" "$RUN_OUT" "pre-commit stub:"
assert_stdout_contains "3a: agent-lint warning" "$RUN_OUT" "WARNING: agent-lint not found on PATH — skipping"

echo "=== Section 4: preflight failure ==="

REPO_4A="$TMPROOT/repo-pre-commit-absent"
STUB_4A="$TMPROOT/stub-pre-commit-absent"
setup_git_repo "$REPO_4A"
make_stub_dir "$STUB_4A" absent absent
run_checks "$REPO_4A" "$(controlled_path "$STUB_4A")"
assert_exit_eq "4a: pre-commit absent" "$RUN_EXIT" 1
assert_stdout_contains "4a: pre-commit missing error" "$RUN_OUT" "ERROR: pre-commit not found"

echo ""
echo "=== Summary ==="
echo "PASS=$PASS"
echo "FAIL=$FAIL"

if [[ "$FAIL" -ne 0 ]]; then
    echo "Failed tests:" >&2
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t" >&2
    done
    exit 1
fi

exit 0
