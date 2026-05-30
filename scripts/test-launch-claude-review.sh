#!/usr/bin/env bash
# Regression harness for launch-claude-review.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d /tmp/larch-test-launch-claude-review-XXXXXX)"
OUTSIDE_CONTEXT_ROOT=""
trap 'rm -rf "$TMPROOT"; [[ -z "${OUTSIDE_CONTEXT_ROOT:-}" ]] || rm -rf "$OUTSIDE_CONTEXT_ROOT"' EXIT

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
if [[ -n "${LARCH_TEST_CLAUDE_STDIN_LOG:-}" ]]; then
    tee "$LARCH_TEST_CLAUDE_STDIN_LOG" >/dev/null
else
    cat >/dev/null
fi
printf 'claude review ok\n'
STUB
chmod +x "$STUB_BIN/claude"
export LARCH_TEST_CLAUDE_STDIN_LOG="$TMPROOT/claude-stdin.log"

prompt="$TMPROOT/prompt.txt"
output="$TMPROOT/out.txt"
printf 'review this\n' > "$prompt"

PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$output" \
    --prompt-file "$prompt" \
    --mode description \
    --timeout 5 >/dev/null

[[ "$(cat "$output")" == "claude review ok" ]] || { echo "FAIL: output passthrough" >&2; exit 1; }
[[ "$(cat "$output.done")" == "0" ]] || { echo "FAIL: done sentinel" >&2; exit 1; }
grep -Fq "TOOL=claude" "$output.meta" || { echo "FAIL: claude metadata" >&2; exit 1; }

set +e
"$REPO_ROOT/scripts/launch-claude-review.sh" --output "$TMPROOT/bad.txt" --prompt-file "$prompt" --mode description --timeout 0 >/dev/null 2>"$TMPROOT/bad.stderr"
rc=$?
set -e
[[ "$rc" -eq 2 ]] || { echo "FAIL: bad timeout exit=$rc" >&2; exit 1; }

# Test --agent-file path: render-specialist-prompt.sh is invoked; output still reaches caller.
# Use a real agent file from the repo (code-reviewer.md is always present).
agent_file="$REPO_ROOT/agents/code-reviewer.md"
agent_output="$TMPROOT/agent-out.txt"
diff_file="$TMPROOT/agent-diff.txt"
printf 'test diff content\n' > "$diff_file"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$agent_output" \
    --agent-file "$agent_file" \
    --mode diff \
    --diff-file "$diff_file" \
    --timeout 5 >/dev/null
[[ "$(cat "$agent_output")" == "claude review ok" ]] || { echo "FAIL: agent-file output passthrough" >&2; exit 1; }
[[ -f "$agent_output.done" ]] || { echo "FAIL: agent-file done sentinel" >&2; exit 1; }

# #2292: subprocess validation errors (launch-claude-subprocess.sh's fail()
# via larch_err) must propagate up to this launcher's stderr. Without the
# tempfile-capture-and-re-emit dance, the subprocess's larch_quiet_init
# clobbers FD 4 with its own log file and validation messages are lost.
# Symlink prompt triggers canonical_existing_file's [[ ! -L "$p" ]] reject.
sym_prompt="$TMPROOT/prompt-symlink.txt"
ln -s "$prompt" "$sym_prompt"
sym_out="$TMPROOT/sym-out.txt"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$sym_out" \
    --prompt-file "$sym_prompt" \
    --mode description \
    --timeout 5 >/dev/null 2>"$TMPROOT/sym-err"
sym_rc=$?
set -e
[[ "$sym_rc" -eq 2 ]] || { echo "FAIL: symlink prompt should yield exit 2, got $sym_rc" >&2; exit 1; }
grep -Fq 'invalid --prompt-file' "$TMPROOT/sym-err" \
    || { echo "FAIL: subprocess validation 'invalid --prompt-file' did not propagate to launch-claude-review.sh stderr (got: $(cat "$TMPROOT/sym-err"))" >&2; exit 1; }
grep -Fq 'launch-claude-subprocess.sh' "$TMPROOT/sym-err" \
    || { echo "FAIL: subprocess prefix missing from propagated stderr (got: $(cat "$TMPROOT/sym-err"))" >&2; exit 1; }

