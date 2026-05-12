#!/usr/bin/env bash
# test-launch-codex-ci.sh — argv contract tests for launch-codex-ci.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR_BASE="$(mktemp -d -t launch-codex-ci-test.XXXXXX)"
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

if grep -q -- "--task-kind \"\$TIMING_TASK_KIND\"" "$REPO_ROOT/scripts/launch-codex-ci.sh"; then ok "uses timing task kind"; else fail "uses timing task kind"; fi
if grep -q 'codex-ci-fix' "$REPO_ROOT/scripts/lib-timing-kinds.sh"; then ok "timing allow-list includes codex-ci-fix"; else fail "timing allow-list includes codex-ci-fix"; fi

cat > "$TMPDIR_BASE/token-record" <<'EOF'
TOOL=codex
TOTAL=99
RAW=codex_ci_fix
EOF
"$REPO_ROOT/scripts/append-token-record.sh" --input "$TMPDIR_BASE/token-record" --tmpdir "$TMPDIR_BASE"
if grep -q '"tool":"codex"' "$TMPDIR_BASE/token-report.ndjson"; then ok "append-token-record normalizes codex sidecar"; else fail "append-token-record normalizes codex sidecar"; fi

if [[ "$FAIL" -ne 0 ]]; then
    echo "test-launch-codex-ci: $FAIL failure(s), $PASS pass(es)" >&2
    exit 1
fi
echo "test-launch-codex-ci: $PASS pass(es)"
