#!/usr/bin/env bash
# test-verify-run-log-completeness.sh — regression harness for verify-run-log-completeness.sh

set -euo pipefail

# Drop inherited ambient override so default-case tests use the canonical manifest.
unset LARCH_VERIFY_MANIFEST

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
VERIFY="$SCRIPT_DIR/verify-run-log-completeness.sh"
MANIFEST="$SCRIPT_DIR/../docs/run-logs-required-files.tsv"

[ -x "$VERIFY" ] || { echo "FAIL: $VERIFY not executable" >&2; exit 1; }
[ -f "$MANIFEST" ] || { echo "FAIL: $MANIFEST not found" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-verify-run-log-completeness.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() { echo "  ok: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

assert_contains() {
    local label="$1" haystack="$2" needle="$3"
    if [[ "$haystack" == *"$needle"* ]]; then pass "$label"
    else fail "$label (missing '$needle'; got '${haystack:0:200}')"; fi
}

assert_equal() {
    local actual="$1" expected="$2" label="$3"
    if [[ "$actual" == "$expected" ]]; then pass "$label"
    else fail "$label (expected '$expected', got '$actual')"; fi
}

load_required_files() {
    awk -F '\t' '
        $1 == "relative_path" { next }
        $1 ~ /^#/ || $1 == "" { next }
        $2 ~ /^(always|step5|step7a)$/ { print $1 }
    ' "$MANIFEST"
}

assert_manifest_matches_batch_table() {
    # shellcheck source=scripts/larch-log-batches.sh
    source "$SCRIPT_DIR/larch-log-batches.sh"

    local mismatch=0 relative_path condition batch_slug extension expected_ext
    while IFS=$'\t' read -r relative_path condition batch_slug extension; do
        [ "$relative_path" = "relative_path" ] && continue
        [ -n "$relative_path" ] || continue
        case "$relative_path" in \#*) continue ;; esac
        case "$condition" in
            always|step5|step7a|step8|step9a1) ;;
            *) continue ;;
        esac
        case "$batch_slug" in
            manifest|direct-file) continue ;;
        esac

        if ! expected_ext="$(larch_log_batch_extension "$batch_slug" 2>/dev/null)"; then
            fail "manifest batch slug missing from larch-log-batches: $batch_slug"
            mismatch=1
            continue
        fi
        if [ ".$extension" != "$expected_ext" ]; then
            fail "manifest extension mismatch for $batch_slug: manifest .$extension vs batch table $expected_ext"
            mismatch=1
        else
            pass "manifest extension matches batch table for $batch_slug"
        fi
    done < "$MANIFEST"

    return "$mismatch"
}

REQUIRED_FILES=()
while IFS= read -r required_file; do
    REQUIRED_FILES+=("$required_file")
done < <(load_required_files)
assert_manifest_matches_batch_table

make_complete_run_dir() {
    local dir="$1"
    mkdir -p "$dir"
    for f in "${REQUIRED_FILES[@]}"; do
        printf 'placeholder\n' > "$dir/$f"
    done
}

# Test 1: all files present → OK
run_ok="$TMP/run-ok"
make_complete_run_dir "$run_ok"
out="$("$VERIFY" "$run_ok" 2>&1 || true)"
assert_contains "complete run emits OK" "$out" "OK"

# Test 15: repo-relative LARCH_VERIFY_MANIFEST resolves under REPO_ROOT (not process cwd)
if out="$(cd "$TMP" && LARCH_VERIFY_MANIFEST="docs/run-logs-required-files.tsv" "$VERIFY" "$run_ok" 2>&1)"; then
    :
else
    :
fi
assert_contains "relative manifest path resolves from repo root" "$out" "OK"

# Test 16: LARCH_VERIFY_MANIFEST relative path cannot escape repo with ..
if out="$(LARCH_VERIFY_MANIFEST='../outside-manifest.tsv' "$VERIFY" "$run_ok" 2>&1)"; then
    fail "expected non-zero exit for .. in LARCH_VERIFY_MANIFEST"
else
    assert_contains "manifest .. segment rejected" "$out" ".."
fi

