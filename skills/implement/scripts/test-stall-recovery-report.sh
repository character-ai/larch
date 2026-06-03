#!/usr/bin/env bash
# test-stall-recovery-report.sh — offline harness for stall-recovery-report.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SCRIPTS_DIR="$REPO_ROOT/scripts"
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
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then pass "$label"; else fail "$label" "missing: $needle" "$haystack"; fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then fail "$label" "unexpected: $needle" "$haystack"; else pass "$label"; fi
}

kv() {
    local key=$1 file=$2
    awk -v k="$key" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$file"
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

dir=$(make_tmp case8a)
run_capture "$SANDBOX/case8a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "8: missing ship state exits 0"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case8a.out")" "8: no-signal missing ship state is unrecoverable"
assert_eq false "$(kv STALL_TRACKING "$SANDBOX/case8a.out")" "8: no-signal missing ship state stays non-stalled"

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
cp "$REPO_ROOT/scripts/read-session-env-key.sh" "$copyroot/scripts/"
cat >"$copyroot/scripts/redact-secrets.sh" <<'SH'
#!/usr/bin/env bash
cat >"$STALL_REDACTOR_MARKER"
{
    cat "$STALL_REDACTOR_MARKER"
    printf '\nInjected %s\n' 'ghp_''abcdef123456789012345678901234567890'
} | sed 's/ghp_[A-Za-z0-9_][A-Za-z0-9_]*/<REDACTED-TOKEN>/g'
SH
chmod +x "$copyroot/skills/implement/scripts/stall-recovery-report.sh" "$copyroot/scripts/redact-secrets.sh"
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
assert_eq false "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$tmp" --key STALL_TRACKING --default "")" "19: temp read-back sees false before mv"
assert_eq true "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: disk remains true before mv"
run_capture "$SANDBOX/case19a.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case19a.out")" "19: in-memory true remains authoritative before mv"
mv -f "$tmp" "$dir/ship-pr-state.sh"
assert_eq false "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: destination read-back sees false after mv"
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
assert_eq true "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: mv failure leaves disk stalled"
dir=$(make_tmp case19d)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
tmp="$dir/ship-pr-state.sh.tmp.$$"
awk 'BEGIN{done=0} /^STALL_TRACKING=/{print "STALL_TRACKING=false"; done=1; next} /^STALL_STEP=/{print "STALL_STEP="; next} {print} END{if(!done) print "STALL_TRACKING=false"}' "$dir/ship-pr-state.sh" >"$tmp"
mv -f "$tmp" "$dir/ship-pr-state.sh"
assert_eq false "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: destination read-back must see false after mv in success path"
mv -f "$dir/ship-pr-state.sh" "$dir/ship-pr-state.sh.gone"
assert_eq "" "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "19: missing destination read-back falls back to empty default"

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
case "$("$REPO_ROOT/scripts/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" in
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

dir=$(make_tmp case20c)
write_state "$dir" 8 ci-initial
run_capture "$SANDBOX/case20c.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/missing.log"
assert_eq 0 "$RC" "20: invalid failure-detail-log no longer exits"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case20c.out")" "20: invalid failure-detail-log falls back to remaining evidence"

dir=$(make_tmp case20d)
printf 'STALL_TRACKING=true\n' >"$dir/session-env.sh"
printf 'network error while contacting GitHub\n' >"$dir/failure.log"
run_capture "$SANDBOX/case20d.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true --failure-detail-log "$dir/failure.log"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case20d.out")" "20: in-memory-only stall can classify from failure detail log"

dir=$(make_tmp case20e)
write_state "$dir" 5 review "" "NOTE=api rate limit from stale state"
printf 'shellcheck: lint failed in review loop\n' >"$dir/failure.log"
run_capture "$SANDBOX/case20e.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
assert_eq lint-failure "$(kv FAILURE_CLASS "$SANDBOX/case20e.out")" "20: lint evidence outranks transient stale evidence"

