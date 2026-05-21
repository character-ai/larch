#!/usr/bin/env bash
# test-clarify-comment.sh — offline harness for clarify-comment-post.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
POST="$REPO_ROOT/scripts/clarify-comment-post.sh"

[ -x "$POST" ] || {
    echo "FAIL: $POST not executable" >&2
    exit 1
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-clarify-comment.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

ORIG_PATH="$PATH"
STUB="$TMP/stub"
mkdir -p "$STUB"
CAPTURE="$TMP/posted-body.txt"
export CAPTURE

cat > "$STUB/gh" <<'GHSTUB'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
    printf '%s\n' 'owner/repo'
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "comment" ]; then
    i=1
    while [ "$i" -le "$#" ]; do
        eval "a=\${$i}"
        if [ "$a" = "--body-file" ]; then
            n=$((i + 1))
            eval "bf=\${$n}"
            cp "$bf" "$CAPTURE"
            echo "https://github.com/owner/repo/issues/42#issuecomment-7001"
            exit 0
        fi
        i=$((i + 1))
    done
    exit 2
fi
exit 2
GHSTUB
chmod +x "$STUB/gh"
export PATH="$STUB:$ORIG_PATH"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

CONTENT="$TMP/c.txt"
printf 'line1\nline2\n' > "$CONTENT"

echo "=== request marker prefix ==="
rm -f "$CAPTURE"
out="$(PATH="$STUB:$ORIG_PATH" "$POST" --issue 42 --kind request --id 1 --content-file "$CONTENT" --repo owner/repo)"
echo "$out" | grep -q 'POSTED=true' || fail "POSTED"
echo "$out" | grep -q 'MARKER=<!-- larch:clarify-request id=1 -->' || fail "marker"
head -1 "$CAPTURE" | grep -q '^<!-- larch:clarify-request id=1 -->$' || fail "first line marker"

echo "=== response marker prefix ==="
rm -f "$CAPTURE"
out="$(PATH="$STUB:$ORIG_PATH" "$POST" --issue 42 --kind response --id 1 --content-file "$CONTENT" --repo owner/repo)"
head -1 "$CAPTURE" | grep -q '^<!-- larch:clarify-response id=1 -->$' || fail "response first line"

echo "=== invalid id 0 ==="
set +e
out="$(PATH="$STUB:$ORIG_PATH" "$POST" --issue 42 --kind request --id 0 --content-file "$CONTENT" --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "1" ] || fail "id0 exit $rc"
echo "$out" | grep -q 'ERROR=invalid-id' || fail "invalid-id missing: $out"

echo "=== invalid id -1 ==="
set +e
out="$(PATH="$STUB:$ORIG_PATH" "$POST" --issue 42 --kind request --id -1 --content-file "$CONTENT" --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "1" ] || fail "id-1 exit $rc"
echo "$out" | grep -q 'ERROR=invalid-id' || fail "invalid-id -1: $out"

echo "=== invalid id abc ==="
set +e
out="$(PATH="$STUB:$ORIG_PATH" "$POST" --issue 42 --kind request --id abc --content-file "$CONTENT" --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "1" ] || fail "id abc exit $rc"
echo "$out" | grep -q 'ERROR=invalid-id' || fail "invalid-id abc: $out"

echo "=== invalid kind ==="
set +e
out="$(PATH="$STUB:$ORIG_PATH" "$POST" --issue 42 --kind blah --id 1 --content-file "$CONTENT" --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "1" ] || fail "kind exit $rc"
echo "$out" | grep -q 'ERROR=invalid-kind' || fail "invalid-kind: $out"

echo "All assertions passed."
