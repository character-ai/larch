#!/usr/bin/env bash
# Regression harness for scripts/relevant-checks.sh.
#
# Black-box contract test: invoke relevant-checks.sh inside disposable git repos
# with a controlled PATH so host pre-commit / agent-lint installs cannot change
# the documented exit-code behavior.
#
# Usage:
#   bash scripts/test-relevant-checks.sh
#
# Exit codes:
#   0 - all assertions passed
#   1 - at least one assertion failed

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/relevant-checks.sh"

if [[ ! -f "$SCRIPT" ]]; then
    echo "ERROR: required script not found: $SCRIPT" >&2
    exit 1
fi

TMPROOT=
trap '[[ -n "$TMPROOT" ]] && rm -rf "$TMPROOT"' EXIT
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-relevant-checks-XXXXXX")

export HOME="$TMPROOT/fakehome"
mkdir -p "$HOME"
export GIT_CONFIG_GLOBAL=/dev/null
export GIT_CONFIG_SYSTEM=/dev/null

REAL_GIT=$(command -v git || true)
if [[ -z "$REAL_GIT" ]]; then
    echo "ERROR: git is required on PATH to run this harness" >&2
    exit 1
fi
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

assert_stdout_not_contains() {
    local label="$1" stdout="$2" needle="$3"
    if [[ "$stdout" == *"$needle"* ]]; then
        fail "$label: expected stdout not to contain '$needle'; got: ${stdout:0:400}"
    else
        pass
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

setup_design_reference_repo() {
    local dir="$1"
    setup_git_repo "$dir"
    (
        cd "$dir"
        mkdir -p skills/design/references
        printf '%s\n' "approval gates baseline" > skills/design/references/approval-gates.md
        git add skills/design/references/approval-gates.md
        git commit -q -m "add design reference"
        git checkout -q -b design-reference-change
        printf '%s\n' "approval gates changed" > skills/design/references/approval-gates.md
        git add skills/design/references/approval-gates.md
        git commit -q -m "change design reference"
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

    case "$pre_commit" in
        absent)
            ;;
        present)
            cat > "$dir/pre-commit" <<'EOF'
#!/usr/bin/env bash
echo "pre-commit stub: $*"
exit 0
EOF
            chmod +x "$dir/pre-commit"
            ;;
        *)
            # Numeric exit code — emulate pre-commit success (rc=0) or failure
            # (rc>0). On non-zero, the script-under-test propagates the exit
            # code without invoking the run_post_checks agent-lint phase.
            cat > "$dir/pre-commit" <<EOF
#!/usr/bin/env bash
echo "pre-commit stub: \$*"
if [[ "$pre_commit" -ne 0 ]]; then
    echo "pre-commit stub: simulated lint failure" >&2
fi
exit "$pre_commit"
EOF
            chmod +x "$dir/pre-commit"
            ;;
    esac

    if [[ "$agent_rc" != "absent" ]]; then
        cat > "$dir/agent-lint" <<EOF
#!/usr/bin/env bash
echo "agent-lint stub: \$*"
exit "$agent_rc"
EOF
        chmod +x "$dir/agent-lint"
    fi

    cat > "$dir/make" <<'EOF'
#!/usr/bin/env bash
echo "make stub: $*"
exit 0
EOF
    chmod +x "$dir/make"
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

assert_repo_status_eq() {
    local label="$1" repo="$2" expected="$3"
    local status
    status=$(cd "$repo" && git status --short)
    if [[ "$status" == "$expected" ]]; then
        pass
    else
        fail "$label: expected git status to stay stable; before=${expected//$'\n'/; } after=${status//$'\n'/; }"
    fi
}

