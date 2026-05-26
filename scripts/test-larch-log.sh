#!/usr/bin/env bash
# test-larch-log.sh — regression harness for scripts/larch-log.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
LARCH_LOG="$SCRIPT_DIR/larch-log.sh"
LARCH_LOG_FLUSH="$SCRIPT_DIR/larch-log-flush.sh"

[ -x "$LARCH_LOG" ] || { echo "FAIL: $LARCH_LOG not executable" >&2; exit 1; }
[ -x "$LARCH_LOG_FLUSH" ] || { echo "FAIL: $LARCH_LOG_FLUSH not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-larch-log.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export LARCH_LOG_ROOT="$TMP/larch-logs"
unset LARCH_BREADCRUMB_STREAM LARCH_QUIET_ACTIVE LARCH_QUIET_PID \
    LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG LARCH_BREADCRUMBS_SURFACED_FILE || true

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

with_implement_tmpdir() {
    local tmpdir="$1"
    shift
    IMPLEMENT_TMPDIR="$tmpdir" "$@"
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:400})"
    fi
}

assert_append_rejects_markdown() {
    local batch="$1" label="$2"
    local raw_markdown="$TMP/raw-$batch.md"
    local out rc
    printf '## Raw Markdown\n\n- this is not a JSON record\n' > "$raw_markdown"
    set +e
    out="$("$LARCH_LOG" append --skill implement --run-id abc123 --batch "$batch" --record-file "$raw_markdown" 2>&1)"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then pass "$label exits non-zero"; else fail "$label should exit non-zero"; fi
    assert_contains "$out" "json-lines sanitizer rejected $batch" "$label error mentions json-lines sanitizer"
}

echo "=== init creates manifest ==="
out="$("$LARCH_LOG" init --skill implement --run-id abc123 --issue 1438)"
assert_contains "$out" "LOG_WRITTEN=true" "init writes"
manifest="$LARCH_LOG_ROOT/implement/abc123/manifest.json"
if [ -f "$manifest" ]; then pass "manifest exists"; else fail "manifest missing"; fi
if grep -q '"schema_version": 2' "$manifest"; then pass "manifest schema version"; else fail "manifest schema version"; fi
if grep -q '"operator_cwd":' "$manifest"; then pass "manifest operator cwd"; else fail "manifest operator cwd"; fi
if grep -q '"operator_repo_root":' "$manifest"; then pass "manifest operator repo root"; else fail "manifest operator repo root"; fi
if grep -q '"operator_cwd": "<OPERATOR_CWD>"' "$manifest"; then pass "manifest operator cwd redacted"; else fail "manifest operator cwd redacted"; fi
if grep -q '"operator_repo_root": "<REPO_ROOT>"' "$manifest"; then pass "manifest operator repo root redacted"; else fail "manifest operator repo root redacted"; fi
if grep -q '"steps_ran": {}' "$manifest" || grep -q '"steps_ran":{}' "$manifest"; then pass "manifest steps_ran default object"; else fail "manifest steps_ran default object"; fi

echo "=== replace write is redacted and idempotent ==="
payload="$TMP/payload.md"
cat > "$payload" <<'EOF'
## Goal
Verify redaction.

## Implementation Plan
Write a sectioned plan-goals-test payload that includes a token-like secret so
the larch-log write path can prove redaction while still satisfying the
plan-goals sanitizer contract.

token eyJfakeheadr12.fakepayload34.fakesign5678

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

echo "=== json-lines append rejects raw markdown ==="
# Seed one valid record to review-findings and oos-issues so we can assert
# their line counts stay at 1 after the rejected append (mirrors the
# execution-issues line-count guard that runs after its rejected appends).
printf '{"event":"seed"}\n' > "$record"
"$LARCH_LOG" append --skill implement --run-id abc123 --batch review-findings --record-file "$record" >/dev/null
"$LARCH_LOG" append --skill implement --run-id abc123 --batch oos-issues --record-file "$record" >/dev/null
assert_append_rejects_markdown "execution-issues" "execution-issues markdown append"
assert_append_rejects_markdown "review-findings" "review-findings markdown append"
assert_append_rejects_markdown "oos-issues" "oos-issues markdown append"
line_count="$(wc -l < "$LARCH_LOG_ROOT/implement/abc123/execution-issues.ndjson" | tr -d ' ')"
if [ "$line_count" = "2" ]; then pass "rejected execution-issues append leaves existing records unchanged"; else fail "rejected execution-issues append changed line count to $line_count"; fi
line_count="$(wc -l < "$LARCH_LOG_ROOT/implement/abc123/review-findings.ndjson" | tr -d ' ')"
if [ "$line_count" = "1" ]; then pass "rejected review-findings append leaves existing records unchanged"; else fail "rejected review-findings append changed line count to $line_count"; fi
line_count="$(wc -l < "$LARCH_LOG_ROOT/implement/abc123/oos-issues.ndjson" | tr -d ' ')"
if [ "$line_count" = "1" ]; then pass "rejected oos-issues append leaves existing records unchanged"; else fail "rejected oos-issues append changed line count to $line_count"; fi

echo "=== exists reports path without writing ==="
out="$("$LARCH_LOG" exists --skill implement --run-id abc123 --batch execution-issues)"
assert_contains "$out" "LOG_WRITTEN=false" "exists no write"
assert_contains "$out" "UNCHANGED=true" "exists found"

echo "=== manifest updates mutable fields ==="
out="$("$LARCH_LOG" manifest --skill implement --run-id abc123 --field status=done --field pr_number=99)"
assert_contains "$out" "LOG_WRITTEN=true" "manifest update writes"
if grep -q '"status": "done"' "$manifest"; then pass "manifest status updated"; else fail "manifest status updated"; fi
if grep -q '"pr_number": 99' "$manifest"; then pass "manifest field stored as JSON number"; else fail "manifest field stored as JSON number"; fi

