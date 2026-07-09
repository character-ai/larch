#!/usr/bin/env bash
# test-hook-anti-read-poll.sh — offline harness for hook-anti-read-poll.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HOOK="$SCRIPT_DIR/hook-anti-read-poll.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-anti-read-poll.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export TMPDIR="$TMP"

mk_payload() {
    local path="$1" offset="${2:-0}" cwd="${3-/tmp/test-proj}" session_id="${4:-}" conversation_id="${5:-}"
    jq -cn --arg p "$path" --argjson off "$offset" --arg cwd "$cwd" --arg sid "$session_id" --arg cid "$conversation_id" \
        '{tool_name:"Read",tool_input:{file_path:$p,offset:$off},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)
         + (if ($cid|length) > 0 then {conversation_id:$cid} else {} end)'
}

mk_bash_payload() {
    local command="$1" cwd="${2-/tmp/test-proj}" session_id="${3:-}"
    jq -cn --arg cmd "$command" --arg cwd "$cwd" --arg sid "$session_id" \
        '{tool_name:"Bash",tool_input:{command:$cmd},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}

state_basename_for() {
    local cwd="$1" session_key="$2"
    PYTHONPATH="$REPO_ROOT/python" python3 - "$cwd" "$session_key" <<'PY'
import sys
from larch.core.hook_anti_read_poll import state_basename
print(state_basename(sys.argv[1], sys.argv[2]))
PY
}

state_path_for() {
    local cwd="$1" session_key="$2" basename
    basename=$(state_basename_for "$cwd" "$session_key")
    printf '%s/larch-read-poll/%s' "$TMPDIR" "$basename"
}

path_hash_for() {
    local path="$1"
    PYTHONPATH="$REPO_ROOT/python" python3 - "$path" <<'PY'
import sys
from larch.core.hook_anti_read_poll import path_hash
print(path_hash(sys.argv[1]))
PY
}

run_hook() {
    local now="$1" path="$2" offset="${3:-0}" cwd="${4-/tmp/test-proj}" session_id="${5:-}" conversation_id="${6:-}"
    mk_payload "$path" "$offset" "$cwd" "$session_id" "$conversation_id" | HOOK_ANTI_READ_POLL_NOW="$now" "$HOOK"
}

assert_reminder() {
    local out="$1" label="$2" forbidden="${3:-}"
    local context event
    context=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null || true)
    event=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.hookEventName // empty' 2>/dev/null || true)
    if [ "$event" = "PostToolUse" ] && [ "$context" = "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling." ]; then
        if [ -n "$forbidden" ] && printf '%s' "$out" | command grep -Fq "$forbidden"; then
            fail "$label (reminder leaked forbidden text: $forbidden)"
        else
            pass "$label"
        fi
    else
        fail "$label (got: $out)"
    fi
}

assert_silent() {
    local out="$1" label="$2"
    if [ -z "$out" ]; then pass "$label"; else fail "$label (got: $out)"; fi
}

assert_no_hook_state() {
    local dir="$1" label="$2" tmp_count state_count
    tmp_count=$(find "$dir" -name '.*.tmp.*' -print | wc -l | tr -d ' ')
    state_count=$(find "$dir" -name '*.state' -print | wc -l | tr -d ' ')
    if [ "$tmp_count" = "0" ] && [ "$state_count" = "0" ]; then
        pass "$label"
    else
        fail "$label"
    fi
}

if jq -e --arg cmd 'hook-anti-read-poll.sh' '.hooks.PostToolUse[]? | select(.matcher == "Read|Bash") | .hooks[]? | select(.command | test($cmd))' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json registers hook-anti-read-poll.sh under matcher Read|Bash'
else
    fail 'hooks.json must register hook-anti-read-poll.sh under matcher Read|Bash'
fi

assert_silent "$(run_hook 0 /tmp/file.md 0 /proj generic)" 'call 1 silent'
assert_silent "$(run_hook 1 /tmp/file.md 0 /proj generic)" 'call 2 silent'
assert_reminder "$(run_hook 2 /tmp/file.md 0 /proj generic)" 'call 3 warns' '/tmp/file.md'
assert_silent "$(run_hook 3 /tmp/file.md 0 /proj generic)" 'call 4 after threshold silent'

assert_silent "$(run_hook 4 /tmp/file.md 100 /proj offset)" 'different offset call 1 silent'
assert_silent "$(run_hook 5 /tmp/file.md 100 /proj offset)" 'different offset call 2 silent'
assert_reminder "$(run_hook 6 /tmp/file.md 100 /proj offset)" 'different offset call 3 warns' '/tmp/file.md'

assert_silent "$(run_hook 40 /tmp/file.md 100 /proj slow)" 'slow call 1 silent'
assert_silent "$(run_hook 71 /tmp/file.md 100 /proj slow)" 'window expiry resets counter'
assert_silent "$(mk_bash_payload 'cat tasks/example.output' /proj bash | HOOK_ANTI_READ_POLL_NOW=0 "$HOOK")" 'Bash events ignored'

assert_silent "$(run_hook 100 /tmp/conv.md 0 /proj/conv '' '')" 'nosession call 1 silent'
assert_silent "$(run_hook 101 /tmp/conv.md 0 /proj/conv '' '')" 'nosession call 2 silent'
assert_silent "$(run_hook 102 /tmp/conv.md 0 /proj/conv '' conv-only)" 'conversation_id partitions from nosession'
assert_reminder "$(run_hook 103 /tmp/conv.md 0 /proj/conv '' '')" 'nosession partition still warns after conversation_id call'

