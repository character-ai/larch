#!/usr/bin/env bash
# test-local-cleanup.sh — regression harness for post-merge local cleanup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLEANUP="$SCRIPT_DIR/local-cleanup.sh"
SYSTEM_GIT="$(command -v git)"

[ -x "$CLEANUP" ] || { echo "FAIL: $CLEANUP not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-local-cleanup.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

GIT_WRAPPER_DIR="$TMP/git-wrapper-bin"
mkdir -p "$GIT_WRAPPER_DIR"
cat > "$GIT_WRAPPER_DIR/git" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$GIT_ARG_LOG"
exec "$REAL_GIT" "$@"
EOF
chmod +x "$GIT_WRAPPER_DIR/git"

PASS=0
FAIL=0

pass() {
    echo "  ok: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "FAIL: $1" >&2
    FAIL=$((FAIL + 1))
}

assert_contains() {
    local label="$1"
    local haystack="$2"
    local needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

assert_not_contains() {
    local label="$1"
    local haystack="$2"
    local needle="$3"
    if [[ "$haystack" != *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (unexpected $needle; got ${haystack:0:400})"
    fi
}

assert_equals() {
    local label="$1"
    local got="$2"
    local expected="$3"
    if [ "$got" = "$expected" ]; then
        pass "$label"
    else
        fail "$label (expected $expected; got $got)"
    fi
}

assert_not_equals() {
    local label="$1"
    local got="$2"
    local unexpected="$3"
    if [ "$got" != "$unexpected" ]; then
        pass "$label"
    else
        fail "$label (unexpectedly got $unexpected)"
    fi
}

config_git_identity() {
    local repo="$1"
    git -C "$repo" config user.email "ci@test"
    git -C "$repo" config user.name "Test CI"
}

init_git_repo_main() {
    local repo="$1"
    mkdir -p "$repo"
    git -C "$repo" init -q
    git -C "$repo" symbolic-ref HEAD refs/heads/main
    config_git_identity "$repo"
}

commit_path() {
    local repo="$1"
    local path="$2"
    local content="$3"
    local subject="$4"
    mkdir -p "$(dirname "$repo/$path")"
    printf '%s\n' "$content" > "$repo/$path"
    git -C "$repo" add -- "$path"
    git -C "$repo" commit -q -m "$subject"
}

setup_remote_repo() {
    local label="$1"
    local remote="$TMP/$label-origin.git"
    local seed="$TMP/$label-seed"
    local repo="$TMP/$label-repo"

    git init -q --bare "$remote"
    init_git_repo_main "$seed"
    commit_path "$seed" "README.md" "initial" "init"
    git -C "$seed" remote add origin "$remote"
    git -C "$seed" push -q -u origin main
    git --git-dir="$remote" symbolic-ref HEAD refs/heads/main

    git clone -q "$remote" "$repo"
    git -C "$repo" checkout -q main
    config_git_identity "$repo"
    git -C "$repo" branch feature
    printf '%s\n' "$repo"
}

run_cleanup() {
    local label="$1"
    local repo="$2"
    local out_file="$TMP/$label-cleanup.out"
    local err_file="$TMP/$label-cleanup.err"
    local git_log="$TMP/$label-git-args.log"

    : > "$git_log"
    (
        cd "$repo"
        REAL_GIT="$SYSTEM_GIT" GIT_ARG_LOG="$git_log" PATH="$GIT_WRAPPER_DIR:$PATH" \
            "$CLEANUP" --branch feature > "$out_file" 2> "$err_file"
    )
    LAST_CLEANUP_OUT="$(cat "$out_file")"
    LAST_CLEANUP_ERR="$(cat "$err_file")"
    LAST_GIT_ARGS="$(cat "$git_log")"
}

run_cleanup_args() {
    local label="$1"
    local out_file="$TMP/$label-cleanup.out"
    local err_file="$TMP/$label-cleanup.err"
    shift

    set +e
    "$CLEANUP" "$@" > "$out_file" 2> "$err_file"
    LAST_CLEANUP_RC=$?
    set -e
    LAST_CLEANUP_OUT="$(cat "$out_file")"
    LAST_CLEANUP_ERR="$(cat "$err_file")"
}

run_cleanup_args "help" --help
assert_equals "help exits zero" "$LAST_CLEANUP_RC" "0"
assert_contains "help prints usage" "$LAST_CLEANUP_ERR" "Usage: local-cleanup.sh --branch BRANCH_NAME"

run_cleanup_args "missing-branch"
assert_equals "missing-branch exits one" "$LAST_CLEANUP_RC" "1"
assert_equals "missing-branch emits no keys" "$LAST_CLEANUP_OUT" ""
assert_contains "missing-branch prints required error" "$LAST_CLEANUP_ERR" "ERROR: --branch is required"

run_cleanup_args "branch-main" --branch main
assert_equals "branch-main exits one" "$LAST_CLEANUP_RC" "1"
assert_equals "branch-main emits no keys" "$LAST_CLEANUP_OUT" ""
assert_contains "branch-main prints safety error" "$LAST_CLEANUP_ERR" "ERROR: --branch must not be 'main'"

flush_repo=$(setup_remote_repo "flush-orphan")
commit_path \
    "$flush_repo" \
    "larch-logs/implement/prior-run/session-transcript.jsonl" \
    '{"type":"message","text":"prior"}' \
    "chore(larch-logs): flush implement run prior-run"
flush_origin=$(git -C "$flush_repo" rev-parse origin/main)
run_cleanup "flush-orphan" "$flush_repo"
assert_contains "flush-orphan success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_contains "flush-orphan branch deleted" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=true"
assert_contains "flush-orphan drop warning" "$LAST_CLEANUP_ERR" "Dropping 1 prior-run larch-log flush commit(s) before pull"
assert_contains "pull uses ff-only" "$LAST_GIT_ARGS" "pull --ff-only origin main"
assert_not_contains "pull avoids merge-capable shape" "$LAST_GIT_ARGS" "pull origin main"
flush_head=$(git -C "$flush_repo" rev-parse HEAD)
assert_equals "flush-orphan reset to origin/main" "$flush_head" "$flush_origin"

no_orphan_repo=$(setup_remote_repo "no-orphan")
no_orphan_origin=$(git -C "$no_orphan_repo" rev-parse origin/main)
run_cleanup "no-orphan" "$no_orphan_repo"
assert_contains "no-orphan success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_contains "no-orphan branch deleted" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=true"
assert_not_contains "no-orphan no drop warning" "$LAST_CLEANUP_ERR" "Dropping"
no_orphan_head=$(git -C "$no_orphan_repo" rev-parse HEAD)
assert_equals "no-orphan remains on origin/main" "$no_orphan_head" "$no_orphan_origin"

ff_from_feature_repo=$(setup_remote_repo "ff-from-feature")
ff_from_feature_bare=$(git -C "$ff_from_feature_repo" remote get-url origin)
git -C "$ff_from_feature_repo" checkout -q feature
ff_from_feature_pusher="$TMP/ff-from-feature-pusher"
git clone -q "$ff_from_feature_bare" "$ff_from_feature_pusher"
config_git_identity "$ff_from_feature_pusher"
commit_path \
    "$ff_from_feature_pusher" \
    "release-landed.txt" \
    "release merged" \
    "Release v1.2.3"
git -C "$ff_from_feature_pusher" push -q origin main
ff_from_feature_expected=$(git -C "$ff_from_feature_pusher" rev-parse HEAD)
run_cleanup "ff-from-feature" "$ff_from_feature_repo"
assert_contains "ff-from-feature success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_contains "ff-from-feature ends on main" "$LAST_CLEANUP_OUT" "CURRENT_BRANCH=main"
assert_contains "ff-from-feature branch deleted" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=true"
assert_contains "ff-from-feature pull uses ff-only" "$LAST_GIT_ARGS" "pull --ff-only origin main"
ff_from_feature_head=$(git -C "$ff_from_feature_repo" rev-parse HEAD)
assert_equals "ff-from-feature fast-forwards main" "$ff_from_feature_head" "$ff_from_feature_expected"
if git -C "$ff_from_feature_repo" show-ref --verify --quiet refs/heads/feature; then
    fail "ff-from-feature deletes feature branch"
else
    pass "ff-from-feature deletes feature branch"
fi

non_flush_repo=$(setup_remote_repo "non-flush-ahead")
commit_path "$non_flush_repo" "operator-note.txt" "keep me" "operator local note"
non_flush_origin=$(git -C "$non_flush_repo" rev-parse origin/main)
run_cleanup "non-flush-ahead" "$non_flush_repo"
assert_contains "non-flush-ahead success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_not_contains "non-flush-ahead no drop warning" "$LAST_CLEANUP_ERR" "Dropping"
non_flush_head=$(git -C "$non_flush_repo" rev-parse HEAD)
assert_not_equals "non-flush-ahead keeps local commit" "$non_flush_head" "$non_flush_origin"
if [ -f "$non_flush_repo/operator-note.txt" ]; then
    pass "non-flush-ahead preserves non-flush file"
else
    fail "non-flush-ahead preserves non-flush file"
fi

divergent_repo=$(setup_remote_repo "divergent-main")
divergent_bare=$(git -C "$divergent_repo" remote get-url origin)
commit_path "$divergent_repo" "operator-note.txt" "keep me" "operator local note"
divergent_local_head=$(git -C "$divergent_repo" rev-parse HEAD)
git -C "$divergent_repo" config pull.rebase false
divergent_pusher="$TMP/divergent-main-pusher"
git clone -q "$divergent_bare" "$divergent_pusher"
config_git_identity "$divergent_pusher"
commit_path \
    "$divergent_pusher" \
    "landed-from-pr.txt" \
    "remote advance" \
    "feat: remote release merge"
git -C "$divergent_pusher" push -q origin main
run_cleanup "divergent-main" "$divergent_repo"
assert_contains "divergent-main failure envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=false"
assert_contains "divergent-main stays on main" "$LAST_CLEANUP_OUT" "CURRENT_BRANCH=main"
assert_contains "divergent-main does not delete branch" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=false"
assert_contains "divergent-main reports pull failure" "$LAST_CLEANUP_ERR" "Failed to pull origin main"
divergent_head=$(git -C "$divergent_repo" rev-parse HEAD)
assert_equals "divergent-main keeps local head" "$divergent_head" "$divergent_local_head"
divergent_parent_words=$(git -C "$divergent_repo" rev-list --parents -n 1 HEAD | wc -w | tr -d ' ')
assert_equals "divergent-main creates no merge commit" "$divergent_parent_words" "2"
if git -C "$divergent_repo" show-ref --verify --quiet refs/heads/feature; then
    pass "divergent-main preserves feature branch"
else
    fail "divergent-main preserves feature branch"
fi

# Remote advances with non-larch-logs paths after local flush-only ahead, while
# origin/main in the clone is still the pre-advance tip until fetch (pre-fetch SHA
# must gate the diff predicate; post-fetch origin/main would widen the diff).
squash_gap_repo=$(setup_remote_repo "squash-gap")
squash_gap_bare=$(git -C "$squash_gap_repo" remote get-url origin)
commit_path \
    "$squash_gap_repo" \
    "larch-logs/implement/squash-gap/session-transcript.jsonl" \
    '{"type":"message","text":"flush-only"}' \
    "chore(larch-logs): flush implement run squash-gap"
squash_gap_pusher="$TMP/squash-gap-pusher"
git clone -q "$squash_gap_bare" "$squash_gap_pusher"
config_git_identity "$squash_gap_pusher"
commit_path \
    "$squash_gap_pusher" \
    "landed-from-pr.txt" \
    "squash simulation" \
    "feat: simulate post-merge remote advance"
git -C "$squash_gap_pusher" push -q origin main
squash_gap_expected=$(git -C "$squash_gap_pusher" rev-parse HEAD)
run_cleanup "squash-gap" "$squash_gap_repo"
assert_contains "squash-gap success envelope" "$LAST_CLEANUP_OUT" "CLEANUP_SUCCESS=true"
assert_contains "squash-gap branch deleted" "$LAST_CLEANUP_OUT" "BRANCH_DELETED=true"
assert_contains "squash-gap drop warning" "$LAST_CLEANUP_ERR" "Dropping 1 prior-run larch-log flush commit(s) before pull"
squash_gap_head=$(git -C "$squash_gap_repo" rev-parse HEAD)
assert_equals "squash-gap reset to origin/main after remote advance" "$squash_gap_head" "$squash_gap_expected"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