# Test 2: missing execution-issues.ndjson from a Step-7a-complete run → MISSING reported
run_missing_step7a="$TMP/run-missing-step7a"
make_complete_run_dir "$run_missing_step7a"
rm "$run_missing_step7a/execution-issues.ndjson"
out="$("$VERIFY" "$run_missing_step7a" 2>&1 || true)"
assert_contains "missing step7a artifact emits MISSING" "$out" "MISSING=execution-issues.ndjson"

# Test 3: missing multiple files → all listed in MISSING
run_missing_multi="$TMP/run-missing-multi"
make_complete_run_dir "$run_missing_multi"
rm "$run_missing_multi/execution-issues.ndjson"
rm "$run_missing_multi/token-report.json"
out="$("$VERIFY" "$run_missing_multi" 2>&1 || true)"
assert_contains "multi-missing includes execution-issues" "$out" "execution-issues.ndjson"
assert_contains "multi-missing includes token-report" "$out" "token-report.json"

# Test 4: nonexistent run dir → error exit
out="$("$VERIFY" "$TMP/nonexistent-run" 2>&1 || true)"
assert_contains "nonexistent dir emits error" "$out" "not found"

# Test 5: pre-Step-7a partial tree should not require Step-5+ files
run_pre_step7a="$TMP/run-pre-step7a"
mkdir -p "$run_pre_step7a"
printf 'placeholder\n' > "$run_pre_step7a/manifest.json"
printf 'placeholder\n' > "$run_pre_step7a/plan-goals-test.md"
printf 'placeholder\n' > "$run_pre_step7a/plan-review-tally.json"
out="$("$VERIFY" "$run_pre_step7a" 2>&1 || true)"
assert_contains "pre-step7a partial emits OK" "$out" "OK"

# Test 6: Step-5 partial tree should require Step-5 files but not Step-7a+ files
run_step5="$TMP/run-step5"
mkdir -p "$run_step5"
for f in manifest.json plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl; do
    printf 'placeholder\n' > "$run_step5/$f"
done
out="$("$VERIFY" "$run_step5" 2>&1 || true)"
assert_contains "step5 partial emits OK" "$out" "OK"

# Test 7: Step-7a inferred from one artifact should require the rest of the Step-7a set
run_partial_step7a="$TMP/run-partial-step7a"
mkdir -p "$run_partial_step7a"
for f in manifest.json plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json; do
    printf 'placeholder\n' > "$run_partial_step7a/$f"
done
out="$("$VERIFY" "$run_partial_step7a" 2>&1 || true)"
assert_contains "partial step7a emits MISSING" "$out" "MISSING="
assert_contains "partial step7a requires execution-issues" "$out" "execution-issues.ndjson"
assert_contains "partial step7a requires timing-report" "$out" "timing-report.json"
assert_contains "partial step7a requires session-transcript" "$out" "session-transcript.jsonl"

# Test 8: Step-8 tree with explicit steps_ran.step9a1=false should not require Step-9a.1-only batches
run_step8="$TMP/run-step8"
mkdir -p "$run_step8"
cat > "$run_step8/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{"step9a1":false}}
EOF
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md final-summary.md; do
    printf 'placeholder\n' > "$run_step8/$f"
done
out="$("$VERIFY" "$run_step8" 2>&1 || true)"
assert_contains "step8 partial with step9a1 skipped emits OK" "$out" "OK"

# Test 9: pr_number-only later-phase signal should trigger Step-8/9a.1 requirements
run_pr_number="$TMP/run-pr-number"
mkdir -p "$run_pr_number"
cat > "$run_pr_number/manifest.json" <<'EOF'
{
  "updated_at": "2026-05-20T12:00:00Z",
  "pr_number": "123",
  "status": "in-progress"
}
EOF
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson; do
    printf 'placeholder\n' > "$run_pr_number/$f"
done
out="$("$VERIFY" "$run_pr_number" 2>&1 || true)"
assert_contains "pr-number-only emits MISSING" "$out" "MISSING="
assert_contains "pr-number-only requires version bump reasoning" "$out" "version-bump-reasoning.md"
assert_contains "pr-number-only requires final summary" "$out" "final-summary.md"
assert_contains "pr-number-only requires run statistics" "$out" "run-statistics.md"
assert_contains "pr-number-only requires session transcript" "$out" "session-transcript.jsonl"

