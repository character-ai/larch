#!/usr/bin/env bash
# Regression harness for scripts/lib-submodule-prohibition.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
LIB="$REPO_ROOT/scripts/lib-submodule-prohibition.sh"
# shellcheck source=scripts/lib-submodule-prohibition.sh
source "$LIB"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-lib-submodule-prohibition.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail() { echo "FAIL: $1" >&2; exit 1; }

# Case 1: no-submodules branch (empty string arg).
out=$(emit_submodule_prohibition "")
printf '%s\n' "$out" | grep -Fq '## PROHIBITION: Submodules' || fail "case1: PROHIBITION header missing"
printf '%s\n' "$out" | grep -Fq 'No checked-out submodule paths were discovered' || fail "case1: no-submodules message missing"
printf '%s\n' "$out" | grep -Fq '.git/' || fail "case1: .git/ catch-all missing"

# Case 2: no-submodules branch (absent file arg).
out=$(emit_submodule_prohibition "$TMP/nonexistent.txt")
printf '%s\n' "$out" | grep -Fq 'No checked-out submodule paths were discovered' || fail "case2: absent file should use no-submodules branch"

# Case 3: with-submodules branch.
sublist="$TMP/submodules.txt"
printf 'vendor/foo\nexternal/bar\n' > "$sublist"
out=$(emit_submodule_prohibition "$sublist")
printf '%s\n' "$out" | grep -Fq '## PROHIBITION: Submodules' || fail "case3: PROHIBITION header missing"
printf '%s\n' "$out" | grep -Fq '- vendor/foo' || fail "case3: vendor/foo not listed"
printf '%s\n' "$out" | grep -Fq '- external/bar' || fail "case3: external/bar not listed"
printf '%s\n' "$out" | grep -Fq 'No checked-out submodule paths' && fail "case3: should NOT emit no-submodules message"
printf '%s\n' "$out" | grep -Fq '.git/' || fail "case3: .git/ catch-all missing"

echo "PASS: test-lib-submodule-prohibition.sh"
