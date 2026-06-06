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
printf 'stub transcript\n' > "${@: -1}"
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

echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
