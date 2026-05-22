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

# Case 1 — sourceable output sets all expected vars
case_dir="$TMPROOT/case1"
design_tmpdir="$case_dir/design-tmpdir"
mkdir -p "$design_tmpdir"
out_file="$case_dir/source-env.sh"

CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out_file" \
    --design-tmpdir "$design_tmpdir" \
    --session-id "ABC-123" \
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
symlink="$HOME/.cache/larch/sessions/current-design-env.sh"
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
    --session-id "DEF-456"

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
    --output "$out4a" --design-tmpdir "$design4a" --session-id "RUN-1"
CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SUBJECT" \
    --output "$out4b" --design-tmpdir "$design4b" --session-id "RUN-2"

target=$(readlink "$symlink")
[ "$target" = "$out4b" ] || fail "case4: symlink did not follow second run ($target)"

(
    # shellcheck disable=SC1090,SC2153
    source "$symlink"
    [ "$SESSION_ID" = "RUN-2" ] || exit 41
    [ "$DESIGN_TMPDIR" = "$design4b" ] || exit 42
) || fail "case4: re-sourced symlink does not reflect latest run (subshell exit $?)"

# Case 5 — argv validation rejects obvious bad input
if "$SUBJECT" --output /tmp/x --design-tmpdir relative --session-id RUN-3 \
        2>/tmp/wdce-bad-tmpdir.err; then
    fail "case5: relative --design-tmpdir was accepted"
fi
grep -q "must be an absolute path" /tmp/wdce-bad-tmpdir.err || \
    fail "case5: relative --design-tmpdir missing expected error"

if "$SUBJECT" --output /tmp/x --design-tmpdir /tmp/y --session-id "bad id" \
        2>/tmp/wdce-bad-session.err; then
    fail "case5: invalid --session-id was accepted"
fi
grep -q "Invalid --session-id" /tmp/wdce-bad-session.err || \
    fail "case5: invalid --session-id missing expected error"

echo "PASS: test-write-design-current-env.sh"
