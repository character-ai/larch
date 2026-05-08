#!/usr/bin/env bash
# Regression harness for scripts/resolve-repo.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/resolve-repo.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-resolve-repo.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

stub_dir="$TMPROOT/bin"
mkdir -p "$stub_dir"
cat > "$stub_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
case "${GH_MODE:-success}" in
    success)
        if [[ "$*" == "repo view --json nameWithOwner --jq .nameWithOwner" ]]; then
            echo "owner/repo"
            exit 0
        fi
        ;;
    fail)
        exit 1
        ;;
esac
echo "unexpected gh command: $*" >&2
exit 2
GH
chmod +x "$stub_dir/gh"

repo="$TMPROOT/repo"
git init "$repo" >/dev/null
git -C "$repo" remote add origin git@github.com:fallback/repo.git

out=$(cd "$repo" && GH_MODE=success PATH="$stub_dir:$PATH" "$SCRIPT")
[[ "$out" == "owner/repo" ]] || fail "gh repo view success did not win"

out=$(cd "$repo" && GH_MODE=fail PATH="$stub_dir:$PATH" "$SCRIPT")
[[ "$out" == "fallback/repo" ]] || fail "git remote fallback did not resolve"

# Trailing-slash HTTPS remote: the github-remote-repo.sh fallback strips
# trailing slashes. Without the helper delegation this used to silently fail.
git -C "$repo" remote set-url origin https://github.com/trail/slash.git/
out=$(cd "$repo" && GH_MODE=fail PATH="$stub_dir:$PATH" "$SCRIPT")
[[ "$out" == "trail/slash" ]] || fail "trailing-slash HTTPS remote did not resolve (got '$out')"

# Credentialed HTTPS remote (token@github.com).
git -C "$repo" remote set-url origin "https://x-access-token:secret@github.com/cred/repo.git"
out=$(cd "$repo" && GH_MODE=fail PATH="$stub_dir:$PATH" "$SCRIPT")
[[ "$out" == "cred/repo" ]] || fail "credentialed HTTPS remote did not resolve (got '$out')"

git -C "$repo" remote remove origin
set +e
(cd "$repo" && GH_MODE=fail PATH="$stub_dir:$PATH" "$SCRIPT") >"$TMPROOT/fail.out" 2>"$TMPROOT/fail.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "complete resolution failure should exit non-zero"
grep -q 'ERROR=could not resolve repo' "$TMPROOT/fail.err" || fail "failure did not emit ERROR"

echo "PASS: test-resolve-repo.sh"
