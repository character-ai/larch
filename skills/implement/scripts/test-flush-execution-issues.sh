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

kv_value() {
    local key=$1 body=$2
    printf '%s\n' "$body" | awk -F= -v key="$key" '$1==key{print substr($0, index($0, "=") + 1); exit}'
}

setup_plugin() {
    local root=$1
    mkdir -p "$root/scripts" "$root/python"
    cat > "$root/python/cli.py" <<'STUB'
import os
import sys
from pathlib import Path

def _parse(args):
    d = {}
    i = 0
    while i < len(args):
        if args[i] == "--redact":
            i += 1
            continue
        if args[i].startswith("--") and i + 1 < len(args):
            d[args[i][2:]] = args[i + 1]
            i += 2
        else:
            print(f"unknown option: {args[i]}", file=sys.stderr)
            raise SystemExit(2)
    return d

def main():
    if sys.argv[1:3] == ["execution-issues", "flush"]:
        sys.path.insert(0, os.environ["LARCH_TEST_REPO_ROOT"] + "/python")
        from execution_issues import flush_execution_issues_main
        raise SystemExit(flush_execution_issues_main(sys.argv[3:]))
    if len(sys.argv) < 3 or sys.argv[1] != "run-log":
        print(f"unsupported command: {sys.argv[1:]}", file=sys.stderr)
        raise SystemExit(2)
    verb = sys.argv[2]
    if verb == "append":
        if os.environ.get("LARCH_LOG_FAIL", "") == "1":
            print("simulated larch-log failure", file=sys.stderr)
            raise SystemExit(1)
        d = _parse(sys.argv[3:])
        path = Path(d["log-root"]) / d["skill"] / d["run-id"] / f"{d['batch']}.ndjson"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(Path(d["record-file"]).read_text(encoding="utf-8"))
        print("LOG_WRITTEN=true")
        print(f"LOG_PATH={path}")
        raise SystemExit(0)
    if verb == "append-failure":
        d = _parse(sys.argv[3:])
        log = d.get("log", "")
        body = Path(d["output-file"]).read_text(encoding="utf-8") if d.get("output-file") else ""
        with open(log, "a", encoding="utf-8") as handle:
            handle.write(f"\n### {d.get('category', 'Tool Failures')}\n\n")
            handle.write(f"- **Step {d.get('site', '')} — {d.get('tool', '')} failed (exit {d.get('exit-code', '')})**:\n")
            handle.write(body)
            handle.write("\n")
        raise SystemExit(0)
    print(f"unsupported command: {verb}", file=sys.stderr)
    raise SystemExit(2)

if __name__ == "__main__":
    main()
STUB
}

run_helper() {
    local plugin=$1 tmpdir=$2 log_root=$3 run_id=$4 issue_log=$5
    set +e
    CLAUDE_PLUGIN_ROOT="$plugin" IMPLEMENT_TMPDIR="$tmpdir" LARCH_TEST_REPO_ROOT="$REPO_ROOT" \
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
if [ -f "$case_dir/.execution-issues-step7a-reached" ]; then pass "empty input writes Step 7a checkpoint"; else fail "empty input writes Step 7a checkpoint"; fi

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
append_log=$(kv_value APPEND_LOG_FILE "$out")
if [ -n "$append_log" ] && [ -r "$append_log" ]; then pass "single-section preserves append log file"; else fail "single-section preserves append log file"; fi
assert_file_contains '"step":"7a"' "$batch" "single-section records step 7a"
assert_file_contains '"source":"execution-issues.md pre-bump"' "$batch" "single-section records pre-bump source"
if [ -s "$case_dir/.execution-issues-flushed.sha" ]; then pass "single-section writes sentinel"; else fail "single-section writes sentinel"; fi
if [ ! -s "$case_dir/execution-issues.md" ]; then pass "single-section clears flushed issue log"; else fail "single-section clears flushed issue log"; fi

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
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Warnings

- one warning
ISSUES
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-idem" "$case_dir/execution-issues.md")
rc=$?
after=$(line_count "$batch")
assert_equals 0 "$rc" "idempotent rerun exits 0"
assert_contains "FLUSH_STATUS=already-flushed" "$out" "idempotent rerun emits already-flushed"
assert_contains "RECORDS=0" "$out" "idempotent rerun emits zero records"
assert_equals "$before" "$after" "idempotent rerun appends no duplicate"

case_dir="$TMP_ROOT/per-section-probe"
mkdir -p "$case_dir"
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Warnings

- already flushed section
ISSUES
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-section-probe" "$case_dir/execution-issues.md")
rc=$?
batch="$case_dir/larch-logs/implement/run-section-probe/execution-issues.ndjson"
assert_equals 0 "$rc" "per-section probe seed exits 0"
assert_contains "FLUSH_STATUS=ok" "$out" "per-section probe seed emits ok"
rm -f "$case_dir/.execution-issues-flushed.sha"
cat > "$case_dir/execution-issues.md" <<'ISSUES'
### Warnings

- already flushed section
ISSUES
before=$(line_count "$batch")
out=$(run_helper "$PLUGIN" "$case_dir" "$case_dir/larch-logs" "run-section-probe" "$case_dir/execution-issues.md")
rc=$?
after=$(line_count "$batch")
assert_equals 0 "$rc" "per-section probe rerun exits 0"
assert_contains "FLUSH_STATUS=already-flushed" "$out" "per-section probe rerun emits already-flushed"
assert_contains "RECORDS=0" "$out" "per-section probe rerun emits zero records"
assert_equals "$before" "$after" "per-section probe rerun appends no duplicate"
if [ ! -s "$case_dir/execution-issues.md" ]; then pass "per-section probe rerun clears flushed issue log"; else fail "per-section probe rerun clears flushed issue log"; fi

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
append_log=$(kv_value APPEND_LOG_FILE "$out")
if [ -n "$append_log" ] && [ -r "$append_log" ]; then pass "failure preserves append log file"; else fail "failure preserves append log file"; fi
assert_file_contains "run-log failed" "$case_dir/execution-issues.md" "larch-log failure is appended to execution issues"
assert_file_contains "simulated larch-log failure" "$case_dir/execution-issues.md" "larch-log failure output is captured"

echo "=== test-flush-execution-issues: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
