#!/usr/bin/env bash
# test-generate-code-flow-diagram.sh — offline harness for generate-code-flow-diagram.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/generate-code-flow-diagram.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-generate-code-flow-diagram.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cat > "$plugin/scripts/launch-claude-subprocess.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [ $# -gt 0 ]; do case "$1" in --output-file) out=$2; shift 2 ;; *) shift ;; esac; done
cat > "$out" <<'EOF'
## Code Flow Diagram

```mermaid
flowchart TD
  A[Start] --> B[Done]
```
EOF
printf 'STATUS=OK\n'
STUB
cat > "$plugin/scripts/sanitize-mermaid-fragment.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${SANITIZE_REJECT:-}" = 1 ]; then printf 'STATUS=rejected\nREASON_TOKEN=test-reject\n'; exit 1; fi
printf 'STATUS=ok\n'
STUB
chmod +x "$plugin/scripts/launch-claude-subprocess.sh" "$plugin/scripts/sanitize-mermaid-fragment.sh"

repo="$TMP_ROOT/repo"; mkdir -p "$repo"; git -C "$repo" init -q; git -C "$repo" config user.email a@b.test; git -C "$repo" config user.name tester
printf 'x\n' > "$repo/file.txt"; git -C "$repo" add file.txt; git -C "$repo" commit -qm init
tmp="$TMP_ROOT/session"; mkdir -p "$tmp"
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --implement-tmpdir "$tmp")
assert_contains 'STATUS=ok' "$out" 'happy path emits ok'
assert_contains 'DIAGRAM_FILE=' "$out" 'happy path emits diagram file'
if [ -s "$tmp/code-flow-diagram.md" ]; then pass 'diagram promoted'; else fail 'diagram promoted'; fi

tmp2="$TMP_ROOT/session2"; mkdir -p "$tmp2"
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" SANITIZE_REJECT=1 "$HELPER" --implement-tmpdir "$tmp2")
assert_contains 'STATUS=skipped' "$out" 'sanitizer rejection is skippable'
assert_contains 'SKIP_REASON=test-reject' "$out" 'rejection reason emitted'

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing tmpdir exits non-zero'; else fail 'missing tmpdir exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing args emits envelope'

finish
