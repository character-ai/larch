#!/usr/bin/env bash
# Regression harness for scripts/gh-pr-body-update.sh --repo gh threading.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/gh-pr-body-update.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-pr-body-update.XXXXXX")"
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
printf '%s\n' "$*" >> "${GH_LOG:?}"
if [[ "$1 $2" != "pr edit" ]]; then
    echo "unexpected gh command: $*" >&2
    exit 2
fi
exit "${GH_EXIT:-0}"
GH
chmod +x "$stub_dir/gh"

printf 'body\n' > "$TMPROOT/body.md"
out=$(GH_LOG="$TMPROOT/gh.log" PATH="$stub_dir:$PATH" "$SCRIPT" --pr 123 --body-file "$TMPROOT/body.md" --repo fork/repo)
grep -Fxq 'UPDATED=true' <<<"$out" || fail "update should succeed"
grep -Fq 'pr edit 123 --repo fork/repo --body-file' "$TMPROOT/gh.log" \
    || fail "gh pr edit did not receive --repo"

set +e
GH_LOG="$TMPROOT/bad-gh.log" PATH="$stub_dir:$PATH" "$SCRIPT" --pr 123 --body-file "$TMPROOT/body.md" --repo 'bad' >"$TMPROOT/bad.out" 2>"$TMPROOT/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "malformed --repo should fail"

echo "PASS: test-gh-pr-body-update.sh"
