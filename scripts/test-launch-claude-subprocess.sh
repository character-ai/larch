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

# --allow-root: context file under extra root accepted
extra_root=$(mktemp -d "${TMPDIR:-/tmp}/test-allow-root.XXXXXX")
trap 'rm -rf "$TMP" "$extra_root"' EXIT
extra_ctx="$extra_root/extra-context.txt"
printf 'extra context body\n' > "$extra_ctx"
extra_out="$TMP/out-extra.txt"
if ! PATH="$BIN:$PATH" "$SCRIPT" \
        --prompt-file "$prompt" \
        --output-file "$extra_out" \
        --timeout 5 \
        --allow-root "$extra_root" \
        --context-files "$extra_ctx" \
        --timing-task-kind claude-review \
        > "$TMP/extra-stdout" 2>"$TMP/extra-err"; then
    fail "--allow-root: extra-root context file rejected (should be accepted)"
fi
grep -Fq 'STATUS=OK' "$TMP/extra-stdout" || fail "--allow-root: missing STATUS=OK"
grep -Fq 'stub reviewer output' "$extra_out" || fail "--allow-root: output not written"
[[ "$(cat "$extra_out.done")" = "0" ]] || fail "--allow-root: .done exit code missing"

# --allow-root: context file under extra root rejected without the flag
extra_out2="$TMP/out-extra2.txt"
if PATH="$BIN:$PATH" "$SCRIPT" \
        --prompt-file "$prompt" \
        --output-file "$extra_out2" \
        --timeout 5 \
        --context-files "$extra_ctx" \
        --timing-task-kind claude-review \
        >/dev/null 2>"$TMP/extra2-err"; then
    fail "--allow-root: extra-root context file accepted without --allow-root (should be rejected)"
fi
grep -Fq 'context file outside allowed roots' "$TMP/extra2-err" || fail "--allow-root: rejection message missing from stderr"

# argv regression: --no-markdown must not appear in the script
grep -qF -- '--no-markdown' "$SCRIPT" && fail "argv regression: --no-markdown found in $SCRIPT"

# stderr artifact: happy-path run produces an ${out}.stderr sibling (even if empty)
[[ -f "${out}.stderr" ]] || fail "happy-path run did not produce ${out}.stderr"

# fail-loud: a stub that exits 0 but emits nothing must trigger the fail-loud guard
cat > "$BIN/claude" <<'STUB'
#!/usr/bin/env bash
exit 0
STUB
chmod +x "$BIN/claude"
out_empty="$TMP/out-empty.txt"
if PATH="$BIN:$PATH" "$SCRIPT" \
        --prompt-file "$prompt" \
        --output-file "$out_empty" \
        --timeout 5 \
        --timing-task-kind claude-review \
        >/dev/null 2>/dev/null; then
    fail "fail-loud: empty-output with exit 0 should have been treated as ERROR (non-zero exit)"
fi

echo "All assertions passed."
