#!/usr/bin/env bash
# test-run-step3-review.sh - Regression harness for run-step3-review.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
LAUNCHER="$SCRIPT_DIR/run-step3-review.sh"

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-run-step3-review.XXXXXX")"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

pass() {
    printf '  ok: %s\n' "$1"
    PASS=$((PASS + 1))
}

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    FAIL=$((FAIL + 1))
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$label"
    else
        fail "$label (missing $needle; got ${haystack:0:300})"
    fi
}

assert_file_equals() {
    local file="$1" expected="$2" label="$3"
    local actual
    actual="$(cat "$file")"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_file_has_keys() {
    local file="$1" label="$2"
    shift 2
    local key
    for key in "$@"; do
        if grep -Fq "${key}=" "$file"; then
            pass "$label has $key"
        else
            fail "$label missing $key"
        fi
    done
}

assert_not_contains() {
    local haystack="$1" needle="$2" label="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        fail "$label (unexpected $needle; got ${haystack:0:300})"
    else
        pass "$label"
    fi
}

write_common_inputs() {
    local dir="$1" classification="$2"
    mkdir -p "$dir"
    cat >"$dir/run-params.json" <<EOF
{"schema_version":2,"design_classification":"$classification","workflow_path":"$classification","partition_requested":false,"brainstorm_requested":false}
EOF
    printf '# Plan\n\ndiff_lines: 1\n' >"$dir/plan.txt"
    printf 'feature\n' >"$dir/feature-description.txt"
}

write_loop_stub() {
    local dir="$1" body="$2"
    local stub="$dir/plan-review-loop-stub.sh"
    mkdir -p "$dir"
    cat >"$stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
$body
EOF
    chmod +x "$stub"
    printf '%s\n' "$stub"
}

launcher_env=(env -u LARCH_QUIET_LOG_FILE -u IMPLEMENT_TMPDIR -u SESSION_ENV_PATH -u REVIEW_TMPDIR -u LARCH_TIMING_LEDGER LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$REPO_ROOT")

for case_dir in \
    default-mode loop-validation preview preview-nonheader preview-nonheader-exit1 \
    preview-exact-missing preview-missing-repair preview-two-call preview-bare-missing \
    no-preview cap cap-cleanup symlink-round bad-count persist tally loop-tally \
    degraded panel weird revision-failed-rc main-agent-rc stale file-precedence \
    invalid-cap-real integration-seam breadcrumb-rounds scope-preference stale-implement \
    scope-ok scope-desync scope-stale-tally-error scope-bad scope-outside scope-empty \
    scope-recover symlink-inner symlink-outer symlink-outer-cap mark-skipped-entry \
    mark-no-duplicate; do
    mkdir -p "$TMP/$case_dir"
done

echo "=== missing --design-tmpdir ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'missing design-tmpdir exits 2'
else
    fail "missing design-tmpdir rc=$rc"
fi
assert_contains "$out" '--design-tmpdir is required' 'missing design-tmpdir error'

DARGV="$TMP/argv"

echo "=== unknown option ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --bogus 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'unknown option exits 2'
else
    fail "unknown option rc=$rc"
fi
assert_contains "$out" 'unknown option: --bogus' 'unknown option error'

echo "=== --mode single is rejected ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --mode single 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass '--mode single exits 2'
else
    fail "--mode single rc=$rc"
fi
assert_contains "$out" '--mode single is no longer accepted' '--mode single error message'

echo "=== mutually exclusive mode flags exit 2 ==="
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --preview-only --no-preview 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass '--preview-only --no-preview exits 2'
else
    fail "--preview-only --no-preview rc=$rc"
fi
assert_contains "$out" 'mutually exclusive' 'mutual exclusion error message'

echo "=== omitted mode flags default to --no-preview ==="
D_DEFAULT="$TMP/default-mode"
stub="$(write_loop_stub "$D_DEFAULT" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_DEFAULT")"
assert_contains "$out" 'LOOP_STATUS=complete' 'omitted mode defaults to no-preview review path'



echo "=== --mode loop validates starting-round phase evidence ==="
D_LOOP_VAL="$TMP/loop-validation"
printf '2\n' >"$D_LOOP_VAL/review-round-count.txt"
set +e
out=$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$D_LOOP_VAL" --mode loop --starting-round 1 2>&1)
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass '--mode loop starting-round without phase exits 2'
else
    fail "--mode loop starting-round without phase rc=$rc"
fi
assert_contains "$out" 'requires phase evidence' '--mode loop missing phase error'

printf 'awaiting-continuation\n' >"$D_LOOP_VAL/.step3-round-2.phase"
cont_stub="$(write_loop_stub "$D_LOOP_VAL" "printf 'PLAN_REVIEW_CONTINUE=false\nPLAN_REVIEW_CONTINUE_REASON=small-clean\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\n'")"
out=$("${launcher_env[@]}" RUN_STEP3_CONTINUATION_SH="$cont_stub" "$LAUNCHER" --design-tmpdir "$D_LOOP_VAL" --mode loop --starting-round 2)
assert_contains "$out" 'STEP3_REVIEW_LOOP_STATUS=complete' '--mode loop resumes with phase evidence'

echo "=== --mode loop rejects --round-num misuse ==="
set +e
out=$("${launcher_env[@]}" "$LAUNCHER" --design-tmpdir "$DARGV" --mode loop --round-num 1 2>&1)
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass '--mode loop --round-num exits 2'
else
    fail "--mode loop --round-num rc=$rc"
fi
assert_contains "$out" '--mode loop does not take --round-num' '--mode loop --round-num error'

echo "=== --preview-only renders plan and creates sentinel ==="
D_PV="$TMP/preview"
preview_stub="$D_PV/preview-stub.sh"
cat >"$preview_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '\n## Plan Candidate for Review\n\npreview body\n'
STUBEOF
chmod +x "$preview_stub"
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$preview_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only exits 0'
else
    fail "--preview-only rc=$rc"
fi
assert_contains "$out" '## Plan Candidate for Review' '--preview-only renders header'
if [[ -e "$D_PV/.step3-entry-plan-printed" ]]; then
    pass '--preview-only creates sentinel'
else
    fail '--preview-only should create .step3-entry-plan-printed sentinel'
fi

echo "=== --preview-only second call skips render (sentinel exists) ==="
set +e
out2="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$preview_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV" 2>&1)"
rc2=$?
set -e
if [[ "$rc2" -eq 0 ]]; then
    pass '--preview-only second call exits 0'
