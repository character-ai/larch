#!/usr/bin/env bash
# test-slack-issue-announce.sh — offline harness for slack-issue-announce.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/slack-issue-announce.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-slack-issue-announce.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

out=$("$HELPER" --pr-url https://example.test/pr/1 --issue-number 9 --run-id run-4)
assert_contains 'STATUS=skipped' "$out" 'missing webhook skips'
assert_contains 'REASON=webhook-not-set' "$out" 'skip reason emitted'

fake="$TMP_ROOT/fake-curl"
cat > "$fake" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${CURL_ARGS_LOG:?}"
exit 0
STUB
chmod +x "$fake"
out=$(LARCH_SLACK_WEBHOOK_URL=https://hooks.example.test __LARCH_FAKE_CURL="$fake" CURL_ARGS_LOG="$TMP_ROOT/curl.log" "$HELPER" --pr-url https://example.test/pr/1 --issue-number 9 --run-id run-4 --pr-title "A PR")
assert_contains 'STATUS=posted' "$out" 'webhook posts'
assert_contains 'https://hooks.example.test' "$(cat "$TMP_ROOT/curl.log")" 'curl receives webhook'

set +e
bad=$("$HELPER" --pr-url x 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing args exits non-zero'; else fail 'missing args exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing args emits envelope'

finish
