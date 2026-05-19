#!/usr/bin/env bash
# Regression harness for scripts/create-pr.sh --repo gh threading.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/create-pr.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-create-pr.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

setup_repo() {
    local name="$1"
    local bare="$TMPROOT/$name-origin.git"
    local repo="$TMPROOT/$name"
    git init --bare "$bare" >/dev/null
    git init "$repo" >/dev/null
    git -C "$repo" config user.name "Larch Test"
    git -C "$repo" config user.email "larch-test@example.invalid"
    git -C "$repo" checkout -b feature >/dev/null 2>&1
    printf 'body\n' > "$repo/file.txt"
    git -C "$repo" add file.txt
    git -C "$repo" commit -m "Initial" >/dev/null
    git -C "$repo" remote add origin "$bare"
    printf 'PR body\n' > "$repo/body.md"
    printf '%s\n' "$repo"
}

stub_dir="$TMPROOT/bin"
mkdir -p "$stub_dir"
cat > "$stub_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${GH_LOG:?}"
if [[ "$1 $2" != "pr view" && "$1 $2" != "pr create" && "$1 $2" != "repo view" ]]; then
    echo "unexpected gh command: $*" >&2
    exit 2
fi
if [[ "$1 $2" == "repo view" ]]; then
    case "${GH_DEFAULT_BRANCH_MODE:-detect}" in
        detect) echo "develop" ;;
        fallback) exit 1 ;;
        *) echo "${GH_DEFAULT_BRANCH_MODE}" ;;
    esac
    exit 0
fi
case "${GH_MODE:-create}" in
    existing)
        if [[ "$1 $2" == "pr view" && "$*" == *"--json title"* ]]; then
            echo "Backfilled title"
        else
            printf '{"number":123,"url":"https://github.com/fork/repo/pull/123","state":"OPEN","title":""}\n'
        fi
        ;;
    fallback)
        if [[ "$1 $2" == "pr view" ]]; then
            if [[ "$*" == *"--json number"* ]]; then
                echo "456"
            else
                exit 1
            fi
        else
            echo "https://example.invalid/no-number"
        fi
        ;;
    create)
        if [[ "$1 $2" == "pr view" ]]; then
            exit 1
        else
            echo "https://github.com/fork/repo/pull/456"
        fi
        ;;
esac
GH
chmod +x "$stub_dir/gh"

repo=$(setup_repo create)
out=$(cd "$repo" && GH_LOG="$TMPROOT/create-gh.log" GH_MODE=create PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md --repo fork/repo)
grep -Fxq 'PR_STATUS=created' <<<"$out" || fail "create path did not report created"
if grep -E '^(pr view|pr create)' "$TMPROOT/create-gh.log" | grep -v -- '--repo fork/repo' >/dev/null; then
    fail "create path has gh pr view/create without --repo"
fi
grep -Fq 'repo view --repo fork/repo --json defaultBranchRef --jq .defaultBranchRef.name' "$TMPROOT/create-gh.log" || fail "create path did not detect default branch with --repo"
grep -Fq -- '--base develop' "$TMPROOT/create-gh.log" || fail "create path did not use detected default branch"

repo=$(setup_repo explicit-base)
out=$(cd "$repo" && GH_LOG="$TMPROOT/base-gh.log" GH_MODE=create PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md --repo fork/repo --base release)
grep -Fxq 'PR_STATUS=created' <<<"$out" || fail "explicit base path did not report created"
grep -Fq -- '--base release' "$TMPROOT/base-gh.log" || fail "explicit base path did not use --base value"
if grep -Fq 'repo view' "$TMPROOT/base-gh.log"; then
    fail "explicit base path should not detect default branch"
fi

repo=$(setup_repo fallback-base)
out=$(cd "$repo" && GH_LOG="$TMPROOT/base-fallback-gh.log" GH_MODE=create GH_DEFAULT_BRANCH_MODE=fallback PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md --repo fork/repo)
grep -Fxq 'PR_STATUS=created' <<<"$out" || fail "base fallback path did not report created"
grep -Fq -- '--base main' "$TMPROOT/base-fallback-gh.log" || fail "base fallback path did not fall back to main"

repo=$(setup_repo existing)
out=$(cd "$repo" && GH_LOG="$TMPROOT/existing-gh.log" GH_MODE=existing PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md --repo fork/repo)
grep -Fxq 'PR_STATUS=existing' <<<"$out" || fail "existing path did not report existing"
if grep -E '^(pr view|pr create)' "$TMPROOT/existing-gh.log" | grep -v -- '--repo fork/repo' >/dev/null; then
    fail "existing path has gh pr view/create without --repo"
fi

repo=$(setup_repo fallback)
out=$(cd "$repo" && GH_LOG="$TMPROOT/fallback-gh.log" GH_MODE=fallback PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md --repo fork/repo)
grep -Fxq 'PR_NUMBER=456' <<<"$out" || fail "fallback PR number path did not run"
if grep -E '^(pr view|pr create)' "$TMPROOT/fallback-gh.log" | grep -v -- '--repo fork/repo' >/dev/null; then
    fail "fallback path has gh pr view/create without --repo"
