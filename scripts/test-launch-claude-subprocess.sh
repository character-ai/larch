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

fail_bin="$TMP/bin-fail"
mkdir -p "$fail_bin"
cat > "$fail_bin/claude" <<'FAIL_STUB'
#!/usr/bin/env bash
printf 'agent stderr failure\n' >&2
exit 1
FAIL_STUB
chmod +x "$fail_bin/claude"
fail_out="$TMP/fail-out.txt"
printf 'prompt\n' > "$TMP/fail-prompt.md"
PATH="$fail_bin:$PATH" "$SCRIPT" --prompt-file "$TMP/fail-prompt.md" --output-file "$fail_out" --timeout 5 >/dev/null || true
[[ -s "${fail_out}.stderr-tail" ]] || fail "failure path missing .stderr-tail"
[[ -f "${fail_out}.done" ]] || fail "failure path missing .done"
fail_tail_mtime=$(stat -c %Y "${fail_out}.stderr-tail" 2>/dev/null || stat -f %m "${fail_out}.stderr-tail" 2>/dev/null || printf '')
fail_done_mtime=$(stat -c %Y "${fail_out}.done" 2>/dev/null || stat -f %m "${fail_out}.done" 2>/dev/null || printf '')
[[ "$fail_tail_mtime" =~ ^[0-9]+$ && "$fail_done_mtime" =~ ^[0-9]+$ && "$fail_tail_mtime" -le "$fail_done_mtime" ]] \
    || fail "failure path .stderr-tail must exist before .done (tail=$fail_tail_mtime done=$fail_done_mtime)"

read_tools_reject_session="$TMP/read-tools-reject-session"
mkdir -p "$read_tools_reject_session/staged-context"
read_tools_reject_prompt="$read_tools_reject_session/staged-context/prompt.md"
printf 'Read staged context by path.\n' >"$read_tools_reject_prompt"
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --prompt-file "$read_tools_reject_prompt" \
    --output-file "$read_tools_reject_session/out.txt" \
    --timeout 5 \
    --read-tools-add-dir "$read_tools_reject_session/staged-context" \
    --timing-task-kind scout-dynamic-archetypes \
    >/dev/null 2>"$TMP/read-tools-add-dir-without-flag-err"
add_dir_no_flag_rc=$?
set -e
[[ "$add_dir_no_flag_rc" -eq 2 ]] || fail "--read-tools-add-dir without --read-tools must exit 2"
grep -Fq -- '--read-tools-add-dir requires --read-tools' "$TMP/read-tools-add-dir-without-flag-err" \
    || fail "--read-tools-add-dir without --read-tools rejection message"

outside_add_dir="$TMP/read-tools-outside-root"
mkdir -p "$outside_add_dir/staged-context"
outside_prompt="$outside_add_dir/staged-context/prompt.md"
printf 'Read staged context by path.\n' >"$outside_prompt"
set +e
PATH="$BIN:$PATH" "$SCRIPT" \
    --prompt-file "$outside_prompt" \
    --output-file "$outside_add_dir/out.txt" \
    --timeout 5 \
    --read-tools \
    --read-tools-add-dir "$TMP" \
    --timing-task-kind scout-dynamic-archetypes \
    >/dev/null 2>"$TMP/read-tools-add-dir-outside-err"
outside_add_dir_rc=$?
set -e
[[ "$outside_add_dir_rc" -eq 2 ]] || fail "--read-tools-add-dir outside session root must exit 2"
grep -Fq -- '--read-tools-add-dir outside session root' "$TMP/read-tools-add-dir-outside-err" \
    || fail "--read-tools-add-dir outside session root rejection message"

ln -s "$prompt" "$TMP/link.md"
if PATH="$BIN:$PATH" LARCH_QUIET_LOG_FILE="$TMP/quiet.log" "$SCRIPT" --prompt-file "$TMP/link.md" --output-file "$TMP/bad.txt" --timeout 5 >/dev/null 2>"$TMP/err"; then
    fail "symlink prompt accepted"
fi
grep -Fq 'invalid --prompt-file' "$TMP/err" || fail "symlink rejection message missing from stderr"
[[ -f "$TMP/quiet.log" ]] || fail "quiet log not created despite LARCH_QUIET_LOG_FILE being set"
# Stage 2: larch_err mirrors to quiet log by design; only check that stderr got the message
: # symlink rejection quiet-log mirror check removed (larch_err writes to both)

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

# Restore the happy-path stub for the context-file boundary checks below.
cat > "$BIN/claude" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
grep -q 'You are a read-only reviewer' || exit 7
printf 'stub reviewer output\n'
STUB
chmod +x "$BIN/claude"