echo "=== manifest rejects invalid steps_ran-prefixed keys ==="
set +e
out="$("$LARCH_LOG" manifest --skill implement --run-id abc123 --field steps_ranxfoo=true 2>&1)"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass "manifest rejects steps_ran typo key"; else fail "manifest rejects steps_ran typo key"; fi
assert_contains "$out" "invalid steps_ran manifest key" "manifest error names steps_ran guard"

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

echo "=== commit outside git worktree fails closed ==="
_saved_log_root="$LARCH_LOG_ROOT"
unset LARCH_LOG_ROOT
_outside_git="$TMP/outside-git"
mkdir -p "$_outside_git"
set +e
out="$(cd "$_outside_git" && "$LARCH_LOG" commit --log-root "$TMP/outside-staging/larch-logs" --skill implement --run-id outsidegit 2>&1)"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass "commit outside git exits non-zero"; else fail "commit outside git should fail"; fi
assert_contains "$out" "commit requires a git worktree" "commit outside git error mentions worktree requirement"
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
git -C "$_repo" checkout -q -b feature-log-commit
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
mkdir -p "$_staging/breadcrumbs"
PEM_BEGIN='-----BEGIN RSA PRIVATE ''KEY-----'
PEM_END='-----END RSA PRIVATE ''KEY-----'
{
    printf '%s\n' "larch:bc t=now d=0 p=1 s=test c=progress text=tmpdir /tmp/larch-implement-demoABC"
    printf '%s\n' "$PEM_BEGIN"
    printf '%s\n' 'MIIBOgIBAAJBAKj34GkxFhD90vcNLYLInFEX6Ppy1tPf9Cnzj4p4WGeKLs1Pt8Qu'
    printf '%s\n' "$PEM_END"
} > "$_staging/breadcrumbs/foo.ndjson"
_mf_staging="$_staging/larch-logs/implement/$_rid/manifest.json"
if command -v jq >/dev/null 2>&1; then
    _commit_ts_before="$(jq -r '.updated_at' "$_mf_staging")"
    sleep 1
else
    _commit_ts_before=""
fi
_commit_out="$(cd "$_repo" && with_implement_tmpdir "$_staging" "$LARCH_LOG" commit --log-root "$_staging/larch-logs" --skill implement --run-id "$_rid")"
assert_contains "$_commit_out" "LOG_WRITTEN=true" "commit reports written"
_batch="$_repo/larch-logs/implement/$_rid/plan-goals-test.md"
if [ -f "$_batch" ]; then pass "commit copies batch to repo under larch-logs/<skill>/<run-id>/"; else fail "commit copies batch to repo (missing $_batch)"; fi
_breadcrumbs="$_repo/larch-logs/implement/$_rid/breadcrumbs/foo.ndjson"
if [ -f "$_breadcrumbs" ]; then pass "commit publishes breadcrumbs directory"; else fail "commit publishes breadcrumbs directory (missing $_breadcrumbs)"; fi
if [ ! -e "$_repo/larch-logs/implement/$_rid/breadcrumbs/foo.quiet" ] && [ ! -e "$_repo/larch-logs/implement/$_rid/breadcrumbs/foo.done" ]; then
    pass "commit publishes only ndjson breadcrumbs"
else
    fail "commit must not publish non-ndjson breadcrumb sidecars"
fi
if grep -q '<REDACTED-PRIVATE-KEY>' "$_breadcrumbs" 2>/dev/null; then pass "commit redacts breadcrumb PEM"; else fail "commit redacts breadcrumb PEM"; fi
if grep -q 'MIIBOgIBAAJB' "$_breadcrumbs" 2>/dev/null; then fail "commit leaked raw breadcrumb PEM"; else pass "commit omits raw breadcrumb PEM"; fi
if grep -q '<TMPDIR>' "$_breadcrumbs" 2>/dev/null; then pass "commit redacts breadcrumb tmpdir path"; else fail "commit redacts breadcrumb tmpdir path"; fi
_mf="$_repo/larch-logs/implement/$_rid/manifest.json"
if [ -f "$_mf" ]; then pass "commit copies manifest to repo"; else fail "commit copies manifest to repo (missing $_mf)"; fi
if [ -n "$_commit_ts_before" ] && command -v jq >/dev/null 2>&1; then
    _commit_ts_after="$(jq -r '.updated_at' "$_mf")"
    if [ "$_commit_ts_before" != "$_commit_ts_after" ]; then pass "commit refreshes manifest updated_at"; else fail "commit did not refresh manifest updated_at"; fi
fi
if git -C "$_repo" log -1 --format=%s | grep -qF "larch-logs"; then pass "commit creates git commit in repo"; else fail "commit creates git commit in repo"; fi
export LARCH_LOG_ROOT="$_saved_log_root"

