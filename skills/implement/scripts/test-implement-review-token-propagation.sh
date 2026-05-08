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
cat > "$IMPLEMENT_ENV" <<EOF_ENV
SLACK_OK=true
SLACK_MISSING=
REPO=owner/repo
REPO_UNAVAILABLE=false
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

token_session_id=$("$READ_KEY" --file "$REVIEW_ENV" --key LARCH_TOKEN_SESSION_ID --default "")
claude_source_file=$("$READ_KEY" --file "$REVIEW_ENV" --key LARCH_CLAUDE_SOURCE_FILE --default "")
[[ "$token_session_id" == "parent-implement-session" ]] || fail "review session-env lost LARCH_TOKEN_SESSION_ID"
[[ "$claude_source_file" == "$TMP/claude-source.env" ]] || fail "review session-env lost LARCH_CLAUDE_SOURCE_FILE"

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
    "$LAUNCH_CURSOR_REVIEW" --output "$OUTPUT" --timeout 5 --prompt "review prompt" >/dev/null

[[ "$(cat "$TOKEN_CAPTURE")" == "parent-implement-session" ]] \
    || fail "cursor review launcher did not inherit parent token session id"

echo "PASS: test-implement-review-token-propagation.sh"
