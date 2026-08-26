#!/usr/bin/env bash
# Assert committed harness scripts never invoke python3 (#8942).

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SELF_REL='scripts/test-harness-no-python3.sh'

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

# Token split so this file itself does not trip the scan.
_py='python'
_needle="${_py}3"

hits="$(
  {
    find "$REPO_ROOT/scripts" -maxdepth 1 -type f -name 'test-*.sh' -print
    find "$REPO_ROOT/skills" -type f -path '*/scripts/test-*.sh' -print
  } | LC_ALL=C sort -u | while IFS= read -r path; do
    rel="${path#"$REPO_ROOT"/}"
    [[ "$rel" == "$SELF_REL" ]] && continue
    NEEDLE="$_needle" awk -v rel="$rel" '
      BEGIN { needle = ENVIRON["NEEDLE"] }
      /^[[:space:]]*#/ { next }
      # Meta-assertions that search for the retired interpreter are allowed.
      /grep[^\n]*needle_placeholder/ { next }
      index($0, needle) == 0 { next }
      # Allow probes that only search for the token (grep/assert_not_contains).
      $0 ~ ("grep[^\n]*" needle) { next }
      $0 ~ ("assert_not_contains[^\n]*" needle) { next }
      # Flag remaining mentions: invocations or leftover heredocs/stubs.
      { printf "%s:%d:%s\n", rel, NR, $0 }
    ' "$path"
  done
)"

if [[ -n "$hits" ]]; then
  printf '%s\n' "$hits" >&2
  fail "committed harness scripts must not invoke ${_needle}"
fi

printf 'PASS: test-harness-no-python3.sh (no %s invocations in harness scripts)\n' "$_needle"