echo "=== commit fails closed on unsafe breadcrumb source ==="
_bc_fail_repo="$TMP/breadcrumb-fail-repo"
_bc_fail_staging="$TMP/breadcrumb-fail-staging"
_bc_fail_run="breadcrumbfail123"
mkdir -p "$_bc_fail_staging/breadcrumbs"
git init "$_bc_fail_repo" >/dev/null 2>&1
git -C "$_bc_fail_repo" config user.email "ci@test"
git -C "$_bc_fail_repo" config user.name "Test CI"
touch "$_bc_fail_repo/.gitkeep"
git -C "$_bc_fail_repo" add .
git -C "$_bc_fail_repo" commit -q -m "init"
git -C "$_bc_fail_repo" checkout -q -b feature-breadcrumb-fail
(cd "$_bc_fail_repo" && "$LARCH_LOG" init --log-root "$_bc_fail_staging/larch-logs" --skill implement --run-id "$_bc_fail_run" --issue 42) >/dev/null
(cd "$_bc_fail_repo" && "$LARCH_LOG" write --log-root "$_bc_fail_staging/larch-logs" --skill implement --run-id "$_bc_fail_run" --batch plan-goals-test --input-file "$_cpayload") >/dev/null
printf 'raw breadcrumb\n' > "$_bc_fail_staging/raw-breadcrumb.txt"
ln -s "$_bc_fail_staging/raw-breadcrumb.txt" "$_bc_fail_staging/breadcrumbs/bad.ndjson"
_bc_fail_rc=0
(cd "$_bc_fail_repo" && with_implement_tmpdir "$_bc_fail_staging" "$LARCH_LOG" commit --log-root "$_bc_fail_staging/larch-logs" --skill implement --run-id "$_bc_fail_run" >/dev/null 2>&1) || _bc_fail_rc=$?
if [ "$_bc_fail_rc" -ne 0 ]; then pass "commit exits non-zero on symlinked breadcrumb"; else fail "commit should fail on symlinked breadcrumb"; fi
if [ ! -e "$_bc_fail_repo/larch-logs/implement/$_bc_fail_run/breadcrumbs" ]; then
    pass "failed breadcrumb commit leaves no breadcrumbs directory"
else
    fail "failed breadcrumb commit must not leave breadcrumbs directory"
fi

echo "=== commit fails closed on breadcrumb redactor failure ==="
_bc_redact_repo="$TMP/breadcrumb-redact-repo"
_bc_redact_staging="$TMP/breadcrumb-redact-staging"
_bc_redact_run="breadcrumbredact123"
mkdir -p "$_bc_redact_staging/breadcrumbs"
git init "$_bc_redact_repo" >/dev/null 2>&1
git -C "$_bc_redact_repo" config user.email "ci@test"
git -C "$_bc_redact_repo" config user.name "Test CI"
touch "$_bc_redact_repo/.gitkeep"
git -C "$_bc_redact_repo" add .
git -C "$_bc_redact_repo" commit -q -m "init"
git -C "$_bc_redact_repo" checkout -q -b feature-breadcrumb-redact
(cd "$_bc_redact_repo" && "$LARCH_LOG" init --log-root "$_bc_redact_staging/larch-logs" --skill implement --run-id "$_bc_redact_run" --issue 42) >/dev/null
(cd "$_bc_redact_repo" && "$LARCH_LOG" write --log-root "$_bc_redact_staging/larch-logs" --skill implement --run-id "$_bc_redact_run" --batch plan-goals-test --input-file "$_cpayload") >/dev/null
printf 'breadcrumb redactor failure fixture\n' > "$_bc_redact_staging/breadcrumbs/fail.ndjson"
_orig_redact="$SCRIPT_DIR/redact-secrets.sh"
_saved_redact="$TMP/redact-secrets.original.sh"
cp "$_orig_redact" "$_saved_redact"
cat >"$TMP/redact-secrets.fail.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
exit 1
EOF
chmod +x "$TMP/redact-secrets.fail.sh"
cp "$TMP/redact-secrets.fail.sh" "$_orig_redact"
_bc_redact_rc=0
(cd "$_bc_redact_repo" && with_implement_tmpdir "$_bc_redact_staging" "$LARCH_LOG" commit --log-root "$_bc_redact_staging/larch-logs" --skill implement --run-id "$_bc_redact_run" >/dev/null 2>&1) || _bc_redact_rc=$?
cp "$_saved_redact" "$_orig_redact"
if [ "$_bc_redact_rc" -ne 0 ]; then pass "commit exits non-zero on breadcrumb redactor failure"; else fail "commit should fail on breadcrumb redactor failure"; fi
if [ ! -e "$_bc_redact_repo/larch-logs/implement/$_bc_redact_run/breadcrumbs" ]; then
    pass "redactor failure leaves no published breadcrumbs directory"
else
    fail "redactor failure must not leave published breadcrumbs directory"
fi

echo "=== commit rejects breadcrumb source outside session tmpdirs ==="
_bc_scope_repo="$TMP/breadcrumb-scope-repo"
_bc_scope_staging="$TMP/breadcrumb-scope-staging"
_bc_scope_run="breadcrumbscope123"
_outside_source="$TMP/outside-breadcrumbs"
mkdir -p "$_outside_source"
printf 'larch:bc t=now d=0 p=1 s=test c=progress text=outside\n' > "$_outside_source/outside.ndjson"
git init "$_bc_scope_repo" >/dev/null 2>&1
git -C "$_bc_scope_repo" config user.email "ci@test"
git -C "$_bc_scope_repo" config user.name "Test CI"
touch "$_bc_scope_repo/.gitkeep"
git -C "$_bc_scope_repo" add .
git -C "$_bc_scope_repo" commit -q -m "init"
git -C "$_bc_scope_repo" checkout -q -b feature-breadcrumb-scope
(cd "$_bc_scope_repo" && "$LARCH_LOG" init --log-root "$_bc_scope_staging/larch-logs" --skill implement --run-id "$_bc_scope_run" --issue 42) >/dev/null
(cd "$_bc_scope_repo" && "$LARCH_LOG" write --log-root "$_bc_scope_staging/larch-logs" --skill implement --run-id "$_bc_scope_run" --batch plan-goals-test --input-file "$_cpayload") >/dev/null
_bc_scope_rc=0
(cd "$_bc_scope_repo" && LARCH_BREADCRUMB_SOURCE_DIR="$_outside_source" with_implement_tmpdir "$_bc_scope_staging" "$LARCH_LOG" commit --log-root "$_bc_scope_staging/larch-logs" --skill implement --run-id "$_bc_scope_run" >/dev/null 2>&1) || _bc_scope_rc=$?
if [ "$_bc_scope_rc" -ne 0 ]; then pass "commit rejects breadcrumb source outside session tmpdirs"; else fail "commit should reject breadcrumb source outside session tmpdirs"; fi

