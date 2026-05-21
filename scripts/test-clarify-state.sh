#!/usr/bin/env bash
# test-clarify-state.sh — offline harness for clarify-state.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE="$REPO_ROOT/scripts/clarify-state.sh"

[ -x "$STATE" ] || {
    echo "FAIL: $STATE not executable" >&2
    exit 1
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-clarify-state.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

ORIG_PATH="$PATH"
STUB="$TMP/stub"
mkdir -p "$STUB"
COMMENTS_JSON="$TMP/comments.json"
export COMMENTS_JSON

cat > "$STUB/gh" <<'GHSTUB'
#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
    printf '%s\n' 'owner/repo'
    exit 0
fi
if [ "$1" = "api" ]; then
    cat "$COMMENTS_JSON"
    exit 0
fi
exit 2
GHSTUB
chmod +x "$STUB/gh"
export PATH="$STUB:$ORIG_PATH"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

expect_kv() {
    local haystack="$1"
    local needle="$2"
    case "$haystack" in
        *"$needle"*) ;;
        *) fail "missing $needle in $haystack" ;;
    esac
}

run_case() {
    local name="$1" json="$2" want="$3"
    printf '%s' "$json" > "$COMMENTS_JSON"
    set +e
    out="$(PATH="$STUB:$ORIG_PATH" "$STATE" --issue 7 --repo owner/repo 2>&1)"
    rc=$?
    set -e
    [ "$rc" = "0" ] || fail "$name exit $rc: $out"
    case "$out" in
        *$want*) ;;
        *) fail "$name: want *$want* got: $out" ;;
    esac
}

echo "=== zero comments ==="
run_case 'clean' '[]' 'STATE=clean'

echo "=== one request no response ==="
run_case 'await' '[{"body":"<!-- larch:clarify-request id=1 -->\nhi"}]' 'STATE=awaiting-response'

echo "=== one request matching response ==="
run_case 'pending' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"}]' 'STATE=response-pending'

echo "=== two requests same id ==="
run_case 'dupreq' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-request id=1 -->"}]' 'STATE=ambiguous'

echo "=== two responses same id ==="
run_case 'dupresp' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"}]' 'STATE=ambiguous'

echo "=== response without prior request ==="
run_case 'orphan' '[{"body":"<!-- larch:clarify-response id=1 -->"}]' 'STATE=ambiguous'

echo "=== non-monotonic ids ==="
run_case 'nonmono' '[{"body":"<!-- larch:clarify-request id=2 -->"},{"body":"<!-- larch:clarify-request id=1 -->"}]' 'STATE=ambiguous'

echo "=== multi-round completed ==="
run_case 'multi_done' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"},{"body":"<!-- larch:clarify-request id=2 -->"},{"body":"<!-- larch:clarify-response id=2 -->"}]' 'STATE=response-pending'

echo "=== multi-round in progress ==="
run_case 'multi_prog' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"},{"body":"<!-- larch:clarify-request id=2 -->"}]' 'STATE=awaiting-response'

echo "All assertions passed."