fi

repo=$(setup_repo badrepo)
set +e
(cd "$repo" && GH_LOG="$TMPROOT/bad-gh.log" PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md --repo 'bad') >"$TMPROOT/bad.out" 2>"$TMPROOT/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "malformed --repo should fail"

# Regression for issue #1496: GH_REPO_ARGS empty array under bash 3.2 + set -u.
# Pre-fix, all four `gh pr view/create "${GH_REPO_ARGS[@]}"` sites aborted with
# `unbound variable` on macOS system bash when --repo was not passed. Run the
# script without --repo and assert (a) it does not abort with that message and
# (b) every gh subcommand was reached without any --repo prefix.
repo=$(setup_repo norepo)
set +e
(cd "$repo" && GH_LOG="$TMPROOT/norepo-gh.log" GH_MODE=create PATH="$stub_dir:$PATH" "$SCRIPT" --title "Test PR" --body-file body.md) >"$TMPROOT/norepo.out" 2>"$TMPROOT/norepo.err"
rc=$?
set -e
if grep -q 'unbound variable' "$TMPROOT/norepo.err"; then
    fail "create-pr.sh aborted with 'unbound variable' under bash $BASH_VERSION when --repo omitted (issue #1496)"
fi
[[ "$rc" -eq 0 ]] || fail "no-repo path failed unexpectedly: rc=$rc; stderr=$(cat "$TMPROOT/norepo.err")"
grep -Fxq 'PR_STATUS=created' <"$TMPROOT/norepo.out" || fail "no-repo path did not report created"
if grep -E '^(pr view|pr create)' "$TMPROOT/norepo-gh.log" | grep -E -- '--repo' >/dev/null; then
    fail "no-repo path threaded an unexpected --repo argument to gh"
fi

# Same regression under /bin/bash (bash 3.2 on macOS) when available — exercises
# the actual interpreter that triggered the reported defect; no-op skip on
# Linux runners that ship bash 4+ as /bin/bash.
if [[ -x /bin/bash ]] && /bin/bash --version | grep -qE 'version 3\.[0-9]'; then
    repo=$(setup_repo norepo32)
    set +e
    (cd "$repo" && GH_LOG="$TMPROOT/norepo32-gh.log" GH_MODE=create PATH="$stub_dir:$PATH" /bin/bash "$SCRIPT" --title "Test PR" --body-file body.md) >"$TMPROOT/norepo32.out" 2>"$TMPROOT/norepo32.err"
    rc=$?
    set -e
    if grep -q 'unbound variable' "$TMPROOT/norepo32.err"; then
        fail "create-pr.sh aborted with 'unbound variable' under /bin/bash 3.2 when --repo omitted (issue #1496)"
    fi
    [[ "$rc" -eq 0 ]] || fail "no-repo path failed under /bin/bash 3.2: rc=$rc; stderr=$(cat "$TMPROOT/norepo32.err")"
    grep -Fxq 'PR_STATUS=created' <"$TMPROOT/norepo32.out" || fail "no-repo path under /bin/bash 3.2 did not report created"
    if grep -E '^(pr view|pr create)' "$TMPROOT/norepo32-gh.log" | grep -E -- '--repo' >/dev/null; then
        fail "no-repo path under /bin/bash 3.2 threaded an unexpected --repo argument to gh"
    fi
fi

# Test: gh pr create exits 1 with empty stderr → diagnostic block is non-empty
# The gh stub below always exits 1 with no stderr output on pr create.
stub_empty_err_dir="$TMPROOT/bin-empty-err"
mkdir -p "$stub_empty_err_dir"
cat > "$stub_empty_err_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-} ${2:-}" == "pr view" ]]; then
    exit 1
fi
if [[ "${1:-} ${2:-}" == "pr create" ]]; then
    # Exit non-zero with no stderr and no stdout to trigger the diagnostic stub.
    exit 1
fi
if [[ "${1:-} ${2:-}" == "repo view" ]]; then
    echo "main"
    exit 0
fi
exit 2
GH
chmod +x "$stub_empty_err_dir/gh"

repo_empty=$(setup_repo empty-err)
set +e
(cd "$repo_empty" && PATH="$stub_empty_err_dir:$PATH" "$SCRIPT" --title "Empty err test" --body-file body.md --repo fork/repo) \
    >"$TMPROOT/empty-err.out" 2>"$TMPROOT/empty-err.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "empty-stderr pr create should have failed"
# The error message must be non-empty and contain the argv hint (not an empty block)
grep -q 'gh pr create' "$TMPROOT/empty-err.err" || fail "error message should contain 'gh pr create' argv hint, got: $(cat "$TMPROOT/empty-err.err")"
grep -q 'no diagnostic captured' "$TMPROOT/empty-err.err" || fail "error message should contain 'no diagnostic captured' stub, got: $(cat "$TMPROOT/empty-err.err")"

echo "PASS: test-create-pr.sh"
