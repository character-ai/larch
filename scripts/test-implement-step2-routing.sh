#!/usr/bin/env bash
# Regression coverage for /implement Step 1 implementer waterfall prose (Step 2 binds the resolved --coder).

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
    grep -Fq -- "$needle" "$file" || fail "$label missing: $needle"
}

assert_not_contains() {
    local file="$1"
    local needle="$2"
    local label="$3"
    if grep -Fq -- "$needle" "$file"; then
        fail "$label forbidden substring present: $needle"
    fi
}

assert_contains "$IMPLEMENT_SKILL" '### Implementer waterfall' "implementer waterfall heading"
assert_contains "$IMPLEMENT_SKILL" 'Cursor → Codex → Claude' "implement waterfall"
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
assert_contains "$IMPLEMENT_SKILL" '--coder=cursor requested but Cursor runtime probe failed' "explicit cursor unavailable bail"
assert_contains "$IMPLEMENT_SKILL" '--coder=cursor requested but Cursor binary not found' "explicit cursor binary not found bail"
assert_contains "$IMPLEMENT_SKILL" '--coder=codex requested but Codex binary not found' "explicit codex binary not found bail"
assert_contains "$IMPLEMENT_SKILL" '--coder=codex requested but Codex runtime probe failed' "explicit codex unavailable bail"
assert_contains "$IMPLEMENT_SKILL" '--design-only requires external-backed plan-review but no external reviewer is available' "design-only externals-down bail"
assert_not_contains "$IMPLEMENT_SKILL" "When \`coder_explicit=true\`, the explicit value wins. Do not apply the Cursor → Codex → Claude waterfall" "removed blanket explicit-coder bypass sentence"
assert_contains "$IMPLEMENT_SKILL" 'coder_fallback=true' "coder fallback manifest flag"
assert_contains "$IMPLEMENT_SKILL" 'Cursor and Codex both unavailable' "both-down warning"
assert_contains "$IMPLEMENT_SKILL" 'they do not select the implementer.' "diff_lines informational non-routing clause"

assert_contains "$DESIGN_SKILL" 'diff_lines: <N>' "design plan diff_lines"
# shellcheck disable=SC2016 # literal runtime path text, not shell.
assert_contains "$DESIGN_SKILL" '$DESIGN_TMPDIR/diff-lines.txt' "design diff-lines export"

# Removed diff_lines-gated coder carve-outs must not silently return to SKILL.md.
assert_not_contains "$IMPLEMENT_SKILL" 'diff_lines < 30' "legacy diff_lines < 30 carve-out"
assert_not_contains "$IMPLEMENT_SKILL" 'diff_lines <= 3' "removed diff_lines <= 3 carve-out"
assert_not_contains "$IMPLEMENT_SKILL" '⚡ diff_lines' "removed diff_lines breadcrumb prefix"

echo "PASS: test-implement-step2-routing.sh"