dir=$(make_tmp case20f)
write_state "$dir" 8 ci-initial
printf 'network error talking to GitHub API\n' >"$dir/failure.log"
run_capture "$SANDBOX/case20f.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
assert_eq transient-infra "$(kv FAILURE_CLASS "$SANDBOX/case20f.out")" "20: broader network error matches transient infra"

dir=$(make_tmp case20g)
write_state "$dir" 8 ci-initial
printf 'authentication failed for profile default\n' >"$dir/failure.log"
run_capture "$SANDBOX/case20g.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case20g.out")" "20: standalone auth failure is unrecoverable"

dir=$(make_tmp case20h)
write_state "$dir" 8 ci-initial "" "NOTE=api rate limit from stale state"
printf 'build finished without retry markers\n' >"$dir/failure.log"
run_capture "$SANDBOX/case20h.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case20h.out")" "20: stale state note does not override clean failure-detail log"

dir=$(make_tmp case20i)
write_state "$dir" 8 ci-initial "terminal/SENTINEL_SECRET_20I" "NOTE=note sentinel SENTINEL_SECRET_20I"
printf 'non-matching detail\n' >"$dir/failure.log"
run_capture "$dir/classify.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/failure.log"
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/classify.out" >"$dir/body.out"
"$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/classify.out" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
assert_not_contains "SENTINEL_SECRET_20I" "$(cat "$(kv BODY_FILE "$dir/body.out")" "$(kv BODY_FILE "$dir/comment.out")")" "20: public outputs omit bail-reason-only and NOTE sentinels"

# CI-fix exhaustion with a readable failure-detail log is recoverable: route to
# step8-shippr for an inline fix instead of terminal unrecoverable (#3335).
dir=$(make_tmp case20j)
write_state "$dir" 8 ci-initial ci-fix-exhausted
printf 'ci-fix-exhausted: python-lint\n--- CI log (run 42) ---\nE501 line too long in bar.py\n' >"$dir/detail.log"
run_capture "$SANDBOX/case20j.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/detail.log"
assert_eq ci-fix-exhausted "$(kv FAILURE_CLASS "$SANDBOX/case20j.out")" "20: ci-fix-exhausted with detail log is recoverable"
assert_eq step8-shippr "$(kv RESUME_HINT "$SANDBOX/case20j.out")" "20: ci-fix-exhausted routes to ship-pr resume"
# Without a readable detail log there is nothing to act on -> stays unrecoverable.
dir=$(make_tmp case20k)
write_state "$dir" 8 ci-initial ci-fix-exhausted
run_capture "$SANDBOX/case20k.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case20k.out")" "20: ci-fix-exhausted without detail log stays unrecoverable"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case20k.out")" "20: ci-fix-exhausted without detail log does not resume"
# A more precise evidence signature still outranks the generic ci-fix-exhausted class.
dir=$(make_tmp case20l)
write_state "$dir" 8 ci-initial ci-fix-exhausted
printf 'pytest reports 2 failing tests\n' >"$dir/detail.log"
run_capture "$SANDBOX/case20l.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/detail.log"
assert_eq test-failure "$(kv FAILURE_CLASS "$SANDBOX/case20l.out")" "20: precise test evidence outranks ci-fix-exhausted"
assert_eq step8-shippr "$(kv RESUME_HINT "$SANDBOX/case20l.out")" "20: test evidence at step8 still resumes ship-pr"