else
    fail "--preview-only second call rc=$rc2"
fi
if [[ -z "$(printf '%s' "$out2" | tr -d '[:space:]')" ]]; then
    pass '--preview-only second call emits nothing (sentinel suppresses)'
else
    fail "--preview-only second call should emit nothing; got: ${out2:0:100}"
fi

echo "=== --preview-only non-header renderer output does not create sentinel ==="
D_PV3="$TMP/preview-nonheader"
nonheader_stub="$D_PV3/nonheader-stub.sh"
cat >"$nonheader_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**\n'
exit 0
STUBEOF
chmod +x "$nonheader_stub"
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$nonheader_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV3" >/dev/null 2>&1 || true
if [[ ! -e "$D_PV3/.step3-entry-plan-printed" ]]; then
    pass '--preview-only non-header output does not create sentinel'
else
    fail '--preview-only should not create sentinel for non-header renderer output'
fi

echo "=== --preview-only renderer exit 1 non-header body does not create sentinel ==="
D_PV3B="$TMP/preview-nonheader-exit1"
nonheader_exit1_stub="$D_PV3B/nonheader-exit1-stub.sh"
cat >"$nonheader_exit1_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf 'partial output without header\n'
exit 1
STUBEOF
chmod +x "$nonheader_exit1_stub"
set +e
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$nonheader_exit1_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV3B" >/dev/null 2>&1
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only renderer exit 1 non-header does not abort preview path'
else
    fail "--preview-only renderer exit 1 non-header rc=$rc (should not abort)"
fi
if [[ ! -e "$D_PV3B/.step3-entry-plan-printed" ]]; then
    pass '--preview-only renderer exit 1 non-header does not create sentinel'
else
    fail '--preview-only should not create sentinel for exit 1 non-header renderer output'
fi

echo "=== --preview-only exact missing-plan warning does not create sentinel on allowlisted tmpdir ==="
D_PV5="$TMP/preview-exact-missing"
rm -f "$D_PV5/plan.txt"
exact_missing_stub="$D_PV5/exact-missing-stub.sh"
cat >"$exact_missing_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**\n'
exit 0
STUBEOF
chmod +x "$exact_missing_stub"
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$exact_missing_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV5" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only exact missing-plan warning exits 0'
else
    fail "--preview-only exact missing-plan warning rc=$rc"
fi
assert_contains "$out" '**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**' '--preview-only exact missing-plan warning emits warning'
if [[ ! -e "$D_PV5/.step3-entry-plan-printed" ]]; then
    pass '--preview-only exact missing-plan warning does not create sentinel'
else
    fail '--preview-only should not create sentinel for exact missing-plan warning on allowlisted tmpdir'
fi

echo "=== --preview-only missing plan then repair re-renders preview ==="
D_PV5B="$TMP/preview-missing-repair"
rm -f "$D_PV5B/plan.txt"
missing_repair_warning_stub="$D_PV5B/missing-repair-warning-stub.sh"
cat >"$missing_repair_warning_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**\n'
exit 0
STUBEOF
chmod +x "$missing_repair_warning_stub"
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$missing_repair_warning_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV5B" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only missing-plan first call exits 0'
else
    fail "--preview-only missing-plan first call rc=$rc"
fi
assert_contains "$out" '**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**' '--preview-only missing-plan first call emits warning'
if [[ ! -e "$D_PV5B/.step3-entry-plan-printed" ]]; then
    pass '--preview-only missing-plan first call leaves sentinel absent'