# Test 10: pretty-printed status=done should trigger Step-9a.1 requirements
run_done_status="$TMP/run-done-status"
mkdir -p "$run_done_status"
cat > "$run_done_status/manifest.json" <<'EOF'
{
  "meta": {
    "note": "status is intentionally not the first key"
  },
  "status": "done"
}
EOF
for f in plan-goals-test.md plan-review-tally.json; do
    printf 'placeholder\n' > "$run_done_status/$f"
done
out="$("$VERIFY" "$run_done_status" 2>&1 || true)"
assert_contains "done-status emits MISSING" "$out" "MISSING="
assert_contains "done-status requires run statistics" "$out" "run-statistics.md"

# Test 11: exn-agg-validate-fail + glob — signal present but no matching stderr file → MISSING glob token
run_exn_val="$TMP/run-exn-validate-missing"
mkdir -p "$run_exn_val"
for f in manifest.json plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json session-transcript.jsonl; do
    printf 'placeholder\n' > "$run_exn_val/$f"
done
printf '%s\n' '{"body":"merged output failed validation"}' > "$run_exn_val/execution-issues.ndjson"
out="$("$VERIFY" "$run_exn_val" 2>&1 || true)"
assert_contains "exn-agg validate signal without stderr → MISSING glob" "$out" "MISSING="
assert_contains "exn-agg validate MISSING names aggregator-validate glob" "$out" "round-*/aggregator-validate.stderr"

# Test 12: exn-agg-dispatch-fail + glob — dispatch signal but no stderr file
run_exn_disp="$TMP/run-exn-dispatch-missing"
mkdir -p "$run_exn_disp"
for f in manifest.json plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json session-transcript.jsonl; do
    printf 'placeholder\n' > "$run_exn_disp/$f"
done
printf '%s\n' '{"body":"DISPATCH_OK=false"}' > "$run_exn_disp/execution-issues.ndjson"
out="$("$VERIFY" "$run_exn_disp" 2>&1 || true)"
assert_contains "exn-agg dispatch signal without stderr → MISSING glob" "$out" "MISSING="
assert_contains "exn-agg dispatch MISSING names aggregator-dispatch glob" "$out" "round-*/aggregator-dispatch.stderr"

# Test 13: exn-agg-validate-fail satisfied when round stderr exists → OK
run_exn_ok="$TMP/run-exn-validate-ok"
mkdir -p "$run_exn_ok/round-1"
for f in manifest.json plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json session-transcript.jsonl; do
    printf 'placeholder\n' > "$run_exn_ok/$f"
done
printf '%s\n' '{"body":"merged output failed validation"}' > "$run_exn_ok/execution-issues.ndjson"
printf 'stub\n' > "$run_exn_ok/round-1/aggregator-validate.stderr"
out="$("$VERIFY" "$run_exn_ok" 2>&1 || true)"
assert_contains "exn-agg validate with stderr present emits OK" "$out" "OK"

# Test 14: manifest relative_path with invalid characters → error (LARCH_VERIFY_MANIFEST)
bad_manifest="$TMP/bad-chars-manifest.tsv"
{
    printf '%s\t%s\t%s\t%s\n' relative_path condition batch_slug extension
    printf '%s\t%s\t%s\t%s\n' 'bad path.txt' always direct-file md
} > "$bad_manifest"
run_bad_chars="$TMP/run-bad-chars"
mkdir -p "$run_bad_chars"
if out="$(LARCH_VERIFY_MANIFEST="$bad_manifest" "$VERIFY" "$run_bad_chars" 2>&1)"; then
    fail "invalid chars in manifest relative_path: expected non-zero verifier exit"
else
    assert_contains "invalid chars in manifest relative_path" "$out" "invalid characters"
fi

# Test 15: oos-issues.ndjson alone satisfies step9a1 while run-statistics.md is missing → still MISSING run-statistics
run_oos_step9a1="$TMP/run-oos-step9a1-missing-run-stats"
mkdir -p "$run_oos_step9a1"
cat > "$run_oos_step9a1/manifest.json" <<'EOF'
{}
EOF
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md final-summary.md; do
    printf 'placeholder\n' > "$run_oos_step9a1/$f"
