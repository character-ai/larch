#!/usr/bin/env bash
# test-post-tracking-issue.sh — offline harness for post-tracking-issue.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/post-tracking-issue.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-post-tracking-issue.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0
FAIL=0

pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)"; printf 'ACTUAL: %s\n' "$2" >&2 ;; esac; }
finish(){ if [ "$FAIL" -ne 0 ]; then printf 'FAILURES=%s\n' "$FAIL" >&2; exit 1; fi; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"
mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cat > "$plugin/scripts/read-plugin-version.sh" <<'STUB'
#!/usr/bin/env bash
printf 'LARCH_PLUGIN_VERSION=9.9.9\n'
STUB
cat > "$plugin/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" > "${TRACKING_ARGS_LOG:?}"
while [ $# -gt 0 ]; do
  case "$1" in
    --content-file) cp "$2" "${TRACKING_CONTENT_LOG:?}"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'COMMENT_URL=https://example.test/comment/1\n'
STUB
chmod +x "$plugin/scripts/read-plugin-version.sh" "$plugin/scripts/tracking-issue-summary.sh"

# Happy path: IMPLEMENT_TMPDIR with parent-issue.md and session-env.sh
impl_dir="$TMP_ROOT/impl"
mkdir -p "$impl_dir"
printf 'ISSUE_NUMBER=12\nRUN_ID=run-1\nADOPTED=true\n' > "$impl_dir/parent-issue.md"
printf 'REPO=owner/repo\nCODER=codex\n' > "$impl_dir/session-env.sh"

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" \
      "$HELPER" --implement-tmpdir "$impl_dir")
assert_contains 'POSTED=true' "$out" 'happy path posts'
assert_contains 'COMMENT_URL=https://example.test/comment/1' "$out" 'happy path emits URL'
assert_contains '<!-- larch:metadata v1 runid=run-1 -->' "$(cat "$TMP_ROOT/args.log")" 'marker passed'
assert_contains "Coder: \`codex\`" "$(cat "$TMP_ROOT/content.md")" 'content includes coder from session-env'
assert_contains "Larch version: \`9.9.9\`" "$(cat "$TMP_ROOT/content.md")" 'content includes version'

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args-em.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content-em.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested true)
assert_contains 'POSTED=true' "$out" 'emergency metadata posts'
assert_contains 'Emergency: true' "$(cat "$TMP_ROOT/content-em.md")" 'emergency metadata includes line'

out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args-emf.log" \
      TRACKING_CONTENT_LOG="$TMP_ROOT/content-emf.md" \
      "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested false)
assert_contains 'POSTED=true' "$out" 'non-emergency metadata posts'
if grep -Fq 'Emergency: true' "$TMP_ROOT/content-emf.md"; then
    fail 'non-emergency metadata omits line'
else
    pass 'non-emergency metadata omits line'
fi

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --implement-tmpdir "$impl_dir" --emergency-requested maybe 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 2 ]; then pass 'invalid emergency flag exits 2'; else fail 'invalid emergency flag exits 2'; fi
assert_contains 'POSTED=false' "$bad" 'invalid emergency flag emits envelope'
assert_contains 'ERROR=--emergency-requested must be true or false' "$bad" 'invalid emergency flag emits validation error'

# Missing --implement-tmpdir
set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing --implement-tmpdir exits non-zero'; else fail 'missing --implement-tmpdir exits non-zero'; fi
assert_contains 'POSTED=false' "$bad" 'missing arg emits envelope'

finish
