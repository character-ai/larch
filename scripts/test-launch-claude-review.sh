#!/usr/bin/env bash
# Regression harness for launch-claude-review.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPROOT="$(mktemp -d /tmp/larch-test-launch-claude-review-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/claude" <<'STUB'
#!/usr/bin/env bash
cat >/dev/null
printf 'claude review ok\n'
STUB
chmod +x "$STUB_BIN/claude"

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

# --role voter: context files (diff, plan, feature, scope) must NOT be forwarded
# to launch-claude-subprocess.sh. Verify by passing an invalid (symlink) diff file —
# if it were forwarded, canonical_existing_file would reject it and exit 2;
# with --role voter the symlink is accepted at parse time but never appended,
# so the voter succeeds.
voter_output="$TMPROOT/voter-out.txt"
voter_prompt="$TMPROOT/voter-prompt.txt"
printf 'vote on this ballot\n' > "$voter_prompt"
diff_for_voter="$TMPROOT/diff-for-voter-symlink.txt"
ln -s "$prompt" "$diff_for_voter"
PATH="$STUB_BIN:$PATH" "$REPO_ROOT/scripts/launch-claude-review.sh" \
    --output "$voter_output" \
    --prompt-file "$voter_prompt" \
    --mode description \
    --role voter \
    --diff-file "$diff_for_voter" \
    --timeout 5 >/dev/null
[[ "$(cat "$voter_output")" == "claude review ok" ]] \
    || { echo "FAIL: --role voter output passthrough (got: $(cat "$voter_output"))" >&2; exit 1; }

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

echo "PASS: test-launch-claude-review.sh"
