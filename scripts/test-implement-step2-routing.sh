#!/usr/bin/env bash
# Regression coverage for /implement Step 0 implementer selection (Step 2 binds the resolved --coder).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
IMPLEMENT_SKILL="$REPO_ROOT/skills/implement/SKILL.md"
BOOTSTRAP_SH="$REPO_ROOT/scripts/implement-bootstrap.sh"
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

assert_contains "$IMPLEMENT_SKILL" 'phase_coder_select' "script-side coder selection pointer"
assert_contains "$IMPLEMENT_SKILL" 'Cursor → Codex → Claude' "implement waterfall"
assert_contains "$IMPLEMENT_SKILL" '--up-to-phase coder' "Step 0 bootstrap coder phase"
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
assert_contains "$BOOTSTRAP_SH" '--coder=${tool} requested but ${tool_caps} runtime probe failed' "explicit runtime unavailable bail"
# shellcheck disable=SC2016 # literal source text, not shell.
assert_contains "$BOOTSTRAP_SH" '--coder=${tool} requested but ${tool_caps} binary not found' "explicit binary not found bail"
# shellcheck disable=SC2016 # literal source text, not shell.
assert_contains "$BOOTSTRAP_SH" '${binary_key} could not be determined' "explicit binary-found undetermined bail"
assert_not_contains "$IMPLEMENT_SKILL" '### Implementer waterfall' "deleted prompt-side waterfall heading"
assert_not_contains "$IMPLEMENT_SKILL" 'Codex → Cursor → Claude' "old waterfall order"
assert_contains "$IMPLEMENT_SKILL" 'coder_fallback=true' "coder fallback manifest flag"
assert_contains "$BOOTSTRAP_SH" 'Cursor unavailable — falling back to Codex implementer' "cursor-to-codex warning"
assert_contains "$BOOTSTRAP_SH" 'Codex unavailable — falling back to Claude implementer' "codex-to-claude warning"
# shellcheck disable=SC2016 # literal source text, not shell.
assert_contains "$BOOTSTRAP_SH" '[ -z "${PLAN_FILE:-}" ]' "missing-plan empty PLAN_FILE guard"
# shellcheck disable=SC2016 # literal source text, not shell.
assert_contains "$BOOTSTRAP_SH" '[ ! -f "${PLAN_FILE:-/nonexistent}" ]' "missing-plan unreadable PLAN_FILE guard"
# shellcheck disable=SC2016 # literal source text, not shell.
assert_contains "$BOOTSTRAP_SH" '[ ! -f "${IMPLEMENT_TMPDIR:-/nonexistent}/feature-description.txt" ]' "missing-plan feature-description guard"
assert_contains "$IMPLEMENT_SKILL" 'does not route the implementer' "diff_lines informational non-routing clause"

assert_contains "$DESIGN_SKILL" 'diff_lines: <N>' "design plan diff_lines"
# shellcheck disable=SC2016 # literal runtime path text, not shell.
assert_contains "$DESIGN_SKILL" '$DESIGN_TMPDIR/diff-lines.txt' "design diff-lines export"

# Removed diff_lines-gated coder carve-outs must not silently return to SKILL.md.
assert_not_contains "$IMPLEMENT_SKILL" 'diff_lines < 30' "legacy diff_lines < 30 carve-out"
assert_not_contains "$IMPLEMENT_SKILL" 'diff_lines <= 3' "removed diff_lines <= 3 carve-out"
assert_not_contains "$IMPLEMENT_SKILL" '⚡ diff_lines' "removed diff_lines breadcrumb prefix"

echo "PASS: test-implement-step2-routing.sh"