run_capture "$SANDBOX/case21-badargv.out" "$SCRIPT" unknown-subcommand
assert_eq 1 "$RC" "21: bad argv exits 1"
run_capture "$SANDBOX/case21-missing.out" "$SCRIPT" classify
assert_eq 2 "$RC" "21: missing required exits 2"
dir=$(make_tmp case21-malformed)
printf 'not valid\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case21-malformed.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 3 "$RC" "21: malformed ship-pr-state exits 3"
dir=$(make_tmp case21-state-symlink)
printf 'PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=8\n' >"$dir/ship-pr-state.real"
ln -s "$dir/ship-pr-state.real" "$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case21-state-symlink.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 3 "$RC" "21: classify rejects symlinked ship-pr-state"
dir=$(make_tmp case21-classification-outside)
cp "$SANDBOX/case1.out" "$dir/class.env"
outside_class=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-class-outside.XXXXXX")
cp "$dir/class.env" "$outside_class"
run_capture "$SANDBOX/case21-classification-outside.out" "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$outside_class"
assert_eq 1 "$RC" "21: bug-body rejects classification file outside tmpdir"
assert_contains "--classification-file outside implement tmpdir" "$(cat "$SANDBOX/case21-classification-outside.out.err")" "21: bug-body outside tmpdir stderr"
run_capture "$SANDBOX/case21-issue-classification-outside.out" "$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$outside_class" --body-file "$dir/class.env"
assert_eq 1 "$RC" "21: issue-input-file rejects classification file outside tmpdir"
assert_contains "--classification-file outside implement tmpdir" "$(cat "$SANDBOX/case21-issue-classification-outside.out.err")" "21: issue-input-file outside tmpdir stderr"
rm -f "$outside_class"
dir=$(make_tmp case21-classification-symlink)
cp "$SANDBOX/case1.out" "$dir/real-class.env"
ln -s "$dir/real-class.env" "$dir/class.env"
run_capture "$SANDBOX/case21-classification-symlink.out" "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env"
assert_eq 1 "$RC" "21: bug-body rejects classification symlink"
assert_contains "--classification-file must not be a symlink" "$(cat "$SANDBOX/case21-classification-symlink.out.err")" "21: bug-body classification symlink stderr"

dir=$(make_tmp case21-body-outside)
cp "$SANDBOX/case1.out" "$dir/class.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
outside_body=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-body-outside.XXXXXX")
cp "$(kv BODY_FILE "$dir/body.out")" "$outside_body"
run_capture "$SANDBOX/case21-body-outside.out" "$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$outside_body"
assert_eq 1 "$RC" "21: issue-input-file rejects body file outside tmpdir"
assert_contains "--body-file outside implement tmpdir" "$(cat "$SANDBOX/case21-body-outside.out.err")" "21: issue-input-file outside tmpdir stderr"
rm -f "$outside_body"

dir=$(make_tmp case21-record-stress)
"$SCRIPT" init-attempts --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" >/dev/null
cp "$SANDBOX/case1.out" "$dir/class.env"
for i in 1 2 3 4 5 6 7 8 9 10; do
    "$SCRIPT" record-attempt --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env" --class transient-infra --signature "sig-$i" --resume-hint step8-shippr --outcome failed >/dev/null
done
assert_eq 10 "$(kv attempt_count "$dir/attempts.env")" "21: record-attempt stress count"
assert_contains "attempt.10.signature=sig-10" "$(cat "$dir/attempts.env")" "21: record-attempt stress preserves final append"

outside_out=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-output-outside.XXXXXX")
run_capture "$SANDBOX/case21-bugbody-out.out" "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" --output-file "$outside_out"
assert_eq 1 "$RC" "21: bug-body rejects output file outside tmpdir"
assert_contains "--output-file outside implement tmpdir" "$(cat "$SANDBOX/case21-bugbody-out.out.err")" "21: bug-body outside tmpdir stderr"
run_capture "$SANDBOX/case21-comment-out.out" "$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$dir/attempts.env" --output-file "$outside_out"
assert_eq 1 "$RC" "21: bug-comment rejects output file outside tmpdir"
assert_contains "--output-file outside implement tmpdir" "$(cat "$SANDBOX/case21-comment-out.out.err")" "21: bug-comment output outside tmpdir stderr"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
run_capture "$SANDBOX/case21-issue-out.out" "$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$(kv BODY_FILE "$dir/body.out")" --output-file "$outside_out"
assert_eq 1 "$RC" "21: issue-input-file rejects output file outside tmpdir"
assert_contains "--output-file outside implement tmpdir" "$(cat "$SANDBOX/case21-issue-out.out.err")" "21: issue-input-file output outside tmpdir stderr"
rm -f "$outside_out"