echo "=== missing breadcrumb source does not delete committed breadcrumbs ==="
_bc_missing_repo="$TMP/breadcrumb-missing-repo"
_bc_missing_staging="$TMP/breadcrumb-missing-staging"
_bc_missing_run="breadcrumbmissing123"
mkdir -p "$_bc_missing_staging/breadcrumbs"
git init "$_bc_missing_repo" >/dev/null 2>&1
git -C "$_bc_missing_repo" config user.email "ci@test"
git -C "$_bc_missing_repo" config user.name "Test CI"
touch "$_bc_missing_repo/.gitkeep"
git -C "$_bc_missing_repo" add .
git -C "$_bc_missing_repo" commit -q -m "init"
git -C "$_bc_missing_repo" checkout -q -b feature-breadcrumb-missing
(cd "$_bc_missing_repo" && "$LARCH_LOG" init --log-root "$_bc_missing_staging/larch-logs" --skill implement --run-id "$_bc_missing_run" --issue 42) >/dev/null
(cd "$_bc_missing_repo" && "$LARCH_LOG" write --log-root "$_bc_missing_staging/larch-logs" --skill implement --run-id "$_bc_missing_run" --batch plan-goals-test --input-file "$_cpayload") >/dev/null
printf 'larch:bc t=now d=0 p=1 s=test c=progress text=first\n' > "$_bc_missing_staging/breadcrumbs/existing.ndjson"
(cd "$_bc_missing_repo" && with_implement_tmpdir "$_bc_missing_staging" "$LARCH_LOG" commit --log-root "$_bc_missing_staging/larch-logs" --skill implement --run-id "$_bc_missing_run") >/dev/null
rm -rf "$_bc_missing_staging/breadcrumbs"
(cd "$_bc_missing_repo" && with_implement_tmpdir "$_bc_missing_staging" "$LARCH_LOG" commit --log-root "$_bc_missing_staging/larch-logs" --skill implement --run-id "$_bc_missing_run") >/dev/null
if [ -f "$_bc_missing_repo/larch-logs/implement/$_bc_missing_run/breadcrumbs/existing.ndjson" ]; then
    pass "missing breadcrumb source leaves committed breadcrumbs intact"
else
    fail "missing breadcrumb source must not delete committed breadcrumbs"
fi

echo "=== commit does not include orphan stale-run directories ==="
_saved_log_root="$LARCH_LOG_ROOT"
unset LARCH_LOG_ROOT
_stale_repo="$TMP/stale-repo"
_stale_staging="$TMP/stale-staging"
_fresh_run="freshrun-abc123"
_stale_run="stalerun-old999"
_stale_payload="$TMP/stale-commit-payload.md"
mkdir -p "$_stale_staging"
git init "$_stale_repo" >/dev/null 2>&1
git -C "$_stale_repo" config user.email "ci@test"
git -C "$_stale_repo" config user.name "Test CI"
touch "$_stale_repo/.gitkeep"
git -C "$_stale_repo" add .
git -C "$_stale_repo" commit -q -m "init"
git -C "$_stale_repo" checkout -q -b feature-stale-isolation
# Pre-populate stale run dir in staging (simulates PREV_IMPLEMENT_TMPDIR handoff)
mkdir -p "$_stale_staging/larch-logs/implement/$_stale_run"
printf '{"schema_version":2,"skill":"implement","run_id":"%s","status":"in-progress"}\n' "$_stale_run" \
    > "$_stale_staging/larch-logs/implement/$_stale_run/manifest.json"
cat > "$_stale_payload" <<'EOF'
## Goal
Verify stale staging directories are ignored.

## Implementation Plan
Write a valid plan-goals-test payload for the fresh run while a stale run
directory already exists in the same staging root.

## Test plan
Run scripts/test-larch-log.sh.
EOF
# Init + write fresh run using same staging root that contains the stale dir
(cd "$_stale_repo" && "$LARCH_LOG" init --log-root "$_stale_staging/larch-logs" \
    --skill implement --run-id "$_fresh_run" --issue 99) >/dev/null
(cd "$_stale_repo" && "$LARCH_LOG" write --log-root "$_stale_staging/larch-logs" \
    --skill implement --run-id "$_fresh_run" --batch plan-goals-test \
    --input-file "$_stale_payload") >/dev/null
(cd "$_stale_repo" && "$LARCH_LOG" commit --log-root "$_stale_staging/larch-logs" \
    --skill implement --run-id "$_fresh_run") >/dev/null
# Assert: fresh run files exist in repo
if [ -f "$_stale_repo/larch-logs/implement/$_fresh_run/plan-goals-test.md" ]; then
    pass "commit includes fresh run plan-goals-test.md"
else
    fail "commit did not include fresh run plan-goals-test.md"
fi
# Assert: stale run dir was NOT copied or staged into the repo
if [ ! -e "$_stale_repo/larch-logs/implement/$_stale_run" ]; then
    pass "commit does not copy stale run directory to repo"
else
    fail "commit must not copy stale run directory to repo (found $_stale_repo/larch-logs/implement/$_stale_run)"