else
    fail '--preview-only missing-plan first call should not create sentinel'
fi
printf '# Plan\n\nrepaired\n' >"$D_PV5B/plan.txt"
missing_repair_header_stub="$D_PV5B/missing-repair-header-stub.sh"
cat >"$missing_repair_header_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '\n## Plan Candidate for Review\n\nrepaired preview\n'
exit 0
STUBEOF
chmod +x "$missing_repair_header_stub"
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$missing_repair_header_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV5B" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only repaired plan call exits 0'
else
    fail "--preview-only repaired plan call rc=$rc"
fi
assert_contains "$out" '## Plan Candidate for Review' '--preview-only repaired plan call re-renders header'
if [[ -e "$D_PV5B/.step3-entry-plan-printed" ]]; then
    pass '--preview-only repaired plan call creates sentinel'
else
    fail '--preview-only repaired plan call should create sentinel'
fi

echo "=== --preview-only stale sentinel on disallowed tmpdir still emits warnings ==="
D_PV6="$(mktemp -d /var/tmp/test-run-step3-review-disallowed.XXXXXX 2>/dev/null || mktemp -d "${REPO_ROOT}/test-run-step3-disallowed.XXXXXX")"
touch "$D_PV6/.step3-entry-plan-printed"
warn_stub="$D_PV6/warn-stub.sh"
cat >"$warn_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf '**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**\n'
exit 0
STUBEOF
chmod +x "$warn_stub"
set +e
out="$("${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$warn_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV6" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass '--preview-only stale sentinel on disallowed tmpdir exits 0'
else
    fail "--preview-only stale sentinel on disallowed tmpdir rc=$rc"
fi
assert_contains "$out" 'DESIGN_TMPDIR not under allowlist' 'stale sentinel on disallowed tmpdir still emits warning'
rm -rf "$D_PV6"

echo "=== --preview-only two-call non-header then header creates sentinel on second call ==="
D_PV7="$TMP/preview-two-call"
two_call_stub="$D_PV7/two-call-stub.sh"
cat >"$two_call_stub" <<'STUBEOF'
#!/usr/bin/env bash
if [[ "${STEP3_PREVIEW_CALL:-1}" == 1 ]]; then
    printf '**⚠ 3: DESIGN_TMPDIR not under allowlist; cannot present plan candidate**\n'
    exit 0
fi
printf '\n## Plan Candidate for Review\n\nsecond call body\n'
STUBEOF
chmod +x "$two_call_stub"
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 STEP3_PREVIEW_CALL=1 RUN_STEP3_EMIT_PREVIEW_SH="$two_call_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV7" >/dev/null 2>&1 || true
if [[ ! -e "$D_PV7/.step3-entry-plan-printed" ]]; then
    pass '--preview-only first call non-header does not create sentinel'
else
    fail '--preview-only first call non-header should not create sentinel'
fi
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 STEP3_PREVIEW_CALL=2 RUN_STEP3_EMIT_PREVIEW_SH="$two_call_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV7" >/dev/null 2>&1 || true
if [[ -e "$D_PV7/.step3-entry-plan-printed" ]]; then
    pass '--preview-only second call header creates sentinel'
else
    fail '--preview-only second call with header should create sentinel'
fi

echo "=== --preview-only missing/empty plan.txt sentinel not created without exact warning ==="
D_PV4="$TMP/preview-bare-missing"
mkdir -p "$D_PV4"
cat >"$D_PV4/session-env.sh" <<'SEOF'
LARCH_CLAUDE_PLUGIN_ROOT=PLACEHOLDER
SEOF
missing_stub="$D_PV4/missing-stub.sh"
cat >"$missing_stub" <<'STUBEOF'
#!/usr/bin/env bash
printf 'Some other warning without the exact string\n'
exit 0
STUBEOF
chmod +x "$missing_stub"
"${launcher_env[@]}" LARCH_QUIET_DISABLE=1 RUN_STEP3_EMIT_PREVIEW_SH="$missing_stub" \
    "$LAUNCHER" --preview-only --design-tmpdir "$D_PV4" >/dev/null 2>&1 || true
if [[ ! -e "$D_PV4/.step3-entry-plan-printed" ]]; then
    pass '--preview-only bare missing plan without exact warning: no sentinel'
else
    fail '--preview-only should not create sentinel without exact missing-plan warning'
fi

echo "=== --no-preview captured output has no plan preview ==="
D_NP="$TMP/no-preview"
stub="$(write_loop_stub "$D_NP" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --no-preview --design-tmpdir "$D_NP")"
if [[ "$out" == *'## Plan Candidate for Review'* ]]; then
    fail '--no-preview should not output plan preview'
else
    pass '--no-preview captured output has no plan preview'
fi
assert_contains "$out" 'LOOP_STATUS=complete' '--no-preview emits review KVs'

echo "=== cap-reached short-circuit ==="
D1="$TMP/cap"
printf '5\n' >"$D1/review-round-count.txt"
stub="$(write_loop_stub "$D1" 'exit 97')"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1")"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass 'cap-reached exit 0'
else
    fail "cap-reached rc=$rc"
fi
assert_contains "$out" 'LOOP_STATUS=cap-reached' 'cap-reached KV'
assert_contains "$out" 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' 'skipped-cap-reached KV'
grep -Fq 'LOOP_STATUS=cap-reached' "$D1/.step3-review-result.env" || fail 'result env cap-reached'
[[ "$(cat "$D1/review-round-count.txt")" == "5" ]] || fail 'cap-reached leaves counter unchanged'

echo "=== cap-reached preserves round forensics while clearing top-level stale artifacts ==="
D1B="$TMP/cap-cleanup"
printf '5\n' >"$D1B/review-round-count.txt"
mkdir -p "$D1B/plan-review/round-1" "$D1B/plan-review/round-2"
printf 'stale\n' >"$D1B/plan-review/round-1/stale.txt"
printf 'stale\n' >"$D1B/plan-review/round-2/stale.txt"
printf 'stale accepted\n' >"$D1B/accepted-plan-findings.md"
printf 'stale rejected\n' >"$D1B/rejected-findings.md"
printf 'stale oos\n' >"$D1B/oos.md"
printf 'cumulative oos\n' >"$D1B/oos-accepted-design.md"
printf 'stale tally\n' >"$D1B/voting-tally.md"
printf 'stale ballot\n' >"$D1B/ballot.txt"
stub="$(write_loop_stub "$D1B" 'exit 97')"
set +e
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1B" >/dev/null
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
    pass 'cap-reached cleanup exit 0'
else
    fail "cap-reached cleanup rc=$rc"
fi
[[ -e "$D1B/plan-review/round-1/stale.txt" ]] || fail 'cap-reached should preserve stale round-1 forensics'
[[ -e "$D1B/plan-review/round-2/stale.txt" ]] || fail 'cap-reached should preserve stale round-2 forensics'
[[ ! -e "$D1B/accepted-plan-findings.md" ]] || fail 'cap-reached should clear stale accepted findings'
[[ ! -e "$D1B/rejected-findings.md" ]] || fail 'cap-reached should clear stale rejected findings'
[[ ! -e "$D1B/oos.md" ]] || fail 'cap-reached should clear stale round OOS'
[[ ! -e "$D1B/voting-tally.md" ]] || fail 'cap-reached should clear stale voting tally'
[[ ! -e "$D1B/ballot.txt" ]] || fail 'cap-reached should clear stale ballot'
grep -Fq 'cumulative oos' "$D1B/oos-accepted-design.md" || fail 'cap-reached should preserve cumulative accepted OOS'

echo "=== symlinked plan-review round dir skipped during cleanup ==="
D1S="$TMP/symlink-round"
mkdir -p "$D1S/plan-review/round-keeper" "$D1S/plan-review/round-2"
printf 'keep-me\n' >"$D1S/plan-review/round-keeper/stale.txt"
printf 'inactive\n' >"$D1S/plan-review/round-2/stale.txt"
ln -s "$D1S/plan-review/round-keeper" "$D1S/plan-review/round-1"
stub="$(write_loop_stub "$D1S" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1S")"
assert_contains "$out" 'refusing to remove symlinked round artifact round-1' 'symlinked round cleanup warning'
[[ -f "$D1S/plan-review/round-keeper/stale.txt" ]] || fail 'symlinked round-1 target must survive cleanup'
[[ -L "$D1S/plan-review/round-1" ]] || fail 'symlinked round-1 link should remain'
[[ -f "$D1S/plan-review/round-2/stale.txt" ]] || fail 'inactive non-symlink round-2 should be preserved'