assert_pin_phase_accounting_present() {
    local label="$1"
    if awk '
        /PINS_EXIT=\$\?/ { saw_exit=1; next }
        saw_exit && /PHASES_RUN=\$\(\(PHASES_RUN \+ 1\)\)/ { found=1; exit }
        saw_exit && /if \[ "\$PINS_EXIT" -ne 0 \]; then/ { exit }
        END { exit(found ? 0 : 1) }
    ' "$SCRIPT"; then
        pass
    else
        fail "$label: missing PHASES_RUN increment immediately after pin verifier exit capture"
    fi
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

# 3b — changed file + pre-commit success + agent-lint success: pins the dual-phase
# happy path (run-checks.sh increments PHASES_RUN after pre-commit succeeds, then
# run_post_checks invokes agent-lint and the final exit_with_phase_check exits 0).
REPO_3B="$TMPROOT/repo-changed-file-agent-zero"
STUB_3B="$TMPROOT/stub-changed-file-agent-zero"
setup_changed_file_repo "$REPO_3B"
make_stub_dir "$STUB_3B" present 0
run_checks "$REPO_3B" "$(controlled_path "$STUB_3B")"
assert_exit_eq "3b: changed file + pre-commit ok + agent-lint ok" "$RUN_EXIT" 0
assert_stdout_contains "3b: pre-commit stub invoked" "$RUN_OUT" "pre-commit stub:"
assert_stdout_contains "3b: agent-lint stub invoked" "$RUN_OUT" "agent-lint stub:"

# 3c — changed file + pre-commit non-zero: pins the pre-commit-failure early-exit
# branch that propagates the exit code without invoking the run_post_checks
# agent-lint phase. Agent-lint is stubbed present so a regression that
# mistakenly invokes it would surface via the agent-lint banner.
REPO_3C="$TMPROOT/repo-changed-file-pre-commit-fails"
STUB_3C="$TMPROOT/stub-changed-file-pre-commit-fails"
setup_changed_file_repo "$REPO_3C"
make_stub_dir "$STUB_3C" 5 0
run_checks "$REPO_3C" "$(controlled_path "$STUB_3C")"
assert_exit_eq "3c: changed file + pre-commit rc=5 → exit propagates" "$RUN_EXIT" 5
assert_stdout_contains "3c: pre-commit stub invoked" "$RUN_OUT" "pre-commit stub:"
# agent-lint must NOT have run: a successful agent-lint stub would print
# "agent-lint stub:" — its absence pins the "skip post-checks on pre-commit
# failure" branch.
if [[ "$RUN_OUT" == *"agent-lint stub:"* ]]; then
    fail "3c: agent-lint must not run when pre-commit fails; got: ${RUN_OUT:0:400}"
else
    pass
fi

# 3d — changed file + pre-commit success + agent-lint non-zero: pins the
# changed-file dual-phase failure path (PHASES_RUN incremented by pre-commit
# success, then run_post_checks invokes agent-lint and exit_with_phase_check
# propagates the non-zero rc). Complements 2b, which exercises the same
# propagation on the empty-MODIFIED_FILES path.
REPO_3D="$TMPROOT/repo-changed-file-agent-seven"
STUB_3D="$TMPROOT/stub-changed-file-agent-seven"
setup_changed_file_repo "$REPO_3D"
make_stub_dir "$STUB_3D" present 7
run_checks "$REPO_3D" "$(controlled_path "$STUB_3D")"
assert_exit_eq "3d: changed file + pre-commit ok + agent-lint rc=7" "$RUN_EXIT" 7
assert_stdout_contains "3d: pre-commit stub invoked" "$RUN_OUT" "pre-commit stub:"
assert_stdout_contains "3d: agent-lint stub invoked" "$RUN_OUT" "agent-lint stub:"

echo "=== Section 3e: direct targets and pin verification ==="

REPO_3E="$TMPROOT/repo-design-reference-no-pins"
STUB_3E="$TMPROOT/stub-design-reference-no-pins"
setup_design_reference_repo "$REPO_3E"
make_stub_dir "$STUB_3E" present absent
run_checks "$REPO_3E" "$(controlled_path "$STUB_3E")"
assert_exit_eq "3e: design reference routes direct target with missing pin verifier" "$RUN_EXIT" 0
assert_stdout_contains "3e: design reference routes test-design-structure" "$RUN_OUT" "=== Running direct relevant make target(s): test-lint-foreground-markers test-design-structure ==="
assert_stdout_contains "3e: direct targets invoked through make" "$RUN_OUT" "make stub: test-lint-foreground-markers test-design-structure"
assert_stdout_contains "3e: missing pin verifier warning" "$RUN_OUT" "WARNING: scripts/check-contains-pins.sh not found"

REPO_3F="$TMPROOT/repo-design-reference-with-pins"
STUB_3F="$TMPROOT/stub-design-reference-with-pins"
setup_design_reference_repo "$REPO_3F"
mkdir -p "$REPO_3F/scripts"
cat > "$REPO_3F/scripts/check-contains-pins.sh" <<'EOF'
#!/usr/bin/env bash
test -f "$2"
echo "pin verifier stub: $*"
exit 0
EOF
chmod +x "$REPO_3F/scripts/check-contains-pins.sh"
make_stub_dir "$STUB_3F" present absent
STATUS_3F_BEFORE=$(cd "$REPO_3F" && git status --short)
run_checks "$REPO_3F" "$(controlled_path "$STUB_3F")"
assert_exit_eq "3f: present pin verifier runs and exits 0" "$RUN_EXIT" 0
assert_stdout_contains "3f: pin verifier invoked" "$RUN_OUT" "pin verifier stub: --changed-files"
assert_stdout_contains "3f: agent-lint absence after pin phase is non-fatal" "$RUN_OUT" "WARNING: agent-lint not found on PATH — skipping"
assert_repo_status_eq "3f: relevant-checks stays read-only on pin verifier success" "$REPO_3F" "$STATUS_3F_BEFORE"
assert_pin_phase_accounting_present "3f: pin phase increments PHASES_RUN"

REPO_3G="$TMPROOT/repo-design-reference-with-failing-pins"
STUB_3G="$TMPROOT/stub-design-reference-with-failing-pins"
setup_design_reference_repo "$REPO_3G"
mkdir -p "$REPO_3G/scripts"
cat > "$REPO_3G/scripts/check-contains-pins.sh" <<'EOF'
#!/usr/bin/env bash
echo "pin verifier stub: $*"
exit 1
EOF
chmod +x "$REPO_3G/scripts/check-contains-pins.sh"
make_stub_dir "$STUB_3G" present 0
STATUS_3G_BEFORE=$(cd "$REPO_3G" && git status --short)
run_checks "$REPO_3G" "$(controlled_path "$STUB_3G")"
assert_exit_eq "3g: failing pin verifier exit propagates" "$RUN_EXIT" 1
assert_stdout_contains "3g: failing pin verifier invoked" "$RUN_OUT" "pin verifier stub: --changed-files"
assert_stdout_not_contains "3g: agent-lint must not run after pin verifier failure" "$RUN_OUT" "agent-lint stub:"
assert_repo_status_eq "3g: relevant-checks stays read-only on pin verifier failure" "$REPO_3G" "$STATUS_3G_BEFORE"

echo "=== Section 4: preflight failure ==="

REPO_4A="$TMPROOT/repo-pre-commit-absent"
STUB_4A="$TMPROOT/stub-pre-commit-absent"
setup_git_repo "$REPO_4A"
make_stub_dir "$STUB_4A" absent absent
run_checks "$REPO_4A" "$(controlled_path "$STUB_4A")"
assert_exit_eq "4a: pre-commit absent" "$RUN_EXIT" 1
assert_stdout_contains "4a: pre-commit missing error" "$RUN_OUT" "ERROR: pre-commit not found"

# 4b — invocation outside a git repository: pins the rev-parse-failure branch
# (`git rev-parse --show-toplevel` exits non-zero when cwd is not inside a git
# worktree). Pre-commit is stubbed present so the pre-commit preflight succeeds
# and the script reaches the rev-parse check.
DIR_4B="$TMPROOT/non-git-dir"
STUB_4B="$TMPROOT/stub-non-git"
mkdir -p "$DIR_4B"
make_stub_dir "$STUB_4B" present absent
# The stub git wrapper must inherit the same env, so the controlled PATH is
# enough — the wrapper's `exec real_git` will fail rev-parse because the cwd is
# not inside any git repo.
run_checks "$DIR_4B" "$(controlled_path "$STUB_4B")"
assert_exit_eq "4b: not inside a git repository → exit 1" "$RUN_EXIT" 1
assert_stdout_contains "4b: not-a-git-repo error" "$RUN_OUT" "not inside a git repository"

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