fi
# Assert: commit message references only the fresh run-id
_stale_commit_msg=$(git -C "$_stale_repo" log -1 --format=%s)
if printf '%s' "$_stale_commit_msg" | grep -qF "$_fresh_run" && ! printf '%s' "$_stale_commit_msg" | grep -qF "$_stale_run"; then
    pass "commit message references only fresh run-id"
else
    fail "commit message should reference only fresh run-id (got: $_stale_commit_msg)"
fi
export LARCH_LOG_ROOT="$_saved_log_root"

echo "=== flush no-ops after post-merge sentinel ==="
_saved_log_root="$LARCH_LOG_ROOT"
unset LARCH_LOG_ROOT
_sentinel_repo="$TMP/sentinel-repo"
_sentinel_impl="$TMP/sentinel-impl"
_sentinel_run="sentinelrun123"
mkdir -p "$_sentinel_impl"
git init "$_sentinel_repo" >/dev/null 2>&1
git -C "$_sentinel_repo" config user.email "ci@test"
git -C "$_sentinel_repo" config user.name "Test CI"
touch "$_sentinel_repo/.gitkeep"
git -C "$_sentinel_repo" add .
git -C "$_sentinel_repo" commit -q -m "init"
printf '%s\n' "$_sentinel_run" > "$_sentinel_impl/session-id"
printf 'MERGE_RESULT=merged\n' > "$_sentinel_impl/post-merge-sentinel"
_spayload="$TMP/sentinel-payload.md"
cat > "$_spayload" <<'EOF'
## Goal
Verify post-merge flush suppression.

## Implementation Plan
Stage a valid plan-goals-test payload, create the post-merge sentinel, and run
the flush helper. The helper must exit successfully without creating a commit.

## Test plan
Run scripts/test-larch-log.sh.
EOF
(cd "$_sentinel_repo" && "$LARCH_LOG" init --log-root "$_sentinel_impl/larch-logs" --skill implement --run-id "$_sentinel_run" --issue 42) >/dev/null
(cd "$_sentinel_repo" && "$LARCH_LOG" write --log-root "$_sentinel_impl/larch-logs" --skill implement --run-id "$_sentinel_run" --batch plan-goals-test --input-file "$_spayload") >/dev/null
_sentinel_head_before=$(git -C "$_sentinel_repo" rev-parse HEAD)
if (cd "$_sentinel_repo" && env "PATH=${PATH:-}" "IMPLEMENT_TMPDIR=$_sentinel_impl" "LARCH_NO_LOGS_COMMIT=false" "$LARCH_LOG_FLUSH"); then
    pass "flush exits 0 with post-merge sentinel"
else
    fail "flush exits 0 with post-merge sentinel"
fi
_sentinel_head_after=$(git -C "$_sentinel_repo" rev-parse HEAD)
if [ "$_sentinel_head_after" = "$_sentinel_head_before" ]; then
    pass "flush does not advance HEAD after sentinel"
else
    fail "flush should not advance HEAD after sentinel"
fi
if [ ! -e "$_sentinel_repo/larch-logs/implement/$_sentinel_run" ]; then
    pass "flush leaves no round directory under repo after sentinel"
else
    fail "flush should not leave a round directory under repo after sentinel"
fi
echo "=== flush honors Step 7a checkpoint without prior batch ==="
_checkpoint_repo="$TMP/checkpoint-repo"
_checkpoint_impl="$TMP/checkpoint-impl"
_checkpoint_run="checkpointrun123"
mkdir -p "$_checkpoint_impl"
git init "$_checkpoint_repo" >/dev/null 2>&1
git -C "$_checkpoint_repo" config user.email "ci@test"
git -C "$_checkpoint_repo" config user.name "Test CI"
touch "$_checkpoint_repo/.gitkeep"
git -C "$_checkpoint_repo" add .
git -C "$_checkpoint_repo" commit -q -m "init"
git -C "$_checkpoint_repo" checkout -q -b feature-checkpoint-flush
printf '%s\n' "$_checkpoint_run" > "$_checkpoint_impl/session-id"
: > "$_checkpoint_impl/.execution-issues-step7a-reached"
cat > "$_checkpoint_impl/execution-issues.md" <<'EOF'
### Warnings

- logged after an empty Step 7a checkpoint
EOF
(cd "$_checkpoint_repo" && "$LARCH_LOG" init --log-root "$_checkpoint_impl/larch-logs" --skill implement --run-id "$_checkpoint_run" --issue 44) >/dev/null
(cd "$_checkpoint_repo" && "$LARCH_LOG" write --log-root "$_checkpoint_impl/larch-logs" --skill implement --run-id "$_checkpoint_run" --batch plan-goals-test --input-file "$_spayload") >/dev/null
_checkpoint_head_before=$(git -C "$_checkpoint_repo" rev-parse HEAD)
if (cd "$_checkpoint_repo" && env "PATH=${PATH:-}" "CLAUDE_PLUGIN_ROOT=$REPO_ROOT" "IMPLEMENT_TMPDIR=$_checkpoint_impl" "LARCH_NO_LOGS_COMMIT=false" "$LARCH_LOG_FLUSH"); then
    pass "checkpoint flush exits 0"
else
    fail "checkpoint flush exits 0"
fi
_checkpoint_head_after=$(git -C "$_checkpoint_repo" rev-parse HEAD)
if [ "$_checkpoint_head_after" != "$_checkpoint_head_before" ]; then
    pass "checkpoint flush creates commit"
else
    fail "checkpoint flush creates commit"
fi
_checkpoint_batch="$_checkpoint_repo/larch-logs/implement/$_checkpoint_run/execution-issues.ndjson"
if [ -f "$_checkpoint_batch" ]; then
    pass "checkpoint flush commits execution issues without prior batch"
