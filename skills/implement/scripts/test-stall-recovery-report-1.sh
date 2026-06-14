#!/usr/bin/env bash
# test-stall-recovery-report-1.sh — offline harness for stall-recovery-report.sh (part 1 of 3)

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SCRIPT="$SCRIPT_DIR/stall-recovery-report.sh"
CONTRACT_MD="$SCRIPT_DIR/stall-recovery-report.md"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-stall-recovery-test.XXXXXX")
trap 'rm -rf "$SANDBOX"' EXIT

pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$*" | sed 's/^/    /'; }

GHP_TOKEN_CASE13='ghp_''123456789012345678901234567890123456'
GHP_TOKEN_CASE16='ghp_''abcdef123456789012345678901234567890'

assert_eq() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then pass "$label"; else fail "$label" "expected=$expected actual=$actual"; fi
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if grep -qF -- "$needle" <<<"$haystack"; then pass "$label"; else fail "$label" "missing: $needle" "$haystack"; fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if grep -qF -- "$needle" <<<"$haystack"; then fail "$label" "unexpected: $needle" "$haystack"; else pass "$label"; fi
}

kv() {
    local key=$1 file=$2
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file"
}

read_session_key() {
    python3 "$REPO_ROOT/python/cli.py" session read-key "$@"
}

run_capture() {
    local out=$1
    shift
    set +e
    "$@" >"$out" 2>"$out.err"
    RC=$?
    set -e
}

make_tmp() {
    local name=$1
    mkdir -p "$SANDBOX/$name"
    printf '%s\n' "$SANDBOX/$name"
}

write_state() {
    local dir=$1 step=$2 phase=$3 bail=${4:-} extra=${5:-}
    cat >"$dir/ship-pr-state.sh" <<EOF
PHASE=$phase
STALL_TRACKING=true
STALL_STEP=$step
BAIL_REASON=$bail
EXIT_CODE=4
$extra
EOF
}

classify_fixture() {
    local name=$1 step=$2 phase=$3 log_text=$4 out dir log
    out="$SANDBOX/$name.out"
    dir=$(make_tmp "$name")
    write_state "$dir" "$step" "$phase"
    log="$dir/failure.log"
    printf '%s\n' "$log_text" >"$log"
    run_capture "$out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$log"
    CLASSIFY_OUT="$out"
}

classify_fixture case1 8 ci-initial "gh: API rate limit exceeded"
out=$CLASSIFY_OUT
assert_eq 0 "$RC" "1: transient classify exits 0"
assert_eq transient-infra "$(kv FAILURE_CLASS "$out")" "1: transient-infra"
assert_eq step8-shippr "$(kv RESUME_HINT "$out")" "1: transient resume hint"

classify_fixture case2 2 implementation "pytest reports a failing test"
out=$CLASSIFY_OUT
assert_eq test-failure "$(kv FAILURE_CLASS "$out")" "2: test-failure"
assert_eq step2-impl "$(kv RESUME_HINT "$out")" "2: test-failure resume hint"
classify_fixture case2b 2 implementation "Jest suite failed with 3 failing tests"
out=$CLASSIFY_OUT
assert_eq test-failure "$(kv FAILURE_CLASS "$out")" "2: jest-only test-failure"
assert_eq step2-impl "$(kv RESUME_HINT "$out")" "2: jest-only resume hint"

classify_fixture case3 5 review "lint-fix-loop exhausted after shellcheck failure"
out=$CLASSIFY_OUT
assert_eq lint-failure "$(kv FAILURE_CLASS "$out")" "3: lint-failure"
assert_eq step5-review "$(kv RESUME_HINT "$out")" "3: lint-failure resume hint"

classify_fixture case4 2 implementation "orchestrator-envelope-invalid in step2 dispatch"
out=$CLASSIFY_OUT
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$out")" "4: dispatch-failure"
assert_eq step2-impl "$(kv RESUME_HINT "$out")" "4: dispatch-failure resume hint"

dir=$(make_tmp case5a)
write_state "$dir" 3 checks
run_capture "$SANDBOX/case5a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq contract-failure "$(kv FAILURE_CLASS "$SANDBOX/case5a.out")" "5: step3 contract"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case5a.out")" "5: step3 no resume"
dir=$(make_tmp case5b)
write_state "$dir" 6 checks
run_capture "$SANDBOX/case5b.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq contract-failure "$(kv FAILURE_CLASS "$SANDBOX/case5b.out")" "5: step6 contract"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case5b.out")" "5: step6 no resume"

dir=$(make_tmp case6a)
write_state "$dir" 0 ship adopted-issue-closed
run_capture "$SANDBOX/case6a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case6a.out")" "6: adopted issue closed unrecoverable"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case6a.out")" "6: adopted issue closed no resume"
assert_eq adopted-issue-closed "$(kv BAIL_REASON "$SANDBOX/case6a.out")" "6: adopted issue closed stays allowlisted"
dir=$(make_tmp case6b)
write_state "$dir" 0 ship tracking-init-failed
run_capture "$SANDBOX/case6b.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case6b.out")" "6: tracking init failed unrecoverable"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case6b.out")" "6: tracking init failed no resume"
assert_eq tracking-init-failed "$(kv BAIL_REASON "$SANDBOX/case6b.out")" "6: tracking init failed stays allowlisted"

