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
printf '%s' "${GIT_COMMIT_ERR:-}" >&2
exit "${GIT_COMMIT_RC:-0}"
STUB
chmod +x "$plugin/scripts/git-commit.sh"

repo="$TMP_ROOT/repo"; mkdir -p "$repo"; git -C "$repo" init -q; git -C "$repo" config user.email a@b.test; git -C "$repo" config user.name tester
printf 'x\n' > "$repo/file.txt"; git -C "$repo" add file.txt; git -C "$repo" commit -qm init
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args.log" "$HELPER" --message "Implement thing" file.txt)
assert_contains 'COMMITTED=true' "$out" 'happy path emits committed true'
assert_contains 'SHA=' "$out" 'happy path emits SHA key'
assert_contains '-m Implement thing file.txt' "$(cat "$TMP_ROOT/args.log")" 'passes message and files'

printf 'file.txt\0' > "$TMP_ROOT/paths.nul"
out_pathspec=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/pathspec-args.log" "$HELPER" --message "Recover thing" --pathspec-from-file "$TMP_ROOT/paths.nul" --pathspec-file-nul ignored.txt)
assert_contains 'COMMITTED=true' "$out_pathspec" 'pathspec mode emits committed true'
assert_contains "-m Recover thing --only --pathspec-from-file $TMP_ROOT/paths.nul --pathspec-file-nul" "$(cat "$TMP_ROOT/pathspec-args.log")" 'pathspec mode forwards only and nul flags'
if [[ "$(cat "$TMP_ROOT/pathspec-args.log")" != *"ignored.txt"* ]]; then
    pass 'pathspec mode ignores positional files'
else
    fail 'pathspec mode ignores positional files'
fi

set +e
failed=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args.log" GIT_COMMIT_RC=7 GIT_COMMIT_ERR='hook rejected commit' "$HELPER" --message "Implement thing" file.txt 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 7 ]; then pass 'helper failure preserves exit code'; else fail 'helper failure preserves exit code'; fi
assert_contains 'COMMITTED=false' "$failed" 'helper failure emits committed false'
assert_contains 'ERROR=hook rejected commit' "$failed" 'helper failure surfaces stderr'

set +e
bad=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" file.txt 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing message exits non-zero'; else fail 'missing message exits non-zero'; fi
assert_contains 'COMMITTED=false' "$bad" 'missing message emits envelope'

finish
