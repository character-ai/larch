#!/usr/bin/env bash
# test-commit-implementation.sh — offline harness for commit-implementation.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/commit-implementation.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-commit-implementation.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cat > "$plugin/scripts/git-commit.sh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${GIT_COMMIT_ARGS_LOG:?}"
exit "${GIT_COMMIT_RC:-0}"
STUB
chmod +x "$plugin/scripts/git-commit.sh"

repo="$TMP_ROOT/repo"; mkdir -p "$repo"; git -C "$repo" init -q; git -C "$repo" config user.email a@b.test; git -C "$repo" config user.name tester
printf 'x\n' > "$repo/file.txt"; git -C "$repo" add file.txt; git -C "$repo" commit -qm init
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args.log" "$HELPER" --message "Implement thing" file.txt)
assert_contains 'COMMITTED=true' "$out" 'happy path emits committed true'
assert_contains 'SHA=' "$out" 'happy path emits SHA key'
assert_contains '-m Implement thing file.txt' "$(cat "$TMP_ROOT/args.log")" 'passes message and files'

set +e
bad=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" file.txt 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing message exits non-zero'; else fail 'missing message exits non-zero'; fi
assert_contains 'COMMITTED=false' "$bad" 'missing message emits envelope'

finish
