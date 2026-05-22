#!/usr/bin/env bash
# Regression harness for scripts/write-design-current-env.sh.
#
# shellcheck disable=SC2153
# (DESIGN_TMPDIR / SESSION_TMPDIR / SESSION_ID / etc. are introduced into
# subshell scopes via `source` of the writer's output file; shellcheck
# cannot follow that flow and otherwise warns "Possible misspelling".)

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd -P)
SUBJECT="$REPO_ROOT/scripts/write-design-current-env.sh"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-wdce-test.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

export HOME="$TMPROOT/home"
mkdir -p "$HOME"

TEST_CLAUDE_PID=8888881
symlink="$HOME/.cache/larch/sessions/current-design-env-${TEST_CLAUDE_PID}.sh"

# Case 1 — sourceable output sets all expected vars
case_dir="$TMPROOT/case1"
design_tmpdir="$case_dir/design-tmpdir"
mkdir -p "$design_tmpdir"
out_file="$case_dir/source-env.sh"

CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out_file" \
    --design-tmpdir "$design_tmpdir" \
    --session-id "ABC-123" \
    --claude-pid "$TEST_CLAUDE_PID" \
    --codex-present true \
    --cursor-present false \
    --codex-available true \
    --cursor-available false \
    --issue-number 2588

[ -f "$out_file" ] || fail "case1: output file not created"

# Source in a subshell and confirm the expected exports survived
(
    # shellcheck disable=SC1090,SC2153
    source "$out_file"
    [ "$DESIGN_TMPDIR" = "$design_tmpdir" ] || exit 11
    [ "$SESSION_TMPDIR" = "$design_tmpdir" ] || exit 12
    [ "$SESSION_ID" = "ABC-123" ] || exit 13
    [ "$ISSUE_NUMBER" = "2588" ] || exit 14
    [ "$CODEX_PRESENT" = "true" ] || exit 15
    [ "$CURSOR_PRESENT" = "false" ] || exit 16
    [ "$CODEX_AVAILABLE" = "true" ] || exit 17
    [ "$CURSOR_AVAILABLE" = "false" ] || exit 18
    [ "$CLAUDE_PLUGIN_ROOT" = "$REPO_ROOT" ] || exit 19
) || fail "case1: sourcing did not set expected vars (subshell exit $?)"

# Stable symlink should point at the output
[ -L "$symlink" ] || fail "case1: stable symlink not created"
target=$(readlink "$symlink")
[ "$target" = "$out_file" ] || fail "case1: symlink target $target != $out_file"

# Case 2 — shell-quoting survives a path with a space
case2_dir="$TMPROOT/case 2 with spaces"
design2="$case2_dir/d t"
mkdir -p "$design2"
out2="$case2_dir/source-env.sh"

CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out2" \
    --design-tmpdir "$design2" \
    --session-id "DEF-456" \
    --claude-pid "$TEST_CLAUDE_PID"

(
    # shellcheck disable=SC1090,SC2153
    source "$out2"
    [ "$DESIGN_TMPDIR" = "$design2" ] || exit 21
    [ "$SESSION_TMPDIR" = "$design2" ] || exit 22
) || fail "case2: spaces in path were not preserved through source (subshell exit $?)"

# Case 3 — atomic write: tmpfile must not survive after success
shopt -s nullglob
leftover=("$case_dir"/source-env.sh.tmp.*)
shopt -u nullglob
[ "${#leftover[@]}" -eq 0 ] || fail "case3: temp file leaked after atomic write: ${leftover[*]}"

# Case 4 — idempotent re-run overwrites cleanly and the symlink follows
case4_dir="$TMPROOT/case4"
design4a="$case4_dir/dir-a"
design4b="$case4_dir/dir-b"
mkdir -p "$design4a" "$design4b"
out4a="$case4_dir/a/source-env.sh"
out4b="$case4_dir/b/source-env.sh"
mkdir -p "$(dirname "$out4a")" "$(dirname "$out4b")"

CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out4a" --design-tmpdir "$design4a" --session-id "RUN-1" \
    --claude-pid "$TEST_CLAUDE_PID"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out4b" --design-tmpdir "$design4b" --session-id "RUN-2" \
    --claude-pid "$TEST_CLAUDE_PID"

target=$(readlink "$symlink")
[ "$target" = "$out4b" ] || fail "case4: symlink did not follow second run ($target)"

(
    # shellcheck disable=SC1090,SC2153
    source "$symlink"
    [ "$SESSION_ID" = "RUN-2" ] || exit 41
    [ "$DESIGN_TMPDIR" = "$design4b" ] || exit 42
) || fail "case4: re-sourced symlink does not reflect latest run (subshell exit $?)"