dir=$(make_tmp case22-clear-success)
write_state "$dir" 8 ci-initial "adopted-issue-closed" "BAIL_FAILURE_DETAIL_LOG=$dir/failure.log"
run_capture "$SANDBOX/case22-clear-success.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall success exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-success.out")" "22: clear-stall success emits CLEARED=true"
assert_eq false "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall sets STALL_TRACKING=false on disk"
if grep -q '^STALL_STEP=$' "$dir/ship-pr-state.sh"; then
    pass "22: clear-stall clears STALL_STEP on disk"
else
    fail "22: clear-stall clears STALL_STEP on disk"
fi
assert_eq ci-initial "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: clear-stall preserves PHASE"
assert_eq 4 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key EXIT_CODE --default "")" "22: clear-stall preserves EXIT_CODE"
assert_eq adopted-issue-closed "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key BAIL_REASON --default "")" "22: clear-stall preserves BAIL_REASON"
assert_eq "$dir/failure.log" "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key BAIL_FAILURE_DETAIL_LOG --default "")" "22: clear-stall preserves BAIL_FAILURE_DETAIL_LOG"

dir=$(make_tmp case22-clear-absent)
run_capture "$SANDBOX/case22-clear-absent.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall absent state exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-absent.out")" "22: clear-stall absent state emits CLEARED=true"
assert_eq false "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default missing)" "22: clear-stall absent state writes STALL_TRACKING=false"

dir=$(make_tmp case22-clear-malformed)
printf 'not valid\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-malformed.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: clear-stall malformed state exits 3"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-malformed.out")" "22: clear-stall malformed state emits CLEARED=false"

dir=$(make_tmp case22-clear-symlink)
printf 'PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=8\nBAIL_REASON=\nEXIT_CODE=4\n' >"$dir/ship-pr-state.real"
ln -s "$dir/ship-pr-state.real" "$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-symlink.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: clear-stall symlinked state exits 3"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-symlink.out")" "22: clear-stall symlinked state emits CLEARED=false"

dir=$(make_tmp case22-clear-append)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
EXIT_CODE=4
PR_URL=https://example.test/pr/1
EOF
run_capture "$SANDBOX/case22-clear-append.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-append.out")" "22: clear-stall append-when-absent emits CLEARED=true"
assert_eq false "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall append-when-absent writes STALL_TRACKING=false"
if grep -q '^STALL_STEP=$' "$dir/ship-pr-state.sh"; then
    pass "22: clear-stall append-when-absent writes empty STALL_STEP"
else
    fail "22: clear-stall append-when-absent writes empty STALL_STEP"
fi
assert_eq https://example.test/pr/1 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key PR_URL --default "")" "22: clear-stall append-when-absent preserves PR_URL"

dir=$(make_tmp case22-clear-empty)
: >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-empty.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall empty state exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-empty.out")" "22: clear-stall empty state emits CLEARED=true"
assert_eq false "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default missing)" "22: clear-stall empty state writes STALL_TRACKING=false"

dir=$(make_tmp case22-clear-comments)
printf '# comment only\n\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-comments.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall comment-only state exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-comments.out")" "22: clear-stall comment-only state emits CLEARED=true"
assert_eq false "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default missing)" "22: clear-stall comment-only state writes STALL_TRACKING=false"

