#!/usr/bin/env bash
# Regression harness for hook-block-skill-relevant-checks.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HOOK="$REPO_ROOT/scripts/hook-block-skill-relevant-checks.sh"
BASH_BIN=$(command -v bash)

if ! command -v jq >/dev/null 2>&1; then
    echo "FAIL: harness jq not on PATH; cannot validate hook JSON" >&2
    exit 1
fi

tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-hook-relevant-checks.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

payload() {
    local key="$1" value="$2" cwd="$3" sid="$4"
    jq -cn --arg key "$key" --arg value "$value" --arg cwd "$cwd" --arg sid "$sid" '
      {tool_name:"Skill", cwd:$cwd, session_id:$sid, tool_input:{}} |
      .tool_input[$key] = $value
    '
}

invoke() {
    local input="$1"
    printf '%s' "$input" | XDG_CACHE_HOME="$tmp/cache" "$HOOK"
}

make_keepalive() {
    local prefix="$1" cwd="$2" sid="$3" leaf="$4"
    local dir="$tmp/cache/larch/sessions/$prefix-$leaf"
    mkdir -p "$dir"
    printf 'CLONE_PATH=%s\nSESSION_ID=%s\n' "$cwd" "$sid" > "$dir/.larch-keepalive"
    printf '%s\n' "$dir"
}

assert_deny() {
    local label="$1" input="$2" out
    out=$(invoke "$input")
    [[ -n "$out" ]] || fail "$label: expected deny stdout"
    decision=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // empty')
    event=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.hookEventName // empty')
    reason=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason // empty')
    [[ "$event" == "PreToolUse" && "$decision" == "deny" ]] || fail "$label: bad deny envelope: $out"
    [[ "$reason" == *"run-relevant-checks-captured.sh"* ]] || fail "$label: reason missing helper pointer"
}

assert_allow() {
    local label="$1" input="$2" out
    out=$(invoke "$input")
    [[ -z "$out" ]] || fail "$label: expected empty allow stdout, got: $out"
}

cwd="$tmp/worktree"
mkdir -p "$cwd"
sid="session-A"
make_keepalive "claude-implement" "$cwd" "$sid" "normal" >/dev/null
assert_deny "tool_input.skill active implement" "$(payload skill relevant-checks "$cwd" "$sid")"
assert_deny "tool_input.skill_name active implement" "$(payload skill_name relevant-checks "$cwd" "$sid")"

make_keepalive "claude-review" "$cwd" "$sid" "standalone" >/dev/null
assert_deny "review active" "$(payload skill relevant-checks "$cwd" "$sid")"
assert_deny "larch-prefixed active" "$(payload skill larch:relevant-checks "$cwd" "$sid")"

assert_allow "different skill" "$(payload skill review "$cwd" "$sid")"
assert_allow "cwd mismatch" "$(payload skill relevant-checks "$tmp/other" "$sid")"
assert_allow "session mismatch" "$(payload skill relevant-checks "$cwd" "session-B")"

stale_dir=$(make_keepalive "claude-implement" "$tmp/stale-cwd" "stale-session" "stale")
touch -t 200001010000 "$stale_dir/.larch-keepalive"
out=$(printf '%s' "$(payload skill relevant-checks "$tmp/stale-cwd" stale-session)" | LARCH_ACTIVE_SESSION_TTL_SECONDS=1 XDG_CACHE_HOME="$tmp/cache" "$HOOK")
[[ -z "$out" ]] || fail "stale keepalive should fail open"

stub="$tmp/no-jq-bin"
mkdir -p "$stub"
ln -s "$BASH_BIN" "$stub/bash"
for tool in dirname basename pwd cat; do
    resolved=$(command -v "$tool" || true)
    [[ -n "$resolved" ]] && ln -s "$resolved" "$stub/$tool"
done
out=$(printf '%s' "$(payload skill relevant-checks "$cwd" "$sid")" | PATH="$stub" XDG_CACHE_HOME="$tmp/cache" "$BASH_BIN" "$HOOK")
[[ -z "$out" ]] || fail "missing jq should fail open"

echo "test-hook-block-skill-relevant-checks: ok"
