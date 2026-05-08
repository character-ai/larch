#!/usr/bin/env bash
# Regression harness for scripts/create-pr.sh --repo gh threading.
set -euo pipefail

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
if [[ "$1 $2" != "pr view" && "$1 $2" != "pr create" ]]; then
    echo "unexpected gh command: $*" >&2
    exit 2
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

echo "PASS: test-create-pr.sh"
