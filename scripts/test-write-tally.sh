#!/usr/bin/env bash
# test-write-tally.sh — regression tests for scripts/write-tally.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
WRITE_TALLY="$SCRIPT_DIR/write-tally.sh"

[ -x "$WRITE_TALLY" ] || { echo "FAIL: $WRITE_TALLY not executable" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "FAIL: jq is required" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-write-tally.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

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

assert_file_missing() {
    local path="$1" label="$2"
    if [ ! -e "$path" ]; then
        pass "$label"
    else
        fail "$label (unexpected path exists: $path)"
    fi
}

assert_json_field() {
    local file="$1" filter="$2" expected="$3" label="$4"
    local actual
    actual="$(jq -r "$filter" "$file")"
    if [ "$actual" = "$expected" ]; then
        pass "$label"
    else
        fail "$label (expected $expected; got $actual)"
    fi
}

body="$TMP/body.md"
cat > "$body" <<'EOF'
Voting accepted the plan with one small follow-up tracked in the run log.
EOF

echo "=== happy path: plan-review hard ==="
log_root="$TMP/logs-plan"
out="$("$WRITE_TALLY" --log-root "$log_root" --skill implement --run-id run-plan \
    --phase plan-review --mode hard --rounds 3 --accepted 2 --rejected 1 --body-file "$body")"
assert_contains "$out" "LOG_WRITTEN=true" "plan write emits LOG_WRITTEN"
plan_json="$log_root/implement/run-plan/plan-review-tally.json"
if jq -e . "$plan_json" >/dev/null; then pass "plan JSON valid"; else fail "plan JSON invalid"; fi
assert_json_field "$plan_json" '.schema_version' "1" "plan schema version"
assert_json_field "$plan_json" '.phase' "plan-review" "plan phase"
assert_json_field "$plan_json" '.batch' "plan-review-tally" "plan batch"
assert_json_field "$plan_json" '.mode' "hard" "plan mode"
assert_json_field "$plan_json" '.rounds' "3" "plan rounds"
assert_json_field "$plan_json" '.accepted_count' "2" "plan accepted count"
assert_json_field "$plan_json" '.rejected_count' "1" "plan rejected count"
assert_json_field "$plan_json" '.body' "$(cat "$body")" "plan body"

echo "=== happy path: code-review simple ==="
log_root="$TMP/logs-code"
out="$("$WRITE_TALLY" --log-root "$log_root" --skill implement --run-id run-code \
    --phase code-review --mode simple --rounds 1 --accepted 0 --rejected 0 --body-file "$body")"
assert_contains "$out" "LOG_WRITTEN=true" "code write emits LOG_WRITTEN"
code_json="$log_root/implement/run-code/code-review-tally.json"
assert_json_field "$code_json" '.batch' "code-review-tally" "code batch slug"
assert_json_field "$code_json" '.mode' "simple" "code mode"

echo "=== defaults ==="
log_root="$TMP/logs-defaults"
"$WRITE_TALLY" --log-root "$log_root" --skill implement --run-id run-defaults \
    --phase plan-review --mode simple --body-file "$body" >/dev/null
defaults_json="$log_root/implement/run-defaults/plan-review-tally.json"
assert_json_field "$defaults_json" '.rounds' "0" "default rounds"
assert_json_field "$defaults_json" '.accepted_count' "0" "default accepted"
assert_json_field "$defaults_json" '.rejected_count' "0" "default rejected"

echo "=== missing required flag ==="
set +e
missing_out="$("$WRITE_TALLY" --log-root "$TMP/logs-missing" --skill implement --run-id run-missing \
    --mode simple --body-file "$body" 2>"$TMP/missing.err")"
missing_rc=$?
set -e
if [ "$missing_rc" -eq 2 ]; then pass "missing phase exits 2"; else fail "missing phase exit $missing_rc"; fi
assert_contains "$(cat "$TMP/missing.err")" "--phase is required" "missing phase diagnostic"
if [ -z "$missing_out" ]; then
    pass "missing phase stdout empty"
else
    fail "missing phase stdout not empty: $missing_out"
fi

echo "=== invalid phase ==="
set +e
invalid_phase_out="$("$WRITE_TALLY" --log-root "$TMP/logs-invalid-phase" --skill implement --run-id run-invalid-phase \
    --phase code-search --mode simple --body-file "$body" 2>"$TMP/invalid-phase.err")"
invalid_phase_rc=$?
set -e
if [ "$invalid_phase_rc" -eq 2 ]; then pass "invalid phase exits 2"; else fail "invalid phase exit $invalid_phase_rc"; fi
assert_contains "$(cat "$TMP/invalid-phase.err")" "--phase must be plan-review or code-review" "invalid phase diagnostic"
if [ -z "$invalid_phase_out" ]; then
    pass "invalid phase stdout empty"
else
    fail "invalid phase stdout not empty: $invalid_phase_out"
fi

echo "=== invalid mode ==="
set +e
invalid_mode_out="$("$WRITE_TALLY" --log-root "$TMP/logs-invalid-mode" --skill implement --run-id run-invalid-mode \
    --phase plan-review --mode quick --body-file "$body" 2>"$TMP/invalid-mode.err")"
invalid_mode_rc=$?
set -e
if [ "$invalid_mode_rc" -eq 2 ]; then pass "invalid mode exits 2"; else fail "invalid mode exit $invalid_mode_rc"; fi
assert_contains "$(cat "$TMP/invalid-mode.err")" "--mode must be simple or hard" "invalid mode diagnostic"
if [ -z "$invalid_mode_out" ]; then
    pass "invalid mode stdout empty"
else
    fail "invalid mode stdout not empty: $invalid_mode_out"
fi

echo "=== missing body file ==="
set +e
missing_body_out="$("$WRITE_TALLY" --log-root "$TMP/logs-missing-body" --skill implement --run-id run-missing-body \
    --phase plan-review --mode simple --body-file "$TMP/does-not-exist.md" 2>"$TMP/missing-body.err")"
missing_body_rc=$?
set -e
if [ "$missing_body_rc" -eq 2 ]; then pass "missing body exits 2"; else fail "missing body exit $missing_body_rc"; fi
assert_contains "$(cat "$TMP/missing-body.err")" "body file not found" "missing body diagnostic"
if [ -z "$missing_body_out" ]; then
    pass "missing body stdout empty"
else
    fail "missing body stdout not empty: $missing_body_out"
fi

echo "=== composer failure passthrough ==="
stub_composer="$TMP/failing-compose.sh"
cat > "$stub_composer" <<'EOF'
#!/usr/bin/env bash
exit 9
EOF
chmod +x "$stub_composer"
set +e
compose_out="$(LARCH_WRITE_TALLY_COMPOSER="$stub_composer" "$WRITE_TALLY" \
    --log-root "$TMP/logs-compose-fail" --skill implement --run-id run-compose-fail \
    --phase plan-review --mode simple --body-file "$body" 2>"$TMP/compose-fail.err")"
compose_rc=$?
set -e
if [ "$compose_rc" -eq 2 ]; then pass "composer failure exits 2"; else fail "composer failure exit $compose_rc"; fi
assert_contains "$compose_out" "FAILED=true" "composer failure FAILED"
assert_contains "$compose_out" "ERROR=compose-tally-record.sh failed" "composer failure ERROR"
assert_file_missing "$TMP/logs-compose-fail/implement/run-compose-fail/plan-review-tally.json" "composer failure leaves no batch"

echo "=== writer failure passthrough ==="
bad_root="$TMP/not-a-directory"
printf 'not a directory\n' > "$bad_root"
set +e
writer_out="$("$WRITE_TALLY" --log-root "$bad_root" --skill implement --run-id run-writer-fail \
    --phase plan-review --mode simple --body-file "$body" 2>"$TMP/writer-fail.err")"
writer_rc=$?
set -e
if [ "$writer_rc" -ne 0 ]; then pass "writer failure exits non-zero"; else fail "writer failure should exit non-zero"; fi
assert_contains "$writer_out" "LOG_WRITTEN=false" "writer failure envelope LOG_WRITTEN"
assert_contains "$writer_out" "ERROR=cannot create log directory" "writer failure envelope ERROR"

echo "=== atomicity on failure ==="
atomic_root="$TMP/logs-atomic"
set +e
"$WRITE_TALLY" --log-root "$atomic_root" --skill implement --run-id run-atomic \
    --phase plan-review --mode simple --body-file "$TMP/missing-atomic.md" >/dev/null 2>"$TMP/atomic.err"
atomic_rc=$?
set -e
if [ "$atomic_rc" -eq 2 ]; then pass "atomic failure exits 2"; else fail "atomic failure exit $atomic_rc"; fi
assert_file_missing "$atomic_root/implement/run-atomic/plan-review-tally.json" "atomic failure leaves no batch"

echo "=== channel discipline ==="
stdout_file="$TMP/channel.out"
stderr_file="$TMP/channel.err"
set +e
"$WRITE_TALLY" --log-root "$TMP/logs-channel" --skill implement --run-id run-channel \
    --phase bad --mode simple --body-file "$body" >"$stdout_file" 2>"$stderr_file"
channel_rc=$?
set -e
if [ "$channel_rc" -eq 2 ]; then pass "channel invalid exits 2"; else fail "channel invalid exit $channel_rc"; fi
if [ ! -s "$stdout_file" ]; then
    pass "validation stdout empty"
else
    fail "validation stdout not empty: $(cat "$stdout_file")"
fi
assert_contains "$(cat "$stderr_file")" "--phase must be plan-review or code-review" "validation diagnostic on stderr"

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "All assertions passed."
