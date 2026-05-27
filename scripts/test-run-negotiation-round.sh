#!/usr/bin/env bash
# Offline regression harness for scripts/run-negotiation-round.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-run-negotiation-round.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

assert_file_equals() {
    local label="$1" expected="$2" file="$3"
    local actual=""
    actual="$(cat "$file" 2>/dev/null || true)"
    if [[ "$actual" == "$expected" ]]; then
        pass
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

PROMPT_FILE="$TMPROOT/prompt.txt"
printf 'negotiate\n' > "$PROMPT_FILE"

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"

cat > "$STUB_BIN/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${CODEX_STUB_ARGV_LOG:?}"
: "${CODEX_STUB_LOCK_PATH:?}"
: "${CODEX_STUB_LOCK_SEEN_FILE:?}"
output=""
last=""
json=false
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"
    if [[ "$last" == "--output-last-message" ]]; then
        output="$arg"
    fi
    if [[ "$arg" == "--json" ]]; then
        json=true
    fi
    last="$arg"
done
[[ -n "$output" ]] || exit 9
[[ "$json" == "true" ]] || exit 10
if [[ -d "$CODEX_STUB_LOCK_PATH" ]]; then
    printf 'present' > "$CODEX_STUB_LOCK_SEEN_FILE"
fi
printf 'codex negotiation final\n' > "$output"
printf '{"type":"token_usage","input_tokens":1000,"cached_input_tokens":900,"output_tokens":50}\n'
printf 'codex sidecar diagnostic\n' >&2
exit "${CODEX_STUB_RC:-0}"
EOF
chmod +x "$STUB_BIN/codex"

cat > "$STUB_BIN/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${CURSOR_STUB_ARGV_LOG:?}"
: "${CURSOR_STUB_LOCK_PATH:?}"
: "${CURSOR_STUB_LOCK_SEEN_FILE:?}"
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$CURSOR_STUB_ARGV_LOG"
done
if [[ -d "$CURSOR_STUB_LOCK_PATH" ]]; then
    printf 'present' > "$CURSOR_STUB_LOCK_SEEN_FILE"
fi
printf 'cursor negotiation ok\n'
EOF
chmod +x "$STUB_BIN/cursor"

CODEX_LOCK_USER="larch-test-neg-codex-$$"
CODEX_LOCK_PATH="/tmp/larch-codex-serial-${CODEX_LOCK_USER}.lock"
CODEX_OUTPUT="$TMPROOT/codex.out"
CODEX_STDOUT="$TMPROOT/codex.stdout"
CODEX_ARGV="$TMPROOT/codex.argv"
CODEX_LOCK_SEEN="$TMPROOT/codex.lock-seen"
CODEX_LEDGER="$TMPROOT/codex-token-ledger.jsonl"
rm -rf "$CODEX_LOCK_PATH"
PATH="$STUB_BIN:$PATH" \
    USER="$CODEX_LOCK_USER" \
    CODEX_STUB_ARGV_LOG="$CODEX_ARGV" \
    CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
    CODEX_STUB_LOCK_SEEN_FILE="$CODEX_LOCK_SEEN" \
    LARCH_TOKEN_LEDGER="$CODEX_LEDGER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=5 \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_STDOUT"
assert_file_equals "codex stdout envelope" "RESPONSE_FILE=$CODEX_OUTPUT" "$CODEX_STDOUT"
assert_file_equals "codex response body" "codex negotiation final" "$CODEX_OUTPUT"
assert_file_equals "codex lock held at spawn" "present" "$CODEX_LOCK_SEEN"
if [[ -s "${CODEX_OUTPUT%.txt}.events.jsonl" ]]; then
    pass
else
    fail "codex events file should be non-empty"
fi
if [[ -f "${CODEX_OUTPUT%.txt}.sidecar" ]]; then
    pass
else
    fail "codex sidecar should exist"
fi
if grep -Fq '"type":"token_usage"' "${CODEX_OUTPUT%.txt}.sidecar"; then
    fail "codex sidecar must not contain token_usage JSONL"
else
    pass
fi
if grep -Fq 'codex sidecar diagnostic' "${CODEX_OUTPUT%.txt}.sidecar"; then
    pass
else
    fail "codex sidecar should keep stderr diagnostics"
fi
if jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_negotiation" and .input==100 and .cache_read==900 and .output==50 and .total==1050)' "$CODEX_LEDGER" >/dev/null; then
    pass
else
    fail "codex token ledger should contain codex_negotiation row"
fi
if grep -Fxq -- '--output-last-message' "$CODEX_ARGV"; then
    pass
else
    fail "codex argv should include --output-last-message"
fi
if grep -Fxq -- '--json' "$CODEX_ARGV"; then
    pass
else
    fail "codex argv should include --json"
fi
if grep -Fxq -- '--' "$CODEX_ARGV"; then
    pass
else
    fail "codex argv should include -- separator"
fi
rm -rf "$CODEX_LOCK_PATH"

CODEX_FAIL_OUTPUT="$TMPROOT/codex-fail.txt"
CODEX_FAIL_STDOUT="$TMPROOT/codex-fail.stdout"
CODEX_FAIL_ARGV="$TMPROOT/codex-fail.argv"
CODEX_FAIL_LOCK_SEEN="$TMPROOT/codex-fail.lock-seen"
CODEX_FAIL_LEDGER="$TMPROOT/codex-fail-token-ledger.jsonl"
rm -f "${CODEX_FAIL_OUTPUT%.txt}.events.jsonl"
printf 'stale events\n' > "${CODEX_FAIL_OUTPUT%.txt}.events.jsonl"
set +e
PATH="$STUB_BIN:$PATH" \
    USER="$CODEX_LOCK_USER" \
    CODEX_STUB_ARGV_LOG="$CODEX_FAIL_ARGV" \
    CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
    CODEX_STUB_LOCK_SEEN_FILE="$CODEX_FAIL_LOCK_SEEN" \
    CODEX_STUB_RC=42 \
    LARCH_TOKEN_LEDGER="$CODEX_FAIL_LEDGER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_FAIL_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_FAIL_STDOUT"
CODEX_FAIL_RC=$?
set -e
assert_eq "failing codex exits 2" "2" "$CODEX_FAIL_RC"
assert_file_equals "failing codex stdout envelope" "RESPONSE_FILE=$CODEX_FAIL_OUTPUT" "$CODEX_FAIL_STDOUT"
if [[ -s "${CODEX_FAIL_OUTPUT%.txt}.events.jsonl" ]] && ! grep -Fq 'stale events' "${CODEX_FAIL_OUTPUT%.txt}.events.jsonl"; then
    pass
else
    fail "failing codex should overwrite stale events"
fi
if jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_negotiation" and .total==1050)' "$CODEX_FAIL_LEDGER" >/dev/null; then
    pass
else
    fail "failing codex should still record token ledger row"
fi

CURSOR_LOCK_USER="larch-test-neg-cursor-$$"
CURSOR_LOCK_PATH="/tmp/larch-cursor-serial-${CURSOR_LOCK_USER}.lock"
CURSOR_OUTPUT="$TMPROOT/cursor.out"
CURSOR_STDOUT="$TMPROOT/cursor.stdout"
CURSOR_ARGV="$TMPROOT/cursor.argv"
CURSOR_LOCK_SEEN="$TMPROOT/cursor.lock-seen"
rm -rf "$CURSOR_LOCK_PATH"
PATH="$STUB_BIN:$PATH" \
    USER="$CURSOR_LOCK_USER" \
    CURSOR_STUB_ARGV_LOG="$CURSOR_ARGV" \
    CURSOR_STUB_LOCK_PATH="$CURSOR_LOCK_PATH" \
    CURSOR_STUB_LOCK_SEEN_FILE="$CURSOR_LOCK_SEEN" \
    CURSOR_API_KEY="stub-key" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool cursor \
    --prompt-file "$PROMPT_FILE" \
    --output "$CURSOR_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CURSOR_STDOUT"
assert_file_equals "cursor stdout envelope" "RESPONSE_FILE=$CURSOR_OUTPUT" "$CURSOR_STDOUT"
assert_file_equals "cursor response body" "cursor negotiation ok" "$CURSOR_OUTPUT"
assert_file_equals "cursor lock held at spawn" "present" "$CURSOR_LOCK_SEEN"
if grep -Fxq -- '--api-key' "$CURSOR_ARGV"; then
    pass
else
    fail "cursor argv should include --api-key when CURSOR_API_KEY is set"
fi
if grep -Fxq -- '--workspace' "$CURSOR_ARGV"; then
    pass
else
    fail "cursor argv should include --workspace"
fi
rm -rf "$CURSOR_LOCK_PATH"

assert_eq "harness failures" "0" "$FAIL"
echo "test-run-negotiation-round: $PASS pass(es)"
