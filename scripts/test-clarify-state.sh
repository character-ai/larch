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
    if [ "${COMMENTS_JSON_DUAL:-}" = "1" ]; then
        cat "${COMMENTS_JSON_PART1:?}"
        cat "${COMMENTS_JSON_PART2:?}"
        exit 0
    fi
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

expect_line() {
    local haystack="$1"
    local needle="$2"
    printf '%s\n' "$haystack" | grep -Fxq "$needle" || fail "missing exact line '$needle' in output"
}

run_case() {
    local name="$1" json="$2"
    shift 2
    printf '%s' "$json" > "$COMMENTS_JSON"
    unset COMMENTS_JSON_DUAL COMMENTS_JSON_PART1 COMMENTS_JSON_PART2
    set +e
    out="$(PATH="$STUB:$ORIG_PATH" "$STATE" --issue 7 --repo owner/repo 2>&1)"
    rc=$?
    set -e
    [ "$rc" = "0" ] || fail "$name exit $rc: $out"
    local line
    for line in "$@"; do
        expect_line "$out" "$line"
    done
}

run_case_dual() {
    local name="$1" p1="$2" p2="$3"
    shift 3
    unset COMMENTS_JSON
    export COMMENTS_JSON_DUAL=1
    export COMMENTS_JSON_PART1="$TMP/page1.json"
    export COMMENTS_JSON_PART2="$TMP/page2.json"
    printf '%s' "$p1" > "$COMMENTS_JSON_PART1"
    printf '%s' "$p2" > "$COMMENTS_JSON_PART2"
    set +e
    out="$(PATH="$STUB:$ORIG_PATH" "$STATE" --issue 7 --repo owner/repo 2>&1)"
    rc=$?
    set -e
    [ "$rc" = "0" ] || fail "$name exit $rc: $out"
    local line
    for line in "$@"; do
        expect_line "$out" "$line"
    done
}

echo "=== zero comments ==="
run_case 'clean' '[]' 'STATE=clean' 'LAST_REQUEST_ID=' 'LAST_RESPONSE_ID='

echo "=== clarify marker id=0 ignored (aligns with posting helper) ==="
run_case 'id0ignored' '[{"body":"<!-- larch:clarify-request id=0 -->\nmore"}]' \
    'STATE=clean' 'LAST_REQUEST_ID=' 'LAST_RESPONSE_ID='

echo "=== one request no response ==="
run_case 'await' '[{"body":"<!-- larch:clarify-request id=1 -->\nhi"}]' \
    'STATE=awaiting-response' 'LAST_REQUEST_ID=1' 'LAST_RESPONSE_ID='

echo "=== one request matching response ==="
run_case 'pending' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"}]' \
    'STATE=response-pending' 'LAST_REQUEST_ID=1' 'LAST_RESPONSE_ID=1'

echo "=== two requests same id ==="
run_case 'dupreq' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-request id=1 -->"}]' \
    'STATE=ambiguous' 'LAST_REQUEST_ID=1' 'LAST_RESPONSE_ID='

echo "=== two responses same id ==="
run_case 'dupresp' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"}]' \
    'STATE=ambiguous' 'LAST_REQUEST_ID=1' 'LAST_RESPONSE_ID=1'

echo "=== response without prior request ==="
run_case 'orphan' '[{"body":"<!-- larch:clarify-response id=1 -->"}]' \
    'STATE=ambiguous' 'LAST_REQUEST_ID=' 'LAST_RESPONSE_ID=1'

echo "=== non-monotonic ids ==="
run_case 'nonmono' '[{"body":"<!-- larch:clarify-request id=2 -->"},{"body":"<!-- larch:clarify-request id=1 -->"}]' \
    'STATE=ambiguous' 'LAST_REQUEST_ID=1' 'LAST_RESPONSE_ID='

echo "=== gap: response for id=2 before id=1 satisfied ==="
run_case 'gap_high_response' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-request id=2 -->"},{"body":"<!-- larch:clarify-response id=2 -->"}]' \
    'STATE=ambiguous' 'LAST_REQUEST_ID=2' 'LAST_RESPONSE_ID=2'

echo "=== multi-round completed ==="
run_case 'multi_done' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"},{"body":"<!-- larch:clarify-request id=2 -->"},{"body":"<!-- larch:clarify-response id=2 -->"}]' \
    'STATE=response-pending' 'LAST_REQUEST_ID=2' 'LAST_RESPONSE_ID=2'

echo "=== multi-round in progress ==="
run_case 'multi_prog' '[{"body":"<!-- larch:clarify-request id=1 -->"},{"body":"<!-- larch:clarify-response id=1 -->"},{"body":"<!-- larch:clarify-request id=2 -->"}]' \
    'STATE=awaiting-response' 'LAST_REQUEST_ID=2' 'LAST_RESPONSE_ID=1'

echo "=== gh api pagination merge (two JSON roots) ==="
run_case_dual 'paginate_merge' \
    '[{"body":"<!-- larch:clarify-request id=1 -->"}]' \
    '[{"body":"<!-- larch:clarify-response id=1 -->"}]' \
    'STATE=response-pending' 'LAST_REQUEST_ID=1' 'LAST_RESPONSE_ID=1'

LABEL="$REPO_ROOT/scripts/clarify-label.sh"
[ -x "$LABEL" ] || fail "clarify-label.sh not executable"
grep -Fq -- '--create-if-missing' "$LABEL" || fail "clarify-label.sh missing --create-if-missing argv"

echo "=== clarify-label: --create-if-missing stubbed gh ==="
LABEL_STUB="$TMP/label-stub"
LABEL_LOG="$TMP/gh-label-create.log"
mkdir -p "$LABEL_STUB"
: > "$LABEL_LOG"
cat > "$LABEL_STUB/gh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [ "\$1" = "repo" ] && [ "\$2" = "view" ]; then
    printf '%s\n' 'owner/repo'
    exit 0
fi
if [ "\$1" = "issue" ] && [ "\$2" = "view" ]; then
    printf '%s\n' 'needs-other-label'
    exit 0
fi
if [ "\$1" = "label" ] && [ "\$2" = "create" ]; then
    printf 'create\n' >> "$LABEL_LOG"
    exit 0
fi
if [ "\$1" = "issue" ] && [ "\$2" = "edit" ]; then
    exit 0
fi
echo "label-stub: unhandled \$*" >&2
exit 2
EOF
chmod +x "$LABEL_STUB/gh"
set +e
out1="$(PATH="$LABEL_STUB:$ORIG_PATH" "$LABEL" --issue 7 --action add --create-if-missing --repo owner/repo 2>&1)"
rc1=$?
out2="$(PATH="$LABEL_STUB:$ORIG_PATH" "$LABEL" --issue 7 --action add --create-if-missing --repo owner/repo 2>&1)"
rc2=$?
set -e
[ "$rc1" = "0" ] || fail "clarify-label first add exit $rc1: $out1"
[ "$rc2" = "0" ] || fail "clarify-label second add exit $rc2: $out2"
creates=$(wc -l < "$LABEL_LOG" | tr -d ' ')
[ "$creates" = "2" ] || fail "expected gh label create twice (once per invocation), got $creates"

echo "All assertions passed."
