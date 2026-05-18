#!/usr/bin/env bash
# test-post-tracking-issue.sh — offline harness for post-tracking-issue.sh.
# shellcheck disable=SC2016

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
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
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

session="$TMP_ROOT/session"
mkdir -p "$session"
printf 'REPO=owner/repo\n' > "$session/session-env.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_ARGS_LOG="$TMP_ROOT/args.log" TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" "$HELPER" --issue 12 --run-id run-1 --session-env "$session/session-env.sh" --coder codex)
assert_contains 'POSTED=true' "$out" 'happy path posts'
assert_contains 'COMMENT_URL=https://example.test/comment/1' "$out" 'happy path emits URL'
assert_contains '<!-- larch:metadata v1 runid=run-1 -->' "$(cat "$TMP_ROOT/args.log")" 'marker passed'
assert_contains 'Coder: `codex`' "$(cat "$TMP_ROOT/content.md")" 'content includes coder'

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --issue 12 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing required args exits non-zero'; else fail 'missing required args exits non-zero'; fi
assert_contains 'POSTED=false' "$bad" 'missing args emits envelope'

finish