echo "=== non-numeric review-round-count treated as zero ==="
D1C="$TMP/bad-count"
printf 'abc\n' >"$D1C/review-round-count.txt"
stub="$(write_loop_stub "$D1C" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D1C")"
assert_contains "$out" 'review-round-count.txt non-numeric' 'non-numeric count warning'
if [[ "$(cat "$D1C/review-round-count.txt")" == "1" ]]; then
    pass 'non-numeric count treated as zero then round 1 persisted'
else
    fail 'non-numeric count should persist round 1'
fi

echo "=== pending round persisted before launch ==="
D2="$TMP/persist"
stub="$(write_loop_stub "$D2" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D2" >/dev/null
if [[ "$(cat "$D2/review-round-count.txt")" == "1" ]]; then
    pass 'pending round persisted'
else
    fail 'pending round not persisted'
fi

echo "=== tally-error rollback ==="
D3="$TMP/tally"
printf '2\n' >"$D3/review-round-count.txt"
stub="$(write_loop_stub "$D3" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 2")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D3" >/dev/null
if [[ "$(cat "$D3/review-round-count.txt")" == "2" ]]; then
    pass 'tally-error rollback'
else
    fail 'tally-error should rollback count'
fi

echo "=== loop-status tally-error rollback ==="
D3B="$TMP/loop-tally"
printf '2\n' >"$D3B/review-round-count.txt"
stub="$(write_loop_stub "$D3B" "printf 'LOOP_STATUS=tally-error\nACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=3\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D3B" >/dev/null
if [[ "$(cat "$D3B/review-round-count.txt")" == "2" ]]; then
    pass 'loop-status tally-error rollback'