dir=$(make_tmp case22-clear-mv-fail)
write_state "$dir" 8 ci-initial
before_clear=$(cat "$dir/ship-pr-state.sh")
fail_bin="$SANDBOX/fail-bin"
mkdir -p "$fail_bin"
cat >"$fail_bin/mv" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$fail_bin/mv"
run_capture "$SANDBOX/case22-clear-mv-fail.out" env PATH="$fail_bin:$PATH" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: clear-stall mv failure exits 1"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-mv-fail.out")" "22: clear-stall mv failure emits CLEARED=false"
assert_eq "$before_clear" "$(cat "$dir/ship-pr-state.sh")" "22: clear-stall mv failure leaves ship-pr-state.sh unchanged"
assert_eq true "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall mv failure leaves STALL_TRACKING=true on disk"

dir=$(make_tmp case22-seed-rewrite)
write_state "$dir" 8 ci-initial "first-fixer-non-health" "BAIL_FAILURE_DETAIL_LOG=$dir/failure.log"
run_capture "$SANDBOX/case22-seed-rewrite.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir" --stall-step 5 --phase review
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-rewrite.out")" "22: seed-terminal-state rewrite emits SEEDED=true"
assert_eq rewrite "$(kv SEED_MODE "$SANDBOX/case22-seed-rewrite.out")" "22: seed-terminal-state rewrite emits SEED_MODE=rewrite"
assert_eq true "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state rewrite keeps STALL_TRACKING=true"
assert_eq 5 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state rewrite refreshes STALL_STEP"
assert_eq review "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: seed-terminal-state rewrite refreshes PHASE"
assert_eq 4 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key EXIT_CODE --default "")" "22: seed-terminal-state rewrite preserves EXIT_CODE"
assert_eq first-fixer-non-health "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key BAIL_REASON --default "")" "22: seed-terminal-state rewrite preserves BAIL_REASON"
assert_eq "$dir/failure.log" "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key BAIL_FAILURE_DETAIL_LOG --default "")" "22: seed-terminal-state rewrite preserves BAIL_FAILURE_DETAIL_LOG"

dir=$(make_tmp case22-seed-empty)
: >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-seed-empty.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-empty.out")" "22: seed-terminal-state empty file emits SEEDED=true"
assert_eq seed "$(kv SEED_MODE "$SANDBOX/case22-seed-empty.out")" "22: seed-terminal-state empty file uses SEED_MODE=seed"
assert_eq true "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state empty file seeds STALL_TRACKING=true"

dir=$(make_tmp case22-seed-comments)
printf '# header\n\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-seed-comments.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir" --stall-step 5 --phase review
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-comments.out")" "22: seed-terminal-state comment-only file emits SEEDED=true"
assert_eq seed "$(kv SEED_MODE "$SANDBOX/case22-seed-comments.out")" "22: seed-terminal-state comment-only file uses SEED_MODE=seed"
assert_eq 5 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state comment-only file honors stall-step override"

dir=$(make_tmp case22-seed-fresh)
run_capture "$SANDBOX/case22-seed-fresh.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-fresh.out")" "22: seed-terminal-state fresh emits SEEDED=true"
assert_eq seed "$(kv SEED_MODE "$SANDBOX/case22-seed-fresh.out")" "22: seed-terminal-state fresh emits SEED_MODE=seed"
assert_eq true "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state fresh sets STALL_TRACKING=true"
assert_eq ci-initial "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: seed-terminal-state fresh seeds PHASE=ci-initial"
assert_eq 8 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state fresh seeds STALL_STEP=8"
assert_eq 4 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key EXIT_CODE --default "")" "22: seed-terminal-state fresh seeds EXIT_CODE=4"
if grep -q '^BAIL_REASON=$' "$dir/ship-pr-state.sh"; then
    pass "22: seed-terminal-state fresh seeds empty BAIL_REASON"
else
    fail "22: seed-terminal-state fresh seeds empty BAIL_REASON"
fi
if grep -q '^BAIL_FAILURE_DETAIL_LOG=$' "$dir/ship-pr-state.sh"; then
    pass "22: seed-terminal-state fresh seeds empty BAIL_FAILURE_DETAIL_LOG"