dir=$(make_tmp case7)
write_state "$dir" 8 ci-initial "" "NOTE=network timeout"
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
run_capture "$dir/first.env" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env"
"$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class "$(kv FAILURE_CLASS "$dir/first.env")" --signature "$(kv FAILURE_SIGNATURE "$dir/first.env")" --resume-hint "$(kv RESUME_HINT "$dir/first.env")" --outcome failed >/dev/null
run_capture "$dir/second.env" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env"
assert_eq same-cause-repeat "$(kv FAILURE_CLASS "$dir/second.env")" "7: same-cause-repeat"
assert_eq none "$(kv RESUME_HINT "$dir/second.env")" "7: same-cause-repeat suppresses redispatch hint"
run_capture "$SANDBOX/case7-policy.out" "$SCRIPT" retry-policy --class same-cause-repeat
assert_eq same-cause-repeat "$(kv FAILURE_CLASS "$SANDBOX/case7-policy.out")" "7: retry-policy echoes class"
assert_eq 2 "$(kv MAX_ATTEMPTS "$SANDBOX/case7-policy.out")" "7: retry-policy same-cause cap"
assert_eq none "$(kv RETRY_DELAY "$SANDBOX/case7-policy.out")" "7: retry-policy same-cause delay"
run_capture "$SANDBOX/case7-policy-transient.out" "$SCRIPT" retry-policy --class transient-infra
assert_eq 4 "$(kv MAX_ATTEMPTS "$SANDBOX/case7-policy-transient.out")" "7: retry-policy transient cap"
assert_eq "sleep-seconds.sh 5" "$(kv RETRY_DELAY "$SANDBOX/case7-policy-transient.out")" "7: retry-policy transient delay"
assert_eq 1 "$(kv attempt_count "$dir/attempts.env")" "7: same-cause repeat starts after first failed attempt"
"$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class same-cause-repeat --signature "$(kv FAILURE_SIGNATURE "$dir/second.env")" --resume-hint none --outcome alternate >/dev/null
assert_eq 2 "$(kv attempt_count "$dir/attempts.env")" "7: alternate strategy attempt increments durable count"
run_capture "$SANDBOX/case7-policy-post-alt.out" "$SCRIPT" retry-policy --class same-cause-repeat
assert_eq 2 "$(kv MAX_ATTEMPTS "$SANDBOX/case7-policy-post-alt.out")" "7: same-cause policy still reports alternate-inclusive cap"
dir=$(make_tmp case7b)
write_state "$dir" 8 ci-initial
run_capture "$SANDBOX/case7b.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason "network timeout while posting issue"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case7b.out")" "7: bail-reason-only evidence classifies transient infra"
dir=$(make_tmp case7g)
write_state "$dir" 2 implementation
run_capture "$SANDBOX/case7g.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason wrapper-validation-failure
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$SANDBOX/case7g.out")" "7: argv-only wrapper-validation-failure stays dispatch-failure"
assert_eq step2-impl "$(kv RESUME_HINT "$SANDBOX/case7g.out")" "7: argv-only wrapper-validation-failure keeps step2 resume"
assert_eq wrapper-validation-failure "$(kv BAIL_REASON "$SANDBOX/case7g.out")" "7: argv-only wrapper-validation-failure renders allowlisted bail"
dir=$(make_tmp case7h)
write_state "$dir" 2 checks "" "NOTE=invalid envelope in step2 dispatch"
run_capture "$SANDBOX/case7h.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason orchestrator-envelope-invalid
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$SANDBOX/case7h.out")" "7: #3550 envelope evidence stays dispatch-failure"
assert_eq step2-impl "$(kv RESUME_HINT "$SANDBOX/case7h.out")" "7: #3550 envelope evidence keeps step2 resume"
assert_eq orchestrator-envelope-invalid "$(kv BAIL_REASON "$SANDBOX/case7h.out")" "7: #3550 envelope bail renders allowlisted token"
dir=$(make_tmp case7i)
write_state "$dir" 2 implementation
IMPLEMENT_BAIL_REASON=
FINAL_BAIL_REASON=orchestrator-envelope-invalid
export IMPLEMENT_BAIL_REASON FINAL_BAIL_REASON
run_capture "$SANDBOX/case7i.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$SANDBOX/case7i.out")" "7: FINAL_BAIL_REASON fallback orchestrator classifies dispatch"
assert_eq orchestrator-envelope-invalid "$(kv BAIL_REASON "$SANDBOX/case7i.out")" "7: FINAL_BAIL_REASON fallback orchestrator renders bail"
dir=$(make_tmp case7j)
write_state "$dir" 2 implementation
IMPLEMENT_BAIL_REASON=
FINAL_BAIL_REASON=wrapper-validation-failure
export IMPLEMENT_BAIL_REASON FINAL_BAIL_REASON
run_capture "$SANDBOX/case7j.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$SANDBOX/case7j.out")" "7: FINAL_BAIL_REASON fallback wrapper classifies dispatch"
assert_eq wrapper-validation-failure "$(kv BAIL_REASON "$SANDBOX/case7j.out")" "7: FINAL_BAIL_REASON fallback wrapper renders bail"
unset IMPLEMENT_BAIL_REASON FINAL_BAIL_REASON
dir=$(make_tmp case7k)
run_capture "$SANDBOX/case7k.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true --stall-step 2 --phase implementation --bail-reason dirty-state-after-timeout
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$SANDBOX/case7k.out")" "7: dirty-state-after-timeout is dispatch failure, not transient"
assert_eq step2-impl "$(kv RESUME_HINT "$SANDBOX/case7k.out")" "7: argv-only Step 2 hard-bail resumes implementation"
assert_eq 2 "$(kv STALL_STEP "$SANDBOX/case7k.out")" "7: argv-only Step 2 hard-bail preserves stall step"
assert_eq implementation "$(kv PHASE "$SANDBOX/case7k.out")" "7: argv-only Step 2 hard-bail preserves phase"
assert_eq dirty-state-after-timeout "$(kv BAIL_REASON "$SANDBOX/case7k.out")" "7: dirty-state-after-timeout renders allowlisted bail"
dir=$(make_tmp case7k2)
write_state "$dir" 2 implementation protected-path-edit-required-out-of-scope "NOTE=network timeout"
run_capture "$SANDBOX/case7k2.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq protected-path "$(kv FAILURE_CLASS "$SANDBOX/case7k2.out")" "7: protected-path bail is not transient"
assert_eq step2-impl "$(kv RESUME_HINT "$SANDBOX/case7k2.out")" "7: protected-path bail resumes implementation"
assert_eq protected-path-edit-required-out-of-scope "$(kv BAIL_REASON "$SANDBOX/case7k2.out")" "7: protected-path bail renders allowlisted token"
assert_eq protected-path-bail-token "$(kv MATCHED_CLASSIFIER_PATTERN "$SANDBOX/case7k2.out")" "7: protected-path bail pattern wins over stale evidence"
dir=$(make_tmp case7k3)
run_capture "$SANDBOX/case7k3.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true --stall-step 2 --phase implementation --bail-reason protected-path-edit-required-out-of-scope
assert_eq protected-path "$(kv FAILURE_CLASS "$SANDBOX/case7k3.out")" "7: argv-only protected-path bail classifies"
assert_eq step2-impl "$(kv RESUME_HINT "$SANDBOX/case7k3.out")" "7: argv-only protected-path bail resumes implementation"
dir=$(make_tmp case7k4)
write_state "$dir" 2 implementation submodule-edit-required-out-of-scope
run_capture "$SANDBOX/case7k4.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq submodule-restricted "$(kv FAILURE_CLASS "$SANDBOX/case7k4.out")" "7: submodule-restricted bail classifies"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case7k4.out")" "7: submodule-restricted bail does not resume implementation"
assert_eq submodule-edit-required-out-of-scope "$(kv BAIL_REASON "$SANDBOX/case7k4.out")" "7: submodule-restricted bail renders allowlisted token"
assert_eq submodule-restricted-bail-token "$(kv MATCHED_CLASSIFIER_PATTERN "$SANDBOX/case7k4.out")" "7: submodule-restricted bail pattern is explicit"
dir=$(make_tmp case7k5)
write_state "$dir" 2 implementation submodule-edit-required-out-of-scope "NOTE=network timeout"
run_capture "$SANDBOX/case7k5.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq submodule-restricted "$(kv FAILURE_CLASS "$SANDBOX/case7k5.out")" "7: submodule-restricted bail is not transient"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case7k5.out")" "7: submodule-restricted bail with stale evidence does not resume implementation"
assert_eq submodule-restricted-bail-token "$(kv MATCHED_CLASSIFIER_PATTERN "$SANDBOX/case7k5.out")" "7: submodule-restricted bail pattern wins over stale evidence"
dir=$(make_tmp case7k6)
write_state "$dir" 2 implementation "" "NOTE=network timeout"
run_capture "$SANDBOX/case7k6.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason submodule-edit-required-out-of-scope
assert_eq submodule-restricted "$(kv FAILURE_CLASS "$SANDBOX/case7k6.out")" "7: argv-only submodule-restricted bail classifies"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case7k6.out")" "7: argv-only submodule-restricted bail does not resume implementation"
assert_eq submodule-restricted-bail-token "$(kv MATCHED_CLASSIFIER_PATTERN "$SANDBOX/case7k6.out")" "7: argv-only submodule-restricted bail pattern wins over stale evidence"
dir=$(make_tmp case7l)
write_state "$dir" 2 implementation
run_capture "$SANDBOX/case7l.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason main-branch-post-dispatch
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$SANDBOX/case7l.out")" "7: main-branch-post-dispatch classifies dispatch"
assert_eq main-branch-post-dispatch "$(kv BAIL_REASON "$SANDBOX/case7l.out")" "7: main-branch-post-dispatch renders allowlisted bail"
dir=$(make_tmp case7l2)
write_state "$dir" 2 implementation
run_capture "$SANDBOX/case7l2.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason recovery-out-of-scope
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case7l2.out")" "7: recovery-out-of-scope stays unrecoverable"
assert_eq recovery-out-of-scope "$(kv BAIL_REASON "$SANDBOX/case7l2.out")" "7: recovery-out-of-scope renders allowlisted bail"
dir=$(make_tmp case7l3)
write_state "$dir" 2 implementation
run_capture "$SANDBOX/case7l3.out" "$SCRIPT" classify --implement-tmpdir "$dir" --bail-reason ci-fix-exhausted
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case7l3.out")" "7: ci-fix-exhausted without detail log stays unrecoverable"
assert_eq ci-fix-exhausted "$(kv BAIL_REASON "$SANDBOX/case7l3.out")" "7: ci-fix-exhausted renders allowlisted bail"

