#!/usr/bin/env bash
# test-sessionstart-statusline.sh — offline harness for the SessionStart statusline hook.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
SCRIPT="$SCRIPT_DIR/sessionstart-statusline.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_empty() { if [ -z "$1" ]; then pass "$2"; else fail "$2 (expected empty stdout, got: $1)"; fi; }

tmp="$(mktemp -d "${TMPDIR:-/tmp}/larch-sessionstart-statusline.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT

if [ -x "$SCRIPT" ]; then pass 'script executable'; else fail 'script must be executable'; fi

if jq -e '.hooks.SessionStart[]? | .hooks[]? | select(.type == "command" and .command == "${CLAUDE_PLUGIN_ROOT}/scripts/sessionstart-statusline.sh" and .timeout == 5)' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json registers SessionStart statusline hook'
else
    fail 'hooks.json must register sessionstart-statusline.sh under SessionStart'
fi

mkdir -p "$tmp/plugin-missing/scripts"
cp "$SCRIPT" "$tmp/plugin-missing/scripts/sessionstart-statusline.sh"
chmod +x "$tmp/plugin-missing/scripts/sessionstart-statusline.sh"
out=$(CLAUDE_PLUGIN_ROOT="$tmp/plugin-missing" "$tmp/plugin-missing/scripts/sessionstart-statusline.sh" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'missing bootstrap entrypoint is silent'

mkdir -p "$tmp/plugin-ok/scripts"
cp "$SCRIPT" "$tmp/plugin-ok/scripts/sessionstart-statusline.sh"
chmod +x "$tmp/plugin-ok/scripts/sessionstart-statusline.sh"
cat > "$tmp/plugin-ok/scripts/larch.sh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$ARG_FILE"
SH
chmod +x "$tmp/plugin-ok/scripts/larch.sh"
arg_file="$tmp/args.txt"
out=$(ARG_FILE="$arg_file" CLAUDE_PLUGIN_ROOT="$tmp/plugin-ok" "$tmp/plugin-ok/scripts/sessionstart-statusline.sh" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'normal path is silent'
expected_args="$tmp/expected-args.txt"
cat > "$expected_args" <<EOF
progress session-reset
progress install-statusline --plugin-root $tmp/plugin-ok
EOF
if cmp -s "$expected_args" "$arg_file"; then
    pass 'bootstrap entrypoint receives reset before install-statusline'
else
    fail "bootstrap argv mismatch: $(cat "$arg_file" 2>/dev/null || true)"
fi

: > "$arg_file"
out=$(LARCH_STATUSLINE_DISABLE=1 ARG_FILE="$arg_file" CLAUDE_PLUGIN_ROOT="$tmp/plugin-ok" "$tmp/plugin-ok/scripts/sessionstart-statusline.sh" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'statusline opt out is silent'
if [ ! -s "$arg_file" ]; then
    pass 'statusline opt out skips bootstrap invocations'
else
    fail "statusline opt out should skip bootstrap invocations: $(cat "$arg_file" 2>/dev/null || true)"
fi

if [ "$FAIL" -ne 0 ]; then
    printf 'FAIL: %s assertion(s) failed, %s passed\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-sessionstart-statusline.sh (%s assertions)\n' "$PASS"
