#!/usr/bin/env bash
# Offline harness for /implement -> /review token telemetry propagation.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SESSION_SETUP="$REPO_ROOT/scripts/session-setup.sh"
READ_KEY="$REPO_ROOT/scripts/read-session-env-key.sh"
LAUNCH_CURSOR_REVIEW="$REPO_ROOT/scripts/launch-cursor-review.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/larch-implement-review-token.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

IMPLEMENT_ENV="$TMP/implement-session-env.sh"
REVIEW_ENV="$TMP/review-session-env.sh"
TIMING_LEDGER="$TMP/timing-ledger.tsv"
cat > "$IMPLEMENT_ENV" <<EOF_ENV
SLACK_OK=true
SLACK_MISSING=
REPO=owner/repo
REPO_UNAVAILABLE=false
LARCH_TIMING_LEDGER=$TIMING_LEDGER
LARCH_TOKEN_SESSION_ID=parent-implement-session
LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env
EOF_ENV
printf 'SOURCE_FILE=/tmp/mock-transcript.jsonl\n' > "$TMP/claude-source.env"

OUT=$("$SESSION_SETUP" \
    --prefix claude-review-token-test \
    --skip-preflight \
    --skip-slack-check \
    --skip-repo-check \
    --caller-env "$IMPLEMENT_ENV" \
    --write-session-env "$REVIEW_ENV")

case "$OUT" in
    *"LARCH_TOKEN_SESSION_ID=parent-implement-session"*) ;;
    *) fail "session-setup stdout did not forward LARCH_TOKEN_SESSION_ID: $OUT" ;;
esac
case "$OUT" in
    *"LARCH_TIMING_LEDGER="*) fail "session-setup stdout unexpectedly emitted LARCH_TIMING_LEDGER: $OUT" ;;
    *) ;;
esac

token_session_id=$("$READ_KEY" --file "$REVIEW_ENV" --key LARCH_TOKEN_SESSION_ID --default "")
claude_source_file=$("$READ_KEY" --file "$REVIEW_ENV" --key LARCH_CLAUDE_SOURCE_FILE --default "")
timing_ledger=$("$READ_KEY" --file "$REVIEW_ENV" --key LARCH_TIMING_LEDGER --default "")
[[ "$token_session_id" == "parent-implement-session" ]] || fail "review session-env lost LARCH_TOKEN_SESSION_ID"
[[ "$claude_source_file" == "$TMP/claude-source.env" ]] || fail "review session-env lost LARCH_CLAUDE_SOURCE_FILE"
[[ "$timing_ledger" == "$TIMING_LEDGER" ]] || fail "review session-env lost LARCH_TIMING_LEDGER"

UNSAFE_ENV="$TMP/unsafe-implement-session-env.sh"
UNSAFE_REVIEW_ENV="$TMP/unsafe-review-session-env.sh"
UNSAFE_ERR="$TMP/unsafe-session-setup.err"
cat > "$UNSAFE_ENV" <<EOF_ENV
SLACK_OK=true
SLACK_MISSING=
REPO=owner/repo
REPO_UNAVAILABLE=false
LARCH_TIMING_LEDGER=/etc/passwd
LARCH_TOKEN_SESSION_ID=parent-implement-session
LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env
EOF_ENV
if ! "$SESSION_SETUP" \
    --prefix claude-review-token-test \
    --skip-preflight \
    --skip-slack-check \
    --skip-repo-check \
    --caller-env "$UNSAFE_ENV" \
    --write-session-env "$UNSAFE_REVIEW_ENV" \
    >/dev/null 2>"$UNSAFE_ERR"; then
    fail "session-setup exited non-zero for unsafe LARCH_TIMING_LEDGER"
fi
unsafe_timing_ledger=$("$READ_KEY" --file "$UNSAFE_REVIEW_ENV" --key LARCH_TIMING_LEDGER --default "")
[[ -z "$unsafe_timing_ledger" ]] || fail "unsafe LARCH_TIMING_LEDGER was written to review session-env"
grep -Fq "session-setup.sh: warning: ignoring unsafe LARCH_TIMING_LEDGER from caller-env (not under accepted root)" "$UNSAFE_ERR" \
    || fail "unsafe LARCH_TIMING_LEDGER warning missing"

STUB_BIN="$TMP/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'EOF_CURSOR'
#!/usr/bin/env bash
set -euo pipefail
: "${CURSOR_TOKEN_SESSION_FILE:?}"
printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$CURSOR_TOKEN_SESSION_FILE"
printf '{"result":"review ok","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
EOF_CURSOR
chmod +x "$STUB_BIN/cursor"

OUTPUT="$TMP/cursor-review.txt"
TOKEN_CAPTURE="$TMP/cursor-token-session.txt"
PATH="$STUB_BIN:$PATH" \
    CURSOR_TOKEN_SESSION_FILE="$TOKEN_CAPTURE" \
    LARCH_TOKEN_SESSION_ID="$token_session_id" \
    LARCH_CLAUDE_SOURCE_FILE="$claude_source_file" \
    LARCH_CURSOR_MODEL=stub-cursor-model \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    env -u IMPLEMENT_TMPDIR \
    "$LAUNCH_CURSOR_REVIEW" --output "$OUTPUT" --timeout 5 --prompt "review prompt" >/dev/null

[[ "$(cat "$TOKEN_CAPTURE")" == "parent-implement-session" ]] \
    || fail "cursor review launcher did not inherit parent token session id"

echo "PASS: test-implement-review-token-propagation.sh"