else
    fail "checkpoint flush commits execution issues without prior batch"
fi
if [ ! -s "$_checkpoint_impl/execution-issues.md" ]; then
    pass "checkpoint flush clears execution issue log"
else
    fail "checkpoint flush clears execution issue log"
fi
echo "=== larch-log.sh commit rejects when post-merge sentinel exists ==="
_commit_sentinel_repo="$TMP/commit-sentinel-repo"
_commit_sentinel_impl="$TMP/commit-sentinel-impl"
_commit_sentinel_run="commitsentinel123"
mkdir -p "$_commit_sentinel_impl"
git init "$_commit_sentinel_repo" >/dev/null 2>&1
git -C "$_commit_sentinel_repo" config user.email "ci@test"
git -C "$_commit_sentinel_repo" config user.name "Test CI"
touch "$_commit_sentinel_repo/.gitkeep"
git -C "$_commit_sentinel_repo" add .
git -C "$_commit_sentinel_repo" commit -q -m "init"
printf 'MERGE_RESULT=merged\n' > "$_commit_sentinel_impl/post-merge-sentinel"
(cd "$_commit_sentinel_repo" && "$LARCH_LOG" init --log-root "$_commit_sentinel_impl/larch-logs" --skill implement --run-id "$_commit_sentinel_run" --issue 43) >/dev/null
(cd "$_commit_sentinel_repo" && "$LARCH_LOG" write --log-root "$_commit_sentinel_impl/larch-logs" --skill implement --run-id "$_commit_sentinel_run" --batch plan-goals-test --input-file "$_spayload") >/dev/null
_commit_sentinel_head_before=$(git -C "$_commit_sentinel_repo" rev-parse HEAD)
_commit_sentinel_stderr="$TMP/commit-sentinel-stderr.txt"
_commit_sentinel_rc=0
(cd "$_commit_sentinel_repo" && env "PATH=${PATH:-}" "IMPLEMENT_TMPDIR=$_commit_sentinel_impl" "$LARCH_LOG" commit \
    --log-root "$_commit_sentinel_impl/larch-logs" --skill implement --run-id "$_commit_sentinel_run") \
    2>"$_commit_sentinel_stderr" || _commit_sentinel_rc=$?
if [ "$_commit_sentinel_rc" -ne 0 ]; then
    pass "larch-log.sh commit exits non-zero with post-merge sentinel"
else
    fail "larch-log.sh commit should exit non-zero with post-merge sentinel"
fi
if grep -q "refusing commit after post-merge sentinel" "$_commit_sentinel_stderr" 2>/dev/null; then
    pass "larch-log.sh commit emits sentinel refusal on stderr"
else
    fail "larch-log.sh commit: expected refusal message on stderr (got: $(head -1 "$_commit_sentinel_stderr" 2>/dev/null))"
fi
_commit_sentinel_head_after=$(git -C "$_commit_sentinel_repo" rev-parse HEAD)
if [ "$_commit_sentinel_head_after" = "$_commit_sentinel_head_before" ]; then
    pass "larch-log.sh commit does not create a commit when sentinel exists"
else
    fail "larch-log.sh commit must not create a commit when sentinel exists"
fi

echo "=== larch-log.sh commit rejects on origin default branch ==="
_default_repo="$TMP/default-branch-repo"
_default_staging="$TMP/default-branch-staging"
_default_run="defaultbranch123"
mkdir -p "$_default_staging"
git init "$_default_repo" >/dev/null 2>&1
git -C "$_default_repo" config user.email "ci@test"
git -C "$_default_repo" config user.name "Test CI"
touch "$_default_repo/.gitkeep"
git -C "$_default_repo" add .
git -C "$_default_repo" commit -q -m "init"
git -C "$_default_repo" branch -M trunk
git -C "$_default_repo" update-ref refs/remotes/origin/trunk HEAD
git -C "$_default_repo" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk
(cd "$_default_repo" && "$LARCH_LOG" init --log-root "$_default_staging/larch-logs" --skill implement --run-id "$_default_run" --issue 44) >/dev/null
(cd "$_default_repo" && "$LARCH_LOG" write --log-root "$_default_staging/larch-logs" --skill implement --run-id "$_default_run" --batch plan-goals-test --input-file "$_spayload") >/dev/null
_default_head_before=$(git -C "$_default_repo" rev-parse HEAD)
_default_stderr="$TMP/default-branch-stderr.txt"
_default_rc=0
(cd "$_default_repo" && env "PATH=${PATH:-}" "IMPLEMENT_TMPDIR=" "$LARCH_LOG" commit \
    --log-root "$_default_staging/larch-logs" --skill implement --run-id "$_default_run") \
    2>"$_default_stderr" || _default_rc=$?
if [ "$_default_rc" -ne 0 ]; then
    pass "larch-log.sh commit exits non-zero on default branch"
else
    fail "larch-log.sh commit should exit non-zero on default branch"
fi
if grep -q "refusing commit on default branch/main" "$_default_stderr" 2>/dev/null; then
    pass "larch-log.sh commit emits default-branch refusal on stderr"
else
    fail "larch-log.sh commit: expected default-branch refusal on stderr (got: $(head -1 "$_default_stderr" 2>/dev/null))"
fi
_default_head_after=$(git -C "$_default_repo" rev-parse HEAD)
if [ "$_default_head_after" = "$_default_head_before" ]; then
    pass "larch-log.sh commit does not create a commit on default branch"
else
    fail "larch-log.sh commit must not create a commit on default branch"
fi
if [ ! -e "$_default_repo/larch-logs/implement/$_default_run" ]; then
    pass "larch-log.sh commit does not copy logs into repo on default branch"
