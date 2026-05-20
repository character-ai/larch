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
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"
    if [[ "$last" == "--output-last-message" ]]; then
        output="$arg"
    fi
    last="$arg"
done
[[ -n "$output" ]] || exit 9
if [[ -d "$CODEX_STUB_LOCK_PATH" ]]; then
    printf 'present' > "$CODEX_STUB_LOCK_SEEN_FILE"
fi
printf 'codex negotiation ok\n' > "$output"
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
rm -rf "$CODEX_LOCK_PATH"
PATH="$STUB_BIN:$PATH" \
    USER="$CODEX_LOCK_USER" \
    CODEX_STUB_ARGV_LOG="$CODEX_ARGV" \
    CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
    CODEX_STUB_LOCK_SEEN_FILE="$CODEX_LOCK_SEEN" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_STDOUT"
assert_file_equals "codex stdout envelope" "RESPONSE_FILE=$CODEX_OUTPUT" "$CODEX_STDOUT"
assert_file_equals "codex response body" "codex negotiation ok" "$CODEX_OUTPUT"
assert_file_equals "codex lock held at spawn" "present" "$CODEX_LOCK_SEEN"
if grep -Fxq -- '--output-last-message' "$CODEX_ARGV"; then
    pass
else
    fail "codex argv should include --output-last-message"
fi
rm -rf "$CODEX_LOCK_PATH"

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
