#!/usr/bin/env bash
# Regression harness for session-setup.sh gh-first repository discovery.
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
SESSION_SETUP="$REPO_ROOT/scripts/session-setup.sh"
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-session-setup-repo.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

make_repo() {
    local label="$1"
    local remote_url="${2:-}"
    local repo="$TMPROOT/$label"

    git init "$repo" >/dev/null 2>&1
    if [[ -n "$remote_url" ]]; then
        git -C "$repo" remote add origin "$remote_url"
    fi
    printf '%s\n' "$repo"
}

write_failing_gh() {
    local bindir="$TMPROOT/bin-gh-fail"

    mkdir -p "$bindir"
    cat > "$bindir/gh" <<'EOF_GH'
#!/usr/bin/env bash
exit 1
EOF_GH
    chmod +x "$bindir/gh"
    printf '%s\n' "$bindir"
}

run_session_setup() {
    local repo="$1"
    shift

    (
        cd "$repo"
        "$SESSION_SETUP" \
            --prefix test-session-setup-repo-fallback \
            --skip-preflight \
            --skip-branch-check \
            "$@"
    )
}

assert_repo_output() {
    local out="$1"
    local expected_repo="$2"
    local expected_unavailable="$3"
    local label="$4"

    grep -Fxq "REPO=$expected_repo" <<< "$out" \
        || fail "$label: expected REPO=$expected_repo, got: $out"
    grep -Fxq "REPO_UNAVAILABLE=$expected_unavailable" <<< "$out" \
        || fail "$label: expected REPO_UNAVAILABLE=$expected_unavailable, got: $out"
}

if command -v gh >/dev/null 2>&1; then
    gh_repo=$(make_repo "gh-success" "git@github.com:owner/repo.git")
    if out=$(run_session_setup "$gh_repo" 2>/dev/null) \
        && grep -Fxq "REPO=owner/repo" <<< "$out"; then
        assert_repo_output "$out" "owner/repo" "false" "gh succeeds"
    else
        echo "SKIP: real gh repo view unavailable for gh-success case"
    fi
else
    echo "SKIP: gh unavailable for gh-success case"
fi

FAIL_GH_BIN=$(write_failing_gh)

ssh_repo=$(make_repo "ssh-origin" "git@github.com:owner/repo.git")
out=$(PATH="$FAIL_GH_BIN:$PATH" run_session_setup "$ssh_repo")
assert_repo_output "$out" "owner/repo" "false" "gh fails, SSH origin parses"

https_repo=$(make_repo "https-origin" "https://github.com/owner/repo.git")
out=$(PATH="$FAIL_GH_BIN:$PATH" run_session_setup "$https_repo")
assert_repo_output "$out" "owner/repo" "false" "gh fails, HTTPS origin parses"

malformed_repo=$(make_repo "malformed-origin" "https://gitlab.example.com/foo/bar")
out=$(PATH="$FAIL_GH_BIN:$PATH" run_session_setup "$malformed_repo")
assert_repo_output "$out" "" "true" "gh fails, malformed origin"

no_origin_repo=$(make_repo "no-origin")
out=$(PATH="$FAIL_GH_BIN:$PATH" run_session_setup "$no_origin_repo")
assert_repo_output "$out" "" "true" "gh fails, no origin"

handoff_repo=$(make_repo "handoff-origin" "git@github.com:owner/repo.git")
prev_tmp="$TMPROOT/prev-implement"
mkdir -p "$prev_tmp/larch-logs/implement/run-1"
printf 'payload\n' > "$prev_tmp/larch-logs/implement/run-1/plan-goals-test.md"
caller_env="$TMPROOT/caller-env.sh"
printf 'PREV_IMPLEMENT_TMPDIR=%s\n' "$prev_tmp" > "$caller_env"
out=$(PATH="$FAIL_GH_BIN:$PATH" run_session_setup "$handoff_repo" --caller-env "$caller_env")
session_tmp=$(awk -F= '$1 == "SESSION_TMPDIR" { print substr($0, index($0, "=") + 1); exit }' <<< "$out")
if [[ -z "$session_tmp" || ! -f "$session_tmp/larch-logs/implement/run-1/plan-goals-test.md" ]]; then
    fail "prev implement larch-logs subtree was not copied into fresh session tmpdir"
fi

echo "PASS: test-session-setup-repo-fallback.sh"
