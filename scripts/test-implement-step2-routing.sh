#!/usr/bin/env bash
# Regression coverage for /implement Step 0 implementer selection (Step 2 binds the resolved --coder).

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# scripts/larch.sh is the only approved Rust entrypoint and reads this root.
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
IMPLEMENT_SKILL="$REPO_ROOT/skills/implement/SKILL.md"
BOOTSTRAP_RS="$REPO_ROOT/crates/larch-cli/src/implement_bootstrap_continuation.rs"
DESIGN_SKILL="$REPO_ROOT/skills/design/SKILL.md"
DISPATCH_RS="$REPO_ROOT/crates/larch-cli/src/implement_step2_commands_impl.rs"

# `external-defaults role` is Rust-owned (#8107). Skip the live registry probe
# when no built binary is available (Python-only harness shards).
RUST_AVAILABLE=0
for candidate in "${LARCH_BINARY:-}" "$REPO_ROOT/target/release/larch" "$REPO_ROOT/target/debug/larch"; do
    if [[ -n "$candidate" && -x "$candidate" ]] && "$candidate" external-defaults role --help >/dev/null 2>&1; then
        export LARCH_BINARY="$candidate"
        RUST_AVAILABLE=1
        break
    fi
done

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
if [[ "$RUST_AVAILABLE" == 1 ]]; then
    role_out="$("$REPO_ROOT/scripts/larch.sh" external-defaults role --role implement.step2_coder)"
    printf '%s\n' "$role_out" | grep -Fq 'KIND=waterfall' || fail "step2 coder role kind missing"
    printf '%s\n' "$role_out" | grep -Fq 'ORDER=codex,cursor,claude' || fail "step2 coder registry order changed"
else
    echo "SKIP: external-defaults role implement.step2_coder (no built larch binary; set LARCH_BINARY)" >&2
fi
assert_contains "$BOOTSTRAP_RS" 'fn coder_order_for_difficulty' "Rust difficulty-keyed coder preference"
assert_contains "$BOOTSTRAP_RS" 'const CURSOR_FIRST: &[&str] = &["cursor", "codex", "claude"]' "moderate coder order"
assert_contains "$BOOTSTRAP_RS" 'const CODEX_FIRST: &[&str] = &["codex", "cursor", "claude"]' "hard coder order"
assert_contains "$DISPATCH_RS" 'fn resolve_step2_effective_difficulty' "shared dispatch difficulty resolver"
assert_not_contains "$DISPATCH_RS" 'fn resolve_step2_difficulty' "duplicate dispatch difficulty resolver"
assert_contains "$BOOTSTRAP_RS" '.find(|candidate| match *candidate {' "single selected coder loop"
assert_contains "$BOOTSTRAP_RS" '.unwrap_or("claude")' "claude terminal waterfall"
assert_contains "$IMPLEMENT_SKILL" 'step-0-bootstrap.sh --mode initial' "Step 0 bootstrap invoke wrapper"
# shellcheck disable=SC2016 # literal markdown/code-span text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
# shellcheck disable=SC2016 # literal source text, not shell.
assert_not_contains "$IMPLEMENT_SKILL" '### Implementer waterfall' "deleted prompt-side waterfall heading"
assert_contains "$BOOTSTRAP_RS" '"cursor" => &["cursor", "codex", "claude"]' "explicit cursor branch"
assert_contains "$BOOTSTRAP_RS" '"codex" => &["codex", "cursor", "claude"]' "explicit codex branch"
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
