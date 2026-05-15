#!/usr/bin/env bash
# Regression harness for scripts/launch-claude-subprocess.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/launch-claude-subprocess.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-launch-claude-subprocess.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

BIN="$TMP/bin"
mkdir -p "$BIN"
cat > "$BIN/claude" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
grep -q 'You are a read-only reviewer' || exit 7
printf 'stub reviewer output\n'
STUB
chmod +x "$BIN/claude"

prompt="$TMP/prompt.md"
ctx="$TMP/context.txt"
out="$TMP/out.txt"
printf 'Review this.\n' > "$prompt"
printf 'context body\n' > "$ctx"

PATH="$BIN:$PATH" "$SCRIPT" --prompt-file "$prompt" --output-file "$out" --timeout 5 --context-files "$ctx" --timing-task-kind claude-review > "$TMP/stdout"

grep -Fq 'STATUS=OK' "$TMP/stdout" || fail "missing STATUS=OK"
grep -Fq 'stub reviewer output' "$out" || fail "output not written"
[[ "$(cat "$out.done")" = "0" ]] || fail ".done exit code missing"
grep -Fq 'OUTER_LAUNCHER=claude' "$out.meta" || fail ".meta missing launcher"
grep -Fq 'TOOL=claude' "$out.meta" || fail ".meta missing tool"
grep -Fq 'STATUS=clean' "$out.dirty-tree" || fail ".dirty-tree missing clean status"

ln -s "$prompt" "$TMP/link.md"
if PATH="$BIN:$PATH" LARCH_QUIET_LOG_FILE="$TMP/quiet.log" "$SCRIPT" --prompt-file "$TMP/link.md" --output-file "$TMP/bad.txt" --timeout 5 >/dev/null 2>"$TMP/err"; then
    fail "symlink prompt accepted"
fi
grep -Fq 'invalid --prompt-file' "$TMP/err" || fail "symlink rejection message missing from stderr"
[[ -f "$TMP/quiet.log" ]] || fail "quiet log not created despite LARCH_QUIET_LOG_FILE being set"
grep -Fq 'invalid --prompt-file' "$TMP/quiet.log" && fail "symlink rejection leaked to quiet log"

# PID sidecar: verify .pid file is written during subprocess execution and removed on exit.
cat > "$BIN/claude" <<'STUB'
#!/usr/bin/env bash
grep -q 'You are a read-only reviewer' || exit 7
sleep 0.3
printf 'pid sidecar test output\n'
STUB
chmod +x "$BIN/claude"
pid_out="$TMP/pid-test.txt"
PATH="$BIN:$PATH" "$SCRIPT" --prompt-file "$prompt" --output-file "$pid_out" --timeout 5 > "$TMP/pid-stdout" 2>/dev/null &
script_pid=$!
for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    sleep 0.05
    [ -f "${pid_out}.pid" ] && break
done
[ -f "${pid_out}.pid" ] || fail ".pid sidecar not written during subprocess execution"
_recorded_pid=$(tr -d '[:space:]' < "${pid_out}.pid" 2>/dev/null)
[ "$_recorded_pid" = "$script_pid" ] || fail ".pid sidecar has wrong PID: expected $script_pid got $_recorded_pid"
wait "$script_pid"
[ ! -f "${pid_out}.pid" ] || fail ".pid sidecar not cleaned up after exit"

echo "All assertions passed."
