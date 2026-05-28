#!/usr/bin/env bash
# test-lib-design-tmpdir.sh — regression harness for scripts/lib-design-tmpdir.sh.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
LIB="$ROOT/scripts/lib-design-tmpdir.sh"
# shellcheck source=scripts/lib-quiet.sh
source "$ROOT/scripts/lib-quiet.sh"
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$LIB"

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/test-lib-design-tmpdir.XXXXXX")
trap 'rm -rf "$SCRATCH"' EXIT

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_ok() {
    local label=$1
    shift
    if "$@" >/dev/null 2>"$SCRATCH/err.$label"; then
        return 0
    fi
    fail "$label: expected success, got: $(cat "$SCRATCH/err.$label" 2>/dev/null || true)"
}

assert_fail() {
    local label=$1
    shift
    if "$@" >/dev/null 2>"$SCRATCH/err.$label"; then
        fail "$label: expected failure"
    fi
    return 0
}

sessions_root="${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions"
mkdir -p "$sessions_root/allowed-sub"
assert_ok "home-sessions" larch_design_tmpdir_validate "$sessions_root/allowed-sub"

assert_ok "tmp-root" larch_design_tmpdir_validate "/tmp/larch-design-tmpdir-$$"

if [[ -n "${TMPDIR:-}" ]]; then
    mkdir -p "${TMPDIR%/}/larch-design-tmpdir-$$"
    assert_ok "tmpdir-set" larch_design_tmpdir_validate "${TMPDIR%/}/larch-design-tmpdir-$$"
fi

if [[ -n "${XDG_CACHE_HOME:-}" ]]; then
    mkdir -p "${XDG_CACHE_HOME%/}/larch/sessions/xdg-$$"
    assert_ok "xdg-cache-home" larch_design_tmpdir_validate "${XDG_CACHE_HOME%/}/larch/sessions/xdg-$$"
fi

# macOS /private/tmp canonicalization (no-op when /tmp is not symlinked).
private_tmp=$(cd /tmp 2>/dev/null && pwd -P)
mkdir -p "$private_tmp/larch-design-tmpdir-private-$$"
assert_ok "private-tmp" larch_design_tmpdir_validate "$private_tmp/larch-design-tmpdir-private-$$"

assert_fail "empty-input" larch_design_tmpdir_validate ""

assert_fail "disallowed-prefix" larch_design_tmpdir_validate "/var/tmp/larch-design-tmpdir-$$"

parent="$SCRATCH/parent"
mkdir -p "$parent"
assert_ok "nonexistent-tail" larch_design_tmpdir_validate "$parent/deep/nested/newdir"

assert_ok "dotdot-traversal" larch_design_tmpdir_validate "$parent/../parent/allowed-via-dotdot"

real_parent="$SCRATCH/real-parent"
mkdir -p "$real_parent/nested"
link_parent="$SCRATCH/link-parent"
ln -s "$real_parent" "$link_parent"
assert_ok "parent-symlink" larch_design_tmpdir_validate "$link_parent/nested/child"

mkdir -p "$sessions_root/leaf-escape"
if [[ -e /etc/passwd ]]; then
    ln -sf /etc/passwd "$sessions_root/leaf-escape/file-symlink"
    assert_fail "leaf-symlink-file" larch_design_tmpdir_validate "$sessions_root/leaf-escape/file-symlink"
fi

file_ancestor="$SCRATCH/not-a-directory"
printf 'x' >"$file_ancestor"
assert_fail "parent-resolution-failed" larch_design_tmpdir_validate "$file_ancestor/child"

glob_tmp="${SCRATCH}/glob-bracket"
mkdir -p "$glob_tmp"
saved_tmpdir="${TMPDIR:-}"
export TMPDIR="$glob_tmp"
# shellcheck disable=SC2034
_larch_design_tmpdir_allowlist=()
assert_ok "glob-metachar-tmpdir" larch_design_tmpdir_validate "${glob_tmp}/nested-$$"
export TMPDIR="$saved_tmpdir"

# Trailing-slash variant on an allowed prefix.
assert_ok "trailing-slash" larch_design_tmpdir_validate "${sessions_root%/}/"

printf 'PASS: test-lib-design-tmpdir.sh\n'