else
    fail 'loop-status tally-error should rollback count'
fi

echo "=== degraded-empty-collector rollback ==="
D4="$TMP/degraded"
printf '1\n' >"$D4/review-round-count.txt"
stub="$(write_loop_stub "$D4" "printf 'LOOP_STATUS=degraded-empty-collector\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D4" >/dev/null
if [[ "$(cat "$D4/review-round-count.txt")" == "1" ]]; then
    pass 'degraded-empty-collector rollback'
else
    fail 'degraded rollback failed'
fi

echo "=== panel-failed keeps round ==="
D5="$TMP/panel"
printf '1\n' >"$D5/review-round-count.txt"
stub="$(write_loop_stub "$D5" "printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=2\nTALLY_PLAN_REVIEW_STATUS=panel-failed\nAGGREGATOR_STATUS=skipped\nVOTING_TALLY_FILE=\n'; exit 1")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D5" >/dev/null
if [[ "$(cat "$D5/review-round-count.txt")" == "2" ]]; then
    pass 'panel-failed keeps round'
else
    fail 'panel-failed should keep pending round'
fi

echo "=== unknown LOOP_STATUS normalizes to panel-failed ==="
D6="$TMP/weird"
stub="$(write_loop_stub "$D6" "printf 'LOOP_STATUS=weird-status\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6")"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'unknown status normalized'

echo "=== removed loop-only LOOP_STATUS normalizes on non-zero rc ==="
D6B="$TMP/revision-failed-rc"
stub="$(write_loop_stub "$D6B" "printf 'LOOP_STATUS=revision-failed\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6B")"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'removed revision-failed normalizes on rc 1'
assert_contains "$out" 'missing or invalid LOOP_STATUS' 'removed revision-failed emits invalid-status warning'

echo "=== main-agent-vote-required preserved on non-zero rc ==="
D6C="$TMP/main-agent-rc"
printf 'scope anchor\n' >"$D6C/plan-review-scope-anchor.txt"
stub="$(write_loop_stub "$D6C" "printf 'LOOP_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=$D6C/plan-review-scope-anchor.txt\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D6C")"
assert_contains "$out" 'LOOP_STATUS=main-agent-vote-required' 'main-agent-vote-required preserved on rc 1'
grep -Fq 'LOOP_STATUS=main-agent-vote-required' "$D6C/.step3-review-result.env" || fail 'result env main-agent-vote-required'

echo "=== stale inner result env ignored after launcher failure ==="
D7="$TMP/stale"
cat >"$D7/.step3-plan-review-result.env" <<'EOF'
LOOP_STATUS=complete
ACCEPTED_COUNT=9
TALLY_PLAN_REVIEW_STATUS=ok
EOF
stub="$(write_loop_stub "$D7" 'exit 2')"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D7")"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'stale inner env ignored'
if grep -Fq 'ACCEPTED_COUNT=9' "$D7/.step3-review-result.env"; then
    fail 'stale accepted count leaked into normalized result env'
else
    pass 'stale accepted count did not leak'
fi

echo "=== inner result env takes precedence over stdout ==="
D8="$TMP/file-precedence"
stub="$(write_loop_stub "$D8" "cat >\"\$DESIGN_TMPDIR/.step3-plan-review-result.env\" <<'EOF'
LOOP_STATUS=complete
ACCEPTED_COUNT=2
IMPORTANT_ACCEPTED_COUNT=1
DEGRADED_PANEL=0
ROUNDS_COMPLETED=1
TALLY_PLAN_REVIEW_STATUS=ok
AGGREGATOR_STATUS=file
VOTING_TALLY_FILE=file-tally.md
COLLECT_OK_COUNT=1
COLLECT_FAILURE_COUNT=0
EOF
printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=7\nAGGREGATOR_STATUS=stdout\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D8")"
assert_contains "$out" 'LOOP_STATUS=complete' 'inner file loop status wins'
grep -Fq 'AGGREGATOR_STATUS=file' "$D8/.step3-review-result.env" || fail 'inner file aggregator should win over stdout'

echo "=== removed round-cap flag is rejected as unknown ==="
D11="$TMP/invalid-cap-real"
round_cap_flag='--round-'"cap"
set +e
out="$("${launcher_env[@]}" "$LAUNCHER" \
    --design-tmpdir "$D11" "$round_cap_flag" 0 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then
    pass 'removed round-cap exits 2'
else
    fail "removed round-cap rc=$rc"
fi
assert_contains "$out" "unknown option: $round_cap_flag" 'removed round-cap unknown option'

