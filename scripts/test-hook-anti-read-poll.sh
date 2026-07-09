#!/usr/bin/env bash
# test-hook-anti-read-poll.sh — offline harness for hook-anti-read-poll.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HOOK="$SCRIPT_DIR/hook-anti-read-poll.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'PASS: %s
' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'FAIL: %s
' "$1" >&2; }
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-anti-read-poll.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export TMPDIR="$TMP"

mk_payload() {
    local path="$1" offset="${2:-0}" cwd="${3:-/tmp/test-proj}" session_id="${4:-}"
    jq -cn --arg p "$path" --argjson off "$offset" --arg cwd "$cwd" --arg sid "$session_id"         '{tool_name:"Read",tool_input:{file_path:$p,offset:$off},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}
mk_bash_payload() {
    local command="$1" cwd="${2:-/tmp/test-proj}" session_id="${3:-}"
    jq -cn --arg cmd "$command" --arg cwd "$cwd" --arg sid "$session_id"         '{tool_name:"Bash",tool_input:{command:$cmd},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}
cksum_hash() {
    printf '%s' "$1" | cksum | awk '{print $1}'
}
state_path_for() {
    local cwd="$1" session_id="$2" session_key cwd_hash session_hash
    cwd_hash=$(cksum_hash "${cwd:-/}")
    if [ -n "$session_id" ]; then
        session_key="$session_id"
    else
        session_key="nosession"
    fi
    session_hash=$(cksum_hash "$session_key")
    printf '%s/larch-read-poll/read-%s-%s.state' "$TMPDIR" "$cwd_hash" "$session_hash"
}
path_hash_for() {
    cksum_hash "$1"
}
run_hook_with_hook() {
    local hook_path="$1" now="$2" path="$3" offset="${4:-0}" cwd="${5:-/tmp/test-proj}" session_id="${6:-}"
    mk_payload "$path" "$offset" "$cwd" "$session_id" | HOOK_ANTI_READ_POLL_NOW="$now" "$hook_path"
}
run_hook() {
    run_hook_with_hook "$HOOK" "$@"
}
assert_reminder() {
    local out="$1" label="$2"
    if printf '%s' "$out" | command grep -q 'Read-poll detected'; then pass "$label"; else fail "$label (got: $out)"; fi
}
assert_silent() {
    local out="$1" label="$2"
    if [ -z "$out" ]; then pass "$label"; else fail "$label (got: $out)"; fi
}

if jq -e --arg cmd 'hook-anti-read-poll.sh' '.hooks.PostToolUse[]? | select(.matcher == "Read|Bash") | .hooks[]? | select(.command | test($cmd))' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json registers hook-anti-read-poll.sh under matcher Read|Bash'
else
    fail 'hooks.json must register hook-anti-read-poll.sh under matcher Read|Bash'
fi

assert_silent "$(run_hook 0 /tmp/file.md 0 /proj generic)" 'call 1 silent'
assert_silent "$(run_hook 1 /tmp/file.md 0 /proj generic)" 'call 2 silent'
assert_reminder "$(run_hook 2 /tmp/file.md 0 /proj generic)" 'call 3 warns'
assert_silent "$(run_hook 3 /tmp/file.md 0 /proj generic)" 'call 4 after threshold silent'
assert_silent "$(run_hook 4 /tmp/file.md 100 /proj offset)" 'different offset call 1 silent'
assert_silent "$(run_hook 5 /tmp/file.md 100 /proj offset)" 'different offset call 2 silent'
assert_reminder "$(run_hook 6 /tmp/file.md 100 /proj offset)" 'different offset call 3 warns'
assert_silent "$(run_hook 40 /tmp/file.md 100 /proj slow)" 'slow call 1 silent'
assert_silent "$(run_hook 71 /tmp/file.md 100 /proj slow)" 'window expiry resets counter'
assert_silent "$(mk_bash_payload 'cat tasks/example.output' /proj bash | HOOK_ANTI_READ_POLL_NOW=0 "$HOOK")" 'Bash events ignored'

leaf_cwd="/proj/leaf-symlink"
leaf_session="leaf-session"
leaf_path="/tmp/leaf-target.md"
leaf_offset=7
leaf_now=1000
leaf_state_path=$(state_path_for "$leaf_cwd" "$leaf_session")
leaf_path_hash=$(path_hash_for "$leaf_path")
mkdir -p "$(dirname "$leaf_state_path")"
leaf_poison_target="$TMP/leaf-poison-target"
leaf_poison_before=$(printf '%s\t%s\t2\t%s\n' "$leaf_path_hash" "$leaf_offset" 995)
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
leaf_expected=$(printf '%s\t%s\t1\t%s' "$leaf_path_hash" "$leaf_offset" "$leaf_now")
leaf_actual=$(tr -d '\n' <"$leaf_state_path")
if [ "$leaf_actual" = "$leaf_expected" ]; then
    pass 'leaf state replacement row records fresh count'
else
    fail "leaf state replacement row mismatch (got: $leaf_actual)"
fi

guardless_hook="$TMP/hook-anti-read-poll-guardless.sh"
python3 - "$HOOK" "$guardless_hook" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text()
needle = 'if [ ! -L "$state_file" ] && [ -f "$state_file" ] && [ -r "$state_file" ]; then'
replacement = 'if [ -r "$state_file" ]; then'
if needle not in text:
    raise SystemExit("read guard needle not found")
dst.write_text(text.replace(needle, replacement, 1))
PY
chmod +x "$guardless_hook"
negative_cwd="/proj/leaf-negative"
negative_session="negative-session"
negative_path="/tmp/leaf-negative.md"
negative_offset=9
negative_now=2000
negative_state_path=$(state_path_for "$negative_cwd" "$negative_session")
negative_path_hash=$(path_hash_for "$negative_path")
mkdir -p "$(dirname "$negative_state_path")"
negative_poison_target="$TMP/negative-poison-target"
printf '%s\t%s\t2\t%s\n' "$negative_path_hash" "$negative_offset" 1995 >"$negative_poison_target"
ln -s "$negative_poison_target" "$negative_state_path"
negative_out=$(run_hook_with_hook "$guardless_hook" "$negative_now" "$negative_path" "$negative_offset" "$negative_cwd" "$negative_session")
assert_reminder "$negative_out" 'negative control shows symlink read guard is load-bearing'

rm -rf "$TMPDIR/larch-read-poll"
parent_cwd="/proj/parent-symlink"
parent_session="parent-session"
parent_path="/tmp/parent-target.md"
parent_offset=11
parent_now=3000
parent_state_path=$(state_path_for "$parent_cwd" "$parent_session")
parent_state_dir=$(dirname "$parent_state_path")
parent_state_base=$(basename "$parent_state_path")
parent_path_hash=$(path_hash_for "$parent_path")
parent_redirect="$TMP/parent-redirect"
mkdir -p "$parent_redirect"
ln -s "$parent_redirect" "$parent_state_dir"
parent_poison_before=$(printf '%s\t%s\t2\t%s\n' "$parent_path_hash" "$parent_offset" 2995)
printf '%s' "$parent_poison_before" >"$parent_redirect/$parent_state_base"
set +e
parent_out=$(run_hook "$parent_now" "$parent_path" "$parent_offset" "$parent_cwd" "$parent_session")
parent_rc=$?
set -e
assert_silent "$parent_out" 'parent state-dir symlink exits without reminder'
if [ "$parent_rc" -eq 0 ]; then
    pass 'parent state-dir symlink hook exits 0'
else
    fail "parent state-dir symlink hook must exit 0 (got: $parent_rc)"
fi
parent_poison_after=$(cat "$parent_redirect/$parent_state_base")
if [ "$parent_poison_after" = "$parent_poison_before" ]; then
    pass 'parent state-dir symlink poison target unchanged'
else
    fail 'parent state-dir symlink poison target must stay unchanged'
fi
parent_tmp_count=$(find "$parent_redirect" -name '.*.tmp.*' -print | wc -l | tr -d ' ')
if [ "$parent_tmp_count" = "0" ]; then
    pass 'parent state-dir symlink does not receive temp state files'
else
    fail 'parent state-dir symlink must not receive temp state files'
fi

if [ "$FAIL" -ne 0 ]; then
    printf 'FAIL: test-hook-anti-read-poll.sh (%s failures, %s passes)
' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-hook-anti-read-poll.sh (%s checks)
' "$PASS"
