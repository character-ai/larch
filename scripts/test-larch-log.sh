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
_commit_out="$(cd "$_repo" && "$LARCH_LOG" commit --log-root "$_staging/larch-logs" --skill implement --run-id "$_rid")"
assert_contains "$_commit_out" "LOG_WRITTEN=true" "commit reports written"
_batch="$_repo/larch-logs/implement/$_rid/plan-goals-test.md"
if [ -f "$_batch" ]; then pass "commit copies batch to repo under larch-logs/<skill>/<run-id>/"; else fail "commit copies batch to repo (missing $_batch)"; fi
_mf="$_repo/larch-logs/implement/$_rid/manifest.json"
if [ -f "$_mf" ]; then pass "commit copies manifest to repo"; else fail "commit copies manifest to repo (missing $_mf)"; fi
if git -C "$_repo" log -1 --format=%s | grep -qF "larch-logs"; then pass "commit creates git commit in repo"; else fail "commit creates git commit in repo"; fi
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
    pass "flush does not create commit after sentinel"
else
    fail "flush does not create commit after sentinel"
fi
if [ ! -e "$_sentinel_repo/larch-logs/implement/$_sentinel_run" ]; then
    pass "flush does not copy logs into repo after sentinel"
else
    fail "flush should not copy logs into repo after sentinel"
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

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