# #3592 bug b: distinct failure evidence produces distinct signatures.
dir=$(make_tmp case7m)
write_state "$dir" 5 review
log_a="$dir/failure-a.log"
log_b="$dir/failure-b.log"
printf 'shellcheck: SC2034 unused variable in hooks.sh\n' >"$log_a"
printf 'markdownlint MD038 failed in SKILL.md\n' >"$log_b"
run_capture "$SANDBOX/case7m-a.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$log_a"
run_capture "$SANDBOX/case7m-b.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$log_b"
sig_a=$(kv FAILURE_SIGNATURE "$SANDBOX/case7m-a.out")
sig_b=$(kv FAILURE_SIGNATURE "$SANDBOX/case7m-b.out")
assert_eq lint-failure "$(kv FAILURE_CLASS "$SANDBOX/case7m-a.out")" "7m: evidence-a classifies lint-failure"
assert_eq lint-failure "$(kv FAILURE_CLASS "$SANDBOX/case7m-b.out")" "7m: evidence-b classifies lint-failure"
if [ "$sig_a" != "$sig_b" ]; then pass "7m: distinct evidence produces distinct signatures"; else fail "7m: distinct evidence produces distinct signatures" "sig_a=$sig_a sig_b=$sig_b"; fi
while IFS='|' read -r klass attempts delay; do
    run_capture "$SANDBOX/retry-$klass.out" "$SCRIPT" retry-policy --class "$klass"
    assert_eq "$klass" "$(kv FAILURE_CLASS "$SANDBOX/retry-$klass.out")" "7: retry-policy class $klass"
    assert_eq "$attempts" "$(kv MAX_ATTEMPTS "$SANDBOX/retry-$klass.out")" "7: retry-policy attempts $klass"
    assert_eq "$delay" "$(kv RETRY_DELAY "$SANDBOX/retry-$klass.out")" "7: retry-policy delay $klass"
done <<'EOF'
transient-infra|4|sleep-seconds.sh 5
test-failure|8|none
lint-failure|8|none
dispatch-failure|3|none
protected-path|1|none
submodule-restricted|0|none
same-cause-repeat|2|none
contract-failure|0|none
unrecoverable|0|none
EOF
while IFS='|' read -r klass attempts delay; do
    run_capture "$SANDBOX/retry-doc-$klass.out" "$SCRIPT" retry-policy --class "$klass"
    assert_eq "$klass" "$(kv FAILURE_CLASS "$SANDBOX/retry-doc-$klass.out")" "7: retry-policy doc class $klass"
    assert_eq "$attempts" "$(kv MAX_ATTEMPTS "$SANDBOX/retry-doc-$klass.out")" "7: retry-policy doc attempts $klass"
    assert_eq "$delay" "$(kv RETRY_DELAY "$SANDBOX/retry-doc-$klass.out")" "7: retry-policy doc delay $klass"
