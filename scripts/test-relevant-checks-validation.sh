#!/usr/bin/env bash
# Regression harness for run-relevant-checks-captured.sh input validation.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HELPER="$REPO_ROOT/scripts/run-relevant-checks-captured.sh"

tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-relevant-checks-validation.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

run_expect_fail() {
    local label="$1"
    shift
    local out rc=0
    out=$("$@" 2>/dev/null) || rc=$?
    [[ "$rc" -ne 0 ]] || fail "$label: expected non-zero"
    printf '%s' "$out"
}

fixture_repo="$tmp/repo"
mkdir -p "$fixture_repo/.claude/skills/relevant-checks/scripts"
cat > "$fixture_repo/.claude/skills/relevant-checks/scripts/run-checks.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
echo "=== Running pre-commit on 1 changed file(s) ==="
SCRIPT
chmod +x "$fixture_repo/.claude/skills/relevant-checks/scripts/run-checks.sh"

xdg="$tmp/cache"
session="$xdg/larch/sessions/claude-implement-repo-XYZ"
mkdir -p "$session"

for site in '..' 'a/b' $'bad\nx' '' '.hidden'; do
    out=$(run_expect_fail "site '$site'" env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site "$site" --tmpdir "$session")
    [[ "$out" == *"FAILURE_REASON=site-validation"* ]] || fail "bad site did not report site-validation: $out"
done

outside="$tmp/outside/claude-implement-repo-XYZ"
mkdir -p "$outside"
out=$(run_expect_fail "outside tmpdir" env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$outside")
[[ "$out" == *"FAILURE_REASON=tmpdir-validation"* ]] || fail "outside tmpdir reason mismatch: $out"

# Nested under /tmp must reject — /tmp fallback root only accepts direct
# children (session-setup.sh creates fallback sessions as direct /tmp
# children only). Two-level nesting like /tmp/foo/claude-implement-* is a
# foreign dir, not a larch fallback session.
nested_tmp="/tmp/larch-test-validation-nested-$$"
mkdir -p "$nested_tmp/claude-implement-nested-test"
out=$(run_expect_fail "nested /tmp tmpdir" env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$nested_tmp/claude-implement-nested-test")
rm -rf "$nested_tmp"
[[ "$out" == *"FAILURE_REASON=tmpdir-validation"* ]] || fail "nested /tmp tmpdir reason mismatch: $out"

# Direct /tmp child with claude-implement-* basename SHOULD validate
# (session-setup.sh's fallback creates exactly this). Use a real /tmp child
# to exercise the fallback-root accept branch.
direct_tmp_session="/tmp/claude-implement-larch-test-validation-direct-$$"
mkdir -p "$direct_tmp_session"
rc=0
out=$(env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$direct_tmp_session" 2>&1) || rc=$?
rm -rf "$direct_tmp_session"
[[ "$rc" -eq 0 ]] || fail "direct /tmp child should validate (rc=$rc, out=$out)"
[[ "$out" == *"RELEVANT_CHECKS_OK=true"* ]] || fail "direct /tmp child should produce success line: $out"

out=$(run_expect_fail "missing tmpdir" env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$tmp/missing")
[[ "$out" == *"FAILURE_REASON=tmpdir-validation"* ]] || fail "missing tmpdir reason mismatch: $out"

out=$(run_expect_fail "relative tmpdir" env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "relative")
[[ "$out" == *"FAILURE_REASON=tmpdir-validation"* ]] || fail "relative tmpdir reason mismatch: $out"

ln -s "$session" "$tmp/session-link"
out=$(run_expect_fail "symlink tmpdir" env XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$tmp/session-link")
[[ "$out" == *"FAILURE_REASON=tmpdir-validation"* ]] || fail "symlink tmpdir reason mismatch: $out"

mkdir -p "$session/relevant-checks"
printf 'preexisting\n' > "$session/relevant-checks/step3-1.log"
out=$(XDG_CACHE_HOME="$xdg" CLAUDE_PROJECT_DIR="$fixture_repo" "$HELPER" --site step3 --tmpdir "$session")
[[ "$out" == RELEVANT_CHECKS_OK=true* ]] || fail "valid invocation failed: $out"
[[ "$(cat "$session/relevant-checks/step3-1.log")" == "preexisting" ]] || fail "preexisting log was clobbered"
[[ -f "$session/relevant-checks/step3-2.log" ]] || fail "helper did not allocate second attempt"

echo "test-relevant-checks-validation: ok"