else
    fail "larch-log.sh commit should not copy logs into repo on default branch"
fi

export LARCH_LOG_ROOT="$_saved_log_root"

echo "=== write-round commits scout and dynamic-archetype artifacts ==="
_wr_staging="$TMP/wr-staging"
_wr_run="wrround-scout-001"
_wr_source="$TMP/wr-source-round1"
mkdir -p "$_wr_source/dynamic-archetypes"

# Allowed round artifacts
printf 'SCOUT_STATUS=ok\nSCOUT_RESULT=fired\n' > "$_wr_source/scout-round1-status.env"
printf '{"archetypes":["api-contract","edge-cases"]}\n' > "$_wr_source/scout-round1-manifest.json"
printf '{"raw":"scout output"}\n' > "$_wr_source/scout-round1-manifest.json.raw"
printf 'findings here\n' > "$_wr_source/findings.md"
# Flattened from dynamic-archetypes/
printf '# reviewer-dyn-api-contract\n' > "$_wr_source/dynamic-archetypes/reviewer-dyn-api-contract.md"
printf '# dyn-api-contract-prompt\n' > "$_wr_source/dynamic-archetypes/dyn-api-contract-prompt.md"
# Denied files that should stay out
printf 'raw output\n' > "$_wr_source/cursor-specialist-correctness-output.txt"
printf 'vote prompt\n' > "$_wr_source/main-agent-vote-prompt.txt"
printf 'pre-retry narrative\n' > "$_wr_source/cursor-vote-output-first-pass.txt"
printf '{"channel":"stdout","pid":1,"time_since_last_progress":3,"capture_phase":"post_sigterm","transcript_tail_capture_phase":"pre_sigterm","diag_capture_note":"x","ps":"--- stall ps snapshot ---","lsof":"","git_state":{"status_porcelain":"","rebase_patch_excerpt":""},"transcript_tail_contract":"non_interleaved: stdout_block_then_stderr_block","last_transcript_lines":[]}\n' > "$_wr_source/cursor-ci-stall-test.json"

"$LARCH_LOG" init --log-root "$_wr_staging/larch-logs" --skill implement --run-id "$_wr_run" --issue 2356 >/dev/null
"$LARCH_LOG" write-round \
    --log-root "$_wr_staging/larch-logs" \
    --skill implement \
    --run-id "$_wr_run" \
    --round 1 \
    --source-dir "$_wr_source" >/dev/null

_wr_round="$_wr_staging/larch-logs/implement/$_wr_run/round-1"

# Test 1: scout status committed
if [ -f "$_wr_round/scout-round1-status.env" ]; then
    pass "write-round commits scout-round1-status.env"
else
    fail "write-round must commit scout-round1-status.env (missing)"
fi

# Test 2: scout manifest committed
if [ -f "$_wr_round/scout-round1-manifest.json" ]; then
    pass "write-round commits scout-round1-manifest.json"
else
    fail "write-round must commit scout-round1-manifest.json (missing)"
fi
if [ -f "$_wr_round/scout-round1-manifest.json.raw" ]; then
    pass "write-round commits scout-round1-manifest.json.raw"
else
    fail "write-round must commit scout-round1-manifest.json.raw (missing)"
fi

# Test 3: dynamic-archetypes flattened to round root (not in a subdir)
if [ -f "$_wr_round/reviewer-dyn-api-contract.md" ] && [ ! -d "$_wr_round/dynamic-archetypes" ]; then
    pass "write-round flattens reviewer-dyn-*.md to round root"
else
    fail "write-round must flatten reviewer-dyn-*.md (missing or still in subdir)"
fi
if [ -f "$_wr_round/dyn-api-contract-prompt.md" ]; then
    pass "write-round flattens dyn-*-prompt.md to round root"
else
    fail "write-round must flatten dyn-*-prompt.md (missing)"
fi

# Test 4: no-regression — existing allowed files still committed
if [ -f "$_wr_round/findings.md" ]; then
    pass "write-round no-regression: findings.md still committed"
else
    fail "write-round no-regression: findings.md missing"
fi

# Test 5: denied files stay denied
if [ ! -f "$_wr_round/cursor-specialist-correctness-output.txt" ]; then
    pass "write-round denied: cursor-specialist-*-output.txt excluded"
else
    fail "write-round must exclude cursor-specialist-*-output.txt"
fi
if [ ! -f "$_wr_round/main-agent-vote-prompt.txt" ]; then
    pass "write-round denied: *-vote-prompt.txt excluded"
else
    fail "write-round must exclude *-vote-prompt.txt"
fi

# Test 5b: cursor-ci stall JSON sidecars (committed round forensics)
if [ -f "$_wr_round/cursor-ci-stall-test.json" ]; then
    pass "write-round commits cursor-ci-stall-*.json"
else
    fail "write-round must commit cursor-ci-stall-*.json (missing)"
fi

# Test 6: parse-retry first-pass voter sidecar is included when present
if [ -f "$_wr_round/cursor-vote-output-first-pass.txt" ]; then
    pass "write-round commits cursor-vote-output-first-pass.txt"
else
    fail "write-round must commit cursor-vote-output-first-pass.txt (missing)"
fi
if grep -q 'pre-retry narrative' "$_wr_round/cursor-vote-output-first-pass.txt" 2>/dev/null; then
    pass "write-round cursor-vote-output-first-pass.txt content matches source"
else
    fail "write-round cursor-vote-output-first-pass.txt content mismatch"
fi

# Byte-for-byte content verification on scout files
_wr_status_content=$(cat "$_wr_round/scout-round1-status.env" 2>/dev/null || true)
if [ "$_wr_status_content" = "$(cat "$_wr_source/scout-round1-status.env")" ]; then
    pass "write-round scout-round1-status.env content matches source"