done < <(
    awk -F'|' '
        /^## Retry Caps$/ { in_caps = 1; next }
        in_caps && /^## / { in_caps = 0 }
        in_caps && /^\| [a-z-]+ \| [0-9]+ \|/ {
            klass=$2
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", klass)
            attempts=$3
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", attempts)
            delay=$4
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", delay)
            gsub(/`/, "", delay)
            if (klass != "failure_class" && klass != "---") print klass "|" attempts "|" delay
        }
    ' "$CONTRACT_MD"
)
classify_fixture case7c 9b pr-prep "network timeout while writing PR body"
out=$CLASSIFY_OUT
assert_eq step8-shippr "$(kv RESUME_HINT "$out")" "7: symbolic step9b maps to ship-pr resume hint"
classify_fixture case7d 10-max-retries ci-initial "network timeout while requeueing CI"
out=$CLASSIFY_OUT
assert_eq step8-shippr "$(kv RESUME_HINT "$out")" "7: symbolic step10-max-retries maps to ship-pr resume hint"
classify_fixture case7e 12d ci-merge "network timeout while merge policy denied retry"
out=$CLASSIFY_OUT
assert_eq none "$(kv RESUME_HINT "$out")" "7: step12d stays non-resumable"
classify_fixture case7f bump-branch-guard bump "network timeout while validating bump branch"
out=$CLASSIFY_OUT
assert_eq none "$(kv RESUME_HINT "$out")" "7: bump-branch-guard stays non-resumable"
classify_fixture case7n merge-loop-iteration-cap merge "merge loop iteration cap reached"
out=$CLASSIFY_OUT
assert_eq unrecoverable "$(kv FAILURE_CLASS "$out")" "7: merge-loop-iteration-cap is unrecoverable"
assert_eq none "$(kv RESUME_HINT "$out")" "7: merge-loop-iteration-cap stays non-resumable"
classify_fixture case7r rebase-failed rebase-failed "rebase failed: conflict in Makefile"
out=$CLASSIFY_OUT
assert_eq transient-infra "$(kv FAILURE_CLASS "$out")" "7: rebase-failed classifies as transient-infra"
assert_eq step8-shippr "$(kv RESUME_HINT "$out")" "7: rebase-failed resumes through ship-pr"
assert_eq rebase-failed "$(kv STALL_STEP "$out")" "7: rebase-failed stall step is preserved"
assert_eq rebase-failed "$(kv PHASE "$out")" "7: rebase-failed phase is preserved"

dir=$(make_tmp case8a)
run_capture "$SANDBOX/case8a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "8: missing ship state exits 0"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case8a.out")" "8: no-signal missing ship state is unrecoverable"
assert_eq false "$(kv STALL_TRACKING "$SANDBOX/case8a.out")" "8: no-signal missing ship state stays non-stalled"


dir=$(make_tmp case_finalize_fallback)
cat >"$dir/finalize-state.sh" <<'STATE'
STALL_TRACKING=true
STALL_STEP=8
EXIT_CODE=4
STATE
printf '%s\n' 'gh: API rate limit exceeded' >"$dir/failure.log"
run_capture "$SANDBOX/case_finalize_fallback.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
assert_eq 0 "$RC" "finalize fallback classify exits 0"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case_finalize_fallback.out")" "finalize fallback classifies from finalize-state stall keys"
assert_eq step8-shippr "$(kv RESUME_HINT "$SANDBOX/case_finalize_fallback.out")" "finalize fallback resume hint"
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case_finalize_fallback.out")" "finalize fallback reports stall tracking"
assert_eq 8 "$(kv STALL_STEP "$SANDBOX/case_finalize_fallback.out")" "finalize fallback reports stall step"

dir=$(make_tmp case_finalize_bail_reason)
cat >"$dir/finalize-state.sh" <<'STATE'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=first-fixer-non-health
EXIT_CODE=3
STATE
run_capture "$SANDBOX/case_finalize_bail_reason.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq first-fixer-non-health "$(kv BAIL_REASON "$SANDBOX/case_finalize_bail_reason.out")" "8: finalize-state bail reason renders"

dir=$(make_tmp case8finalize)
cat >"$dir/ship-pr-state.sh" <<'STATE'
PHASE=ci-initial
EXIT_CODE=4
STATE
cat >"$dir/finalize-state.sh" <<'STATE'
STALL_TRACKING=true
STALL_STEP=8
EXIT_CODE=4
NOTE=network timeout
STATE
run_capture "$SANDBOX/case8finalize.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "8: finalize-only stall exits 0"
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case8finalize.out")" "8: finalize-only stall tracking consulted"
assert_eq 8 "$(kv STALL_STEP "$SANDBOX/case8finalize.out")" "8: finalize-only stall step consulted"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case8finalize.out")" "8: finalize-only evidence classifies"
assert_eq step8-shippr "$(kv RESUME_HINT "$SANDBOX/case8finalize.out")" "8: finalize-only resume hint"

dir=$(make_tmp case8b)
cat >"$dir/session-env.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
PHASE=ci-initial
IMPLEMENT_BAIL_REASON=api rate limit
EOF
run_capture "$SANDBOX/case8b.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "8: session-env-only missing ship state exits 0"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case8b.out")" "8: session env stall still classifies"
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case8b.out")" "8: session env stall tracking wins when state missing"
dir=$(make_tmp case8c)
printf 'STALL_TRACKING=true\n' >"$dir/session-env.sh"
run_capture "$SANDBOX/case8c.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "8: missing ship state with no evidence exits 0"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case8c.out")" "8: missing ship state without recoverable evidence is unrecoverable"

dir=$(make_tmp case8exit_missing)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=
EOF
run_capture "$SANDBOX/case8exit-missing.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unknown "$(kv EXIT_CODE "$SANDBOX/case8exit-missing.out")" "8: missing EXIT_CODE emits unknown"
cp "$SANDBOX/case8exit-missing.out" "$dir/class.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
assert_contains "| Exit code | \`unknown\` |" "$(cat "$(kv BODY_FILE "$dir/body.out")")" "8: missing EXIT_CODE renders unknown"

dir=$(make_tmp case8exit_zero)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=
EXIT_CODE=0
EOF
run_capture "$SANDBOX/case8exit-zero.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$(kv EXIT_CODE "$SANDBOX/case8exit-zero.out")" "8: EXIT_CODE=0 emits 0"
cp "$SANDBOX/case8exit-zero.out" "$dir/class.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
assert_contains "| Exit code | \`0\` |" "$(cat "$(kv BODY_FILE "$dir/body.out")")" "8: EXIT_CODE=0 renders 0"

dir=$(make_tmp case8exit_four)
write_state "$dir" 8 ci-initial
run_capture "$SANDBOX/case8exit-four.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 4 "$(kv EXIT_CODE "$SANDBOX/case8exit-four.out")" "8: EXIT_CODE=4 emits 4"

dir=$(make_tmp case8exit_malformed)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=
EXIT_CODE=abc
EOF
run_capture "$SANDBOX/case8exit-malformed.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unknown "$(kv EXIT_CODE "$SANDBOX/case8exit-malformed.out")" "8: malformed EXIT_CODE emits unknown"

dir=$(make_tmp case9)
write_state "$dir" 8 ci-initial
printf 'x\n' >"$dir/ok.log"
ln -s "$dir/ok.log" "$dir/link.log"
run_capture "$SANDBOX/case9-rel.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log rel.log
assert_eq 0 "$RC" "9: relative log ignored"
assert_contains "--failure-detail-log must be absolute" "$(cat "$SANDBOX/case9-rel.out.err")" "9: relative log stderr"
outside_log=$(mktemp "${TMPDIR:-/tmp}/larch-outside-log.XXXXXX")
printf 'outside\n' >"$outside_log"
run_capture "$SANDBOX/case9-outside.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$outside_log"
rm -f "$outside_log"
assert_eq 0 "$RC" "9: outside tmpdir log ignored"
assert_contains "--failure-detail-log outside implement tmpdir" "$(cat "$SANDBOX/case9-outside.out.err")" "9: outside tmpdir log stderr"
run_capture "$SANDBOX/case9-symlink.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/link.log"
assert_eq 0 "$RC" "9: symlink log ignored"
assert_contains "--failure-detail-log must not be a symlink" "$(cat "$SANDBOX/case9-symlink.out.err")" "9: symlink log stderr"
run_capture "$SANDBOX/case9-dir.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir"
assert_eq 0 "$RC" "9: non-regular log ignored"
assert_contains "--failure-detail-log outside implement tmpdir" "$(cat "$SANDBOX/case9-dir.out.err")" "9: non-regular log stderr"
python3 - <<'PY' >"$dir/oversize.log"
print("x" * 65537, end="")
PY
run_capture "$SANDBOX/case9-oversize.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/oversize.log"
assert_eq 0 "$RC" "9: oversize log ignored"
assert_contains "--failure-detail-log exceeds 64KiB" "$(cat "$SANDBOX/case9-oversize.out.err")" "9: oversize log stderr"

dir=$(make_tmp case10)
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
before=$(cat "$dir/attempts.env")
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
after=$(cat "$dir/attempts.env")
assert_eq "$before" "$after" "10: init-attempts idempotent"

"$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class transient-infra --signature abc --resume-hint step8-shippr --outcome failed >"$dir/record.out"
assert_eq 1 "$(kv ATTEMPT_COUNT "$dir/record.out")" "11: record-attempt increments"
assert_contains "attempt.1.signature=abc" "$(cat "$dir/attempts.env")" "11: record-attempt writes signature"

dir=$(make_tmp case12-yes)
mkdir -p "$dir/skills/implement"
touch "$dir/skills/implement/SKILL.md"
run_capture "$SANDBOX/case12-yes.out" "$SCRIPT" is-larch-dev-clone --working-tree-root "$dir"
assert_eq true "$(kv LARCH_DEV_CLONE "$SANDBOX/case12-yes.out")" "12: dev clone true"
dir=$(make_tmp case12-no)
run_capture "$SANDBOX/case12-no.out" "$SCRIPT" is-larch-dev-clone --working-tree-root "$dir"
assert_eq false "$(kv LARCH_DEV_CLONE "$SANDBOX/case12-no.out")" "12: dev clone false"
dir=$(make_tmp case12-forked)
mkdir -p "$dir/skills/implement"
touch "$dir/skills/implement/SKILL.md"
cat >"$dir/session-env.sh" <<'EOF'
FORKED_TARGET=true
EOF
run_capture "$SANDBOX/case12-forked.out" "$SCRIPT" is-larch-dev-clone --working-tree-root "$dir" --implement-tmpdir "$dir"
assert_eq false "$(kv LARCH_DEV_CLONE "$SANDBOX/case12-forked.out")" "12: forked target suppresses dev clone issue filing"

dir=$(make_tmp case13)
cat >"$dir/class.env" <<'EOF'
FAILURE_CLASS=unrecoverable
FAILURE_SIGNATURE=not-a-hash-SENTINEL_SECRET_13
STALL_STEP=SENTINEL_SECRET_13
PHASE=SENTINEL_SECRET_13
EXIT_CODE=99
EOF
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
"$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class SENTINEL_SECRET_13 --signature SENTINEL_SECRET_13 --resume-hint SENTINEL_SECRET_13 --outcome SENTINEL_SECRET_13 >/dev/null
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
"$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
"$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$(kv BODY_FILE "$dir/body.out")" >"$dir/input.out"
assert_not_contains "SENTINEL_SECRET_13" "$(cat "$(kv BODY_FILE "$dir/body.out")" "$(kv BODY_FILE "$dir/comment.out")" "$(kv INPUT_FILE "$dir/input.out")")" "13: public outputs omit raw sentinels"
assert_not_contains "SENTINEL_SECRET_13" "$(cat "$(kv BODY_FILE "$dir/body.out")")" "13: chat-print payload omits raw sentinels"
assert_eq "" "$(kv BAIL_REASON "$SANDBOX/case5a.out")" "13: empty bail reason stays single-line empty"
assert_not_contains "BAIL_REASON=redacted" "$(cat "$SANDBOX/case5a.out")" "13: empty bail reason does not fall through to redacted"

dir=$(make_tmp case13b)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=ship state sentinel SENTINEL_SECRET_13B
NOTE=note sentinel SENTINEL_SECRET_13B
EOF
printf 'failure detail %s and SENTINEL_SECRET_13B\n' "$GHP_TOKEN_CASE13" >"$dir/failure.log"
run_capture "$dir/classify.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/classify.out" >"$dir/body.out"
"$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/classify.out" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
assert_not_contains "SENTINEL_SECRET_13B" "$(cat "$(kv BODY_FILE "$dir/body.out")" "$(kv BODY_FILE "$dir/comment.out")")" "13: evidence sentinels stay out of public outputs"
assert_not_contains "$GHP_TOKEN_CASE13" "$(cat "$(kv BODY_FILE "$dir/body.out")" "$(kv BODY_FILE "$dir/comment.out")")" "13: evidence ghp token stays out of public outputs"
assert_eq redacted "$(kv BAIL_REASON "$dir/classify.out")" "13: classification bail reason is redacted"
assert_contains "| Bail reason | \`redacted\` |" "$(cat "$(kv BODY_FILE "$dir/body.out")")" "13: redacted bail reason renders redacted"

dir=$(make_tmp case13_bail_rows)
cp "$SANDBOX/case7h.out" "$dir/orchestrator.env"
cp "$SANDBOX/case7g.out" "$dir/wrapper.env"
cp "$SANDBOX/case5a.out" "$dir/none.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/orchestrator.env" --output-file "$dir/orchestrator.md" >"$dir/orchestrator.out"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/wrapper.env" --output-file "$dir/wrapper.md" >"$dir/wrapper.out"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/none.env" --output-file "$dir/none.md" >"$dir/none.out"
assert_contains "| Bail reason | \`orchestrator-envelope-invalid\` |" "$(cat "$dir/orchestrator.md")" "13: orchestrator bail reason renders allowlisted token"
assert_contains "| Bail reason | \`wrapper-validation-failure\` |" "$(cat "$dir/wrapper.md")" "13: wrapper bail reason renders allowlisted token"
assert_contains "| Bail reason | \`none\` |" "$(cat "$dir/none.md")" "13: empty bail reason renders none"

dir=$(make_tmp case13c)
cat >"$dir/session-env.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=SENTINEL_SECRET_13C
PHASE=SENTINEL_SECRET_13C
IMPLEMENT_BAIL_REASON=relative/path SENTINEL_SECRET_13C
EOF
run_capture "$dir/classify.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unknown "$(kv STALL_STEP "$dir/classify.out")" "13: classification stall step is sanitized"
assert_eq unknown "$(kv PHASE "$dir/classify.out")" "13: classification phase is sanitized"
assert_eq redacted "$(kv BAIL_REASON "$dir/classify.out")" "13: classification raw bail metadata is redacted"

dir=$(make_tmp case13g)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=10-detached-head
BAIL_REASON=first-fixer-non-health
NOTE=network/auth issue
EOF
run_capture "$dir/classify.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq step8-shippr "$(kv RESUME_HINT "$dir/classify.out")" "13: suffixed ship-pr step resumes through ship-pr"
assert_eq 10-detached-head "$(kv STALL_STEP "$dir/classify.out")" "13: suffixed ship-pr step is preserved"
assert_eq first-fixer-non-health "$(kv BAIL_REASON "$dir/classify.out")" "13: allowlisted bail token survives classification"

dir=$(make_tmp case13d)
outside_attempts=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-attempts-outside.XXXXXX")
run_capture "$SANDBOX/case13d-init.out" "$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$outside_attempts"
assert_eq 1 "$RC" "13: init-attempts rejects attempts file outside tmpdir"
assert_contains "--attempts-file outside implement tmpdir" "$(cat "$SANDBOX/case13d-init.out.err")" "13: init-attempts outside tmpdir stderr"
printf 'version=1\ncreated_utc=2026-01-01T00:00:00Z\nattempt_count=0\n' >"$outside_attempts"
run_capture "$SANDBOX/case13d-record.out" "$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$outside_attempts" --class transient-infra --signature abc --resume-hint step8-shippr --outcome failed
assert_eq 1 "$RC" "13: record-attempt rejects attempts file outside tmpdir"
assert_contains "--attempts-file outside implement tmpdir" "$(cat "$SANDBOX/case13d-record.out.err")" "13: record-attempt outside tmpdir stderr"
rm -f "$outside_attempts"

dir=$(make_tmp case13e)
printf 'version=1\ncreated_utc=2026-01-01T00:00:00Z\nattempt_count=0\n' >"$dir/real-attempts.env"
ln -s "$dir/real-attempts.env" "$dir/attempts.env"
run_capture "$SANDBOX/case13e.out" "$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class transient-infra --signature abc --resume-hint step8-shippr --outcome failed
assert_eq 1 "$RC" "13: record-attempt rejects attempts symlink"
assert_contains "--attempts-file must not be a symlink" "$(cat "$SANDBOX/case13e.out.err")" "13: record-attempt symlink stderr"
dir=$(make_tmp case13f)
write_state "$dir" 8 ci-initial "" "NOTE=network timeout"
outside_attempts=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-attempts-outside.XXXXXX")
printf 'version=1\ncreated_utc=2026-01-01T00:00:00Z\nattempt_count=0\n' >"$outside_attempts"
run_capture "$SANDBOX/case13f.out" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$outside_attempts"
assert_eq 1 "$RC" "13: classify rejects attempts file outside tmpdir"
assert_contains "--attempts-file outside implement tmpdir" "$(cat "$SANDBOX/case13f.out.err")" "13: classify outside tmpdir stderr"
rm -f "$outside_attempts"

run_capture "$SANDBOX/case14.out" "$SCRIPT" lint
assert_eq 0 "$RC" "14: allowlist parity lint"
if awk '/runtime_bail_token_lines\(\)/,/^}/' "$SCRIPT" | grep -q 'STALL_RECOVERY_BAIL_REASON_TOKENS' \
    && ! awk '/runtime_bail_token_lines\(\)/,/^}/' "$SCRIPT" | grep -q 'ci-decide.sh'; then
    pass "14: runtime bail tokens derive from python/config.py"
else
    fail "14: runtime bail tokens should derive from python/config.py, not ci-decide.sh"
fi

dir=$(make_tmp case15)
cp "$SANDBOX/case5a.out" "$dir/class.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" --output-file "$dir/a.md" >/dev/null
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" --output-file "$dir/b.md" >/dev/null
assert_eq "$(cat "$dir/a.md")" "$(cat "$dir/b.md")" "15: bug-body byte-stable"

copyroot="$SANDBOX/case16-plugin"
mkdir -p "$copyroot/skills/implement/scripts" "$copyroot/scripts"
cp "$SCRIPT" "$copyroot/skills/implement/scripts/stall-recovery-report.sh"
cp "$SCRIPT_DIR/stall-recovery-report-allowlists.tsv" "$copyroot/skills/implement/scripts/"
cp "$SCRIPT_DIR/stall-recovery-report.md" "$copyroot/skills/implement/scripts/"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$copyroot/scripts/"
cp "$REPO_ROOT/scripts/lib-larch-dev-clone.sh" "$copyroot/scripts/"
mkdir -p "$copyroot/python"
cat >"$copyroot/python/cli.py" <<'SH'
import os
import re
import sys

data = sys.stdin.read()
with open(os.environ["STALL_REDACTOR_MARKER"], "w", encoding="utf-8") as handle:
    handle.write(data)
out = data + "\nInjected ghp_" "abcdef123456789012345678901234567890\n"
sys.stdout.write(re.sub(r"ghp_[A-Za-z0-9_]+", "<REDACTED-TOKEN>", out))
SH
chmod +x "$copyroot/skills/implement/scripts/stall-recovery-report.sh"
dir=$(make_tmp case16)
cat >"$dir/class.env" <<'EOF'
FAILURE_CLASS=transient-infra
FAILURE_SIGNATURE=abcdef
STALL_STEP=8
PHASE=ci-initial
EXIT_CODE=6
EOF
STALL_REDACTOR_MARKER="$dir/redactor.in" "$copyroot/skills/implement/scripts/stall-recovery-report.sh" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/out"
assert_contains "Sanitized stall report" "$(cat "$(kv BODY_FILE "$dir/out")")" "16: redactor stub produced body"
if [ -s "$dir/redactor.in" ]; then
    pass "16: redactor was invoked on generated body stream"
else
    fail "16: redactor marker missing"
fi
assert_not_contains "$GHP_TOKEN_CASE16" "$(cat "$(kv BODY_FILE "$dir/out")")" "16: redactor output omits injected ghp token"
assert_contains '<REDACTED-TOKEN>' "$(cat "$(kv BODY_FILE "$dir/out")")" "16: redactor output shows ghp placeholder"

dir=$(make_tmp case17)
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
"$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class transient-infra --signature abc --resume-hint step8-shippr --outcome failed >/dev/null
cp "$SANDBOX/case1.out" "$dir/class.env"
"$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
assert_contains "| Attempt | Class | Signature | Resume hint | Outcome | UTC |" "$(cat "$(kv BODY_FILE "$dir/comment.out")")" "17: bug-comment attempt table"
outside_attempts=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-attempts-outside.XXXXXX")
printf 'version=1\ncreated_utc=2026-01-01T00:00:00Z\nattempt_count=0\n' >"$outside_attempts"
run_capture "$SANDBOX/case17-outside.out" "$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$outside_attempts"
assert_eq 1 "$RC" "17: bug-comment rejects attempts file outside tmpdir"
assert_contains "--attempts-file outside implement tmpdir" "$(cat "$SANDBOX/case17-outside.out.err")" "17: bug-comment outside tmpdir stderr"
rm -f "$outside_attempts"

dir=$(make_tmp case18)
cp "$SANDBOX/case1.out" "$dir/class.env"
mkdir -p "$dir/bin"
printf '#!/usr/bin/env bash\necho "$@" >>"%s/gh.calls"\n' "$dir" >"$dir/bin/gh"
chmod +x "$dir/bin/gh"
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
PATH="$dir/bin:$PATH" LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
assert_eq true "$(kv DRY_RUN_DECISION "$dir/body.out")" "18: dry-run decision true"
PATH="$dir/bin:$PATH" LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
assert_eq true "$(kv DRY_RUN_DECISION "$dir/comment.out")" "18: bug-comment dry-run decision true"
PATH="$dir/bin:$PATH" LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$(kv BODY_FILE "$dir/body.out")" >"$dir/input.out"
assert_eq true "$(kv DRY_RUN_DECISION "$dir/input.out")" "18: issue-input-file dry-run decision true"
if [ ! -f "$dir/gh.calls" ]; then
    pass "18: gh stub not invoked"
else
    fail "18: gh stub should not be invoked" "$(cat "$dir/gh.calls")"
fi
assert_contains "### [Bug] /implement stall: transient-infra at 8" "$(cat "$(kv INPUT_FILE "$dir/input.out")")" "18: dry-run issue input still renders consumer-facing heading"

dir=$(make_tmp case18b)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=first-fixer-non-health
EXIT_CODE=4
EOF
printf 'network error talking to GitHub API\n' >"$dir/failure.log"
mkdir -p "$dir/bin"
printf '#!/usr/bin/env bash\necho \"$@\" >>\"%s/gh.calls\"\n' "$dir" >"$dir/bin/gh"
chmod +x "$dir/bin/gh"
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
run_capture "$dir/classify.capture" env "PATH=$dir/bin:$PATH" "LARCH_STALL_RECOVERY_DRY_RUN=1" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --failure-detail-log "$dir/failure.log"
env "PATH=$dir/bin:$PATH" "LARCH_STALL_RECOVERY_DRY_RUN=1" "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/classify.capture" >"$dir/body.out"
env "PATH=$dir/bin:$PATH" "LARCH_STALL_RECOVERY_DRY_RUN=1" "$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/classify.capture" --body-file "$(kv BODY_FILE "$dir/body.out")" >"$dir/input.out"
env "PATH=$dir/bin:$PATH" "LARCH_STALL_RECOVERY_DRY_RUN=1" "$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/classify.capture" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
assert_eq transient-infra "$(kv FAILURE_CLASS "$dir/classify.capture")" "18: dry-run sequence classifies recoverable stall"
assert_eq true "$(kv DRY_RUN_DECISION "$dir/body.out")" "18: dry-run sequence body decision true"
assert_eq true "$(kv DRY_RUN_DECISION "$dir/comment.out")" "18: dry-run sequence comment decision true"
assert_contains "## Sanitized stall report" "$(cat "$(kv BODY_FILE "$dir/body.out")")" "18: dry-run sequence renders bug body"
assert_contains "## Retry attempts" "$(cat "$(kv BODY_FILE "$dir/comment.out")")" "18: dry-run sequence renders terminal comment"
if [ ! -e "$dir/gh.calls" ]; then
    pass "18: dry-run step18a sequence makes no gh calls"
else
    fail "18: dry-run step18a sequence should not call gh" "$(cat "$dir/gh.calls")"
fi

dir=$(make_tmp case19)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
tmp="$dir/ship-pr-state.sh.tmp.$$"
awk 'BEGIN{done=0} /^STALL_TRACKING=/{print "STALL_TRACKING=false"; done=1; next} /^STALL_STEP=/{print "STALL_STEP="; next} {print} END{if(!done) print "STALL_TRACKING=false"}' "$dir/ship-pr-state.sh" >"$tmp"
assert_eq false "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$tmp" --key STALL_TRACKING --default "")" "19: temp read-back sees false before mv"
assert_eq true "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: disk remains true before mv"
run_capture "$SANDBOX/case19a.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case19a.out")" "19: in-memory true remains authoritative before mv"
mv -f "$tmp" "$dir/ship-pr-state.sh"
assert_eq false "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: destination read-back sees false after mv"
dir=$(make_tmp case19c)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
tmp="$dir/ship-pr-state.sh.tmp.$$"
awk 'BEGIN{done=0} /^STALL_TRACKING=/{print "STALL_TRACKING=false"; done=1; next} /^STALL_STEP=/{print "STALL_STEP="; next} {print} END{if(!done) print "STALL_TRACKING=false"}' "$dir/ship-pr-state.sh" >"$tmp"
rm -f "$tmp"
if ! mv -f "$tmp" "$dir/ship-pr-state.sh" 2>/dev/null; then
    pass "19: missing temp file models mv failure before disk clear"
else
    fail "19: mv failure simulation should not succeed"
fi
assert_eq true "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: mv failure leaves disk stalled"
dir=$(make_tmp case19d)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
tmp="$dir/ship-pr-state.sh.tmp.$$"
awk 'BEGIN{done=0} /^STALL_TRACKING=/{print "STALL_TRACKING=false"; done=1; next} /^STALL_STEP=/{print "STALL_STEP="; next} {print} END{if(!done) print "STALL_TRACKING=false"}' "$dir/ship-pr-state.sh" >"$tmp"
mv -f "$tmp" "$dir/ship-pr-state.sh"
assert_eq false "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: destination read-back must see false after mv in success path"
mv -f "$dir/ship-pr-state.sh" "$dir/ship-pr-state.sh.gone"
assert_eq "" "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: missing destination read-back falls back to empty default"

dir=$(make_tmp case19b)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=false
STALL_STEP=8
BAIL_REASON=api rate limit
EOF
run_capture "$SANDBOX/case19b.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case19b.out")" "19: in-memory true overrides disk false"
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case19b.out")" "19: emitted stall tracking preserves in-memory true"
STALL_TRACKING=true
case "$(python3 "$REPO_ROOT/python/cli.py" session read-key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" in
    false) STALL_TRACKING=false ;;
esac
assert_eq false "$STALL_TRACKING" "19: in-memory clear happens only after false-on-disk is durable"

dir=$(make_tmp case20a)
write_state "$dir" 12d ci-merge "" "NOTE=network/auth issue"
run_capture "$SANDBOX/case20a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case20a.out")" "20: 12d still classifies from evidence"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case20a.out")" "20: 12d does not redispatch ship-pr"

dir=$(make_tmp case20b)
write_state "$dir" 6 checks "" "NOTE=network/auth issue"
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
run_capture "$dir/first.env" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env"
"$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class "$(kv FAILURE_CLASS "$dir/first.env")" --signature "$(kv FAILURE_SIGNATURE "$dir/first.env")" --resume-hint "$(kv RESUME_HINT "$dir/first.env")" --outcome failed >/dev/null
run_capture "$dir/second.env" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env"
assert_eq contract-failure "$(kv FAILURE_CLASS "$dir/second.env")" "20: step6 stays terminal contract-failure"
assert_eq none "$(kv RESUME_HINT "$dir/second.env")" "20: contract-failure at step6 keeps none hint"

dir=$(make_tmp case20)
cp "$SANDBOX/case1.out" "$dir/class.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
"$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$(kv BODY_FILE "$dir/body.out")" >"$dir/input.out"
first_line=$(sed -n '1p' "$(kv INPUT_FILE "$dir/input.out")")
assert_eq "### [Bug] /implement stall: transient-infra at 8" "$first_line" "20: issue input title shape"
run_capture "$dir/parse-input.out" python3 "$REPO_ROOT/python/cli.py" issue parse-input --input-file "$(kv INPUT_FILE "$dir/input.out")" --output-dir "$dir/parsed-input"
assert_eq 0 "$RC" "20: parse-input accepts issue input file"
assert_eq 1 "$(kv ITEMS_TOTAL "$dir/parse-input.out")" "20: headed issue input parses as one item"
run_capture "$dir/parse-body.out" python3 "$REPO_ROOT/python/cli.py" issue parse-input --input-file "$(kv BODY_FILE "$dir/body.out")" --output-dir "$dir/parsed-body"
assert_eq 0 "$RC" "20: parse-input accepts raw bug body"
assert_eq 0 "$(kv ITEMS_TOTAL "$dir/parse-body.out")" "20: heading-less bug body parses as zero items"

while IFS= read -r step_token; do
    [ -n "$step_token" ] || continue
    safe_name=$(printf '%s' "$step_token" | tr -c '[:alnum:]' '_')
    token_dir=$(make_tmp "case20-token-$safe_name")
    cat >"$token_dir/class.env" <<EOF
FAILURE_CLASS=transient-infra
STALL_STEP=$step_token
EOF
    printf 'body for %s\n' "$step_token" >"$token_dir/body.md"
    "$SCRIPT" issue-input-file --implement-tmpdir "$token_dir" --classification-file "$token_dir/class.env" --body-file "$token_dir/body.md" >"$token_dir/input.out"
    first_line=$(sed -n '1p' "$(kv INPUT_FILE "$token_dir/input.out")")
    assert_eq "### [Bug] /implement stall: transient-infra at $step_token" "$first_line" "20: production step token preserved: $step_token"
done <<'EOF'
8b
9a1
9b
10-max-retries
10-head-changed
12b
12c
12d
12-head-changed
12-max-retries
10-detached-head
bump-branch-guard
merge-loop-iteration-cap
rebase-failed
EOF

dir=$(make_tmp case20-unsafe-step)
cat >"$dir/class.env" <<'EOF'
FAILURE_CLASS=transient-infra
STALL_STEP=8a<script>
EOF
printf 'unsafe body fixture\n' >"$dir/body.md"
"$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$dir/body.md" >"$dir/input.out"
first_line=$(sed -n '1p' "$(kv INPUT_FILE "$dir/input.out")")
assert_eq "### [Bug] /implement stall: transient-infra at unknown" "$first_line" "20: unsafe step token becomes unknown"
assert_not_contains "8a<script>" "$first_line" "20: unsafe step token is absent from issue title"

while IFS= read -r step_token; do
    [ -n "$step_token" ] || continue
    safe_name=$(printf '%s' "$step_token" | tr -c '[:alnum:]' '_')
    token_dir=$(make_tmp "case20-invalid-token-$safe_name")
    cat >"$token_dir/class.env" <<EOF
FAILURE_CLASS=transient-infra
STALL_STEP=$step_token
EOF
    printf 'body for invalid %s\n' "$step_token" >"$token_dir/body.md"
    "$SCRIPT" issue-input-file --implement-tmpdir "$token_dir" --classification-file "$token_dir/class.env" --body-file "$token_dir/body.md" >"$token_dir/input.out"
    first_line=$(sed -n '1p' "$(kv INPUT_FILE "$token_dir/input.out")")
    assert_eq "### [Bug] /implement stall: transient-infra at unknown" "$first_line" "20: invalid exact-only step token becomes unknown: $step_token"
    assert_not_contains "$step_token" "$first_line" "20: invalid exact-only step token absent from issue title: $step_token"
done <<'EOF'
8aevil
2a
3a
5-max-retries
6a
EOF

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
