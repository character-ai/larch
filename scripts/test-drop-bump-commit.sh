#!/usr/bin/env bash
# test-drop-bump-commit.sh — Offline regression harness for drop-bump-commit.sh.
# Creates isolated temp repos with controlled commit shapes and validates output.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DROP_SCRIPT="$SCRIPT_DIR/drop-bump-commit.sh"

PASS=0
FAIL=0
TMPDIR_BASE=""

cleanup() {
    [[ -n "$TMPDIR_BASE" && -d "$TMPDIR_BASE" ]] && rm -rf "$TMPDIR_BASE"
}
trap cleanup EXIT

TMPDIR_BASE=$(mktemp -d)

# Helper: create a fresh git repo with an initial commit, then create a bump
# commit touching the specified files.
# Usage: setup_repo <repo_dir> <file1> [<file2> ...]
setup_repo() {
    local repo_dir="$1"; shift
    mkdir -p "$repo_dir"
    cd "$repo_dir"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"

    # Initial commit
    mkdir -p .claude-plugin
    echo '{}' > .claude-plugin/plugin.json
    echo '' > CHANGELOG.md
    git add -A
    git commit -q -m "Initial commit"

    # Bump commit touching specified files
    for f in "$@"; do
        local dir
        dir=$(dirname "$f")
        [[ "$dir" != "." ]] && mkdir -p "$dir"
        echo "bumped" >> "$f"
    done
    git add -A
    git commit -q -m "Bump version to 1.2.3"
}

# Helper: run drop-bump-commit.sh and check DROPPED value
# Usage: run_test <test_name> <expected_dropped> [env_var_setting]
# env_var_setting: "unset" (default), "empty", or a value for LARCH_BUMP_FILES
run_test() {
    local test_name="$1"
    local expected="$2"
    local env_setting="${3:-unset}"
    local drop_arg="${4:-}"

    local output
    if [[ "$env_setting" == "unset" ]]; then
        if [[ -n "$drop_arg" ]]; then
            output=$(unset LARCH_BUMP_FILES; bash "$DROP_SCRIPT" "$drop_arg" 2>/dev/null) || true
        else
            output=$(unset LARCH_BUMP_FILES; bash "$DROP_SCRIPT" 2>/dev/null) || true
        fi
    elif [[ "$env_setting" == "empty" ]]; then
        if [[ -n "$drop_arg" ]]; then
            output=$(LARCH_BUMP_FILES="" bash "$DROP_SCRIPT" "$drop_arg" 2>/dev/null) || true
        else
            output=$(LARCH_BUMP_FILES="" bash "$DROP_SCRIPT" 2>/dev/null) || true
        fi
    else
        if [[ -n "$drop_arg" ]]; then
            output=$(LARCH_BUMP_FILES="$env_setting" bash "$DROP_SCRIPT" "$drop_arg" 2>/dev/null) || true
        else
            output=$(LARCH_BUMP_FILES="$env_setting" bash "$DROP_SCRIPT" 2>/dev/null) || true
        fi
    fi

    local actual
    actual=$(echo "$output" | grep "^DROPPED=" | head -1 | cut -d= -f2)

    if [[ "$actual" == "$expected" ]]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name — expected DROPPED=$expected, got DROPPED=$actual" >&2
        FAIL=$((FAIL + 1))
    fi
}

# --- Default path (LARCH_BUMP_FILES unset) ---

# Test 1: plugin.json only
REPO="$TMPDIR_BASE/test1"
setup_repo "$REPO" .claude-plugin/plugin.json
run_test "Default: plugin.json only → DROPPED=true" "true"

# Test 2: plugin.json + CHANGELOG.md
REPO="$TMPDIR_BASE/test2"
setup_repo "$REPO" .claude-plugin/plugin.json CHANGELOG.md
run_test "Default: plugin.json + CHANGELOG.md → DROPPED=true" "true"

# Test 3: unexpected file
REPO="$TMPDIR_BASE/test3"
setup_repo "$REPO" version.go
run_test "Default: unexpected file → DROPPED=false" "false"

# Test 4: CHANGELOG-only (must reject on default path)
REPO="$TMPDIR_BASE/test4"
setup_repo "$REPO" CHANGELOG.md
run_test "Default: CHANGELOG-only → DROPPED=false" "false"

# --- Custom path (LARCH_BUMP_FILES set) ---

# Test 5: single custom file
REPO="$TMPDIR_BASE/test5"
setup_repo "$REPO" version.go
run_test "Custom: single file → DROPPED=true" "true" "version.go"