echo "=== driver argv matches plan-review-loop contract ==="
# Edit-in-sync: seam stub argv whitelist must match plan-review-loop.sh case parser
# and every flag run-step3-review.sh forwards; scripts/test-design-structure.sh pins drift.
D_SEAM="$TMP/integration-seam"
seam_stub="$D_SEAM/plan-review-loop-seam.sh"
cat >"$seam_stub" <<'STUBEOF'
#!/usr/bin/env bash
set -euo pipefail
while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir|--plan-file|--feature-file|--codex-present|--cursor-present|--round-num|--prune-round-num|--timeout)
            shift 2
            ;;
        *)
            printf 'plan-review-loop.sh: unknown option: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done
printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'
exit 0
STUBEOF
chmod +x "$seam_stub"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$seam_stub" "$LAUNCHER" \
    --design-tmpdir "$D_SEAM")"
assert_contains "$out" 'LOOP_STATUS=complete' 'integration seam settled LOOP_STATUS'
grep -Fq 'LOOP_STATUS=complete' "$D_SEAM/.step3-review-result.env" || fail 'integration seam result env complete'

echo "=== terminal stdout breadcrumbs include round identifiers ==="
D11B="$TMP/breadcrumb-rounds"
stub="$(write_loop_stub "$D11B" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D11B")"
assert_contains "$out" 'STEP3_REVIEW_ROUND_NUM=1' 'stdout STEP3_REVIEW_ROUND_NUM breadcrumb'
assert_contains "$out" 'ROUND_NUM=1' 'stdout ROUND_NUM breadcrumb'

echo "=== scope anchor handoff prefers DESIGN_TMPDIR over stale IMPLEMENT_TMPDIR ==="
D_SCOPE="$TMP/scope-preference"
D_STALE="$TMP/stale-implement"
mkdir -p "$D_STALE"
printf 'scope anchor\n' >"$D_SCOPE/plan-review-scope-anchor.txt"
printf 'stale scope\n' >"$D_STALE/plan-review-scope-anchor.txt"
stub="$(write_loop_stub "$D_SCOPE" "printf 'LOOP_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=$D_SCOPE/plan-review-scope-anchor.txt\n'; exit 0")"
out="$("${launcher_env[@]}" IMPLEMENT_TMPDIR="$D_STALE" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE")"
assert_contains "$out" "SCOPE_ANCHOR_FILE=$D_SCOPE/plan-review-scope-anchor.txt" 'scope anchor uses DESIGN_TMPDIR path'
grep -Fq "SCOPE_ANCHOR_FILE=$D_SCOPE/plan-review-scope-anchor.txt" "$D_SCOPE/.step3-review-result.env" || fail 'scope anchor persisted on main-agent-vote-required'

D_SCOPE_OK="$TMP/scope-ok"
printf 'scope anchor\n' >"$D_SCOPE_OK/plan-review-scope-anchor.txt"
stub="$(write_loop_stub "$D_SCOPE_OK" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=$D_SCOPE_OK/plan-review-scope-anchor.txt\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_OK")"
assert_contains "$out" "SCOPE_ANCHOR_FILE=$D_SCOPE_OK/plan-review-scope-anchor.txt" 'scope anchor persists on ok complete stdout'
grep -Fq "SCOPE_ANCHOR_FILE=$D_SCOPE_OK/plan-review-scope-anchor.txt" "$D_SCOPE_OK/.step3-review-result.env" || fail 'scope anchor persisted on ok complete result env'

echo "=== scope anchor relay requires compatible loop terminal ==="
D_SCOPE_DESYNC="$TMP/scope-desync"
printf 'scope anchor\n' >"$D_SCOPE_DESYNC/plan-review-scope-anchor.txt"
stub="$(write_loop_stub "$D_SCOPE_DESYNC" "printf 'LOOP_STATUS=panel-failed\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=$D_SCOPE_DESYNC/plan-review-scope-anchor.txt\n'; exit 1")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_DESYNC")"
assert_not_contains "$out" 'SCOPE_ANCHOR_FILE=' 'panel-failed desync omits scope anchor from stdout'
grep -Fq 'SCOPE_ANCHOR_FILE=' "$D_SCOPE_DESYNC/.step3-review-result.env" && fail 'panel-failed desync should omit scope anchor from result env'

echo "=== stale exported scope anchor omitted on tally-error ==="
D_SCOPE_STALE="$TMP/scope-stale-tally-error"
printf 'scope anchor\n' >"$D_SCOPE_STALE/plan-review-scope-anchor.txt"
stub="$(write_loop_stub "$D_SCOPE_STALE" "printf 'LOOP_STATUS=tally-error\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=tally-error\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 1")"
out="$("${launcher_env[@]}" SCOPE_ANCHOR_FILE="$D_SCOPE_STALE/plan-review-scope-anchor.txt" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_STALE")"
assert_not_contains "$out" 'SCOPE_ANCHOR_FILE=' 'tally-error stale seed omits scope anchor from stdout'
grep -Fq 'SCOPE_ANCHOR_FILE=' "$D_SCOPE_STALE/.step3-review-result.env" && fail 'tally-error stale seed should omit scope anchor from result env'

