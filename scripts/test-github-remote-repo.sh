#!/usr/bin/env bash
# Regression harness for scripts/github-remote-repo.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/github-remote-repo.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-gh-remote.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_url() {
    local url="$1" expected="$2"
    local out
    out=$("$SCRIPT" "$url")
    [[ "$out" == "$expected" ]] || fail "expected '$expected' for '$url', got '$out'"
}

assert_url 'git@github.com:owner/repo.git' 'owner/repo'
assert_url 'https://github.com/owner/repo.git' 'owner/repo'
assert_url 'https://github.com/owner/repo' 'owner/repo'
assert_url 'ssh://git@github.com/owner/repo.git' 'owner/repo'
assert_url 'git://github.com/owner/repo.git/' 'owner/repo'
assert_url 'https://github.com/org.name/repo-name_1.git/' 'org.name/repo-name_1'

set +e
"$SCRIPT" 'https://ghe.example.com/owner/repo.git' >"$TMPROOT/ghe.out" 2>"$TMPROOT/ghe.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "GHE URL should be rejected"

secret_url='https://token-secret@notgithub.example.com/owner/repo.git'
set +e
"$SCRIPT" "$secret_url" >"$TMPROOT/secret.out" 2>"$TMPROOT/secret.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "credentialed non-GitHub URL should be rejected"
grep -Fq '://<REDACTED>@' "$TMPROOT/secret.err" \
    || fail "credentialed parse error should redact userinfo"
if grep -Fq 'token-secret' "$TMPROOT/secret.err"; then
    fail "credentialed parse error leaked raw userinfo"
fi

repo="$TMPROOT/repo"
git init "$repo" >/dev/null
git -C "$repo" remote add origin git@github.com:remote-owner/remote-repo.git
out=$(cd "$repo" && "$SCRIPT" origin)
[[ "$out" == "remote-owner/remote-repo" ]] || fail "remote name resolution failed: $out"

echo "PASS: test-github-remote-repo.sh"