done
printf 'placeholder\n' > "$run_oos_step9a1/oos-issues.ndjson"
out="$("$VERIFY" "$run_oos_step9a1" 2>&1 || true)"
assert_contains "oos-only step9a1 emits MISSING" "$out" "MISSING="
assert_contains "oos-only step9a1 requires run statistics" "$out" "run-statistics.md"

# Test 16: v2-style tree — final-summary without pr_number/status still requires Step-9a.1 batches
run_v2_final="$TMP/run-v2-final"
mkdir -p "$run_v2_final"
cat > "$run_v2_final/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{}}
EOF
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md final-summary.md; do
    printf 'placeholder\n' > "$run_v2_final/$f"
done
out="$("$VERIFY" "$run_v2_final" 2>&1 || true)"
assert_contains "v2 final-summary requires step9a1" "$out" "MISSING="
assert_contains "v2 final-summary requires run-statistics" "$out" "run-statistics.md"

# Test 17: empty steps_ran + bailed final-summary heading → step9a1 batches not required
run_bail_sig="$TMP/run-bail-signal-step9a1"
mkdir -p "$run_bail_sig"
cat > "$run_bail_sig/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{}}
EOF
printf '%s\n' '## /implement run test-run — bailed' > "$run_bail_sig/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_bail_sig/$f"
done
if ! out="$("$VERIFY" "$run_bail_sig" 2>&1)"; then
    fail "bail-signal empty steps_ran: expected verifier exit 0"
else
    assert_equal "$out" "OK" "bail-signal empty steps_ran emits exactly OK"
    case "$out" in *MISSING=*) fail "bail-signal empty steps_ran: output must not contain MISSING=" ;; esac
fi

# Test 17b: manifest omits steps_ran key + bailed heading → same as jq // {}
run_bail_omit="$TMP/run-bail-signal-omit-steps-ran"
mkdir -p "$run_bail_omit"
cat > "$run_bail_omit/manifest.json" <<'EOF'
{"schema_version":2}
EOF
printf '%s\n' '## /implement run test-run — bailed' > "$run_bail_omit/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_bail_omit/$f"
done
if ! out="$("$VERIFY" "$run_bail_omit" 2>&1)"; then
    fail "omit steps_ran key + bailed: expected verifier exit 0"
else
    assert_equal "$out" "OK" "omit steps_ran key + bailed emits exactly OK"
    case "$out" in *MISSING=*) fail "omit steps_ran key + bailed: output must not contain MISSING=" ;; esac
fi

# Test 17c: bailed-needs-user-input suffix on heading → OK
run_bail_nui="$TMP/run-bail-needs-user-input-step9a1"
mkdir -p "$run_bail_nui"
cat > "$run_bail_nui/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{}}
EOF
printf '%s\n' '## /implement run test-run — bailed-needs-user-input' > "$run_bail_nui/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_bail_nui/$f"
done
if ! out="$("$VERIFY" "$run_bail_nui" 2>&1)"; then
    fail "bailed-needs-user-input heading: expected verifier exit 0"
else
    assert_equal "$out" "OK" "bailed-needs-user-input heading emits exactly OK"
    case "$out" in *MISSING=*) fail "bailed-needs-user-input: output must not contain MISSING=" ;; esac
fi

# Test 17d: nonempty steps_ran without step9a1 + bail + missing run-statistics (audit-scan-run parity)
run_nonempty_no_s9a1="$TMP/run-nonempty-steps-ran-no-step9a1-bail"
mkdir -p "$run_nonempty_no_s9a1"
cat > "$run_nonempty_no_s9a1/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{"step8":true}}
EOF
printf '%s\n' '## /implement run test-run — bailed' > "$run_nonempty_no_s9a1/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_nonempty_no_s9a1/$f"
done
if ! out="$("$VERIFY" "$run_nonempty_no_s9a1" 2>&1)"; then
    fail "nonempty steps_ran without step9a1 + bail: expected verifier exit 0"
