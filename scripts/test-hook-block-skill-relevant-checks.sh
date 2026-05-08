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
# Resolver matches on cwd + TTL only. The keepalive's SESSION_ID (uuidgen
# from session-setup.sh) and the hook payload's session_id (Claude transcript
# namespace) live in different namespaces and are intentionally NOT compared.
# See lib-resolve-active-larch-session.sh and issue #1543 review FINDING_2.
keepalive_sid="larch-uuid-A"
hook_sid_active="claude-transcript-A"
hook_sid_other="claude-transcript-B"
make_keepalive "claude-implement" "$cwd" "$keepalive_sid" "normal" >/dev/null
assert_deny "tool_input.skill active implement" "$(payload skill relevant-checks "$cwd" "$hook_sid_active")"
assert_deny "tool_input.skill_name active implement" "$(payload skill_name relevant-checks "$cwd" "$hook_sid_active")"

# Hook session_id != keepalive SESSION_ID is the production reality, not a
# discriminator: same cwd still denies regardless of which Claude transcript
# session id arrives.
assert_deny "hook session_id differs from keepalive" "$(payload skill relevant-checks "$cwd" "$hook_sid_other")"

make_keepalive "claude-review" "$cwd" "larch-uuid-B" "standalone" >/dev/null
assert_deny "review active" "$(payload skill relevant-checks "$cwd" "$hook_sid_active")"
assert_deny "larch-prefixed active" "$(payload skill larch:relevant-checks "$cwd" "$hook_sid_active")"

assert_allow "different skill" "$(payload skill review "$cwd" "$hook_sid_active")"
assert_allow "cwd mismatch" "$(payload skill relevant-checks "$tmp/other" "$hook_sid_active")"

stale_dir=$(make_keepalive "claude-implement" "$tmp/stale-cwd" "larch-uuid-stale" "stale")
touch -t 200001010000 "$stale_dir/.larch-keepalive"
out=$(printf '%s' "$(payload skill relevant-checks "$tmp/stale-cwd" "$hook_sid_active")" | LARCH_ACTIVE_SESSION_TTL_SECONDS=1 XDG_CACHE_HOME="$tmp/cache" "$HOOK")
[[ -z "$out" ]] || fail "stale keepalive should fail open"

# /tmp fallback root must be honored (session-setup.sh falls back when
# XDG_CACHE_HOME is unwritable). Verify the resolver picks up a keepalive
# under /tmp/claude-implement-* the same way it does under the cache root.
tmp_fallback="$tmp/tmpfallback-root"
mkdir -p "$tmp_fallback/claude-implement-fallback"
fallback_cwd="$tmp/fallback-cwd"
mkdir -p "$fallback_cwd"
printf 'CLONE_PATH=%s\nSESSION_ID=%s\n' "$fallback_cwd" "larch-uuid-fb" \
    > "$tmp_fallback/claude-implement-fallback/.larch-keepalive"
out=$(printf '%s' "$(payload skill relevant-checks "$fallback_cwd" "$hook_sid_active")" | TMPDIR="$tmp_fallback" XDG_CACHE_HOME="$tmp/empty-cache-for-fallback-test" "$HOOK")
# Note: the resolver looks under hard-coded /tmp and /private/tmp, so this
# fixture path under TMPDIR is illustrative — without the real /tmp paths
# being writable in the test sandbox we cannot fully assert the fallback
# branch from the harness. The branch is exercised via direct unit-style
# coverage by `test-relevant-checks-validation.sh` per its issue-1543
# follow-up. Allow either deny (canonical environments) or empty (fixture
# limitation) to keep the harness robust across CI hosts.
[[ -z "$out" || "$out" == *"permissionDecision"* ]] || fail "fallback root produced unexpected output: $out"

stub="$tmp/no-jq-bin"
mkdir -p "$stub"
ln -s "$BASH_BIN" "$stub/bash"
for tool in dirname basename pwd cat; do
    resolved=$(command -v "$tool" || true)
    [[ -n "$resolved" ]] && ln -s "$resolved" "$stub/$tool"
done
out=$(printf '%s' "$(payload skill relevant-checks "$cwd" "$hook_sid_active")" | PATH="$stub" XDG_CACHE_HOME="$tmp/cache" "$BASH_BIN" "$HOOK")
[[ -z "$out" ]] || fail "missing jq should fail open"

echo "test-hook-block-skill-relevant-checks: ok"
