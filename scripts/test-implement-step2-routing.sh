#!/usr/bin/env bash
# Regression coverage for /implement Step 2 coder routing prose.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
IMPLEMENT_SKILL="$REPO_ROOT/skills/implement/SKILL.md"
DESIGN_SKILL="$REPO_ROOT/skills/design/SKILL.md"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_contains() {
    local file="$1"
    local needle="$2"
    local label="$3"
    grep -Fq "$needle" "$file" || fail "$label missing: $needle"
}

assert_contains "$IMPLEMENT_SKILL" 'diff_lines <= 3' "implement carve-out"
assert_contains "$IMPLEMENT_SKILL" 'Cursor → Codex → Claude' "implement waterfall"
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
assert_contains "$IMPLEMENT_SKILL" 'absent, empty, non-integer, or `>=4` value as "no carve-out"' "absent diff_lines waterfall"
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
assert_contains "$IMPLEMENT_SKILL" 'When `coder_explicit=true`, the explicit value wins. Do not apply the `diff_lines <= 3` carve-out, do not apply the Cursor → Codex → Claude waterfall' "explicit coder bypass"
assert_contains "$IMPLEMENT_SKILL" 'coder_fallback=true' "coder fallback manifest flag"
assert_contains "$IMPLEMENT_SKILL" 'Cursor and Codex both unavailable' "both-down warning"

assert_contains "$DESIGN_SKILL" 'diff_lines: <N>' "design plan diff_lines"
# shellcheck disable=SC2016 # literal runtime path text, not shell.
assert_contains "$DESIGN_SKILL" '$DESIGN_TMPDIR/diff-lines.txt' "design diff-lines export"

echo "PASS: test-implement-step2-routing.sh"