else
    fail "22: seed-terminal-state fresh seeds empty BAIL_FAILURE_DETAIL_LOG"
fi

dir=$(make_tmp case22-seed-symlink)
printf 'PHASE=ci-initial\nSTALL_TRACKING=true\nSTALL_STEP=8\nBAIL_REASON=\nEXIT_CODE=4\n' >"$dir/ship-pr-state.real"
ln -s "$dir/ship-pr-state.real" "$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-seed-symlink.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: seed-terminal-state symlinked state exits 3"
assert_eq false "$(kv SEEDED "$SANDBOX/case22-seed-symlink.out")" "22: seed-terminal-state symlinked state emits SEEDED=false"

dir=$(make_tmp case22-seed-malformed)
printf 'bad line\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-seed-malformed.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: seed-terminal-state malformed state exits 3"
assert_eq false "$(kv SEEDED "$SANDBOX/case22-seed-malformed.out")" "22: seed-terminal-state malformed state emits SEEDED=false"

dir=$(make_tmp case22-seed-mv-fail)
write_state "$dir" 8 ci-initial
before_seed=$(cat "$dir/ship-pr-state.sh")
fail_bin="$SANDBOX/fail-bin-seed"
mkdir -p "$fail_bin"
cat >"$fail_bin/mv" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$fail_bin/mv"
run_capture "$SANDBOX/case22-seed-mv-fail.out" env PATH="$fail_bin:$PATH" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: seed-terminal-state mv failure exits 1"
assert_eq false "$(kv SEEDED "$SANDBOX/case22-seed-mv-fail.out")" "22: seed-terminal-state mv failure emits SEEDED=false"
assert_eq "$before_seed" "$(cat "$dir/ship-pr-state.sh")" "22: seed-terminal-state mv failure leaves ship-pr-state.sh unchanged"
assert_eq true "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state mv failure leaves STALL_TRACKING=true on disk"

noop_mv_bin="$SANDBOX/noop-mv-bin"
mkdir -p "$noop_mv_bin"
cat >"$noop_mv_bin/mv" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$noop_mv_bin/mv"

dir=$(make_tmp case22-clear-temp-assert-fail)
write_state "$dir" 8 ci-initial
before_clear=$(cat "$dir/ship-pr-state.sh")
fail_mktemp_bin="$SANDBOX/fail-mktemp-bin"
mkdir -p "$fail_mktemp_bin"
cat >"$fail_mktemp_bin/mktemp" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
chmod +x "$fail_mktemp_bin/mktemp"
run_capture "$SANDBOX/case22-clear-temp-assert-fail.out" env PATH="$fail_mktemp_bin:$PATH" \
  "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: clear-stall temp write failure exits 1"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-temp-assert-fail.out")" "22: clear-stall temp write failure emits CLEARED=false"
assert_eq "$before_clear" "$(cat "$dir/ship-pr-state.sh")" "22: clear-stall temp write failure leaves disk unchanged"

dir=$(make_tmp case22-clear-dest-assert-fail)
write_state "$dir" 8 ci-initial
before_clear=$(cat "$dir/ship-pr-state.sh")
run_capture "$SANDBOX/case22-clear-dest-assert-fail.out" env PATH="$noop_mv_bin:$PATH" \
  "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: clear-stall destination assert failure exits 1"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-dest-assert-fail.out")" "22: clear-stall destination assert failure emits CLEARED=false"
assert_eq "$before_clear" "$(cat "$dir/ship-pr-state.sh")" "22: clear-stall destination assert failure leaves disk unchanged"

