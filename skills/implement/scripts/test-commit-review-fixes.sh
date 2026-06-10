#!/usr/bin/env bash
# test-commit-review-fixes.sh — offline harness for commit-review-fixes.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/commit-review-fixes.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-commit-review-fixes.XXXXXX")"
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
cat > "$plugin/scripts/token-ledger.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
cat > "$plugin/scripts/timing-ledger.sh" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$plugin/scripts/token-ledger.sh" "$plugin/scripts/timing-ledger.sh"

repo="$TMP_ROOT/repo"; mkdir -p "$repo"; git -C "$repo" init -q; git -C "$repo" config user.email a@b.test; git -C "$repo" config user.name tester
printf 'x\n' > "$repo/file.txt"; git -C "$repo" add file.txt; git -C "$repo" commit -qm init
out=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args.log" "$HELPER" file.txt)
assert_contains 'COMMITTED=true' "$out" 'happy path emits committed true'
assert_contains 'Address code review feedback' "$(cat "$TMP_ROOT/args.log")" 'default message used'

# Bash 3.2 regression: no-arg invocation must not abort on FILES[@] unbound variable
out_noarg=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args-noarg.log" "$HELPER")
assert_contains 'COMMITTED=true' "$out_noarg" 'no-arg invocation emits committed true'

printf 'review fix\n' > "$repo/review-fix.txt"
out_stage=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args-stage.log" "$HELPER" --stage-all)
assert_contains 'COMMITTED=true' "$out_stage" 'stage-all invocation emits committed true'
staged_names=$(git -C "$repo" diff --cached --name-only)
assert_contains 'review-fix.txt' "$staged_names" '--stage-all stages untracked review fix'

set +e
failed=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" GIT_COMMIT_ARGS_LOG="$TMP_ROOT/args.log" GIT_COMMIT_RC=9 GIT_COMMIT_ERR='commit hook failed' "$HELPER" file.txt 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 9 ]; then pass 'helper failure preserves exit code'; else fail 'helper failure preserves exit code'; fi
assert_contains 'COMMITTED=false' "$failed" 'helper failure emits committed false'
assert_contains 'ERROR=commit hook failed' "$failed" 'helper failure surfaces stderr'

set +e
bad=$(cd "$repo" && CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --bogus 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'unknown option exits non-zero'; else fail 'unknown option exits non-zero'; fi
assert_contains 'COMMITTED=false' "$bad" 'usage error emits envelope'

finish
