#!/usr/bin/env bash
# test-tracking-issue-summary.sh — slim summary upsert harness.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SUMMARY="$SCRIPT_DIR/tracking-issue-summary.sh"

[ -x "$SUMMARY" ] || { echo "FAIL: $SUMMARY not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-tracking-issue-summary.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

build_stub() {
    local dir="$1"
    local mode="$2"
    mkdir -p "$dir"
    cat > "$dir/gh" <<'GHSTUB'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then
    echo "owner/repo"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "comment" ]; then
    for ((i=1; i<=$#; i++)); do
        if [ "${!i}" = "--body-file" ]; then
            next=$((i + 1))
            cp "${!next}" "$BODY_CAPTURE"
        fi
    done
    echo "https://github.com/owner/repo/issues/7#issuecomment-100"
    exit 0
fi
if [ "$1" = "api" ]; then
    if [ "${STUB_MODE}" = "zero" ]; then
        exit 0
    fi
    if [ "${STUB_MODE}" = "one" ]; then
        if printf '%s\n' "$@" | grep -qx -- "PATCH"; then
            for ((i=1; i<=$#; i++)); do
                if [ "${!i}" = "--input" ]; then
                    next=$((i + 1))
                    jq -r '.body' < "${!next}" > "$BODY_CAPTURE"
                fi
            done
            echo "https://github.com/owner/repo/issues/7#issuecomment-200"
            exit 0
        fi
        printf '200\t<!-- larch:plan v1 runid=abc123 -->\n'
        exit 0
    fi
    if [ "${STUB_MODE}" = "one-stable" ]; then
        if printf '%s\n' "$@" | grep -qx -- "PATCH"; then
            for ((i=1; i<=$#; i++)); do
                if [ "${!i}" = "--input" ]; then
                    next=$((i + 1))
                    jq -r '.body' < "${!next}" > "$BODY_CAPTURE"
                fi
            done
            echo "https://github.com/owner/repo/issues/7#issuecomment-200"
            exit 0
        fi
        printf '200\t<!-- larch:diagrams v1 -->\n'
        exit 0
    fi
    if [ "${STUB_MODE}" = "multi" ]; then
        printf '200\t<!-- larch:plan v1 runid=abc123 -->\n'
        printf '201\t<!-- larch:plan v1 runid=abc123 -->\n'
        exit 0
    fi
fi
exit 1
GHSTUB
    chmod +x "$dir/gh"
    STUB_DIR="$dir"
    export PATH="$STUB_DIR:$ORIG_PATH"
    export STUB_MODE="$mode"
    export BODY_CAPTURE="$TMP/body-$mode.txt"
}

ORIG_PATH="$PATH"
content="$TMP/content.md"
printf 'hello sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n' > "$content"

echo "=== create path ==="
build_stub "$TMP/stub-zero" zero
out="$("$SUMMARY" upsert-summary --issue 7 --marker '<!-- larch:plan v1 runid=abc123 -->' --content-file "$content" --repo owner/repo)"
[[ "$out" == *"UPDATED=false"* ]] || { echo "FAIL: create did not report UPDATED=false: $out" >&2; exit 1; }
grep -q '^<!-- larch:plan v1 runid=abc123 -->$' "$BODY_CAPTURE"
grep -q '<REDACTED-TOKEN>' "$BODY_CAPTURE"

echo "=== update path ==="
build_stub "$TMP/stub-one" one
out="$("$SUMMARY" upsert-summary --issue 7 --marker '<!-- larch:plan v1 runid=abc123 -->' --content-file "$content" --repo owner/repo)"
[[ "$out" == *"COMMENT_ID=200"* ]] || { echo "FAIL: update did not report comment id: $out" >&2; exit 1; }
[[ "$out" == *"UPDATED=true"* ]] || { echo "FAIL: update did not report UPDATED=true: $out" >&2; exit 1; }

stable_content="$TMP/stable-content.md"
cat > "$stable_content" <<'EOF'
## Code Flow Diagram

```mermaid
graph TD
  A --> B
```
EOF

echo "=== stable marker create path ==="
build_stub "$TMP/stub-stable-create" zero
out="$("$SUMMARY" upsert-summary --issue 7 --marker '<!-- larch:diagrams v1 -->' --content-file "$stable_content" --repo owner/repo)"
[[ "$out" == *"UPDATED=false"* ]] || { echo "FAIL: stable create did not report UPDATED=false: $out" >&2; exit 1; }
stable_marker_count=$(grep -c '^<!-- larch:diagrams v1 -->$' "$BODY_CAPTURE" 2>/dev/null || true)
[[ "$stable_marker_count" == "1" ]] || { echo "FAIL: stable create marker count $stable_marker_count" >&2; exit 1; }
grep -q '^## Code Flow Diagram$' "$BODY_CAPTURE" || { echo "FAIL: stable create missing code flow heading" >&2; exit 1; }

echo "=== stable marker update path ==="
build_stub "$TMP/stub-stable-update" one-stable
out="$("$SUMMARY" upsert-summary --issue 7 --marker '<!-- larch:diagrams v1 -->' --content-file "$stable_content" --repo owner/repo)"
[[ "$out" == *"COMMENT_ID=200"* ]] || { echo "FAIL: stable update did not report comment id: $out" >&2; exit 1; }
[[ "$out" == *"UPDATED=true"* ]] || { echo "FAIL: stable update did not report UPDATED=true: $out" >&2; exit 1; }
stable_marker_count=$(grep -c '^<!-- larch:diagrams v1 -->$' "$BODY_CAPTURE" 2>/dev/null || true)
[[ "$stable_marker_count" == "1" ]] || { echo "FAIL: stable update marker count $stable_marker_count" >&2; exit 1; }
grep -q '^## Code Flow Diagram$' "$BODY_CAPTURE" || { echo "FAIL: stable update missing code flow heading" >&2; exit 1; }

echo "=== multiple matches fail closed ==="
build_stub "$TMP/stub-multi" multi
set +e
out="$("$SUMMARY" upsert-summary --issue 7 --marker '<!-- larch:plan v1 runid=abc123 -->' --content-file "$content" --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || { echo "FAIL: multi exit $rc" >&2; exit 1; }
[[ "$out" == *"multiple summary comments found"* ]] || { echo "FAIL: multi error missing: $out" >&2; exit 1; }

echo "All assertions passed."
