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

if jq -e '.hooks.SessionStart[]? | select(.matcher == "startup|resume|clear|compact") | .hooks[]? | select(.type == "command" and .command == "${CLAUDE_PLUGIN_ROOT}/scripts/sessionstart-statusline.sh" and .timeout == 5)' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json registers SessionStart statusline hook'
else
    fail 'hooks.json must register sessionstart-statusline.sh under SessionStart'
fi

mkdir -p "$tmp/no-python"
ln -s /bin/cat "$tmp/no-python/cat"
ln -s /bin/bash "$tmp/no-python/bash"
out=$(PATH="$tmp/no-python" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'missing python3 is silent'

mkdir -p "$tmp/plugin/scripts" "$tmp/plugin/python" "$tmp/bin"
cp "$SCRIPT" "$tmp/plugin/scripts/sessionstart-statusline.sh"
chmod +x "$tmp/plugin/scripts/sessionstart-statusline.sh"
ln -s "$(command -v python3)" "$tmp/bin/python3"
out=$(PATH="$tmp/bin:/bin:/usr/bin" CLAUDE_PLUGIN_ROOT="$tmp/plugin" "$tmp/plugin/scripts/sessionstart-statusline.sh" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'missing cli.py is silent'

mkdir -p "$tmp/plugin-ok/scripts" "$tmp/plugin-ok/python"
cp "$SCRIPT" "$tmp/plugin-ok/scripts/sessionstart-statusline.sh"
chmod +x "$tmp/plugin-ok/scripts/sessionstart-statusline.sh"
cat > "$tmp/plugin-ok/python/cli.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations
import os
import pathlib
import sys
with pathlib.Path(os.environ['ARG_FILE']).open('a', encoding='utf-8') as handle:
    _ = handle.write(' '.join(sys.argv[1:]) + '\n')
PY
chmod +x "$tmp/plugin-ok/python/cli.py"
arg_file="$tmp/args.txt"
out=$(ARG_FILE="$arg_file" PATH="$tmp/bin:/bin:/usr/bin" CLAUDE_PLUGIN_ROOT="$tmp/plugin-ok" "$tmp/plugin-ok/scripts/sessionstart-statusline.sh" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'normal path is silent'
expected_args="$tmp/expected-args.txt"
cat > "$expected_args" <<EOF
progress session-reset
progress install-statusline --plugin-root $tmp/plugin-ok
EOF
if cmp -s "$expected_args" "$arg_file"; then
    pass 'stub cli receives reset before install-statusline'
else
    fail "stub cli argv mismatch: $(cat "$arg_file" 2>/dev/null || true)"
fi

: > "$arg_file"
out=$(LARCH_STATUSLINE_DISABLE=1 ARG_FILE="$arg_file" PATH="$tmp/bin:/bin:/usr/bin" CLAUDE_PLUGIN_ROOT="$tmp/plugin-ok" "$tmp/plugin-ok/scripts/sessionstart-statusline.sh" <<<'{"cwd":"/tmp/repo"}')
assert_empty "$out" 'statusline opt out is silent'
if [ ! -s "$arg_file" ]; then
    pass 'statusline opt out skips cli invocations'
else
    fail "statusline opt out should skip cli invocations: $(cat "$arg_file" 2>/dev/null || true)"
fi

if [ "$FAIL" -ne 0 ]; then
    printf 'FAIL: %s assertion(s) failed, %s passed\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-sessionstart-statusline.sh (%s assertions)\n' "$PASS"
