#!/usr/bin/env bash
# test-write-final-report.sh — offline harness for write-final-report.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
HELPER="$SCRIPT_DIR/write-final-report.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-final-report.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$plugin/scripts/lib-quiet.sh"
cat > "$plugin/scripts/tracking-issue-summary.sh" <<'STUB'
#!/usr/bin/env bash
if [ "${TRACKING_FAIL:-false}" = "true" ]; then
  printf '%s' "${TRACKING_ERR:-summary failed}" >&2
  exit "${TRACKING_RC:-1}"
fi
while [ $# -gt 0 ]; do case "$1" in --content-file) cp "$2" "${TRACKING_CONTENT_LOG:?}"; shift 2 ;; *) shift ;; esac; done
printf 'COMMENT_URL=https://example.test/comment/final\n'
STUB
chmod +x "$plugin/scripts/tracking-issue-summary.sh"

session="$TMP_ROOT/session"; mkdir -p "$session"; printf 'REPO=owner/repo\n' > "$session/session-env.sh"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_CONTENT_LOG="$TMP_ROOT/content.md" "$HELPER" --issue 7 --run-id run-5 --pr-url https://example.test/pr/5 --stall-tracking false --session-env "$session/session-env.sh" --implement-tmpdir "$session")
assert_contains 'STATUS=ok' "$out" 'happy path status ok'
assert_contains 'COMMENT_URL=https://example.test/comment/final' "$out" 'comment URL emitted'
assert_contains 'PR: https://example.test/pr/5' "$(cat "$TMP_ROOT/content.md")" 'summary includes PR'
if [ -s "$session/larch-logs/implement/run-5/final-summary.md" ]; then pass 'final summary file written'; else fail 'final summary file written'; fi

set +e
failed=$(CLAUDE_PLUGIN_ROOT="$plugin" TRACKING_FAIL=true TRACKING_ERR='gh auth failed' "$HELPER" --issue 7 --run-id run-5 --pr-url https://example.test/pr/5 --stall-tracking false --session-env "$session/session-env.sh" --implement-tmpdir "$session" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 1 ]; then pass 'upsert failure exits non-zero'; else fail 'upsert failure exits non-zero'; fi
assert_contains 'STATUS=failed' "$failed" 'upsert failure status failed'
assert_contains 'ERROR=gh auth failed' "$failed" 'upsert failure emits error'

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" --issue 7 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing args exits non-zero'; else fail 'missing args exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing args emits envelope'

finish
