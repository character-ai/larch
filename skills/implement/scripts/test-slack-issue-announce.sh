#!/usr/bin/env bash
# test-slack-issue-announce.sh — offline harness for slack-issue-announce.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/slack-issue-announce.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-slack-issue-announce.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"

# Build IMPLEMENT_TMPDIR with parent-issue.md and ship-pr-state.sh
impl_dir="$TMP_ROOT/impl"; mkdir -p "$impl_dir"
printf 'ISSUE_NUMBER=9\nRUN_ID=run-4\nADOPTED=true\n' > "$impl_dir/parent-issue.md"
printf 'PR_URL=https://example.test/pr/1\nPR_TITLE=A PR\n' > "$impl_dir/ship-pr-state.sh"

# Missing webhook → skipped
out=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'STATUS=skipped' "$out" 'missing webhook skips'
assert_contains 'REASON=webhook-not-set' "$out" 'skip reason emitted'

# With webhook + fake curl → posted
fake="$TMP_ROOT/fake-curl"
cat > "$fake" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${CURL_ARGS_LOG:?}"
exit 0
STUB
chmod +x "$fake"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" LARCH_SLACK_WEBHOOK_URL=https://hooks.example.test \
      __LARCH_FAKE_CURL="$fake" CURL_ARGS_LOG="$TMP_ROOT/curl.log" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'STATUS=posted' "$out" 'webhook posts'
assert_contains 'https://hooks.example.test' "$(cat "$TMP_ROOT/curl.log")" 'curl receives webhook'

# Missing --implement-tmpdir
set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing arg exits non-zero'; else fail 'missing arg exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing arg emits envelope'

finish
