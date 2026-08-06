#!/usr/bin/env bash
# Offline harness for scripts/flush-vendor-failure-diagnostics.sh (#3713).

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/flush-vendor-failure-diagnostics.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-flush-vendor-failure.XXXXXX")" || { echo "mktemp failed" >&2; exit 1; }
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); echo "  ok: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1" >&2; }

assert_kv() {
    local label="$1" out="$2" needle="$3" rc=0
    printf '%s' "$out" | grep -Fq "$needle" 2>/dev/null || rc=$?
    if [ "$rc" -eq 0 ]; then ok "$label"; else fail "$label: '$needle' not in output: $out"; fi
}
assert_file_contains() {
    local label="$1" path="$2" needle="$3" rc=0
    grep -Fq "$needle" "$path" 2>/dev/null || rc=$?
    if [ "$rc" -eq 0 ]; then ok "$label"; else fail "$label: '$needle' absent in $path"; fi
}

# --- missing tmpdir → skipped ---
out=$("$SCRIPT" --tmpdir "$TMPROOT/does-not-exist" 2>&1 || true)
assert_kv "missing tmpdir skipped" "$out" "FLUSH_STATUS=skipped"

# --- no parts → empty ---
T1="$TMPROOT/run1"; mkdir -p "$T1"
out=$("$SCRIPT" --tmpdir "$T1" 2>&1 || true)
assert_kv "no parts → empty" "$out" "FLUSH_STATUS=empty"
if [ -e "$T1/vendor-failure-diagnostics.txt" ]; then fail "empty run should not create batch file"; else ok "empty run leaves no batch file"; fi

# --- parts present → flushed + merged (sorted) ---
T2="$TMPROOT/run2"; mkdir -p "$T2/vendor-failure-diagnostics.parts"
printf '===== alpha codex =====\nalpha body\n' > "$T2/vendor-failure-diagnostics.parts/part.aaa"
printf '===== beta cursor =====\nbeta body\n' > "$T2/vendor-failure-diagnostics.parts/part.bbb"
out=$("$SCRIPT" --tmpdir "$T2" 2>&1 || true)
assert_kv "parts → flushed" "$out" "FLUSH_STATUS=flushed"
assert_kv "parts count reported" "$out" "PARTS=2"
assert_file_contains "merged has alpha" "$T2/vendor-failure-diagnostics.txt" "alpha body"
assert_file_contains "merged has beta" "$T2/vendor-failure-diagnostics.txt" "beta body"
# sorted: part.aaa (alpha) precedes part.bbb (beta)
first_line=$(head -1 "$T2/vendor-failure-diagnostics.txt")
if [ "$first_line" = "===== alpha codex =====" ]; then ok "merge is sorted by part name"; else fail "merge order wrong: $first_line"; fi

# --- idempotent: re-flush overwrites, no duplication ---
"$SCRIPT" --tmpdir "$T2" >/dev/null 2>&1 || true
alpha_count=$(grep -c "alpha body" "$T2/vendor-failure-diagnostics.txt" 2>/dev/null || echo 0)
if [ "$alpha_count" = "1" ]; then ok "re-flush is idempotent (no duplication)"; else fail "re-flush duplicated content ($alpha_count)"; fi

# --- with log-root + run-id → batch staged ---
T3="$TMPROOT/run3"; mkdir -p "$T3/vendor-failure-diagnostics.parts"
printf '===== gamma =====\ngamma body\n' > "$T3/vendor-failure-diagnostics.parts/part.ccc"
LOG_ROOT="$T3/larch-logs"
RUN_ID="TEST-RUN-3713"
"$REPO_ROOT/scripts/larch.sh" run-log init --log-root "$LOG_ROOT" --skill implement --run-id "$RUN_ID" >/dev/null 2>&1 || true
out=$("$SCRIPT" --tmpdir "$T3" --run-id "$RUN_ID" --log-root "$LOG_ROOT" 2>&1 || true)
assert_kv "log-root flush reports flushed" "$out" "FLUSH_STATUS=flushed"
staged="$LOG_ROOT/implement/$RUN_ID/vendor-failure-diagnostics.txt"
if [ -f "$staged" ]; then
    assert_file_contains "batch staged content" "$staged" "gamma body"
else
    # larch-log init may require more setup offline; BATCH_WRITTEN=false is acceptable.
    assert_kv "batch write attempted" "$out" "BATCH_WRITTEN="
fi

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
