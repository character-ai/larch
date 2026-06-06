#!/usr/bin/env bash
# test-launch-codex-exec.sh — argv and auth contract tests for launch-codex-exec.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-codex-exec-test.XXXXXX)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

PASS=0
FAIL=0
ok() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

assert_fails() {
    local label=$1
    shift
    set +e
    "$REPO_ROOT/scripts/launch-codex-exec.sh" "$@" >"$TMPDIR_BASE/out" 2>"$TMPDIR_BASE/err"
    local rc=$?
    set -e
    if [[ "$rc" == 2 ]]; then ok "$label"; else fail "$label"; cat "$TMPDIR_BASE/err"; fi
}

OUT="$TMPDIR_BASE/exec-out.txt"
assert_fails "rejects relative output" --output relative --timeout 60 --prompt hi
assert_fails "rejects missing prompt" --output "$OUT" --timeout 60
assert_fails "rejects both prompt flags" --output "$OUT" --timeout 60 --prompt hi --prompt-file "$OUT"

if grep -q 'launch-codex-exec.sh' "$REPO_ROOT/scripts/lint-fix-loop.sh"; then
    ok "lint-fix-loop references launch-codex-exec.sh"
else
    fail "lint-fix-loop references launch-codex-exec.sh"
fi

if grep -q 'codex-exec' "$REPO_ROOT/scripts/lib-timing-kinds.sh"; then
    ok "timing allow-list includes codex-exec"
else
    fail "timing allow-list includes codex-exec"
fi

stub_bin="$TMPDIR_BASE/stub-bin"
mkdir -p "$stub_bin"
cat >"$stub_bin/codex" <<'EOF'
#!/usr/bin/env bash
out=""
last=""
for arg in "$@"; do
    if [[ -n "${CODEX_STUB_ARGV_LOG:-}" ]]; then
        printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"
    fi
    if [[ "$last" == "--output-last-message" ]]; then
        out="$arg"
    fi
    last="$arg"
done
if [[ -n "${CODEX_STUB_HOME_LOG:-}" ]]; then
    printf '%s\n' "${CODEX_HOME:-}" > "$CODEX_STUB_HOME_LOG"
fi
[[ -n "$out" ]] || exit 9
printf 'stub transcript\n' > "$out"
printf '{"msg":{"usage":{"input_tokens":1,"output_tokens":1}}}\n'
exit 0
EOF
chmod +x "$stub_bin/codex"

set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT" --timeout 60 --workdir "$REPO_ROOT" --prompt "hello") \
    >"$TMPDIR_BASE/launcher.stdout" 2>"$TMPDIR_BASE/launcher.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -q 'LAUNCHER_EXIT=0' "$TMPDIR_BASE/launcher.stdout"; then
    ok "happy path emits LAUNCHER_EXIT"
else
    fail "happy path emits LAUNCHER_EXIT"
fi
if [[ -f "${OUT}.prompt" ]]; then ok "writes prompt sidecar"; else fail "writes prompt sidecar"; fi
if [[ -f "${OUT}.done" && ! -f "${OUT}.inner.done" ]]; then ok "promotes inner sentinel"; else fail "promotes inner sentinel"; fi
if grep -Fq 'OUTER_LAUNCHER_KIND=codex-exec' "${OUT}.meta" && grep -Fq "OUTER_LAUNCHER_ADD_DIRS_JSON=[\"$REPO_ROOT\"]" "${OUT}.meta"; then
    ok "records codex-exec outer metadata"
else
    fail "records codex-exec outer metadata"
fi

OUT_ADD="$TMPDIR_BASE/exec-add-out.txt"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_ADD" --timeout 60 --workdir "$REPO_ROOT" --add-dir "$TMPDIR_BASE" --add-dir "$REPO_ROOT" --prompt "hello") \
    >"$TMPDIR_BASE/launcher-add.stdout" 2>"$TMPDIR_BASE/launcher-add.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -Fq "OUTER_LAUNCHER_ADD_DIRS_JSON=[\"$TMPDIR_BASE\",\"$REPO_ROOT\"]" "${OUT_ADD}.meta"; then
    ok "round-trips repeated add-dir metadata"
else
    fail "round-trips repeated add-dir metadata"
fi