assert_silent "$(mk_payload /tmp/disc.md 0 /proj/disc '' '' | HOOK_ANTI_READ_POLL_NOW=110 HOOK_ANTI_READ_POLL_DISCRIMINATOR=one "$HOOK")" 'discriminator one call 1 silent'
assert_silent "$(mk_payload /tmp/disc.md 0 /proj/disc '' '' | HOOK_ANTI_READ_POLL_NOW=111 HOOK_ANTI_READ_POLL_DISCRIMINATOR=one "$HOOK")" 'discriminator one call 2 silent'
assert_silent "$(mk_payload /tmp/disc.md 0 /proj/disc '' '' | HOOK_ANTI_READ_POLL_NOW=112 HOOK_ANTI_READ_POLL_DISCRIMINATOR=two "$HOOK")" 'non-empty discriminator splits nosession buckets'
assert_reminder "$(mk_payload /tmp/disc.md 0 /proj/disc '' '' | HOOK_ANTI_READ_POLL_NOW=113 HOOK_ANTI_READ_POLL_DISCRIMINATOR=one "$HOOK")" 'original discriminator bucket warns'

assert_silent "$(run_hook 120 /tmp/empty-disc.md 0 /proj/empty-disc '' '')" 'unset discriminator call 1 silent'
assert_silent "$(run_hook 121 /tmp/empty-disc.md 0 /proj/empty-disc '' '')" 'unset discriminator call 2 silent'
assert_reminder "$(mk_payload /tmp/empty-disc.md 0 /proj/empty-disc '' '' | HOOK_ANTI_READ_POLL_NOW=122 HOOK_ANTI_READ_POLL_DISCRIMINATOR= "$HOOK")" 'empty discriminator shares nosession bucket'

assert_silent "$(run_hook 130 /tmp/cwd-default.md 0 / nosession-cwd)" 'explicit root cwd call 1 silent'
assert_silent "$(run_hook 131 /tmp/cwd-default.md 0 '' nosession-cwd)" 'empty cwd defaults to root bucket on call 2'
assert_reminder "$(run_hook 132 /tmp/cwd-default.md 0 / nosession-cwd)" 'empty cwd and root cwd share bucket'

rm -rf "$TMPDIR/larch-read-poll"
state_redirect="$TMP/state-redirect"
mkdir -p "$state_redirect"
ln -s "$state_redirect" "$TMPDIR/larch-read-poll"
set +e
state_out=$(run_hook 200 /tmp/state-target.md 0 /proj/state state-session)
state_rc=$?
set -e
assert_silent "$state_out" 'symlinked state directory exits without reminder'
if [ "$state_rc" -eq 0 ]; then
    pass 'symlinked state directory hook exits 0'
else
    fail "symlinked state directory hook must exit 0 (got: $state_rc)"
fi
assert_no_hook_state "$state_redirect" 'symlinked state directory target receives no hook state'

rm -rf "$TMPDIR/larch-read-poll"
leaf_cwd="/proj/leaf-symlink"
leaf_session="leaf-session"
leaf_path="/tmp/leaf-target.md"
leaf_offset=7
leaf_now=300
leaf_state_path=$(state_path_for "$leaf_cwd" "$leaf_session")
leaf_path_hash=$(path_hash_for "$leaf_path")
mkdir -p "$(dirname "$leaf_state_path")"
leaf_poison_target="$TMP/leaf-poison-target"
leaf_poison_before=$(printf '%s\t%s\t2\t%s\n' "$leaf_path_hash" "$leaf_offset" 295)
printf '%s' "$leaf_poison_before" >"$leaf_poison_target"
ln -s "$leaf_poison_target" "$leaf_state_path"
set +e
leaf_out=$(run_hook "$leaf_now" "$leaf_path" "$leaf_offset" "$leaf_cwd" "$leaf_session")
leaf_rc=$?
set -e
assert_silent "$leaf_out" 'leaf state symlink poison does not trigger reminder'
if [ "$leaf_rc" -eq 0 ]; then
    pass 'leaf state symlink hook exits 0'
else
    fail "leaf state symlink hook must exit 0 (got: $leaf_rc)"
fi
leaf_poison_after=$(cat "$leaf_poison_target")
if [ "$leaf_poison_after" = "$leaf_poison_before" ]; then
    pass 'leaf state symlink poison target unchanged'
else
    fail 'leaf state symlink poison target must stay unchanged'
fi
if [ ! -L "$leaf_state_path" ] && [ -f "$leaf_state_path" ]; then
    pass 'leaf state symlink replaced with regular state file'
else
    fail 'leaf state symlink must be replaced with regular state file'
fi
leaf_actual=$(tr -d '\n' <"$leaf_state_path")
leaf_expected=$(printf '%s\t%s\t1\t%s' "$leaf_path_hash" "$leaf_offset" "$leaf_now")
if [ "$leaf_actual" = "$leaf_expected" ]; then
    pass 'leaf state replacement row records fresh count'
else
    fail "leaf state replacement row mismatch (got: $leaf_actual)"
fi
if printf '%s' "$leaf_actual" | command grep -Fq "$leaf_path"; then
    fail 'state row must not contain raw file path'
else
    pass 'state row stores hashed file path only'
fi

if [ "$FAIL" -ne 0 ]; then
    printf 'FAIL: test-hook-anti-read-poll.sh (%s failures, %s passes)\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-hook-anti-read-poll.sh (%s checks)\n' "$PASS"