# Test 6: single custom file + CHANGELOG.md
REPO="$TMPDIR_BASE/test6"
setup_repo "$REPO" version.go CHANGELOG.md
run_test "Custom: single + CHANGELOG.md → DROPPED=true" "true" "version.go"

# Test 7: multi-file (all present)
REPO="$TMPDIR_BASE/test7"
setup_repo "$REPO" version.go package.json
run_test "Custom: multi-file all present → DROPPED=true" "true" "version.go:package.json"

# Test 8: multi-file (subset — only one changed)
REPO="$TMPDIR_BASE/test8"
setup_repo "$REPO" version.go
run_test "Custom: multi-file subset → DROPPED=true" "true" "version.go:package.json"

# Test 9: missing file (commit touches unlisted file)
REPO="$TMPDIR_BASE/test9"
setup_repo "$REPO" package.json
run_test "Custom: missing file → DROPPED=false" "false" "version.go"

# Test 10: replacement blocks default (plugin.json not in custom set)
REPO="$TMPDIR_BASE/test10"
setup_repo "$REPO" .claude-plugin/plugin.json
run_test "Custom: replacement blocks default → DROPPED=false" "false" "version.go"

# Test 11: empty env var (fail-closed)
REPO="$TMPDIR_BASE/test11"
setup_repo "$REPO" version.go
run_test "Empty env var → DROPPED=false" "false" "empty"

# Test 12: whitespace segments
REPO="$TMPDIR_BASE/test12"
setup_repo "$REPO" version.go
run_test "Whitespace segments → DROPPED=true" "true" " version.go : "

# Test 13: all-empty segments (fail-closed)
REPO="$TMPDIR_BASE/test13"
setup_repo "$REPO" version.go
run_test "All-empty segments → DROPPED=false" "false" ":::"

# Test 14: CHANGELOG.md in custom set (harmless duplicate)
REPO="$TMPDIR_BASE/test14"
setup_repo "$REPO" version.go CHANGELOG.md
run_test "CHANGELOG.md in custom set → DROPPED=true" "true" "version.go:CHANGELOG.md"

# Test 15: CHANGELOG-only on custom path (must reject — no configured bump file touched)
REPO="$TMPDIR_BASE/test15"
setup_repo "$REPO" CHANGELOG.md
run_test "Custom: CHANGELOG-only → DROPPED=false" "false" "version.go"

# Test 16: empty-diff bump commit on custom path (must reject — no files at all)
REPO="$TMPDIR_BASE/test16"
mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
mkdir -p .claude-plugin
echo '{}' > .claude-plugin/plugin.json
echo '' > CHANGELOG.md
git add -A
git commit -q -m "Initial commit"
git commit --allow-empty -q -m "Bump version to 1.2.3"
run_test "Custom: empty-diff → DROPPED=false" "false" "version.go"

# Test 17: untracked file present — Guard 1 must not block on untracked files
# (git reset --hard does not affect untracked files, so they are safe to ignore)
REPO="$TMPDIR_BASE/test17"
setup_repo "$REPO" .claude-plugin/plugin.json
# Add an untracked file (simulates pending larch-log writes)
echo "pending" > "$REPO/larch-logs-pending.txt"
run_test "Untracked file present → DROPPED=true" "true"

# --- Walk-back tests (bump not at HEAD) ---

# Helper: create a repo with HEAD = flush commit, HEAD~1 = bump commit
setup_walkback_repo() {
    local repo_dir="$1"
    mkdir -p "$repo_dir"
    cd "$repo_dir"
    git init -q
    git config user.email "test@test.com"
    git config user.name "Test"

    # Initial commit
    mkdir -p .claude-plugin
    echo '{"version":"1.2.2"}' > .claude-plugin/plugin.json
    echo '' > CHANGELOG.md
    git add -A
    git commit -q -m "Initial commit"

    # Bump commit at HEAD~1
    echo '{"version":"1.2.3"}' > .claude-plugin/plugin.json
    git add -A
    git commit -q -m "Bump version to 1.2.3"

    # Flush commit at HEAD (simulates larch-log flush landing on top of bump)
    mkdir -p larch-logs
    echo 'log data' > larch-logs/run.md
    git add -A
    git commit -q -m "Flush larch-logs before push"
}