OUT_ADD_DEGRADED="$TMPDIR_BASE/exec-add-degraded-out.txt"
ADD_DIR_TAB="$TMPDIR_BASE/add-dir-with-tab"$'\t'"suffix"
mkdir -p "$ADD_DIR_TAB"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" LARCH_TEST_FORCE_NO_JQ=1 \
    bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_ADD_DEGRADED" --timeout 60 --workdir "$REPO_ROOT" --add-dir "$ADD_DIR_TAB" --prompt "hello") \
    >"$TMPDIR_BASE/launcher-add-degraded.stdout" 2>"$TMPDIR_BASE/launcher-add-degraded.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -Fq "OUTER_LAUNCHER_ADD_DIRS_JSON=[\"$REPO_ROOT\"]" "${OUT_ADD_DEGRADED}.meta" && grep -Fq 'recording workdir-only retry metadata' "$TMPDIR_BASE/launcher-add-degraded.stderr"; then
    ok "degrades unsafe add-dir metadata to workdir-only"
else
    fail "degrades unsafe add-dir metadata to workdir-only"
fi

PROMPT_FILE="$TMPDIR_BASE/prompt-file.md"
OUT_PROMPT_FILE="$TMPDIR_BASE/exec-prompt-file-out.txt"
printf 'hello from file\n' > "$PROMPT_FILE"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_PROMPT_FILE" --timeout 60 --workdir "$REPO_ROOT" --prompt-file "$PROMPT_FILE") \
    >"$TMPDIR_BASE/launcher-prompt-file.stdout" 2>"$TMPDIR_BASE/launcher-prompt-file.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -Fq 'hello from file' "${OUT_PROMPT_FILE}.prompt"; then
    ok "accepts prompt-file and writes prompt sidecar"
else
    fail "accepts prompt-file and writes prompt sidecar"
fi

OUT_ENV_KEY="$TMPDIR_BASE/exec-env-key-out.txt"
ARGV_ENV_KEY="$TMPDIR_BASE/env-key.argv"
HOME_ENV_KEY="$TMPDIR_BASE/env-key.home"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    OPENAI_API_KEY="stub-key" CODEX_STUB_ARGV_LOG="$ARGV_ENV_KEY" CODEX_STUB_HOME_LOG="$HOME_ENV_KEY" \
    bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_ENV_KEY" --timeout 60 --workdir "$REPO_ROOT" --prompt "hello") \
    >"$TMPDIR_BASE/launcher-env-key.stdout" 2>"$TMPDIR_BASE/launcher-env-key.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -Fq 'model_providers.openai-larch-env.env_key="OPENAI_API_KEY"' "$ARGV_ENV_KEY"; then
    ok "env-key auth passes provider config by argv"
else
    fail "env-key auth passes provider config by argv"
fi
codex_home_dir=$(cat "$HOME_ENV_KEY" 2>/dev/null || true)
if [[ -n "$codex_home_dir" && ! -e "$codex_home_dir" ]]; then
    ok "removes temp CODEX_HOME after env-key run"
else
    fail "removes temp CODEX_HOME after env-key run"
fi

OUT_LOGIN="$TMPDIR_BASE/exec-login-out.txt"
ARGV_LOGIN="$TMPDIR_BASE/login.argv"
HOME_LOGIN="$TMPDIR_BASE/home-login"
HOME_LOGIN_OBSERVED="$TMPDIR_BASE/login.home"
mkdir -p "$HOME_LOGIN/.codex"
printf '{"tokens":"stub"}\n' > "$HOME_LOGIN/.codex/auth.json"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" HOME="$HOME_LOGIN" \
    CODEX_STUB_ARGV_LOG="$ARGV_LOGIN" CODEX_STUB_HOME_LOG="$HOME_LOGIN_OBSERVED" \
    env -u OPENAI_API_KEY bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_LOGIN" --timeout 60 --workdir "$REPO_ROOT" --prompt "hello") \
    >"$TMPDIR_BASE/launcher-login.stdout" 2>"$TMPDIR_BASE/launcher-login.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && ! grep -Fq 'openai-larch-env' "$ARGV_LOGIN"; then
    ok "login auth omits env-key provider argv"
else
    fail "login auth omits env-key provider argv"
fi
codex_login_home_dir=$(cat "$HOME_LOGIN_OBSERVED" 2>/dev/null || true)
if [[ -n "$codex_login_home_dir" && ! -e "$codex_login_home_dir" ]]; then
    ok "removes temp CODEX_HOME after login run"
else
    fail "removes temp CODEX_HOME after login run"
fi

OUT_AUTH_FAIL="$TMPDIR_BASE/exec-auth-fail-out.txt"
HOME_AUTH_FAIL="$TMPDIR_BASE/home-auth-fail"
mkdir -p "$HOME_AUTH_FAIL/.codex"
printf 'api_key = "literal-secret"\n' > "$HOME_AUTH_FAIL/.codex/config.toml"
chmod 400 "$HOME_AUTH_FAIL/.codex/config.toml"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" HOME="$HOME_AUTH_FAIL" \
    env -u OPENAI_API_KEY bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_AUTH_FAIL" --timeout 60 --workdir "$REPO_ROOT" --prompt "hello") \
    >"$TMPDIR_BASE/launcher-auth-fail.stdout" 2>"$TMPDIR_BASE/launcher-auth-fail.stderr"
rc=$?
set -e
chmod 600 "$HOME_AUTH_FAIL/.codex/config.toml"
if [[ "$rc" -eq 0 ]] && grep -Fq 'LAUNCHER_EXIT=1' "$TMPDIR_BASE/launcher-auth-fail.stdout" && grep -Fq 'codex auth setup failed' "${OUT_AUTH_FAIL}.diag" && [[ -f "${OUT_AUTH_FAIL}.meta" && -f "${OUT_AUTH_FAIL}.done" ]]; then
    ok "auth-prep failure writes preflight bundle"
else
    fail "auth-prep failure writes preflight bundle"
fi

OUT_MODEL_FAIL="$TMPDIR_BASE/exec-model-fail-out.txt"
set +e
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    LARCH_CODEX_MODEL="   " \
    bash "$REPO_ROOT/scripts/launch-codex-exec.sh" \
    --output "$OUT_MODEL_FAIL" --timeout 60 --workdir "$REPO_ROOT" --prompt "hello") \
    >"$TMPDIR_BASE/launcher-model-fail.stdout" 2>"$TMPDIR_BASE/launcher-model-fail.stderr"
rc=$?
set -e
if [[ "$rc" -eq 0 ]] && grep -Fq 'LAUNCHER_EXIT=1' "$TMPDIR_BASE/launcher-model-fail.stdout" && grep -Fq 'agent-model-args.sh failed' "${OUT_MODEL_FAIL}.diag"; then
    ok "model-args failure writes preflight bundle"
else
    fail "model-args failure writes preflight bundle"
fi

echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