# Cleanup invariant: the subprocess-stderr tempfile under $(dirname OUTPUT) must
# not persist after launch-claude-review.sh exits — protects against tmpdir
# bloat in long /implement runs that loop through the launcher many times.
shopt -s nullglob
leaked=( "$(dirname "$sym_out")"/claude-subprocess-stderr.* )
shopt -u nullglob
(( ${#leaked[@]} == 0 )) || { echo "FAIL: subprocess-stderr tempfile leaked: ${leaked[*]}" >&2; exit 1; }

# --role voter: diff context is now forwarded. A symlink diff must therefore
# fail validation the same way reviewer launches do.
voter_prompt="$TMPROOT/voter-prompt.txt"
printf 'vote on this ballot\n' > "$voter_prompt"
diff_for_voter="$TMPROOT/diff-for-voter-symlink.txt"
ln -s "$prompt" "$diff_for_voter"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/voter-out.txt" \
    --prompt-file "$voter_prompt" \
    --mode description \
    --role voter \
    --diff-file "$diff_for_voter" \
    --timeout 5 >/dev/null 2>"$TMPROOT/voter.stderr"
voter_rc=$?
set -e
[[ "$voter_rc" -eq 2 ]] \
    || { echo "FAIL: --role voter with symlink diff should yield exit 2 (got $voter_rc)" >&2; exit 1; }
grep -Fq 'invalid context file' "$TMPROOT/voter.stderr" \
    || { echo "FAIL: --role voter missing 'invalid context file' in stderr" >&2; exit 1; }

# --agent-file is reviewer-only. Reject voter launches before the specialist
# prompt renderer can re-inline diff/plan/scope context into the voter prompt.
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/voter-agent-out.txt" \
    --agent-file "$agent_file" \
    --mode diff \
    --role voter \
    --diff-file "$diff_file" \
    --timeout 5 >/dev/null 2>"$TMPROOT/voter-agent.stderr"
voter_agent_rc=$?
set -e
[[ "$voter_agent_rc" -eq 2 ]] \
    || { echo "FAIL: --agent-file --role voter should yield exit 2 (got $voter_agent_rc)" >&2; exit 1; }
grep -Fq -- '--agent-file is only supported with --role reviewer' "$TMPROOT/voter-agent.stderr" \
    || { echo "FAIL: --agent-file voter rejection missing expected validation message" >&2; exit 1; }

# --role reviewer (explicit): diff file IS forwarded; a symlink diff must still fail.
reviewer_sym_out="$TMPROOT/reviewer-sym-out.txt"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$reviewer_sym_out" \
    --prompt-file "$prompt" \
    --mode diff \
    --role reviewer \
    --diff-file "$diff_for_voter" \
    --timeout 5 >/dev/null 2>"$TMPROOT/reviewer-sym.stderr"
reviewer_sym_rc=$?
set -e
[[ "$reviewer_sym_rc" -eq 2 ]] \
    || { echo "FAIL: --role reviewer with symlink diff should yield exit 2 (got $reviewer_sym_rc)" >&2; exit 1; }
grep -Fq 'invalid context file' "$TMPROOT/reviewer-sym.stderr" \
    || { echo "FAIL: --role reviewer missing 'invalid context file' in stderr" >&2; exit 1; }

# --role with invalid value must exit 2.
set +e
"$REPO_ROOT/scripts/launch-claude-review.sh" --output "$TMPROOT/bad-role.txt" \
    --prompt-file "$prompt" --mode description --role badval --timeout 5 >/dev/null 2>"$TMPROOT/bad-role.stderr"
bad_role_rc=$?
set -e
[[ "$bad_role_rc" -eq 2 ]] || { echo "FAIL: invalid --role should yield exit 2" >&2; exit 1; }
grep -Fq 'reviewer or voter' "$TMPROOT/bad-role.stderr" \
    || { echo "FAIL: invalid --role missing expected validation message" >&2; exit 1; }

ctx_a="$TMPROOT/context-a.txt"
ctx_b="$TMPROOT/context-b.txt"
printf 'EXPLICIT_CONTEXT_A reviewer visible\n' > "$ctx_a"
printf 'EXPLICIT_CONTEXT_B reviewer visible\n' > "$ctx_b"
: > "$LARCH_TEST_CLAUDE_STDIN_LOG"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-reviewer-out.txt" \
    --prompt-file "$prompt" \
    --mode description \
    --role reviewer \
    --context-files "$ctx_a" \
    --context-files "$ctx_b" \
    --timeout 5 >/dev/null
[[ "$(cat "$TMPROOT/context-reviewer-out.txt")" == "claude review ok" ]] \
    || { echo "FAIL: reviewer --context-files output passthrough" >&2; exit 1; }
grep -Fq 'EXPLICIT_CONTEXT_A reviewer visible' "$LARCH_TEST_CLAUDE_STDIN_LOG" \
    || { echo "FAIL: reviewer --context-files missing first context content" >&2; exit 1; }
grep -Fq 'EXPLICIT_CONTEXT_B reviewer visible' "$LARCH_TEST_CLAUDE_STDIN_LOG" \
    || { echo "FAIL: reviewer --context-files missing second context content" >&2; exit 1; }

printf 'EXPLICIT_CONTEXT_A voter visible\n' > "$ctx_a"
printf 'EXPLICIT_CONTEXT_B voter visible\n' > "$ctx_b"
: > "$LARCH_TEST_CLAUDE_STDIN_LOG"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-voter-out.txt" \
    --prompt-file "$voter_prompt" \
    --mode description \
    --role voter \
    --context-files "$ctx_a" \
    --context-files "$ctx_b" \
    --timeout 5 >/dev/null
[[ "$(cat "$TMPROOT/context-voter-out.txt")" == "claude review ok" ]] \
    || { echo "FAIL: voter --context-files output passthrough" >&2; exit 1; }
grep -Fq 'EXPLICIT_CONTEXT_A voter visible' "$LARCH_TEST_CLAUDE_STDIN_LOG" \
    || { echo "FAIL: voter --context-files missing first context content" >&2; exit 1; }
grep -Fq 'EXPLICIT_CONTEXT_B voter visible' "$LARCH_TEST_CLAUDE_STDIN_LOG" \
    || { echo "FAIL: voter --context-files missing second context content" >&2; exit 1; }

set +e
"$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-missing-value-out.txt" \
    --prompt-file "$prompt" \
    --mode description \
    --context-files >/dev/null 2>"$TMPROOT/context-missing-value.stderr"
ctx_missing_value_rc=$?
"$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-flag-value-out.txt" \
    --prompt-file "$prompt" \
    --mode description \
    --context-files --timeout 5 >/dev/null 2>"$TMPROOT/context-flag-value.stderr"
ctx_flag_value_rc=$?
set -e
[[ "$ctx_missing_value_rc" -eq 2 ]] \
    || { echo "FAIL: trailing --context-files should yield exit 2 (got $ctx_missing_value_rc)" >&2; exit 1; }
[[ "$ctx_flag_value_rc" -eq 2 ]] \
    || { echo "FAIL: flag-like --context-files value should yield exit 2 (got $ctx_flag_value_rc)" >&2; exit 1; }
grep -Fq 'launch-claude-review.sh: --context-files requires a value' "$TMPROOT/context-missing-value.stderr" \
    || { echo "FAIL: trailing --context-files missing expected stderr" >&2; exit 1; }
grep -Fq 'launch-claude-review.sh: --context-files requires a value' "$TMPROOT/context-flag-value.stderr" \
    || { echo "FAIL: flag-like --context-files value missing expected stderr" >&2; exit 1; }

set +e
"$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-nonexistent-out.txt" \
    --prompt-file "$prompt" \
    --mode description \
    --context-files "$TMPROOT/does-not-exist.txt" \
    --timeout 5 >/dev/null 2>"$TMPROOT/context-nonexistent.stderr"
ctx_nonexistent_rc=$?
set -e
[[ "$ctx_nonexistent_rc" -eq 2 ]] \
    || { echo "FAIL: nonexistent --context-files should yield exit 2 (got $ctx_nonexistent_rc)" >&2; exit 1; }
grep -Fq 'launch-claude-review.sh: --context-files path missing or unreadable' "$TMPROOT/context-nonexistent.stderr" \
    || { echo "FAIL: nonexistent --context-files missing expected stderr" >&2; exit 1; }

dedup_file="$TMPROOT/dedup-context.txt"
printf 'DEDUP_CONTEXT_UNIQUE\n' > "$dedup_file"
: > "$LARCH_TEST_CLAUDE_STDIN_LOG"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-dedup-out.txt" \
    --prompt-file "$prompt" \
    --mode diff \
    --diff-file "$dedup_file" \
    --context-files "$dedup_file" \
    --timeout 5 >/dev/null
dedup_count=$(grep -Fc 'DEDUP_CONTEXT_UNIQUE' "$LARCH_TEST_CLAUDE_STDIN_LOG" || true)
[[ "$dedup_count" -eq 1 ]] \
    || { echo "FAIL: duplicate implicit/explicit context rendered $dedup_count times" >&2; exit 1; }

: > "$LARCH_TEST_CLAUDE_STDIN_LOG"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-explicit-dedup-out.txt" \
    --prompt-file "$prompt" \
    --mode diff \
    --context-files "$dedup_file" \
    --context-files "$dedup_file" \
    --timeout 5 >/dev/null
explicit_dedup_count=$(grep -Fc 'DEDUP_CONTEXT_UNIQUE' "$LARCH_TEST_CLAUDE_STDIN_LOG" || true)
[[ "$explicit_dedup_count" -eq 1 ]] \
    || { echo "FAIL: duplicate explicit context rendered $explicit_dedup_count times" >&2; exit 1; }

OUTSIDE_CONTEXT_ROOT="$(mktemp -d /tmp/larch-test-launch-context-outside-XXXXXX)"
outside_context="$OUTSIDE_CONTEXT_ROOT/outside-context.txt"
printf 'OUTSIDE_CONTEXT_ALLOWED\n' > "$outside_context"
: > "$LARCH_TEST_CLAUDE_STDIN_LOG"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-outside-out.txt" \
    --prompt-file "$prompt" \
    --mode description \
    --context-files "$outside_context" \
    --timeout 5 >/dev/null
[[ "$(cat "$TMPROOT/context-outside-out.txt")" == "claude review ok" ]] \
    || { echo "FAIL: outside --context-files output passthrough" >&2; exit 1; }
grep -Fq 'OUTSIDE_CONTEXT_ALLOWED' "$LARCH_TEST_CLAUDE_STDIN_LOG" \
    || { echo "FAIL: outside --context-files content missing" >&2; exit 1; }

symlink_context="$TMPROOT/symlink-ctx.txt"
ln -s "$prompt" "$symlink_context"
set +e
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$TMPROOT/context-symlink-out.txt" \
    --prompt-file "$prompt" \
    --mode description \
    --context-files "$symlink_context" \
    --timeout 5 >/dev/null 2>"$TMPROOT/context-symlink.stderr"
ctx_symlink_rc=$?
set -e
[[ "$ctx_symlink_rc" -eq 2 ]] \
    || { echo "FAIL: symlink --context-files should yield exit 2 (got $ctx_symlink_rc)" >&2; exit 1; }
grep -Fq 'invalid context file' "$TMPROOT/context-symlink.stderr" \
    || { echo "FAIL: symlink --context-files missing subprocess stderr" >&2; exit 1; }

unreadable_context="$TMPROOT/unreadable.txt"
printf 'UNREADABLE_CONTEXT\n' > "$unreadable_context"
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    chmod 000 "$unreadable_context"
    set +e
    "$REPO_ROOT/scripts/launch-claude-review.sh" \
        --output "$TMPROOT/context-unreadable-out.txt" \
        --prompt-file "$prompt" \
        --mode description \
        --context-files "$unreadable_context" \
        --timeout 5 >/dev/null 2>"$TMPROOT/context-unreadable.stderr"
    ctx_unreadable_rc=$?
    set -e
    chmod 644 "$unreadable_context"
    [[ "$ctx_unreadable_rc" -eq 2 ]] \
        || { echo "FAIL: unreadable --context-files should yield exit 2 (got $ctx_unreadable_rc)" >&2; exit 1; }
    grep -Fq 'launch-claude-review.sh: --context-files path missing or unreadable' "$TMPROOT/context-unreadable.stderr" \
        || { echo "FAIL: unreadable --context-files missing expected stderr" >&2; exit 1; }
fi

# Timeout clamp: panel callers may pass 1860; subprocess cap is 1800.
clamp_out="$TMPROOT/clamp-out.txt"
clamp_err="$TMPROOT/clamp.stderr"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$clamp_out" \
    --prompt-file "$prompt" \
    --mode description \
    --timeout 1860 >"$TMPROOT/clamp.stdout" 2>"$clamp_err"
[[ "$(cat "$clamp_out")" == "claude review ok" ]] \
    || { echo "FAIL: timeout 1860 should clamp to 1800 and succeed" >&2; exit 1; }
grep -Fq 'clamping to 1800' "$clamp_err" \
    || { echo "FAIL: missing timeout clamp warning" >&2; exit 1; }

unchanged_out="$TMPROOT/unchanged-out.txt"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$unchanged_out" \
    --prompt-file "$prompt" \
    --mode description \
    --timeout 1200 >/dev/null
[[ "$(cat "$unchanged_out")" == "claude review ok" ]] \
    || { echo "FAIL: timeout 1200 should pass through unchanged" >&2; exit 1; }

echo "PASS: test-launch-claude-review.sh"