echo "=== invalid scope anchor handoff clears CR/LF and outside paths ==="
D_SCOPE_BAD="$TMP/scope-bad"
stub="$(write_loop_stub "$D_SCOPE_BAD" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=bad\rpath\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_BAD")"
assert_not_contains "$out" 'SCOPE_ANCHOR_FILE=' 'CR/LF scope anchor is omitted from stdout'
grep -Fq 'SCOPE_ANCHOR_FILE=' "$D_SCOPE_BAD/.step3-review-result.env" && fail 'CR/LF scope anchor should be omitted from result env'
D_SCOPE_OUT="$TMP/scope-outside"
outside_anchor="$TMP/outside-anchor.txt"
printf 'outside\n' >"$outside_anchor"
stub="$(write_loop_stub "$D_SCOPE_OUT" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=$outside_anchor\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_OUT")"
assert_not_contains "$out" 'SCOPE_ANCHOR_FILE=' 'outside scope anchor is omitted from stdout'
grep -Fq 'SCOPE_ANCHOR_FILE=' "$D_SCOPE_OUT/.step3-review-result.env" && fail 'outside scope anchor should be omitted from result env'

echo "=== zero-byte staged scope anchor recovery degrades to panel-failed ==="
D_SCOPE_EMPTY="$TMP/scope-empty"
: >"$D_SCOPE_EMPTY/plan-review-scope-anchor.txt"
stub="$(write_loop_stub "$D_SCOPE_EMPTY" "printf 'LOOP_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_EMPTY")"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'zero-byte staged anchor downgrades to panel-failed'
grep -Fq 'SCOPE_ANCHOR_FILE=' "$D_SCOPE_EMPTY/.step3-review-result.env" && fail 'zero-byte staged anchor must omit scope anchor'

echo "=== main-agent scope anchor recovery degrades durably when unrecoverable ==="
D_SCOPE_REC="$TMP/scope-recover"
stub="$(write_loop_stub "$D_SCOPE_REC" "printf 'LOOP_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\nSCOPE_ANCHOR_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D_SCOPE_REC")"
assert_contains "$out" 'LOOP_STATUS=panel-failed' 'missing main-agent anchor downgrades to panel-failed'
grep -Fq 'LOOP_STATUS=panel-failed' "$D_SCOPE_REC/.step3-review-result.env" || fail 'panel-failed recovery persisted'
grep -Fq 'SCOPE_ANCHOR_FILE=' "$D_SCOPE_REC/.step3-review-result.env" && fail 'panel-failed recovery must omit scope anchor'

echo "=== symlinked inner result env falls back to stdout ==="
D9="$TMP/symlink-inner"
ln -s "$D9/elsewhere.env" "$D9/.step3-plan-review-result.env"
stub="$(write_loop_stub "$D9" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=1\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=stdout\nVOTING_TALLY_FILE=\n'; exit 0")"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D9")"
assert_contains "$out" 'LOOP_STATUS=complete' 'symlink inner stdout fallback loop status'
grep -Fq 'AGGREGATOR_STATUS=stdout' "$D9/.step3-review-result.env" || fail 'symlink inner should use stdout fallback'

echo "=== symlinked outer result env refuses write with WARN ==="
D12="$TMP/symlink-outer"
ln -sf "$D12/outer-target.env" "$D12/.step3-review-result.env"
stub="$(write_loop_stub "$D12" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub" "$LAUNCHER" \
    --design-tmpdir "$D12" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 1 ]]; then
    pass 'symlinked outer result env exit 1'
else
    fail "symlinked outer result env rc=$rc"
fi
assert_contains "$out" 'refusing to write symlinked result env' 'symlinked outer write refusal WARN'
assert_contains "$out" 'LOOP_STATUS=complete' 'symlinked outer still emits LOOP_STATUS on stdout'
[[ -L "$D12/.step3-review-result.env" ]] || fail 'symlinked outer result env must remain a symlink'
[[ ! -f "$D12/outer-target.env" ]] || fail 'symlinked outer must not mutate write target'

echo "=== cap-reached with symlinked outer result env still emits cap-reached ==="
D12B="$TMP/symlink-outer-cap"
printf '5\n' >"$D12B/review-round-count.txt"
ln -sf "$D12B/outer-cap-target.env" "$D12B/.step3-review-result.env"
loop_stub="$(write_loop_stub "$D12B" 'exit 97')"
set +e
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$loop_stub" "$LAUNCHER" \
    --design-tmpdir "$D12B" 2>&1)"
rc=$?
set -e
if [[ "$rc" -eq 1 ]]; then
    pass 'cap-reached symlinked outer exit 1'
else
    fail "cap-reached symlinked outer rc=$rc"
fi
assert_contains "$out" 'LOOP_STATUS=cap-reached' 'cap-reached symlinked outer stdout LOOP_STATUS'
assert_contains "$out" 'TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached' 'cap-reached symlinked outer stdout tally'
[[ -L "$D12B/.step3-review-result.env" ]] || fail 'cap-reached symlinked outer must remain a symlink'

