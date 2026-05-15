#!/usr/bin/env bash
# Offline harness for /implement -> /review token telemetry propagation.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SESSION_SETUP="$REPO_ROOT/scripts/session-setup.sh"
READ_KEY="$REPO_ROOT/scripts/read-session-env-key.sh"
REVIEW_AND_FIX="$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/larch-implement-review-token.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

IMPLEMENT_ENV="$TMP/implement-session-env.sh"
REVIEW_ENV="$TMP/review-session-env.sh"
TIMING_LEDGER="$TMP/timing-ledger.tsv"
cat > "$IMPLEMENT_ENV" <<EOF_ENV
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
REPO=owner/repo
REPO_UNAVAILABLE=false
LARCH_TIMING_LEDGER=/etc/passwd
LARCH_TOKEN_SESSION_ID=parent-implement-session
LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env
EOF_ENV
if ! "$SESSION_SETUP" \
    --prefix claude-review-token-test \
    --skip-preflight \
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

CORE_STUB="$TMP/review-core-stub.sh"
cat > "$CORE_STUB" <<'EOF_CORE'
#!/usr/bin/env bash
set -euo pipefail
out=""
session_env=""
round="1"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir) out="$2"; shift 2 ;;
        --session-env-path) session_env="$2"; shift 2 ;;
        --round-num) round="$2"; shift 2 ;;
        *) shift; [[ $# -gt 0 && "$1" != --* ]] && shift || true ;;
    esac
done
mkdir -p "$out"
printf 'SESSION_ENV_PATH=%s\n' "$session_env" > "${CORE_CAPTURE_FILE:?}"
printf 'LARCH_TOKEN_SESSION_ID=%s\n' "${LARCH_TOKEN_SESSION_ID:-}" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_CLAUDE_SOURCE_FILE=%s\n' "${LARCH_CLAUDE_SOURCE_FILE:-}" >> "$CORE_CAPTURE_FILE"
printf 'LARCH_TIMING_LEDGER=%s\n' "${LARCH_TIMING_LEDGER:-}" >> "$CORE_CAPTURE_FILE"
: > "$out/accepted-findings.md"
: > "$out/rejected-findings.md"
: > "$out/oos-accepted-review.md"
printf '# Review Round %s\n' "$round" > "$out/review-round-summary.md"
printf '{"schema_version":1,"rounds_completed":%s,"accepted_count":0,"rejected_count":0}\n' "$round" > "$out/review-summary.json"
printf 'REVIEW_CORE_STATUS=zero-findings\nROUND_NUM=%s\nACCEPTED_COUNT=0\nREJECTED_COUNT=0\nACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\nPANEL_MODE=normal\nPANEL_SHAPE=simple\n' "$round" "$out" "$out"
EOF_CORE
chmod +x "$CORE_STUB"

IMPLEMENT_TMPDIR="$TMP/claude-implement-token-test"
mkdir -p "$IMPLEMENT_TMPDIR"
cp "$REVIEW_ENV" "$IMPLEMENT_TMPDIR/session-env.sh"
CORE_CAPTURE="$TMP/review-core-capture.env"
CORE_CAPTURE_FILE="$CORE_CAPTURE" \
    LARCH_TOKEN_SESSION_ID="$token_session_id" \
    LARCH_CLAUDE_SOURCE_FILE="$claude_source_file" \
    LARCH_TIMING_LEDGER="$timing_ledger" \
    REVIEW_AND_FIX_REVIEW_CORE_SH="$CORE_STUB" \
    "$REVIEW_AND_FIX" \
        --implement-tmpdir "$IMPLEMENT_TMPDIR" \
        --mode diff \
        --panel simple \
        --round-num 1 \
        --session-env-path "$IMPLEMENT_TMPDIR/session-env.sh" \
        --codex-available true \
        --cursor-available true >/dev/null

grep -Fq "SESSION_ENV_PATH=$IMPLEMENT_TMPDIR/session-env.sh" "$CORE_CAPTURE" \
    || fail "review-and-fix did not pass implement session-env path to review-core"
grep -Fq "LARCH_TOKEN_SESSION_ID=parent-implement-session" "$CORE_CAPTURE" \
    || fail "review-core subprocess did not inherit parent token session id"
grep -Fq "LARCH_CLAUDE_SOURCE_FILE=$TMP/claude-source.env" "$CORE_CAPTURE" \
    || fail "review-core subprocess did not inherit parent Claude source file"
grep -Fq "LARCH_TIMING_LEDGER=$TIMING_LEDGER" "$CORE_CAPTURE" \
    || fail "review-core subprocess did not inherit parent timing ledger"

echo "PASS: test-implement-review-token-propagation.sh"
