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
    --manual-requested true \
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
    [ "$MANUAL_REQUESTED" = "true" ] || exit 14
    [ "$ISSUE_NUMBER" = "2588" ] || exit 15
    [ "$CODEX_PRESENT" = "true" ] || exit 16
    [ "$CURSOR_PRESENT" = "false" ] || exit 17
    [ "$CODEX_AVAILABLE" = "true" ] || exit 18
    [ "$CURSOR_AVAILABLE" = "false" ] || exit 19
    [ "$CLAUDE_PLUGIN_ROOT" = "$REPO_ROOT" ] || exit 20
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

# Case 9 — omitted manual flag leaves MANUAL_REQUESTED unset
case9_dir="$TMPROOT/case9"
design9="$case9_dir/design"
out9="$case9_dir/source-env.sh"
mkdir -p "$design9"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out9" \
    --design-tmpdir "$design9" \
    --session-id "NO-MANUAL" \
    --claude-pid "$TEST_CLAUDE_PID"
(
    set -u
    # shellcheck disable=SC1090,SC2153
    source "$out9"
    [ "${MANUAL_REQUESTED+x}" != x ] || exit 91
) || fail "case9: omitted --manual-requested should leave MANUAL_REQUESTED unset (subshell exit $?)"

# Case 10 — explicit false is accepted and exported literally
case10_dir="$TMPROOT/case10"
design10="$case10_dir/design"
out10="$case10_dir/source-env.sh"
mkdir -p "$design10"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out10" \
    --design-tmpdir "$design10" \
    --session-id "MANUAL-FALSE" \
    --manual-requested false \
    --claude-pid "$TEST_CLAUDE_PID"
(
    # shellcheck disable=SC1090,SC2153
    source "$out10"
    [ "$MANUAL_REQUESTED" = "false" ] || exit 101
) || fail "case10: explicit false manual flag was not preserved (subshell exit $?)"

# Case 11 — invalid manual-requested enum rejected
bad_manual_err="$TMPROOT/wdce-bad-manual.err"
if CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
        --output "$TMPROOT/bad-manual.sh" \
        --design-tmpdir "$TMPROOT/bad-manual-dir" \
        --session-id "BAD-MANUAL" \
        --manual-requested maybe \
        --claude-pid "$TEST_CLAUDE_PID" \
        2>"$bad_manual_err"; then
    fail "case11: invalid --manual-requested value was accepted"
fi
grep -q "Invalid --manual-requested" "$bad_manual_err" || \
    fail "case11: invalid --manual-requested missing expected error"

# Case 12 — re-run without manual flag clears stale true from the rewritten env file
case12_dir="$TMPROOT/case12"
design12="$case12_dir/design"
out12="$case12_dir/source-env.sh"
mkdir -p "$design12"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out12" \
    --design-tmpdir "$design12" \
    --session-id "MANUAL-TRUE" \
    --manual-requested true \
    --claude-pid "$TEST_CLAUDE_PID"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out12" \
    --design-tmpdir "$design12" \
    --session-id "MANUAL-CLEARED" \
    --claude-pid "$TEST_CLAUDE_PID"
(
    set -u
    # shellcheck disable=SC1090,SC2153
    source "$out12"
    [ "$SESSION_ID" = "MANUAL-CLEARED" ] || exit 121
    [ "${MANUAL_REQUESTED+x}" != x ] || exit 122
) || fail "case12: stale MANUAL_REQUESTED=true was not cleared by omitted follow-up write (subshell exit $?)"

# Case 13 — no-flag refresh preserves reviewer keys; MANUAL_REQUESTED still clears
case13_dir="$TMPROOT/case13"
design13="$case13_dir/design"
out13="$case13_dir/source-env.sh"
mkdir -p "$design13"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out13" \
    --design-tmpdir "$design13" \
    --session-id "PRESERVE-SEED" \
    --manual-requested true \
    --codex-present true \
    --cursor-present false \
    --codex-available true \
    --cursor-available false \
    --claude-pid "$TEST_CLAUDE_PID"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out13" \
    --design-tmpdir "$design13" \
    --session-id "PRESERVE-REFRESH" \
    --claude-pid "$TEST_CLAUDE_PID"
(
    set -u
    # shellcheck disable=SC1090,SC2153
    source "$out13"
    [ "$SESSION_ID" = "PRESERVE-REFRESH" ] || exit 131
    [ "${MANUAL_REQUESTED+x}" != x ] || exit 132
    [ "$CODEX_PRESENT" = "true" ] || exit 133
    [ "$CURSOR_PRESENT" = "false" ] || exit 134
    [ "$CODEX_AVAILABLE" = "true" ] || exit 135
    [ "$CURSOR_AVAILABLE" = "false" ] || exit 136
) || fail "case13: no-flag refresh did not preserve reviewer keys or clear MANUAL_REQUESTED (subshell exit $?)"

# Case 14 — partial codex override mirrors alias peer; cursor keys preserved
case14_dir="$TMPROOT/case14"
design14="$case14_dir/design"
out14="$case14_dir/source-env.sh"
mkdir -p "$design14"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out14" \
    --design-tmpdir "$design14" \
    --session-id "PARTIAL-SEED" \
    --codex-present true \
    --cursor-present true \
    --codex-available false \
    --cursor-available true \
    --claude-pid "$TEST_CLAUDE_PID"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out14" \
    --design-tmpdir "$design14" \
    --session-id "PARTIAL-OVERRIDE" \
    --codex-present false \
    --claude-pid "$TEST_CLAUDE_PID"
(
    # shellcheck disable=SC1090,SC2153
    source "$out14"
    [ "$SESSION_ID" = "PARTIAL-OVERRIDE" ] || exit 141
    [ "$CODEX_PRESENT" = "false" ] || exit 142
    [ "$CODEX_AVAILABLE" = "false" ] || exit 143
    [ "$CURSOR_PRESENT" = "true" ] || exit 144
    [ "$CURSOR_AVAILABLE" = "true" ] || exit 145
) || fail "case14: partial codex override did not mirror peer or preserve cursor keys (subshell exit $?)"

# Case 15 — prior env recovery accepts only strict boolean exports
case15_dir="$TMPROOT/case15"
design15="$case15_dir/design"
out15="$case15_dir/source-env.sh"
mkdir -p "$design15"
cat >"$out15" <<'EOF'
#!/usr/bin/env bash
export CODEX_PRESENT=true
export CURSOR_PRESENT=$(touch /tmp/larch-wdce-should-not-exist)
export CODEX_AVAILABLE=maybe
export CURSOR_AVAILABLE=false
EOF
rm -f /tmp/larch-wdce-should-not-exist
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out15" \
    --design-tmpdir "$design15" \
    --session-id "STRICT-RECOVERY" \
    --claude-pid "$TEST_CLAUDE_PID"
[ ! -e /tmp/larch-wdce-should-not-exist ] || \
    fail "case15: prior env command substitution was executed during recovery"
(
    set -u
    # shellcheck disable=SC1090,SC2153
    source "$out15"
    [ "$CODEX_PRESENT" = "true" ] || exit 151
    [ "$CURSOR_AVAILABLE" = "false" ] || exit 152
    [ "${CURSOR_PRESENT+x}" != x ] || exit 153
    [ "${CODEX_AVAILABLE+x}" != x ] || exit 154
) || fail "case15: strict boolean recovery did not preserve expected values (subshell exit $?)"

echo "PASS: test-write-design-current-env.sh"
