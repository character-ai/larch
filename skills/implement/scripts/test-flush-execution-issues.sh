#!/usr/bin/env bash
# test-flush-execution-issues.sh — offline harness for flush-execution-issues.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/flush-execution-issues.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-flush-execution-issues.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() {
    PASS=$((PASS + 1))
    printf 'PASS: %s\n' "$1"
}

fail() {
    FAIL=$((FAIL + 1))
    printf 'FAIL: %s\n' "$1" >&2
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -Fq -- "$needle"; then
        pass "$label"
    else
        fail "$label (missing: $needle)"
    fi
}

assert_file_contains() {
    local needle=$1 path=$2 label=$3
    assert_contains "$needle" "$(cat "$path" 2>/dev/null || true)" "$label"
}

assert_equals() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then
        pass "$label"
    else
        fail "$label (expected $expected got $actual)"
    fi
}

setup_plugin() {
    local root=$1
    mkdir -p "$root/scripts"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    cp "$REPO_ROOT/scripts/lib-execution-issues.sh" "$root/scripts/lib-execution-issues.sh"
    cat > "$root/scripts/larch-log.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [ "${LARCH_LOG_FAIL:-}" = "1" ]; then
    printf 'simulated larch-log failure\n' >&2
    exit 1
fi
cmd=${1:-}
shift || true
[ "$cmd" = "append" ] || { echo "unsupported command: $cmd" >&2; exit 2; }
log_root=""; skill=""; run_id=""; batch=""; record_file=""
while [ $# -gt 0 ]; do
    case "$1" in
        --log-root) log_root=$2; shift 2 ;;
        --skill) skill=$2; shift 2 ;;
        --run-id) run_id=$2; shift 2 ;;
        --batch) batch=$2; shift 2 ;;
        --record-file) record_file=$2; shift 2 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
path="$log_root/$skill/$run_id/$batch.ndjson"
mkdir -p "$(dirname "$path")"
cat "$record_file" >> "$path"
printf 'LOG_WRITTEN=true\nLOG_PATH=%s\n' "$path"
STUB
    cat > "$root/scripts/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
log=""; site=""; tool=""; exit_code=""; output_file=""; category=""
while [ $# -gt 0 ]; do
    case "$1" in
        --log) log=$2; shift 2 ;;
        --site) site=$2; shift 2 ;;
        --tool) tool=$2; shift 2 ;;
        --exit-code) exit_code=$2; shift 2 ;;
        --category) category=$2; shift 2 ;;
        --output-file) output_file=$2; shift 2 ;;
        --redact) shift ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done
{
    printf '\n### %s\n\n' "${category:-Tool Failures}"
    printf -- '- **Step %s — %s failed (exit %s)**:\n' "$site" "$tool" "$exit_code"
    cat "$output_file"
    printf '\n'
} >> "$log"
STUB
    chmod +x "$root/scripts/larch-log.sh" "$root/scripts/append-tool-failure.sh"
}

run_helper() {
    local plugin=$1 tmpdir=$2 log_root=$3 run_id=$4 issue_log=$5
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin" IMPLEMENT_TMPDIR="$tmpdir" \
        "$HELPER" --log-root "$log_root" --run-id "$run_id" --issue-log "$issue_log"
    local rc=$?
    set -e
    return "$rc"
}

line_count() {
    wc -l < "$1" | tr -d '[:space:]'
}

echo "=== test-flush-execution-issues ==="

PLUGIN="$TMP_ROOT/plugin"
setup_plugin "$PLUGIN"

case_dir="$TMP_ROOT/empty"
mkdir -p "$case_dir"
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-empty" "$case_dir/missing.md")
rc=$?
assert_equals 0 "$rc" "empty input exits 0"
assert_contains "FLUSH_STATUS=skip" "$out" "empty input emits skip"
assert_contains "RECORDS=0" "$out" "empty input emits zero records"

case_dir="$TMP_ROOT/single"
mkdir -p "$case_dir"
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Tool Failures

- tool failed once
ISSUES
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-single" "$case_dir/execution-issues.md")
rc=$?
batch="$case_dir/larch-logs/implement/run-single/execution-issues.ndjson"
assert_equals 0 "$rc" "single-section exits 0"
assert_contains "FLUSH_STATUS=ok" "$out" "single-section emits ok"
assert_contains "RECORDS=1" "$out" "single-section emits one record"
assert_file_contains '"step":"7a"' "$batch" "single-section records step 7a"
assert_file_contains '"source":"execution-issues.md pre-bump"' "$batch" "single-section records pre-bump source"
[ -s "$case_dir/.execution-issues-flushed.sha" ] && pass "single-section writes sentinel" || fail "single-section writes sentinel"

case_dir="$TMP_ROOT/multi"
mkdir -p "$case_dir"
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Tool Failures

- first failure

### Warnings

- warning entry
ISSUES
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-multi" "$case_dir/execution-issues.md")
rc=$?
batch="$case_dir/larch-logs/implement/run-multi/execution-issues.ndjson"
assert_equals 0 "$rc" "multi-section exits 0"
assert_contains "FLUSH_STATUS=ok" "$out" "multi-section emits ok"
assert_contains "RECORDS=2" "$out" "multi-section emits two records"
assert_equals 2 "$(line_count "$batch")" "multi-section appends two lines"
assert_file_contains '"category":"Tool Failures"' "$batch" "multi-section includes Tool Failures"
assert_file_contains '"category":"Warnings"' "$batch" "multi-section includes Warnings"

case_dir="$TMP_ROOT/idempotent"
mkdir -p "$case_dir"
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Warnings

- one warning
ISSUES
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-idem" "$case_dir/execution-issues.md")
rc=$?
batch="$case_dir/larch-logs/implement/run-idem/execution-issues.ndjson"
before=$(line_count "$batch")
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-idem" "$case_dir/execution-issues.md")
rc=$?
after=$(line_count "$batch")
assert_equals 0 "$rc" "idempotent rerun exits 0"
assert_contains "FLUSH_STATUS=already-flushed" "$out" "idempotent rerun emits already-flushed"
assert_contains "RECORDS=0" "$out" "idempotent rerun emits zero records"
assert_equals "$before" "$after" "idempotent rerun appends no duplicate"

case_dir="$TMP_ROOT/failure"
mkdir -p "$case_dir"
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Tool Failures

- original failure
ISSUES
set +e
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" IMPLEMENT_TMPDIR="$case_dir" LARCH_LOG_FAIL=1 \
    "$HELPER" --log-root "$case_dir/larch-logs" --run-id "run-fail" --issue-log "$case_dir/execution-issues.md")
rc=$?
set -e
assert_equals 1 "$rc" "larch-log failure exits 1"
assert_contains "FLUSH_STATUS=failed" "$out" "larch-log failure emits failed"
assert_file_contains "larch-log.sh failed" "$case_dir/execution-issues.md" "larch-log failure is appended to execution issues"
assert_file_contains "simulated larch-log failure" "$case_dir/execution-issues.md" "larch-log failure output is captured"

echo "=== test-flush-execution-issues: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