# Case 5 — argv validation rejects obvious bad input
_bad_tmpdir_err="$TMPROOT/wdce-bad-tmpdir.err"
_bad_session_err="$TMPROOT/wdce-bad-session.err"
if "$SUBJECT" --output /tmp/x --design-tmpdir relative --session-id RUN-3 \
        --claude-pid "$TEST_CLAUDE_PID" \
        2>"$_bad_tmpdir_err"; then
    fail "case5: relative --design-tmpdir was accepted"
fi
grep -q "must be an absolute path" "$_bad_tmpdir_err" || \
    fail "case5: relative --design-tmpdir missing expected error"

if "$SUBJECT" --output /tmp/x --design-tmpdir /tmp/y --session-id "bad id" \
        --claude-pid "$TEST_CLAUDE_PID" \
        2>"$_bad_session_err"; then
    fail "case5: invalid --session-id was accepted"
fi
grep -q "Invalid --session-id" "$_bad_session_err" || \
    fail "case5: invalid --session-id missing expected error"

# Case 6 — two Claude PIDs get independent symlink targets (concurrency invariant)
case6_root="$TMPROOT/case6"
pid_a=8888882
pid_b=8888883
design6a="$case6_root/a/d"
design6b="$case6_root/b/d"
mkdir -p "$design6a" "$design6b"
out6a="$case6_root/a/source-env.sh"
out6b="$case6_root/b/source-env.sh"
mkdir -p "$(dirname "$out6a")" "$(dirname "$out6b")"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out6a" --design-tmpdir "$design6a" --session-id "S-A" --claude-pid "$pid_a"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out6b" --design-tmpdir "$design6b" --session-id "S-B" --claude-pid "$pid_b"
link6a="$HOME/.cache/larch/sessions/current-design-env-${pid_a}.sh"
link6b="$HOME/.cache/larch/sessions/current-design-env-${pid_b}.sh"
[ -L "$link6a" ] || fail "case6: symlink for pid_a missing"
[ -L "$link6b" ] || fail "case6: symlink for pid_b missing"
[ "$(readlink "$link6a")" = "$out6a" ] || fail "case6: pid_a symlink wrong target"
[ "$(readlink "$link6b")" = "$out6b" ] || fail "case6: pid_b symlink wrong target"
(
    # shellcheck disable=SC1090,SC2153
    source "$link6a"
    [ "$DESIGN_TMPDIR" = "$design6a" ] || exit 61
    [ "$SESSION_ID" = "S-A" ] || exit 62
) || fail "case6: sourcing pid_a link failed (exit $?)"
(
    # shellcheck disable=SC1090,SC2153
    source "$link6b"
    [ "$DESIGN_TMPDIR" = "$design6b" ] || exit 71
    [ "$SESSION_ID" = "S-B" ] || exit 72
) || fail "case6: sourcing pid_b link failed (exit $?)"

# Case 7 — invalid --claude-pid values rejected
_bad_claude_pid="$TMPROOT/wdce-bad-claude-pid.err"
_inv_tmp="$TMPROOT/inv-tmp"
_inv_out="$TMPROOT/inv-out.sh"
mkdir -p "$_inv_tmp"
for _bad in 0 abc 12345678 08 ''; do
    : > "$_bad_claude_pid"
    if CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
            --output "$_inv_out" \
            --design-tmpdir "$_inv_tmp" \
            --session-id "PID-TEST" \
            --claude-pid "$_bad" \
            2>"$_bad_claude_pid"; then
        fail "case7: invalid --claude-pid '$_bad' was accepted"
    fi
    grep -q "Invalid --claude-pid" "$_bad_claude_pid" || \
        fail "case7: missing Invalid --claude-pid for value '$_bad'"
done

# Case 8 — omitted --claude-pid uses legacy symlink and stderr warning (shim)
(
    export HOME="$TMPROOT/shim-home"
    mkdir -p "$HOME"
    _sh_d="$TMPROOT/shim/design"
    _sh_o="$TMPROOT/shim/source-env.sh"
    mkdir -p "$_sh_d"
    _shim_err="$TMPROOT/shim.stderr"
    if CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
            --output "$_sh_o" \
            --design-tmpdir "$_sh_d" \
            --session-id "SHIM-1" \
            2>"$_shim_err"; then
        :
    else
        fail "case8: legacy shim invocation failed"
    fi
    _legacy="$HOME/.cache/larch/sessions/current-design-env.sh"
    [ -L "$_legacy" ] || fail "case8: legacy symlink not created"
    [ "$(readlink "$_legacy")" = "$_sh_o" ] || fail "case8: legacy symlink wrong target"
    grep -q "WARNING=.*claude-pid omitted" "$_shim_err" || \
        fail "case8: stderr missing transition warning"
) || fail "case8: shim subshell failed (exit $?)"

echo "PASS: test-write-design-current-env.sh"