else
    fail "write-round scout-round1-status.env content mismatch"
fi
_wr_raw_content=$(cat "$_wr_round/scout-round1-manifest.json.raw" 2>/dev/null || true)
if [ "$_wr_raw_content" = "$(cat "$_wr_source/scout-round1-manifest.json.raw")" ]; then
    pass "write-round scout-round1-manifest.json.raw content matches source"
else
    fail "write-round scout-round1-manifest.json.raw content mismatch"
fi

echo "=== write-round keeps baseline artifacts unchanged without scout or dynamic inputs ==="
_wr_plain_staging="$TMP/wr-plain-staging"
_wr_plain_run="wrround-plain-001"
_wr_plain_source="$TMP/wr-source-plain"
mkdir -p "$_wr_plain_source"
printf 'baseline findings\n' > "$_wr_plain_source/findings.md"
printf 'accepted findings\n' > "$_wr_plain_source/accepted-findings.md"
printf 'rejected findings\n' > "$_wr_plain_source/rejected-findings.md"
printf 'vote summary\n' > "$_wr_plain_source/voting-tally.md"
printf 'forbidden raw output\n' > "$_wr_plain_source/cursor-specialist-plan-output.txt"

"$LARCH_LOG" init --log-root "$_wr_plain_staging/larch-logs" --skill implement --run-id "$_wr_plain_run" --issue 2357 >/dev/null
"$LARCH_LOG" write-round \
    --log-root "$_wr_plain_staging/larch-logs" \
    --skill implement \
    --run-id "$_wr_plain_run" \
    --round 1 \
    --source-dir "$_wr_plain_source" >/dev/null

_wr_plain_round="$_wr_plain_staging/larch-logs/implement/$_wr_plain_run/round-1"
for _plain_expected in findings.md accepted-findings.md rejected-findings.md voting-tally.md; do
    if [ -f "$_wr_plain_round/$_plain_expected" ]; then
        pass "write-round plain fixture keeps $_plain_expected"
    else
        fail "write-round plain fixture missing $_plain_expected"
    fi
done
if [ ! -e "$_wr_plain_round/scout-round1-status.env" ] && [ ! -e "$_wr_plain_round/scout-round1-manifest.json" ] && [ ! -e "$_wr_plain_round/dynamic-archetypes" ] && [ ! -e "$_wr_plain_round/cursor-specialist-plan-output.txt" ]; then
    pass "write-round plain fixture does not invent scout, dynamic, or denied artifacts"
else
    fail "write-round plain fixture wrote unexpected artifacts"
fi

echo "=== write-round rejects duplicate basenames across root and dynamic-archetypes ==="
_wr_dup_staging="$TMP/wr-dup-staging"
_wr_dup_run="wrround-dup-001"
_wr_dup_source="$TMP/wr-source-dup"
mkdir -p "$_wr_dup_source/dynamic-archetypes"
printf 'root findings\n' > "$_wr_dup_source/findings.md"
printf 'root dyn\n' > "$_wr_dup_source/reviewer-dyn-api-contract.md"
printf 'dynamic dyn\n' > "$_wr_dup_source/dynamic-archetypes/reviewer-dyn-api-contract.md"

"$LARCH_LOG" init --log-root "$_wr_dup_staging/larch-logs" --skill implement --run-id "$_wr_dup_run" --issue 2358 >/dev/null
_wr_dup_stderr="$TMP/wr-dup-stderr.txt"
_wr_dup_rc=0
_wr_dup_output=$("$LARCH_LOG" write-round \
    --log-root "$_wr_dup_staging/larch-logs" \
    --skill implement \
    --run-id "$_wr_dup_run" \
    --round 1 \
    --source-dir "$_wr_dup_source" \
    2>"$_wr_dup_stderr") || _wr_dup_rc=$?
if [ "$_wr_dup_rc" -ne 0 ] && printf '%s\n' "$_wr_dup_output" | grep -Fq "duplicate round artifact basename 'reviewer-dyn-api-contract.md'"; then
    pass "write-round rejects duplicate flattened basenames"
else
    fail "write-round must reject duplicate flattened basenames"
fi

echo "=== write-round rejects symlinked dynamic-archetypes ==="
_wr_link_staging="$TMP/wr-link-staging"
_wr_link_run="wrround-link-001"
_wr_link_source="$TMP/wr-source-link"
_wr_link_target="$TMP/wr-source-link-target"
mkdir -p "$_wr_link_source" "$_wr_link_target"
printf '# reviewer-dyn-external\n' > "$_wr_link_target/reviewer-dyn-external.md"
ln -s "$_wr_link_target" "$_wr_link_source/dynamic-archetypes"
printf 'root findings\n' > "$_wr_link_source/findings.md"

"$LARCH_LOG" init --log-root "$_wr_link_staging/larch-logs" --skill implement --run-id "$_wr_link_run" --issue 2359 >/dev/null
_wr_link_stderr="$TMP/wr-link-stderr.txt"
_wr_link_rc=0
_wr_link_output=$("$LARCH_LOG" write-round \
    --log-root "$_wr_link_staging/larch-logs" \
    --skill implement \
    --run-id "$_wr_link_run" \
    --round 1 \
    --source-dir "$_wr_link_source" \
    2>"$_wr_link_stderr") || _wr_link_rc=$?
if [ "$_wr_link_rc" -ne 0 ] && printf '%s\n' "$_wr_link_output" | grep -Fq "dynamic-archetypes must not be a symlink"; then
    pass "write-round rejects symlinked dynamic-archetypes"
else
    fail "write-round must reject symlinked dynamic-archetypes"
fi

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