# Test 18: bump at HEAD~1 (flush commit at HEAD) → DROPPED=true, flush preserved
REPO="$TMPDIR_BASE/test18"
setup_walkback_repo "$REPO"
output=""
output=$(cd "$REPO" && bash "$DROP_SCRIPT" 2>/dev/null) || true
actual=$(echo "$output" | grep "^DROPPED=" | head -1 | cut -d= -f2)
if [[ "$actual" == "true" ]]; then
    # Verify the flush commit is now HEAD (bump was removed)
    new_head_subject=$(git -C "$REPO" log -1 --format=%s HEAD 2>/dev/null || true)
    if [[ "$new_head_subject" == "Flush larch-logs before push" ]]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: Test 18 — flush commit not preserved after drop; HEAD subject: $new_head_subject" >&2
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: Test 18 — expected DROPPED=true (bump at HEAD~1), got DROPPED=$actual" >&2
    FAIL=$((FAIL + 1))
fi

# Test 19: bump beyond max-depth → DROPPED=false, warning mentions depth
REPO="$TMPDIR_BASE/test19"
mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
mkdir -p .claude-plugin
echo '{"version":"1.0.0"}' > .claude-plugin/plugin.json
git add -A
git commit -q -m "Initial commit"
# Bump commit
echo '{"version":"1.2.3"}' > .claude-plugin/plugin.json
git add -A
git commit -q -m "Bump version to 1.2.3"
# Add 3 more commits on top so bump is at HEAD~3
for _i in 1 2 3; do
    echo "log $_i" > larch-logs-test-"$_i".txt
    git add -A
    git commit -q -m "Flush commit $_i"
done

stderr_out=""
output=""
output=$(cd "$REPO" && bash "$DROP_SCRIPT" --max-depth 2 2>"$TMPDIR_BASE/test19-stderr.txt") || true
actual=$(echo "$output" | grep "^DROPPED=" | head -1 | cut -d= -f2)
stderr_out=$(cat "$TMPDIR_BASE/test19-stderr.txt" 2>/dev/null || true)
if [[ "$actual" == "false" ]]; then
    if echo "$stderr_out" | grep -Fq "within 2 commits of HEAD"; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: Test 19 — DROPPED=false but depth not mentioned in stderr: $stderr_out" >&2
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: Test 19 — expected DROPPED=false (bump beyond --max-depth 2), got DROPPED=$actual" >&2
    FAIL=$((FAIL + 1))
fi

# Test 20: forced rebase --onto failure → exit 1 and abort cleanup removes rebase state
REPO="$TMPDIR_BASE/test20"
setup_walkback_repo "$REPO"
WRAP_BIN="$TMPDIR_BASE/test20-bin"
REAL_GIT="$(command -v git)"
mkdir -p "$WRAP_BIN"
cat > "$WRAP_BIN/git" <<SH
#!/usr/bin/env bash
if [[ "\${1:-}" == "rebase" && "\${2:-}" == "--onto" ]]; then
    mkdir -p .git/rebase-merge
    printf 'forced\n' > .git/rebase-merge/head-name
    echo "forced rebase failure" >&2
    exit 1
fi
if [[ "\${1:-}" == "rebase" && "\${2:-}" == "--abort" ]]; then
    rm -rf .git/rebase-merge
    exit 0
fi
exec "$REAL_GIT" "\$@"
SH
chmod +x "$WRAP_BIN/git"
set +e
(
    cd "$REPO" &&
    PATH="$WRAP_BIN:$PATH" \
    bash "$DROP_SCRIPT" >"$TMPDIR_BASE/test20-stdout.txt" 2>"$TMPDIR_BASE/test20-stderr.txt"
)
rc=$?
set -e
if [[ "$rc" == "1" ]]; then
    if [[ ! -e "$REPO/.git/rebase-merge" ]]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: Test 20 — rebase state remained after forced failure" >&2
        FAIL=$((FAIL + 1))
    fi
else
    echo "FAIL: Test 20 — expected exit 1 from forced rebase failure, got $rc" >&2
    FAIL=$((FAIL + 1))
fi

# Test 21: CHANGELOG-only with opt-in flag on default path → DROPPED=true
REPO="$TMPDIR_BASE/test21"
setup_repo "$REPO" CHANGELOG.md
run_test "Default: CHANGELOG-only + --allow-changelog-only → DROPPED=true" "true" "unset" "--allow-changelog-only"

# Test 22: CHANGELOG-only without opt-in flag still rejects
REPO="$TMPDIR_BASE/test22"
setup_repo "$REPO" CHANGELOG.md
run_test "Default: CHANGELOG-only without flag → DROPPED=false" "false"