read_stub_root="$SANDBOX/read-stub-plugin"
mkdir -p "$read_stub_root/skills/implement/scripts" "$read_stub_root/scripts"
cp "$SCRIPT" "$read_stub_root/skills/implement/scripts/stall-recovery-report.sh"
cp "$SCRIPT_DIR/stall-recovery-report-allowlists.tsv" "$read_stub_root/skills/implement/scripts/"
cp "$SCRIPT_DIR/stall-recovery-report.md" "$read_stub_root/skills/implement/scripts/"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$read_stub_root/scripts/"
cp "$REPO_ROOT/scripts/lib-larch-dev-clone.sh" "$read_stub_root/scripts/"
cp "$REPO_ROOT/scripts/read-session-env-key.sh" "$read_stub_root/scripts/read-session-env-key.real.sh"
chmod +x "$read_stub_root/skills/implement/scripts/stall-recovery-report.sh" \
  "$read_stub_root/scripts/read-session-env-key.real.sh"
cat >"$read_stub_root/scripts/read-session-env-key.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
stub_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
real="$stub_dir/read-session-env-key.real.sh"
args=("$@")
file="" key=""
index=0
while [ "$index" -lt "${#args[@]}" ]; do
  case "${args[$index]}" in
    --file) index=$((index + 1)); file=${args[$index]:-} ;;
    --key) index=$((index + 1)); key=${args[$index]:-} ;;
  esac
  index=$((index + 1))
done
case "${STALL_READ_STUB:-}" in
  temp-wrong)
    case "$file" in
      *.tmp.*)
        if [ "$key" = STALL_TRACKING ]; then
          printf '%s\n' true
          exit 0
        fi
        ;;
    esac
    ;;
  dest-fail)
    case "$file" in
      *.tmp.*) ;;
      *)
        if [ "$key" = STALL_TRACKING ]; then
          exit 1
        fi
        ;;
    esac
    ;;
esac
exec "$real" "${args[@]}"
STUB
chmod +x "$read_stub_root/scripts/read-session-env-key.sh"
read_stub_script="$read_stub_root/skills/implement/scripts/stall-recovery-report.sh"

dir=$(make_tmp case22-clear-temp-read-wrong)
write_state "$dir" 8 ci-initial
before_clear=$(cat "$dir/ship-pr-state.sh")
run_capture "$SANDBOX/case22-clear-temp-read-wrong.out" env \
  CLAUDE_PLUGIN_ROOT="$read_stub_root" STALL_READ_STUB=temp-wrong \
  "$read_stub_script" clear-stall --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: clear-stall temp read wrong value exits 1"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-temp-read-wrong.out")" "22: clear-stall temp read wrong value emits CLEARED=false"
assert_eq "$before_clear" "$(cat "$dir/ship-pr-state.sh")" "22: clear-stall temp read wrong value leaves disk unchanged"

dir=$(make_tmp case22-clear-dest-read-fail)
write_state "$dir" 8 ci-initial
before_clear=$(cat "$dir/ship-pr-state.sh")
run_capture "$SANDBOX/case22-clear-dest-read-fail.out" env \
  CLAUDE_PLUGIN_ROOT="$read_stub_root" STALL_READ_STUB=dest-fail \
  "$read_stub_script" clear-stall --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: clear-stall destination read failure exits 1"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-dest-read-fail.out")" "22: clear-stall destination read failure emits CLEARED=false"
assert_eq false "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall destination read failure exercises post-mv assertion"

dir=$(make_tmp case22-seed-dest-read-fail)
write_state "$dir" 8 ci-initial
before_seed=$(cat "$dir/ship-pr-state.sh")
run_capture "$SANDBOX/case22-seed-dest-read-fail.out" env \
  CLAUDE_PLUGIN_ROOT="$read_stub_root" STALL_READ_STUB=dest-fail \
  "$read_stub_script" seed-terminal-state --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: seed-terminal-state destination read failure exits 1"
assert_eq false "$(kv SEEDED "$SANDBOX/case22-seed-dest-read-fail.out")" "22: seed-terminal-state destination read failure emits SEEDED=false"
assert_eq "$before_seed" "$(cat "$dir/ship-pr-state.sh")" "22: seed-terminal-state destination read failure leaves disk unchanged"

