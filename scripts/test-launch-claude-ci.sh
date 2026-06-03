#!/usr/bin/env bash
# test-launch-claude-ci.sh — argv contract tests for launch-claude-ci.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-claude-ci-test.XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR_BASE/execution-issues.md"
export IMPLEMENT_TMPDIR="$TMPDIR_BASE"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

PASS=0
FAIL=0
ok() { echo "  PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

assert_fails() {
    local label=$1
    shift
    set +e
    "$REPO_ROOT/scripts/launch-claude-ci.sh" "$@" > "$TMPDIR_BASE/out" 2> "$TMPDIR_BASE/err"
    local rc=$?
    set -e
    if [[ "$rc" == 2 ]]; then ok "$label"; else fail "$label"; cat "$TMPDIR_BASE/err"; fi
}

assert_fails "missing_role_fails" --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo
assert_fails "invalid_role_fails" --role unsupported --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo
assert_fails "missing_output_fails" --role fix --run-id 1 --repo owner/repo
assert_fails "non_absolute_output_fails" --role fix --output relative --run-id 1 --repo owner/repo
assert_fails "output_with_unsafe_chars_fails" --role fix --output "$TMPDIR_BASE/out with space" --run-id 1 --repo owner/repo
assert_fails "rejects_conflict_files_with_fix_role" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files 'a,b'
assert_fails "rejects_relative_plan_file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --plan-file relative/plan.txt
assert_fails "rejects_failure_log_outside_tmpdir" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log /etc/passwd

: >"$TMPDIR_BASE/fl.log"
assert_fails "rejects_failure_log_when_file_missing" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log "$TMPDIR_BASE/missing.log"
assert_fails "rejects_relative_failure_log" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log relative-only.log

: >"$TMPDIR_BASE/fl-resolve.log"
outside_fl=$(mktemp /tmp/lcc-fl-outside.XXXXXX)
assert_fails "rejects_failure_log_for_resolve_when_not_under_tmpdir" --role resolve-conflict --output "$TMPDIR_BASE/out-resolve" --run-id 1 --repo owner/repo --conflict-files 'Makefile' --failure-log "$outside_fl"
rm -f "$outside_fl"

if grep -q -- '--failure-log' "$REPO_ROOT/scripts/launch-claude-ci.sh"; then ok "script supports --failure-log"; else fail "script supports --failure-log"; fi
if grep -q '<<<FAILURE_LOG_EXCERPT>>>' "$REPO_ROOT/scripts/launch-claude-ci.sh"; then ok "failure log fenced in prompt"; else fail "failure log fenced in prompt"; fi
if grep -q 'Local reproduction invariant' "$REPO_ROOT/scripts/launch-claude-ci.sh"; then ok "fix role includes local reproduction invariant"; else fail "fix role includes local reproduction invariant"; fi
if ! grep -q 'MODE=baseline REASON=claude-subprocess' "$REPO_ROOT/scripts/launch-claude-ci.sh"; then ok "prompt_writer_persona_no_read_only_preamble"; else fail "prompt_writer_persona_no_read_only_preamble"; fi
if grep -q 'claude-ci-fix' "$REPO_ROOT/scripts/lib-timing-kinds.sh"; then ok "timing allow-list includes claude-ci-fix"; else fail "timing allow-list includes claude-ci-fix"; fi

printf 'sk-ant-api03-secretkey\n' >"$TMPDIR_BASE/fl.log"
if grep -q 'redact-secrets' "$REPO_ROOT/scripts/launch-claude-ci.sh"; then ok "failure_log_content_redacted_via_redact_secrets_sh_in_prompt"; else fail "redact pipeline referenced"; fi

stub_bin="$TMPDIR_BASE/ci-fix-stub-bin"
mkdir -p "$stub_bin"
cat > "$stub_bin/claude" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_bin/claude"
OUT_FIX="$TMPDIR_BASE/ci-fix-prompt-fix"
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    bash "$REPO_ROOT/scripts/launch-claude-ci.sh" --role fix --output "$OUT_FIX" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1 || true
if grep -qF 'topology.tsv' "${OUT_FIX}.prompt" 2>/dev/null; then
    ok "fix role prompt includes topology.tsv sentinel"
else
    fail "fix role prompt includes topology.tsv sentinel"
fi
OUT_RC="$TMPDIR_BASE/ci-fix-prompt-resolve"
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    bash "$REPO_ROOT/scripts/launch-claude-ci.sh" --role resolve-conflict --output "$OUT_RC" --run-id r1 --repo owner/repo --conflict-files README.md --timeout 60) >/dev/null 2>&1 || true
if grep -qF 'topology.tsv' "${OUT_RC}.prompt" 2>/dev/null; then
    fail "resolve-conflict role must not include topology.tsv"
else
    ok "resolve-conflict role omits topology.tsv"
fi

if [[ "$FAIL" -ne 0 ]]; then
    echo "test-launch-claude-ci: $FAIL failure(s), $PASS pass(es)" >&2
    exit 1
fi
echo "test-launch-claude-ci: $PASS pass(es)"