echo "=== REASON relay from plan-review-loop stub ==="
D_REASON="$TMP/reason-relay"
write_common_inputs "$D_REASON" sketch
# shellcheck disable=SC2016 # Stub body expands DESIGN_TMPDIR when the generated stub runs.
stub_reason="$(write_loop_stub "$D_REASON" 'cat >"$DESIGN_TMPDIR/.step3-plan-review-result.env" <<EOF
LOOP_STATUS=zero-findings-degraded-panel
ACCEPTED_COUNT=0
IMPORTANT_ACCEPTED_COUNT=0
DEGRADED_PANEL=1
ROUNDS_COMPLETED=1
REASON=ballot-items-lost
INSCOPE_REMAINING=30
TALLY_PLAN_REVIEW_STATUS=ok
AGGREGATOR_STATUS=ok
VOTING_TALLY_FILE=
COLLECT_OK_COUNT=1
COLLECT_FAILURE_COUNT=0
EOF
printf "LOOP_STATUS=zero-findings-degraded-panel\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=1\nROUNDS_COMPLETED=1\nREASON=ballot-items-lost\nINSCOPE_REMAINING=30\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n"
exit 0')"
out="$("${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub_reason" "$LAUNCHER" --design-tmpdir "$D_REASON")"
assert_contains "$out" 'REASON=ballot-items-lost' 'stdout relays REASON'
grep -q '^REASON=ballot-items-lost$' "$D_REASON/.step3-review-result.env" || fail 'result env missing REASON=ballot-items-lost'
grep -q '^INSCOPE_REMAINING=30$' "$D_REASON/.step3-review-result.env" || fail 'result env missing INSCOPE_REMAINING=30'

echo "=== normalized result env keys ==="
assert_file_has_keys "$D6/.step3-review-result.env" 'result env' \
    LOOP_STATUS TALLY_PLAN_REVIEW_STATUS STEP3_REVIEW_CAP_REACHED STEP3_REVIEW_ROUND_NUM ROUND_NUM \
    ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED REASON INSCOPE_REMAINING AGGREGATOR_STATUS \
    VOTING_TALLY_FILE REVIEW_ROUND_COUNT

echo "=== skipped-entry: launcher writes missing design Step 3 mark ==="
D_MARK_SKIPPED="$TMP/mark-skipped-entry"
# Seed ledger with Step 2 mark only (simulates skipped design-step3-entry.sh)
printf 'v1\tmark\t100\tdesign\tdesign Step 2b — plan\t-\t-\t-\t-\t-\t-\t-\t-\n' \
    >"$D_MARK_SKIPPED/timing-ledger.tsv"
stub_mark_skip="$(write_loop_stub "$D_MARK_SKIPPED" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub_mark_skip" "$LAUNCHER" \
    --design-tmpdir "$D_MARK_SKIPPED" >/dev/null
mark_count="$(awk -F '\t' '$2 == "mark" && $4 == "design" && $5 == "design Step 3 — plan review" { n++ } END { print n+0 }' "$D_MARK_SKIPPED/timing-ledger.tsv")"
if [[ "$mark_count" -eq 1 ]]; then
    pass "skipped-entry: launcher writes design Step 3 mark"
else
    fail "skipped-entry: expected 1 design Step 3 mark, got $mark_count"
fi

echo "=== no-duplicate: prior design Step 3 mark present, launcher skips re-mark ==="
D_MARK_NODUP="$TMP/mark-no-duplicate"
# Seed ledger with existing design Step 3 mark (simulates normal design-step3-entry.sh path)
printf 'v1\tmark\t100\tdesign\tdesign Step 3 — plan review\t-\t-\t-\t-\t-\t-\t-\t-\n' \
    >"$D_MARK_NODUP/timing-ledger.tsv"
stub_mark_nodup="$(write_loop_stub "$D_MARK_NODUP" "printf 'LOOP_STATUS=complete\nACCEPTED_COUNT=0\nIMPORTANT_ACCEPTED_COUNT=0\nDEGRADED_PANEL=0\nROUNDS_COMPLETED=1\nTALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nVOTING_TALLY_FILE=\n'; exit 0")"
"${launcher_env[@]}" RUN_STEP3_PLAN_REVIEW_LOOP_SH="$stub_mark_nodup" "$LAUNCHER" \
    --design-tmpdir "$D_MARK_NODUP" >/dev/null
mark_count="$(awk -F '\t' '$2 == "mark" && $4 == "design" && $5 == "design Step 3 — plan review" { n++ } END { print n+0 }' "$D_MARK_NODUP/timing-ledger.tsv")"
if [[ "$mark_count" -eq 1 ]]; then
    pass "no-duplicate: prior design Step 3 mark not duplicated"
else
    fail "no-duplicate: expected 1 design Step 3 mark, got $mark_count"
fi

TOTAL=$((PASS + FAIL))
if [[ "$FAIL" -eq 0 ]]; then
    printf 'PASS: test-run-step3-review.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-run-step3-review.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