# Test 23: CHANGELOG-only with opt-in flag on custom path → DROPPED=true
REPO="$TMPDIR_BASE/test23"
setup_repo "$REPO" CHANGELOG.md
run_test "Custom: CHANGELOG-only + --allow-changelog-only → DROPPED=true" "true" "version.go" "--allow-changelog-only"

# Test 24: CHANGELOG-only non-bump subject with opt-in flag still rejects
REPO="$TMPDIR_BASE/test24"
mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
mkdir -p .claude-plugin
echo '{}' > .claude-plugin/plugin.json
echo '' > CHANGELOG.md
git add -A
git commit -q -m "Initial commit"
echo "changed" >> CHANGELOG.md
git add CHANGELOG.md
git commit -q -m "Update CHANGELOG for 1.2.3"
run_test "Default: CHANGELOG-only non-bump subject + flag → DROPPED=false" "false" "unset" "--allow-changelog-only"

# Test 25: HEAD=CHANGELOG, HEAD~1=bump; walk-back drops bump and preserves CHANGELOG HEAD
REPO="$TMPDIR_BASE/test25"
mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
mkdir -p .claude-plugin
echo '{"version":"1.2.2"}' > .claude-plugin/plugin.json
echo '' > CHANGELOG.md
git add -A
git commit -q -m "Initial commit"
echo '{"version":"1.2.3"}' > .claude-plugin/plugin.json
git add .claude-plugin/plugin.json
git commit -q -m "Bump version to 1.2.3"
echo "entry" >> CHANGELOG.md
git add CHANGELOG.md
git commit -q -m "Update CHANGELOG for 1.2.3"
output=$(cd "$REPO" && bash "$DROP_SCRIPT" --allow-changelog-only 2>/dev/null) || true
actual=$(echo "$output" | grep "^DROPPED=" | head -1 | cut -d= -f2)
new_head_subject=$(git -C "$REPO" log -1 --format=%s HEAD 2>/dev/null || true)
if [[ "$actual" == "true" && "$new_head_subject" == "Update CHANGELOG for 1.2.3" ]]; then
    PASS=$((PASS + 1))
else
    echo "FAIL: Test 25 — expected bump at HEAD~1 dropped and CHANGELOG preserved; DROPPED=$actual HEAD=$new_head_subject" >&2
    FAIL=$((FAIL + 1))
fi

# Test 26: HEAD=log-refresh, HEAD~1=CHANGELOG, HEAD~2=bump; walk-back drops bump
REPO="$TMPDIR_BASE/test26"
mkdir -p "$REPO"
cd "$REPO"
git init -q
git config user.email "test@test.com"
git config user.name "Test"
mkdir -p .claude-plugin
echo '{"version":"1.2.2"}' > .claude-plugin/plugin.json
echo '' > CHANGELOG.md
git add -A
git commit -q -m "Initial commit"
echo '{"version":"1.2.3"}' > .claude-plugin/plugin.json
git add .claude-plugin/plugin.json
git commit -q -m "Bump version to 1.2.3"
echo "entry" >> CHANGELOG.md
git add CHANGELOG.md
git commit -q -m "Update CHANGELOG for 1.2.3"
mkdir -p larch-logs
echo "log" > larch-logs/run.md
git add larch-logs/run.md
git commit -q -m "chore(larch-logs): refresh"
output=$(cd "$REPO" && bash "$DROP_SCRIPT" --allow-changelog-only 2>/dev/null) || true
actual=$(echo "$output" | grep "^DROPPED=" | head -1 | cut -d= -f2)
new_head_subject=$(git -C "$REPO" log -1 --format=%s HEAD 2>/dev/null || true)
if [[ "$actual" == "true" && "$new_head_subject" == "chore(larch-logs): refresh" ]] &&
    git -C "$REPO" log --format=%s | grep -q '^Update CHANGELOG for 1.2.3$' &&
    ! git -C "$REPO" log --format=%s | grep -q '^Bump version to 1.2.3$'; then
    PASS=$((PASS + 1))
else
    echo "FAIL: Test 26 — expected bump at HEAD~2 dropped with upper commits preserved; DROPPED=$actual HEAD=$new_head_subject" >&2
    FAIL=$((FAIL + 1))
fi

# --- Summary ---
TOTAL=$((PASS + FAIL))
echo ""
echo "test-drop-bump-commit: $PASS/$TOTAL passed"
if [[ $FAIL -gt 0 ]]; then
    echo "FAILED: $FAIL test(s)" >&2
    exit 1
fi
