#!/usr/bin/env bash
# test-hook-progress-report.sh — offline harness for hook-progress-report.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HOOK="$SCRIPT_DIR/hook-progress-report.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-progress-report.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

payload() {
    local prompt="$1" cwd="${2:-/tmp/proj}"
    jq -cn --arg prompt "$prompt" --arg cwd "$cwd" '{prompt:$prompt,cwd:$cwd}'
}

run_hook() {
    local prompt="$1" output="${2-Progress line}"
    payload "$prompt" | HOOK_PROGRESS_TEST_MODE=1 HOOK_PROGRESS_TEST_OUTPUT="$output" "$HOOK"
}

assert_empty() {
    local out="$1" label="$2"
    if [ -z "$out" ]; then
        pass "$label"
    else
        fail "$label (expected empty stdout, got: $out)"
    fi
}

assert_block_reason() {
    local out="$1" expected="$2" label="$3"
    if printf '%s' "$out" | jq -e --arg expected "$expected" '.decision == "block" and .reason == $expected' >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label (unexpected JSON: $out)"
    fi
}

echo "=== hooks.json registration ==="
if jq -e '
    .hooks.UserPromptSubmit[]?
    | .hooks[]?
    | select(.type == "command" and .command == "${CLAUDE_PLUGIN_ROOT}/scripts/hook-progress-report.sh" and .timeout == 10)
' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json registers UserPromptSubmit progress hook'
else
    fail 'hooks.json must register hook-progress-report.sh under UserPromptSubmit'
fi

echo "=== exact matches block ==="
out_p=$(run_hook p 'progress for p')
assert_block_reason "$out_p" 'progress for p' 'p blocks with report'
out_progress=$(run_hook progress 'progress for word')
assert_block_reason "$out_progress" 'progress for word' 'progress blocks with report'

for prompt in foo pp P ''; do
    out=$(run_hook "$prompt" 'should not appear')
    assert_empty "$out" "no match silent: ${prompt:-empty}"
done

echo "=== empty report and internal errors fail open ==="
out_empty=$(run_hook p '')
assert_empty "$out_empty" 'matching prompt with empty report is silent'
out_error=$(payload p | HOOK_PROGRESS_TEST_MODE=1 HOOK_PROGRESS_TEST_ERROR=1 "$HOOK")
assert_empty "$out_error" 'stubbed engine error is silent'
out_bad=$(printf '{not json' | HOOK_PROGRESS_TEST_MODE=1 HOOK_PROGRESS_TEST_OUTPUT='x' "$HOOK")
assert_empty "$out_bad" 'bad hook JSON is silent'

mkdir -p "$TMP/bin"
ln -s /bin/cat "$TMP/bin/cat"
ln -s /bin/bash "$TMP/bin/bash"
out_no_jq=$(payload p | PATH="$TMP/bin" HOOK_PROGRESS_TEST_MODE=1 HOOK_PROGRESS_TEST_OUTPUT='x' "$HOOK")
assert_empty "$out_no_jq" 'missing jq is silent'

echo "=== multiline reason encoding ==="
multiline=$'line one\nline two "quoted"\nline three'
out_multi=$(run_hook p "$multiline")
assert_block_reason "$out_multi" "$multiline" 'multiline report encoded as JSON string'

if [ "$FAIL" -ne 0 ]; then
    printf 'FAIL: %s assertion(s) failed, %s passed\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-hook-progress-report.sh (%s assertions)\n' "$PASS"
