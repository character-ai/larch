#!/usr/bin/env bash
# test-larch-log.sh — regression harness for scripts/larch-log.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
LARCH_LOG="$SCRIPT_DIR/larch-log.sh"

[ -x "$LARCH_LOG" ] || { echo "FAIL: $LARCH_LOG not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-larch-log.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export LARCH_LOG_ROOT="$TMP/larch-logs"

PASS=0
FAIL=0

fail() {
    echo "FAIL: $1" >&2
    FAIL=$((FAIL + 1))
}

pass() {
    echo "  ok: $1"
    PASS=$((PASS + 1))
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

echo "=== init creates manifest ==="
out="$("$LARCH_LOG" init --skill implement --run-id abc123 --issue 1438)"
assert_contains "$out" "LOG_WRITTEN=true" "init writes"
manifest="$LARCH_LOG_ROOT/implement/abc123/manifest.json"
if [ -f "$manifest" ]; then pass "manifest exists"; else fail "manifest missing"; fi
if grep -q '"schema_version": 2' "$manifest"; then pass "manifest schema version"; else fail "manifest schema version"; fi
if grep -q '"operator_cwd":' "$manifest"; then pass "manifest operator cwd"; else fail "manifest operator cwd"; fi
if grep -q '"operator_repo_root":' "$manifest"; then pass "manifest operator repo root"; else fail "manifest operator repo root"; fi
if grep -q '"status": "in-progress"' "$manifest"; then pass "manifest status"; else fail "manifest status"; fi

echo "=== replace write is redacted and idempotent ==="
payload="$TMP/payload.md"
cat > "$payload" <<'EOF'
## Goal
Verify redaction.

## Implementation Plan
Write a sectioned plan-goals-test payload that includes a token-like secret so
the larch-log write path can prove redaction while still satisfying the
plan-goals sanitizer contract.

token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD

## Test plan
Run scripts/test-larch-log.sh.
EOF
out="$("$LARCH_LOG" write --skill implement --run-id abc123 --batch plan-goals-test --input-file "$payload")"
assert_contains "$out" "LOG_WRITTEN=true" "write emits written"
log_file="$LARCH_LOG_ROOT/implement/abc123/plan-goals-test.md"
if grep -q '<REDACTED-TOKEN>' "$log_file"; then pass "write redacts token"; else fail "write redacts token"; fi
out="$("$LARCH_LOG" write --skill implement --run-id abc123 --batch plan-goals-test --input-file "$payload")"
assert_contains "$out" "UNCHANGED=true" "write unchanged retry"

echo "=== append writes newline-delimited records ==="
record="$TMP/record.ndjson"
printf '{"event":"one"}' > "$record"
out="$("$LARCH_LOG" append --skill implement --run-id abc123 --batch execution-issues --record-file "$record")"
assert_contains "$out" "LOG_WRITTEN=true" "append emits written"
printf '{"event":"two"}\n' > "$record"
"$LARCH_LOG" append --skill implement --run-id abc123 --batch execution-issues --record-file "$record" >/dev/null
line_count="$(wc -l < "$LARCH_LOG_ROOT/implement/abc123/execution-issues.ndjson" | tr -d ' ')"
if [ "$line_count" = "2" ]; then pass "append line count"; else fail "append line count got $line_count"; fi

echo "=== exists reports path without writing ==="
out="$("$LARCH_LOG" exists --skill implement --run-id abc123 --batch execution-issues)"
assert_contains "$out" "LOG_WRITTEN=false" "exists no write"
assert_contains "$out" "UNCHANGED=true" "exists found"

echo "=== manifest updates mutable fields ==="
out="$("$LARCH_LOG" manifest --skill implement --run-id abc123 --field status=done --field pr_number=99)"
assert_contains "$out" "LOG_WRITTEN=true" "manifest update writes"
if grep -q '"status": "done"' "$manifest"; then pass "manifest status updated"; else fail "manifest status updated"; fi
if grep -q '"pr_number": 99' "$manifest"; then pass "manifest field stored as JSON number"; else fail "manifest field stored as JSON number"; fi

echo "=== missing log root fails closed ==="
_saved_log_root="$LARCH_LOG_ROOT"
unset LARCH_LOG_ROOT
set +e
out="$("$LARCH_LOG" init --skill implement --run-id missingroot 2>&1)"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass "init without log root fails"; else fail "init without log root should fail"; fi
assert_contains "$out" "--log-root is required" "missing root error mentions --log-root"
export LARCH_LOG_ROOT="$_saved_log_root"

echo "=== commit copies staged files from explicit log root to repo ==="
_saved_log_root="$LARCH_LOG_ROOT"
unset LARCH_LOG_ROOT
_staging="$TMP/staging"
_repo="$TMP/fake-repo"
mkdir -p "$_staging"
git init "$_repo" >/dev/null 2>&1
git -C "$_repo" config user.email "ci@test"
git -C "$_repo" config user.name "Test CI"
touch "$_repo/.gitkeep"
git -C "$_repo" add .
git -C "$_repo" commit -q -m "init"
_rid="testcommit123"
_cpayload="$TMP/commit-payload.md"
cat > "$_cpayload" <<'EOF'
## Goal
Verify staged commit copying.

## Implementation Plan
Write a valid plan-goals-test payload into an explicit staging log root, then
commit the run so the harness can verify the batch is copied into the fake repo
under larch-logs/implement/<run-id>/.

## Test plan
Run scripts/test-larch-log.sh.
EOF
(cd "$_repo" && "$LARCH_LOG" init --log-root "$_staging/larch-logs" --skill implement --run-id "$_rid" --issue 42) >/dev/null
(cd "$_repo" && "$LARCH_LOG" write --log-root "$_staging/larch-logs" --skill implement --run-id "$_rid" --batch plan-goals-test --input-file "$_cpayload") >/dev/null
_commit_out="$(cd "$_repo" && "$LARCH_LOG" commit --log-root "$_staging/larch-logs" --skill implement --run-id "$_rid" --no-push)"
assert_contains "$_commit_out" "LOG_WRITTEN=true" "commit --no-push reports written"
_batch="$_repo/larch-logs/implement/$_rid/plan-goals-test.md"
if [ -f "$_batch" ]; then pass "commit copies batch to repo under larch-logs/<skill>/<run-id>/"; else fail "commit copies batch to repo (missing $_batch)"; fi
_mf="$_repo/larch-logs/implement/$_rid/manifest.json"
if [ -f "$_mf" ]; then pass "commit copies manifest to repo"; else fail "commit copies manifest to repo (missing $_mf)"; fi
if git -C "$_repo" log -1 --format=%s | grep -qF "larch-logs"; then pass "commit creates git commit in repo"; else fail "commit creates git commit in repo"; fi
export LARCH_LOG_ROOT="$_saved_log_root"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
