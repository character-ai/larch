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
if [[ -n "${CODEX_STUB_HOME_LOG:-}" ]]; then
    printf '%s\n' "${CODEX_HOME:-}" > "$CODEX_STUB_HOME_LOG"
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
if [[ -n "${CURSOR_STUB_ENV_LOG:-}" ]]; then
    printf 'CURSOR_API_KEY=%s\n' "${CURSOR_API_KEY-__UNSET__}" >> "$CURSOR_STUB_ENV_LOG"
fi
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
if grep -Fxq -- '-c' "$CODEX_ARGV" && grep -Fq 'trust_level="trusted"' "$CODEX_ARGV"; then
    pass
else
    fail "codex argv should include trusted workspace config"
fi
rm -rf "$CODEX_LOCK_PATH"

CODEX_ENV_KEY_OUTPUT="$TMPROOT/codex-env-key.out"
CODEX_ENV_KEY_STDOUT="$TMPROOT/codex-env-key.stdout"
CODEX_ENV_KEY_ARGV="$TMPROOT/codex-env-key.argv"
CODEX_ENV_KEY_HOME="$TMPROOT/codex-env-key.home"
CODEX_ENV_KEY_LOCK_SEEN="$TMPROOT/codex-env-key.lock-seen"
rm -rf "$CODEX_LOCK_PATH"
env -u OPENAI_API_KEY \
    PATH="$STUB_BIN:$PATH" \
    TMPDIR="$TMPROOT" \
    USER="$CODEX_LOCK_USER" \
    OPENAI_API_KEY="stub-key" \
    CODEX_STUB_ARGV_LOG="$CODEX_ENV_KEY_ARGV" \
    CODEX_STUB_HOME_LOG="$CODEX_ENV_KEY_HOME" \
    CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
    CODEX_STUB_LOCK_SEEN_FILE="$CODEX_ENV_KEY_LOCK_SEEN" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_ENV_KEY_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_ENV_KEY_STDOUT"
assert_file_equals "codex env-key stdout envelope" "RESPONSE_FILE=$CODEX_ENV_KEY_OUTPUT" "$CODEX_ENV_KEY_STDOUT"
if grep -Fq 'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"' "$CODEX_ENV_KEY_ARGV"; then
    pass
else
    fail "codex env-key branch should pass provider env_key config"
fi
codex_env_key_home_dir=$(cat "$CODEX_ENV_KEY_HOME" 2>/dev/null || true)
if [[ -n "$codex_env_key_home_dir" && ! -e "$codex_env_key_home_dir" ]]; then
    pass
else
    fail "codex env-key branch should remove temp CODEX_HOME"
fi
rm -rf "$CODEX_LOCK_PATH"

CODEX_LOGIN_OUTPUT="$TMPROOT/codex-login.out"
CODEX_LOGIN_STDOUT="$TMPROOT/codex-login.stdout"
CODEX_LOGIN_ARGV="$TMPROOT/codex-login.argv"
CODEX_LOGIN_HOME_LOG="$TMPROOT/codex-login.home"
CODEX_LOGIN_LOCK_SEEN="$TMPROOT/codex-login.lock-seen"
HOME_LOGIN="$TMPROOT/home-login"
mkdir -p "$HOME_LOGIN/.codex"
printf '{"tokens":"stub"}\n' > "$HOME_LOGIN/.codex/auth.json"
rm -rf "$CODEX_LOCK_PATH"
env -u OPENAI_API_KEY \
    PATH="$STUB_BIN:$PATH" \
    TMPDIR="$TMPROOT" \
    HOME="$HOME_LOGIN" \
    USER="$CODEX_LOCK_USER" \
    CODEX_STUB_ARGV_LOG="$CODEX_LOGIN_ARGV" \
    CODEX_STUB_HOME_LOG="$CODEX_LOGIN_HOME_LOG" \
    CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
    CODEX_STUB_LOCK_SEEN_FILE="$CODEX_LOGIN_LOCK_SEEN" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_LOGIN_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_LOGIN_STDOUT"
assert_file_equals "codex login stdout envelope" "RESPONSE_FILE=$CODEX_LOGIN_OUTPUT" "$CODEX_LOGIN_STDOUT"
if grep -Fq 'openai-larch-env' "$CODEX_LOGIN_ARGV"; then
    fail "codex login branch should omit env-key provider argv"
else
    pass
fi
codex_login_home_dir=$(cat "$CODEX_LOGIN_HOME_LOG" 2>/dev/null || true)
if [[ -n "$codex_login_home_dir" && ! -e "$codex_login_home_dir" ]]; then
    pass
else
    fail "codex login branch should remove temp CODEX_HOME"
fi
rm -rf "$CODEX_LOCK_PATH"

CODEX_AUTH_FAIL_OUTPUT="$TMPROOT/codex-auth-fail.out"
CODEX_AUTH_FAIL_STDOUT="$TMPROOT/codex-auth-fail.stdout"
HOME_AUTH_FAIL="$TMPROOT/home-auth-fail"
mkdir -p "$HOME_AUTH_FAIL/.codex"
printf 'api_key = "literal-secret"\n' > "$HOME_AUTH_FAIL/.codex/config.toml"
chmod 400 "$HOME_AUTH_FAIL/.codex/config.toml"
set +e
PATH="$STUB_BIN:$PATH" \
    TMPDIR="$TMPROOT" \
    HOME="$HOME_AUTH_FAIL" \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_AUTH_FAIL_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_AUTH_FAIL_STDOUT"
