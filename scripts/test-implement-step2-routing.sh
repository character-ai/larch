#!/usr/bin/env bash
# Regression coverage for /implement Step 0 implementer selection (Step 2 binds the resolved --coder).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
IMPLEMENT_SKILL="$REPO_ROOT/skills/implement/SKILL.md"
BOOTSTRAP_SH="$REPO_ROOT/python/bootstrap.py"
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
role_out="$(python3 "$REPO_ROOT/python/cli.py" external-defaults role --role implement.step2_coder)"
printf '%s\n' "$role_out" | grep -Fq 'KIND=waterfall' || fail "step2 coder role kind missing"
printf '%s\n' "$role_out" | grep -Fq 'ORDER=codex,cursor,claude' || fail "step2 coder registry order changed"
assert_contains "$BOOTSTRAP_SH" 'external_defaults.tool_order("implement.step2_coder")' "implicit registry-backed coder preference"
assert_contains "$BOOTSTRAP_SH" 'for candidate in order:' "single selected coder loop"
assert_contains "$BOOTSTRAP_SH" 'st.coder = "claude"' "claude terminal waterfall"
assert_contains "$IMPLEMENT_SKILL" 'step-0-bootstrap.sh --mode initial' "Step 0 bootstrap invoke wrapper"
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
assert_not_contains "$IMPLEMENT_SKILL" '### Implementer waterfall' "deleted prompt-side waterfall heading"
assert_contains "$BOOTSTRAP_SH" 'st.opts.coder_opt == "cursor"' "explicit cursor branch"
assert_contains "$BOOTSTRAP_SH" 'st.opts.coder_opt == "codex"' "explicit codex branch"
assert_contains "$IMPLEMENT_SKILL" 'coder_fallback=true' "coder fallback manifest flag"
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
assert_contains "$IMPLEMENT_SKILL" 'does not route the implementer' "diff_lines informational non-routing clause"

assert_contains "$DESIGN_SKILL" 'diff_lines: <N>' "design plan diff_lines"
# shellcheck disable=SC2016 # literal runtime path text, not shell.
assert_contains "$DESIGN_SKILL" '$DESIGN_TMPDIR/diff-lines.txt' "design diff-lines export"

# Removed diff_lines-gated coder carve-outs must not silently return to SKILL.md.
assert_not_contains "$IMPLEMENT_SKILL" 'diff_lines < 30' "legacy diff_lines < 30 carve-out"
assert_not_contains "$IMPLEMENT_SKILL" 'diff_lines <= 3' "removed diff_lines <= 3 carve-out"
assert_not_contains "$IMPLEMENT_SKILL" '⚡ diff_lines' "removed diff_lines breadcrumb prefix"

echo "PASS: test-implement-step2-routing.sh"