else
    assert_equal "$out" "OK" "nonempty steps_ran without step9a1 + bail emits exactly OK"
    case "$out" in *MISSING=*) fail "nonempty steps_ran without step9a1 + bail: output must not contain MISSING=" ;; esac
fi

# Test 18: empty steps_ran + completed-like heading → still require run-statistics
run_completed_sig="$TMP/run-completed-signal-step9a1"
mkdir -p "$run_completed_sig"
cat > "$run_completed_sig/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{}}
EOF
printf '%s\n' '## /implement run test-run — completed' > "$run_completed_sig/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_completed_sig/$f"
done
out="$("$VERIFY" "$run_completed_sig" 2>&1 || true)"
assert_contains "completed-signal still MISSING" "$out" "MISSING="
assert_contains "completed-signal requires run-statistics" "$out" "run-statistics.md"

# Test 18b: manifest omits steps_ran key + completed-like heading → same as Test 18
run_completed_omit="$TMP/run-completed-signal-omit-steps-ran"
mkdir -p "$run_completed_omit"
cat > "$run_completed_omit/manifest.json" <<'EOF'
{"schema_version":2}
EOF
printf '%s\n' '## /implement run test-run — completed' > "$run_completed_omit/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_completed_omit/$f"
done
out="$("$VERIFY" "$run_completed_omit" 2>&1 || true)"
assert_contains "completed-signal omit steps_ran still MISSING" "$out" "MISSING="
assert_contains "completed-signal omit steps_ran requires run-statistics" "$out" "run-statistics.md"

# Test 19: explicit step9a1=false + non-bail summary still OK (manifest-side fix)
run_explicit_bail="$TMP/run-explicit-step9a1-false"
mkdir -p "$run_explicit_bail"
cat > "$run_explicit_bail/manifest.json" <<'EOF'
{"schema_version":2,"steps_ran":{"step9a1":false}}
EOF
printf '%s\n' '## /implement run test-run — completed' > "$run_explicit_bail/final-summary.md"
for f in plan-goals-test.md plan-review-tally.json code-review-tally.json review-findings-full.jsonl token-report.json timing-report.json execution-issues.ndjson session-transcript.jsonl version-bump-reasoning.md; do
    printf 'placeholder\n' > "$run_explicit_bail/$f"
done
if ! out="$("$VERIFY" "$run_explicit_bail" 2>&1)"; then
    fail "explicit step9a1 false with completed heading: expected verifier exit 0"
else
    assert_equal "$out" "OK" "explicit step9a1 false with completed heading emits exactly OK"
    case "$out" in *MISSING=*) fail "explicit step9a1 false: output must not contain MISSING=" ;; esac
fi

# Test 20: corrupt manifest.json + bailed final-summary — step9a1 must not be skipped (mirror audit Test 52e)
run_corrupt_bail="$TMP/run-corrupt-manifest-bail-step9a1"
mkdir -p "$run_corrupt_bail"
req_corrupt_bail="$TMP/req-corrupt-manifest-bail.tsv"
{
    printf '%s\t%s\t%s\t%s\n' relative_path condition batch_slug extension
    printf '%s\n' 'oos-issues.ndjson	step9a1	x	x'
    printf '%s\n' 'run-statistics.md	step9a1	x	x'
} > "$req_corrupt_bail"
printf '%s\n' '{not valid json' > "$run_corrupt_bail/manifest.json"
printf '%s\n' '## /implement run test-run — bailed' > "$run_corrupt_bail/final-summary.md"
if out="$(LARCH_VERIFY_MANIFEST="$req_corrupt_bail" "$VERIFY" "$run_corrupt_bail" 2>&1)"; then
    fail "corrupt manifest + bail: expected non-zero verifier exit"
else
    assert_contains "corrupt manifest + bail emits MISSING" "$out" "MISSING="
    assert_contains "corrupt manifest + bail requires run-statistics" "$out" "run-statistics.md"
    assert_contains "corrupt manifest + bail requires oos-issues" "$out" "oos-issues.ndjson"
fi

echo
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$FAIL" -ne 0 ]; then exit 1; fi
echo "All assertions passed."