CODEX_AUTH_FAIL_RC=$?
set -e
chmod 600 "$HOME_AUTH_FAIL/.codex/config.toml"
assert_eq "codex auth-prep failure exits 2" "2" "$CODEX_AUTH_FAIL_RC"
assert_file_equals "codex auth-prep failure stdout envelope" "RESPONSE_FILE=$CODEX_AUTH_FAIL_OUTPUT" "$CODEX_AUTH_FAIL_STDOUT"
if find "$TMPROOT" -maxdepth 1 -type d -name 'larch-codex-negotiation-home-*' | grep -q .; then
    fail "codex auth-prep failure should clean temp CODEX_HOME"
else
    pass
fi

CODEX_UNSET_ROOT_OUTPUT="$TMPROOT/codex-unset-root.out"
CODEX_UNSET_ROOT_STDOUT="$TMPROOT/codex-unset-root.stdout"
CODEX_UNSET_ROOT_ARGV="$TMPROOT/codex-unset-root.argv"
CODEX_UNSET_ROOT_LOCK_SEEN="$TMPROOT/codex-unset-root.lock-seen"
CODEX_UNSET_ROOT_LEDGER="$TMPROOT/codex-unset-root-token-ledger.jsonl"
rm -rf "$CODEX_LOCK_PATH"
(
    unset CLAUDE_PLUGIN_ROOT
    PATH="$STUB_BIN:$PATH" \
        USER="$CODEX_LOCK_USER" \
        CODEX_STUB_ARGV_LOG="$CODEX_UNSET_ROOT_ARGV" \
        CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
        CODEX_STUB_LOCK_SEEN_FILE="$CODEX_UNSET_ROOT_LOCK_SEEN" \
        LARCH_TOKEN_LEDGER="$CODEX_UNSET_ROOT_LEDGER" \
        LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
        LARCH_EXTERNAL_SERIAL_LOCK_DELAY=5 \
        "$REPO_ROOT/scripts/run-negotiation-round.sh" \
        --tool codex \
        --prompt-file "$PROMPT_FILE" \
        --output "$CODEX_UNSET_ROOT_OUTPUT" \
        --workspace "$REPO_ROOT" \
        > "$CODEX_UNSET_ROOT_STDOUT"
)
assert_file_equals "codex unset-root stdout envelope" "RESPONSE_FILE=$CODEX_UNSET_ROOT_OUTPUT" "$CODEX_UNSET_ROOT_STDOUT"
assert_file_equals "codex unset-root response body" "codex negotiation final" "$CODEX_UNSET_ROOT_OUTPUT"
if jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_negotiation" and .total==1050)' "$CODEX_UNSET_ROOT_LEDGER" >/dev/null; then
    pass
else
    fail "codex unset-root should still record token ledger row"
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

CODEX_MODEL_FAIL_OUTPUT="$TMPROOT/codex-model-fail.txt"
CODEX_MODEL_FAIL_STDOUT="$TMPROOT/codex-model-fail.stdout"
set +e
PATH="$STUB_BIN:$PATH" \
    TMPDIR="$TMPROOT" \
    OPENAI_API_KEY="stub-key" \
    LARCH_CODEX_MODEL="   " \
    "$REPO_ROOT/scripts/run-negotiation-round.sh" \
    --tool codex \
    --prompt-file "$PROMPT_FILE" \
    --output "$CODEX_MODEL_FAIL_OUTPUT" \
    --workspace "$REPO_ROOT" \
    > "$CODEX_MODEL_FAIL_STDOUT"
CODEX_MODEL_FAIL_RC=$?
set -e
assert_eq "codex model-args failure propagates rc" "1" "$CODEX_MODEL_FAIL_RC"
assert_file_equals "codex model-args failure stdout has no response envelope" "" "$CODEX_MODEL_FAIL_STDOUT"
if find "$TMPROOT" -maxdepth 1 -type d -name 'larch-codex-negotiation-home-*' | grep -q .; then
    fail "codex model-args failure should clean temp CODEX_HOME"
else
    pass
fi

CURSOR_LOCK_USER="larch-test-neg-cursor-$$"
CURSOR_LOCK_PATH="/tmp/larch-cursor-serial-${CURSOR_LOCK_USER}.lock"
CURSOR_OUTPUT="$TMPROOT/cursor.out"
CURSOR_STDOUT="$TMPROOT/cursor.stdout"
CURSOR_ARGV="$TMPROOT/cursor.argv"
CURSOR_ENV="$TMPROOT/cursor.env"
CURSOR_LOCK_SEEN="$TMPROOT/cursor.lock-seen"
rm -rf "$CURSOR_LOCK_PATH"
PATH="$STUB_BIN:$PATH" \
    USER="$CURSOR_LOCK_USER" \
    CURSOR_STUB_ARGV_LOG="$CURSOR_ARGV" \
    CURSOR_STUB_ENV_LOG="$CURSOR_ENV" \
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
    fail "cursor argv must NOT include --api-key (issue #3375 env-based auth)"
else
    pass
fi
if grep -Fxq -- 'CURSOR_API_KEY=stub-key' "$CURSOR_ENV"; then
    pass
else
    fail "cursor child must inherit CURSOR_API_KEY in its environment (issue #3375); env log: $(cat "$CURSOR_ENV" 2>/dev/null)"
fi
if grep -Fxq -- '--workspace' "$CURSOR_ARGV"; then
    pass
else
    fail "cursor argv should include --workspace"
fi
rm -rf "$CURSOR_LOCK_PATH"

assert_eq "harness failures" "0" "$FAIL"
echo "test-run-negotiation-round: $PASS pass(es)"
