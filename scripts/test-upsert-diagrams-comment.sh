#!/usr/bin/env bash
# test-upsert-diagrams-comment.sh — offline harness for upsert-diagrams-comment.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/upsert-diagrams-comment.sh"

[ -x "$HELPER" ] || { echo "FAIL: $HELPER not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-upsert-diagrams-comment.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

ORIG_PATH="$PATH"
PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail_assert() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -Fq -- "$needle"; then pass "$label"; else fail_assert "$label (missing: $needle)"; fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -Fq -- "$needle"; then fail_assert "$label (unexpected: $needle)"; else pass "$label"; fi
}

assert_file_contains() {
    local needle=$1 path=$2 label=$3
    assert_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

assert_file_not_contains() {
    local needle=$1 path=$2 label=$3
    assert_not_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

assert_file_lacks_line() {
    local needle=$1 path=$2 label=$3
    if grep -Fxq -- "$needle" "$path" 2>/dev/null; then
        fail_assert "$label (unexpected line: $needle)"
    else
        pass "$label"
    fi
}

assert_equals() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then pass "$label"; else fail_assert "$label (expected $expected got $actual)"; fi
}

finish() {
    printf 'PASS=%s\nFAIL=%s\n' "$PASS" "$FAIL"
    [ "$FAIL" -eq 0 ]
}

build_stub() {
    local dir=$1 mode=$2
    mkdir -p "$dir"
    cat >"$dir/gh" <<'GHSTUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'gh %s\n' "$*" >> "$GH_CALLS"
if [ "$1" = "repo" ]; then
    printf 'owner/repo\n'
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "comment" ]; then
    for ((i=1; i<=$#; i++)); do
        if [ "${!i}" = "--body-file" ]; then
            next=$((i + 1))
            cp "${!next}" "$BODY_CAPTURE"
        fi
    done
    printf 'https://github.com/owner/repo/issues/7#issuecomment-900\n'
    exit 0
fi
if [ "$1" = "api" ]; then
    endpoint=$2
    if [[ "$endpoint" == "/repos/owner/repo/issues/7/comments" ]]; then
        case "$STUB_MODE" in
            none) : ;;
            arch|code|both|fence|redact-existing)
                printf '101\t<!-- larch:diagrams v1 -->\n'
                ;;
            bom-crlf)
                printf '101\t\xef\xbb\xbf<!-- larch:diagrams v1 -->\r\n'
                ;;
            legacy)
                printf '77\t<!-- larch:diagrams v1 runid=old -->\n'
                ;;
            duplicate)
                printf '101\t<!-- larch:diagrams v1 -->\n'
                printf '102\t<!-- larch:diagrams v1 -->\n'
                ;;
            gh-error)
                printf 'token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD leaked\n' >&2
                exit 1
                ;;
        esac
        exit 0
    fi
    if [[ "$endpoint" == "/repos/owner/repo/issues/comments/101" ]]; then
        if printf '%s\n' "$@" | grep -qx -- "DELETE"; then
            printf 'delete 101\n' >> "$GH_CALLS"
            exit 0
        fi
        if printf '%s\n' "$@" | grep -qx -- "PATCH"; then
            for ((i=1; i<=$#; i++)); do
                if [ "${!i}" = "--input" ]; then
                    next=$((i + 1))
                    jq -r '.body' < "${!next}" > "$BODY_CAPTURE"
                fi
            done
            printf 'https://github.com/owner/repo/issues/7#issuecomment-101\n'
            exit 0
        fi
        cat "$EXISTING_BODY"
        exit 0
    fi
fi
exit 1
GHSTUB
    chmod +x "$dir/gh"
    export PATH="$dir:$ORIG_PATH"
    export STUB_MODE="$mode"
}

new_case() {
    local name=$1 mode=$2
    CASE="$TMP/$name"
    mkdir -p "$CASE"
    : >"$CASE/calls.log"
    export GH_CALLS="$CASE/calls.log"
    export BODY_CAPTURE="$CASE/body.txt"
    export EXISTING_BODY="$CASE/existing.md"
    build_stub "$CASE/stub" "$mode"
}

write_arch() {
    local path=$1 text=${2:-"Design core"}
    cat >"$path" <<EOF
## Architecture Diagram

\`\`\`mermaid
graph TD
  A["$text"] --> B["Runtime"]
\`\`\`
EOF
}

write_code() {
    local path=$1 text=${2:-"Call core"}
    cat >"$path" <<EOF
## Code Flow Diagram

\`\`\`mermaid
sequenceDiagram
  participant A as Client
  participant B as "$text"
  A->>B: request
\`\`\`
EOF
}

write_existing_arch() {
    cat >"$EXISTING_BODY" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```mermaid
graph TD
  A["Existing	Tab"] --> B["literal \n text"]
```
EOF
}

write_existing_code() {
    cat >"$EXISTING_BODY" <<'EOF'
<!-- larch:diagrams v1 -->

## Code Flow Diagram

```mermaid
graph TD
  X --> Y
```
EOF
}

write_existing_both_with_fence_heading() {
    cat >"$EXISTING_BODY" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```mermaid
graph TD
  A["## Code Flow Diagram inside label"] --> B
```

## Code Flow Diagram

```mermaid
graph TD
  C["## Architecture Diagram inside label"] --> D
```
EOF
}

write_existing_arch_plain_fence_heading() {
    cat >"$EXISTING_BODY" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```text
## Code Flow Diagram
literal text
```
EOF
}

write_existing_arch_unclosed_fence() {
    cat >"$EXISTING_BODY" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```mermaid
graph TD
  A --> B

## Code Flow Diagram

```mermaid
sequenceDiagram
  A->>B: preserved
```
EOF
}

write_existing_arch_unsafe_mermaid() {
    cat >"$EXISTING_BODY" <<'EOF'
<!-- larch:diagrams v1 -->

## Architecture Diagram

```mermaid
graph TD
  A[bad|pipe] --> B
```
EOF
}

echo "=== test-upsert-diagrams-comment ==="

new_case create-arch none
arch="$CASE/arch.md"
write_arch "$arch"
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$arch")"
assert_contains "UPSERT_STATUS=ok" "$out" "create architecture status ok"
assert_contains "ARCHITECTURE_SOURCE=new" "$out" "create architecture source new"
assert_contains "CODE_FLOW_SOURCE=absent" "$out" "create architecture code absent"
assert_file_contains "<!-- larch:diagrams v1 -->" "$BODY_CAPTURE" "create body has stable marker"
assert_file_contains "## Architecture Diagram" "$BODY_CAPTURE" "create body has architecture section"
assert_file_not_contains "runid=" "$BODY_CAPTURE" "create body omits runid marker"

new_case create-code none
code="$CASE/code.md"
write_code "$code"
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code")"
assert_contains "CODE_FLOW_SOURCE=new" "$out" "create code source new"
assert_file_contains "## Code Flow Diagram" "$BODY_CAPTURE" "create body has code section"
assert_file_not_contains "Architecture diagram not available" "$BODY_CAPTURE" "create code has no architecture placeholder"

new_case preserve-arch arch
write_existing_arch
code="$CASE/code.md"
write_code "$code" "New code"
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code")"
assert_contains "ARCHITECTURE_SOURCE=preserved" "$out" "preserve arch source"
assert_file_contains $'Existing\tTab' "$BODY_CAPTURE" "preserve arch keeps tab"
assert_file_contains 'literal \n text' "$BODY_CAPTURE" "preserve arch keeps literal slash-n"
assert_file_contains "New code" "$BODY_CAPTURE" "preserve arch replaces code"

new_case preserve-code code
write_existing_code
arch="$CASE/arch.md"
write_arch "$arch" "New arch"
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$arch")"
assert_contains "CODE_FLOW_SOURCE=preserved" "$out" "preserve code source"
assert_file_contains "New arch" "$BODY_CAPTURE" "preserve code writes architecture"
assert_file_contains "X --> Y" "$BODY_CAPTURE" "preserve code keeps prior code"

new_case clear-arch both
write_existing_both_with_fence_heading
out="$("$HELPER" --issue 7 --repo owner/repo --clear-architecture)"
assert_contains "ARCHITECTURE_SOURCE=cleared" "$out" "clear architecture source"
assert_file_lacks_line "## Architecture Diagram" "$BODY_CAPTURE" "clear architecture removes top-level section"
assert_file_contains "## Code Flow Diagram" "$BODY_CAPTURE" "clear architecture preserves code"

new_case clear-arch-arch-only arch
write_existing_arch
out="$("$HELPER" --issue 7 --repo owner/repo --clear-architecture)"
assert_contains "UPSERT_STATUS=ok" "$out" "clear architecture only deletes comment"
assert_contains "UPDATED=true" "$out" "clear architecture only reports update"
assert_contains "delete 101" "$(cat "$GH_CALLS")" "clear architecture only deletes existing comment"
assert_not_contains "PATCH" "$(cat "$GH_CALLS")" "clear architecture only skips patch"
if [ ! -e "$BODY_CAPTURE" ]; then pass "clear architecture only leaves no replacement body"; else fail_assert "clear architecture only leaves no replacement body"; fi

new_case clear-code both
write_existing_both_with_fence_heading
out="$("$HELPER" --issue 7 --repo owner/repo --clear-code-flow)"
assert_contains "CODE_FLOW_SOURCE=cleared" "$out" "clear code source"
assert_file_contains "## Architecture Diagram" "$BODY_CAPTURE" "clear code preserves architecture"
assert_file_lacks_line "## Code Flow Diagram" "$BODY_CAPTURE" "clear code removes top-level section"

new_case clear-arch-no-comment none
out="$("$HELPER" --issue 7 --repo owner/repo --clear-architecture)"
assert_contains "UPSERT_STATUS=no-op" "$out" "clear architecture without comment is no-op"
assert_contains "ARCHITECTURE_SOURCE=absent" "$out" "clear architecture without comment reports absent source"
assert_not_contains "gh issue comment" "$(cat "$GH_CALLS")" "clear architecture without comment skips create"
assert_not_contains "PATCH" "$(cat "$GH_CALLS")" "clear architecture without comment skips patch"
assert_not_contains "DELETE" "$(cat "$GH_CALLS")" "clear architecture without comment skips delete"

new_case empty-file-preserve both
write_existing_both_with_fence_heading
empty="$CASE/empty.md"
: >"$empty"
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$empty")"
assert_contains "ARCHITECTURE_SOURCE=preserved" "$out" "empty architecture file preserves"
assert_file_contains "## Architecture Diagram" "$BODY_CAPTURE" "empty file keeps architecture"
assert_file_contains "## Code Flow Diagram" "$BODY_CAPTURE" "empty file keeps code"

new_case fence both
write_existing_both_with_fence_heading
arch="$CASE/arch.md"
write_arch "$arch" "Replacement"
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$arch")"
assert_contains "CODE_FLOW_SOURCE=preserved" "$out" "fence preserves code"
assert_file_contains '## Architecture Diagram inside label' "$BODY_CAPTURE" "fence parser ignores heading inside mermaid"

new_case plain-fence arch
write_existing_arch_plain_fence_heading
code="$CASE/code.md"
write_code "$code" "Replacement code"
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code")"
assert_contains "ARCHITECTURE_SOURCE=preserved" "$out" "plain fence preserves architecture section"
assert_file_contains "$(printf '```text')" "$BODY_CAPTURE" "plain fence keeps non-mermaid fence"
assert_file_contains "Replacement code" "$BODY_CAPTURE" "plain fence replaces code section"

new_case unclosed-fence arch
write_existing_arch_unclosed_fence
code="$CASE/code.md"
write_code "$code" "Replacement code"
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code")"
assert_contains "ARCHITECTURE_SOURCE=preserved" "$out" "unclosed fence preserves architecture section"
assert_file_contains "## Architecture Diagram" "$BODY_CAPTURE" "unclosed fence keeps architecture heading"
assert_file_contains "## Code Flow Diagram" "$BODY_CAPTURE" "unclosed fence keeps code heading"
assert_file_contains "Replacement code" "$BODY_CAPTURE" "unclosed fence replaces code section"
assert_file_not_contains "A->>B: preserved" "$BODY_CAPTURE" "unclosed fence drops malformed preserved tail"

new_case bom-crlf-marker bom-crlf
write_existing_arch
code="$CASE/code.md"
write_code "$code" "BOM code"
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code")"
assert_contains "UPSERT_STATUS=ok" "$out" "bom-crlf marker matches stable comment"
assert_file_contains "BOM code" "$BODY_CAPTURE" "bom-crlf marker updates existing comment"

new_case preserved-unsafe-mermaid arch
write_existing_arch_unsafe_mermaid
code="$CASE/code.md"
write_code "$code" "Replacement code"
set +e
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code" 2>&1)"
rc=$?
set -e
assert_equals 1 "$rc" "preserved unsafe mermaid exits 1"
assert_contains "sanitize-mermaid-fragment.sh rejected architecture section" "$out" "preserved unsafe mermaid reports sanitizer rejection"
assert_not_contains "PATCH" "$(cat "$GH_CALLS")" "preserved unsafe mermaid skips patch"

new_case legacy legacy
code="$CASE/code.md"
write_code "$code"
out="$("$HELPER" --issue 7 --repo owner/repo --code-flow-file "$code")"
assert_contains "UPSERT_STATUS=ok" "$out" "legacy orphan ignored"
assert_file_contains "## Code Flow Diagram" "$BODY_CAPTURE" "legacy orphan creates stable comment"

new_case dry-run none
arch="$CASE/arch.md"
write_arch "$arch" 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD'
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$arch" --dry-run)"
assert_contains "--- content-file ---" "$out" "dry run emits second preview"
assert_contains "<REDACTED-TOKEN>" "$out" "dry run redacts secrets"
assert_not_contains "gh " "$(cat "$GH_CALLS")" "dry run performs no gh calls"

new_case redact none
arch="$CASE/arch.md"
write_arch "$arch" 'sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD'
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$arch")"
assert_file_contains "<REDACTED-TOKEN>" "$BODY_CAPTURE" "upsert redacts before publish"
assert_file_not_contains "sk-ant-" "$BODY_CAPTURE" "upsert removes secret literal"
marker_count=$(grep -c '<!-- larch:diagrams v1 -->' "$BODY_CAPTURE" 2>/dev/null || true)
assert_equals 1 "$marker_count" "content-file did not duplicate marker"

new_case duplicate duplicate
set +e
out="$("$HELPER" --issue 7 --repo owner/repo --clear-code-flow 2>&1)"
rc=$?
set -e
assert_equals 2 "$rc" "duplicate marker exits 2"
assert_contains "multiple summary comments found" "$out" "duplicate marker reports ids"

new_case gh-error gh-error
set +e
out="$("$HELPER" --issue 7 --repo owner/repo --clear-code-flow 2>&1)"
rc=$?
set -e
assert_equals 2 "$rc" "gh-error exits 2"
assert_contains "gh api comments fetch failed:" "$out" "gh-error reports redacted fetch failure"
assert_contains "<REDACTED-TOKEN>" "$out" "gh-error redacts token-shaped stderr"
assert_not_contains "sk-ant-" "$out" "gh-error does not leak raw token"

new_case external-path-denied none
set +e
out="$("$HELPER" --issue 7 --repo owner/repo --architecture-file "$SCRIPT_DIR/upsert-diagrams-comment.sh" --dry-run 2>&1)"
rc=$?
set -e
assert_equals 1 "$rc" "external path denied exits 1"
assert_contains "architecture file must be under a temporary directory" "$out" "external path denied reports tmpdir restriction"

finish
