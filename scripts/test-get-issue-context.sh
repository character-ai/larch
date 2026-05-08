#!/usr/bin/env bash
# Regression harness for scripts/get-issue-context.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/get-issue-context.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-issue-context.XXXXXX")"
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
if [[ "$1 $2" != "issue view" ]]; then
    echo "unexpected gh command" >&2
    exit 2
fi
if [[ "${FAIL_VIEW:-false}" == "true" ]]; then
    echo "not found" >&2
    exit 1
fi
printf '{"title":"Upstream title","body":"Upstream body"}\n'
GH
chmod +x "$stub_dir/gh"

out=$(GH_LOG="$TMPROOT/gh.log" PATH="$stub_dir:$PATH" "$SCRIPT" --issue 42 --repo upstream/repo --tmpdir "$TMPROOT/session")
grep -Fxq "TITLE_FILE=$TMPROOT/session/upstream-issue-title.txt" <<<"$out" || fail "missing TITLE_FILE stdout"
grep -Fxq "BODY_FILE=$TMPROOT/session/upstream-issue-body.txt" <<<"$out" || fail "missing BODY_FILE stdout"
[[ "$(cat "$TMPROOT/session/upstream-issue-title.txt")" == "Upstream title" ]] || fail "title file mismatch"
[[ "$(cat "$TMPROOT/session/upstream-issue-body.txt")" == "Upstream body" ]] || fail "body file mismatch"
grep -Fq 'issue view 42 --repo upstream/repo --json title,body' "$TMPROOT/gh.log" \
    || fail "gh issue view did not target upstream repo"

set +e
GH_LOG="$TMPROOT/fail-gh.log" FAIL_VIEW=true PATH="$stub_dir:$PATH" "$SCRIPT" --issue 42 --repo upstream/repo --tmpdir "$TMPROOT/fail" >"$TMPROOT/fail.out" 2>"$TMPROOT/fail.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing issue should fail"

set +e
PATH="$stub_dir:$PATH" "$SCRIPT" --issue 42 --repo '../bad' --tmpdir "$TMPROOT/bad" >"$TMPROOT/bad.out" 2>"$TMPROOT/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "malformed repo should fail"

echo "PASS: test-get-issue-context.sh"