dir=$(make_tmp case22-seed-temp-assert-fail)
write_state "$dir" 8 ci-initial
before_seed=$(cat "$dir/ship-pr-state.sh")
run_capture "$SANDBOX/case22-seed-temp-assert-fail.out" env PATH="$fail_mktemp_bin:$PATH" \
  "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: seed-terminal-state temp write failure exits 1"
assert_eq false "$(kv SEEDED "$SANDBOX/case22-seed-temp-assert-fail.out")" "22: seed-terminal-state temp write failure emits SEEDED=false"
assert_eq "$before_seed" "$(cat "$dir/ship-pr-state.sh")" "22: seed-terminal-state temp write failure leaves disk unchanged"

dir=$(make_tmp case22-seed-dest-assert-fail)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=false
STALL_STEP=8
BAIL_REASON=
EXIT_CODE=4
EOF
before_seed=$(cat "$dir/ship-pr-state.sh")
run_capture "$SANDBOX/case22-seed-dest-assert-fail.out" env PATH="$noop_mv_bin:$PATH" \
  "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq 1 "$RC" "22: seed-terminal-state destination assert failure exits 1"
assert_eq false "$(kv SEEDED "$SANDBOX/case22-seed-dest-assert-fail.out")" "22: seed-terminal-state destination assert failure emits SEEDED=false"
assert_eq "$before_seed" "$(cat "$dir/ship-pr-state.sh")" "22: seed-terminal-state destination assert failure leaves disk unchanged"

dir=$(make_tmp case22-classify-empty-state)
printf 'STALL_TRACKING=true\nSTALL_STEP=8\n' >"$dir/session-env.sh"
: >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-classify-empty-state.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: classify empty ship-pr-state.sh exits 0"
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case22-classify-empty-state.out")" "22: classify empty ship-pr-state.sh falls back to session-env"

dir=$(make_tmp case22-classify-comments-state)
printf 'STALL_TRACKING=true\nSTALL_STEP=5\nPHASE=review\n' >"$dir/session-env.sh"
printf '# comment only\n\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-classify-comments-state.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: classify comment-only ship-pr-state.sh exits 0"
assert_eq true "$(kv STALL_TRACKING "$SANDBOX/case22-classify-comments-state.out")" "22: classify comment-only ship-pr-state.sh falls back to session-env"
assert_eq 5 "$(kv STALL_STEP "$SANDBOX/case22-classify-comments-state.out")" "22: classify comment-only ship-pr-state.sh uses session STALL_STEP"
assert_eq review "$(kv PHASE "$SANDBOX/case22-classify-comments-state.out")" "22: classify comment-only ship-pr-state.sh uses session PHASE"

dir=$(make_tmp case22-classify-empty-session-false)
printf 'STALL_TRACKING=false\nSTALL_STEP=99\n' >"$dir/session-env.sh"
: >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-classify-empty-session-false.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case22-classify-empty-session-false.out")" "22: classify keyless ship-pr-state with session STALL_TRACKING=false is unrecoverable"
assert_eq false "$(kv STALL_TRACKING "$SANDBOX/case22-classify-empty-session-false.out")" "22: classify keyless ship-pr-state with session STALL_TRACKING=false emits false"

dir=$(make_tmp case22-seed-awk-metachar)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial; print "pwned"
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=
EXIT_CODE=4
EOF
run_capture "$SANDBOX/case22-seed-awk-metachar.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir" --stall-step 5 --phase review
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-awk-metachar.out")" "22: seed-terminal-state rewrite sanitizes metacharacter PHASE from disk"
assert_eq review "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: seed-terminal-state rewrite applies sanitized phase override"
assert_eq 5 "$("$SCRIPTS_DIR/read-session-env-key.sh" --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state rewrite applies stall-step override on metachar disk"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