# Context-file size: 1 MB boundary accepted (#2292 raised the cap from 256 KB to 1 MB
# after PR #2289's 274 KB diff tripped the old cap silently).
ctx_under="$TMP/ctx-1MB.txt"
# 1 MB minus 1 byte → must be accepted.
dd if=/dev/zero bs=1024 count=1023 2>/dev/null | tr '\0' 'x' > "$ctx_under"
printf 'x%.0s' {1..1023} >> "$ctx_under"
[[ "$(wc -c < "$ctx_under" | tr -d ' ')" == "1048575" ]] || fail "1 MB-1 fixture wrong size: $(wc -c < "$ctx_under" | tr -d ' ')"
out_under="$TMP/out-under-cap.txt"
PATH="$BIN:$PATH" "$SCRIPT" \
        --prompt-file "$prompt" \
        --output-file "$out_under" \
        --timeout 5 \
        --context-files "$ctx_under" \
        --timing-task-kind claude-review \
        > "$TMP/under-stdout" 2>"$TMP/under-err" \
    || fail "1 MB-1 context-file rejected (should be accepted; exit=$?, stderr: $(cat "$TMP/under-err"))"
grep -Fq 'STATUS=OK' "$TMP/under-stdout" || fail "1 MB-1 context-file path: missing STATUS=OK"

# Context-file size: 1 MB + 1 byte rejected with the new "1 MB" wording.
ctx_over="$TMP/ctx-over-1MB.txt"
dd if=/dev/zero bs=1024 count=1024 2>/dev/null | tr '\0' 'x' > "$ctx_over"
printf 'x' >> "$ctx_over"
[[ "$(wc -c < "$ctx_over" | tr -d ' ')" == "1048577" ]] || fail "1 MB+1 fixture wrong size: $(wc -c < "$ctx_over" | tr -d ' ')"
out_over="$TMP/out-over-cap.txt"
if PATH="$BIN:$PATH" "$SCRIPT" \
        --prompt-file "$prompt" \
        --output-file "$out_over" \
        --timeout 5 \
        --context-files "$ctx_over" \
        --timing-task-kind claude-review \
        >/dev/null 2>"$TMP/over-err"; then
    fail "1 MB+1 context-file accepted (should be rejected)"
fi
grep -Fq 'context file exceeds 1 MB' "$TMP/over-err" || fail "over-cap rejection message must say 'context file exceeds 1 MB' (got: $(cat "$TMP/over-err"))"
# Pin against the stale 256 KB wording to prevent reverts.
grep -Fq '256 KB' "$TMP/over-err" && fail "stale '256 KB' wording in rejection message; #2292 wording regressed"

read_tools_session="$TMP/read-tools-session"
mkdir -p "$read_tools_session/staged-context"
read_tools_prompt="$read_tools_session/staged-context/prompt.md"
printf 'Read staged context by path.\n' >"$read_tools_prompt"
PATH="$BIN:$PATH" "$SCRIPT" \
    --prompt-file "$read_tools_prompt" \
    --output-file "$read_tools_session/out.txt" \
    --timeout 5 \
    --read-tools \
    --read-tools-add-dir "$read_tools_session/staged-context" \
    --timing-task-kind scout-dynamic-archetypes \
    >"$TMP/read-tools-stdout" 2>"$TMP/read-tools-err" \
    || fail "--read-tools launch failed"
grep -Fq 'STATUS=OK' "$TMP/read-tools-stdout" || fail "--read-tools missing STATUS=OK"
grep -Fq 'staged-context' "$read_tools_session/out.txt.meta" || fail "--read-tools CMD_JSON missing staged-context add-dir"
grep -Fq 'allowedTools' "$read_tools_session/out.txt.meta" || fail "--read-tools CMD_JSON missing allowedTools"
grep -Fq '"Read"' "$read_tools_session/out.txt.meta" || fail "--read-tools CMD_JSON missing Read-only allowlist"
grep -Fq 'Grep' "$read_tools_session/out.txt.meta" && fail "--read-tools CMD_JSON must not allow Grep"
grep -Fq 'Glob' "$read_tools_session/out.txt.meta" && fail "--read-tools CMD_JSON must not allow Glob"
grep -Fq 'Edit' "$read_tools_session/out.txt.meta" && fail "--read-tools CMD_JSON must not allow Edit"
grep -Fq '"plan"' "$read_tools_session/out.txt.meta" || fail "--read-tools CMD_JSON missing permission-mode plan"

echo "All assertions passed."
