#!/usr/bin/env bash
# test-launch-codex-ci.sh — argv contract tests for launch-codex-ci.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-codex-ci-test.XXXXXX)"
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
    "$REPO_ROOT/scripts/launch-codex-ci.sh" "$@" > "$TMPDIR_BASE/out" 2> "$TMPDIR_BASE/err"
    local rc=$?
    set -e
    if [[ "$rc" == 2 ]]; then ok "$label"; else fail "$label"; cat "$TMPDIR_BASE/err"; fi
}

assert_fails "rejects bad role" --role nope --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo
assert_fails "rejects relative output" --role fix --output relative --run-id 1 --repo owner/repo
assert_fails "rejects unsafe output characters" --role fix --output "$TMPDIR_BASE/out with space" --run-id 1 --repo owner/repo
assert_fails "rejects relative --plan-file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --plan-file relative/plan.txt
assert_fails "rejects conflict-files with .." --role resolve-conflict --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files '../etc/passwd'
assert_fails "rejects conflict-files with invalid characters" --role resolve-conflict --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --conflict-files 'foo bar'

: >"$TMPDIR_BASE/failure-log-fixture.log"
assert_fails "rejects_failure_log_outside_implement_tmpdir" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log /etc/passwd
assert_fails "rejects_relative_failure_log" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log relative-only.log
assert_fails "rejects_missing_failure_log_file" --role fix --output "$TMPDIR_BASE/out" --run-id 1 --repo owner/repo --failure-log "$TMPDIR_BASE/no-such-failure.log"

if grep -q -- '--conflict-files' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "script supports --conflict-files"; else fail "script supports --conflict-files"; fi
if grep -q '<<<CONFLICT_PATHS>>>' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "resolve-conflict prompt fences conflict paths"; else fail "resolve-conflict prompt fences conflict paths"; fi
if grep -q -- "--task-kind \"\$TIMING_TASK_KIND\"" "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "uses timing task kind"; else fail "uses timing task kind"; fi
if grep -q 'plan-file' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "script supports --plan-file"; else fail "script supports --plan-file"; fi
if grep -q -- '--failure-log' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "script supports --failure-log"; else fail "script supports --failure-log"; fi
if grep -q 'Local reproduction invariant' "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "fix role prompt carries local reproduction invariant"; else fail "fix role prompt carries local reproduction invariant"; fi
if grep -q 'codex-ci-fix' "$REPO_ROOT/scripts/lib-timing-kinds.sh"; then ok "timing allow-list includes codex-ci-fix"; else fail "timing allow-list includes codex-ci-fix"; fi

cat > "$TMPDIR_BASE/token-record" <<'EOF'
TOOL=codex
TOTAL=99
RAW=codex_ci_fix
EOF
"$REPO_ROOT/scripts/append-token-record.sh" --input "$TMPDIR_BASE/token-record" --tmpdir "$TMPDIR_BASE"
if grep -q '"tool":"codex"' "$TMPDIR_BASE/token-report.ndjson"; then ok "append-token-record normalizes codex sidecar"; else fail "append-token-record normalizes codex sidecar"; fi

stub_bin="$TMPDIR_BASE/ci-fix-stub-bin"
mkdir -p "$stub_bin"
cat > "$stub_bin/codex" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$stub_bin/codex"
OUT_FIX="$TMPDIR_BASE/ci-fix-prompt-fix"
(cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
    bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role fix --output "$OUT_FIX" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1 || true
if grep -qF 'topology.tsv' "${OUT_FIX}.prompt" 2>/dev/null; then
    ok "fix role prompt includes topology.tsv sentinel"
else
    fail "fix role prompt includes topology.tsv sentinel"
fi
for role in resolve-conflict bump-classify changelog-draft; do
    OUT_NF="$TMPDIR_BASE/ci-fix-prompt-$role"
    case "$role" in
        resolve-conflict)
            (cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
                bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role "$role" --output "$OUT_NF" --run-id r1 --repo owner/repo \
                --conflict-files README.md --timeout 60) >/dev/null 2>&1 || true
            ;;
        *)
            (cd "$REPO_ROOT" && PATH="$stub_bin:$PATH" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" IMPLEMENT_TMPDIR="$TMPDIR_BASE" \
                bash "$REPO_ROOT/scripts/launch-codex-ci.sh" --role "$role" --output "$OUT_NF" --run-id r1 --repo owner/repo --timeout 60) >/dev/null 2>&1 || true
            ;;
    esac
    if grep -qF 'topology.tsv' "${OUT_NF}.prompt" 2>/dev/null; then
        fail "non-fix role $role must not include topology.tsv"
    else
        ok "non-fix role $role omits topology.tsv"
    fi
done

if [[ "$FAIL" -ne 0 ]]; then
    echo "test-launch-codex-ci: $FAIL failure(s), $PASS pass(es)" >&2
    exit 1
fi
echo "test-launch-codex-ci: $PASS pass(es)"
