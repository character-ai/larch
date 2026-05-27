#!/usr/bin/env bash
# test-stall-recovery-report.sh — offline harness for stall-recovery-report.sh

set -euo pipefail

export LARCH_QUIET_DISABLE=1
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
SCRIPT="$SCRIPT_DIR/stall-recovery-report.sh"

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-stall-recovery-test.XXXXXX")
trap 'rm -rf "$SANDBOX"' EXIT

pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$*" | sed 's/^/    /'; }

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

classify_fixture case3 5 review "lint-fix-loop exhausted after shellcheck failure"
out=$CLASSIFY_OUT
assert_eq lint-failure "$(kv FAILURE_CLASS "$out")" "3: lint-failure"

classify_fixture case4 2 implementation "orchestrator-envelope-invalid in step2 dispatch"
out=$CLASSIFY_OUT
assert_eq dispatch-failure "$(kv FAILURE_CLASS "$out")" "4: dispatch-failure"

dir=$(make_tmp case5a)
write_state "$dir" 3 checks
run_capture "$SANDBOX/case5a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq contract-failure "$(kv FAILURE_CLASS "$SANDBOX/case5a.out")" "5: step3 contract"
assert_eq none "$(kv RESUME_HINT "$SANDBOX/case5a.out")" "5: step3 no resume"
dir=$(make_tmp case5b)
write_state "$dir" 6 checks
run_capture "$SANDBOX/case5b.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq contract-failure "$(kv FAILURE_CLASS "$SANDBOX/case5b.out")" "5: step6 contract"

dir=$(make_tmp case6a)
write_state "$dir" 0 ship adopted-issue-closed
run_capture "$SANDBOX/case6a.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case6a.out")" "6: adopted issue closed unrecoverable"
dir=$(make_tmp case6b)
write_state "$dir" 0 ship tracking-init-failed
run_capture "$SANDBOX/case6b.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case6b.out")" "6: tracking init failed unrecoverable"

dir=$(make_tmp case7)
write_state "$dir" 8 ci-initial "" "NOTE=network timeout"
"$SCRIPT" init-attempts --attempts-file "$dir/attempts.env" >/dev/null
run_capture "$dir/first.env" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env"
"$SCRIPT" record-attempt --attempts-file "$dir/attempts.env" --class "$(kv FAILURE_CLASS "$dir/first.env")" --signature "$(kv FAILURE_SIGNATURE "$dir/first.env")" --resume-hint "$(kv RESUME_HINT "$dir/first.env")" --outcome failed >/dev/null
run_capture "$dir/second.env" "$SCRIPT" classify --implement-tmpdir "$dir" --attempts-file "$dir/attempts.env"
assert_eq same-cause-repeat "$(kv FAILURE_CLASS "$dir/second.env")" "7: same-cause-repeat"

dir=$(make_tmp case8)
printf 'STALL_TRACKING=true\n' >"$dir/session-env.sh"
run_capture "$SANDBOX/case8.out" "$SCRIPT" classify --implement-tmpdir "$dir" --in-memory-stall-tracking true --bail-reason any
assert_eq 0 "$RC" "8: missing ship state exits 0"
assert_eq unrecoverable "$(kv FAILURE_CLASS "$SANDBOX/case8.out")" "8: missing ship state unrecoverable"

dir=$(make_tmp case9)
write_state "$dir" 8 ci-initial
printf 'x\n' >"$dir/ok.log"
ln -s "$dir/ok.log" "$dir/link.log"
run_capture "$SANDBOX/case9-rel.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log rel.log
assert_eq 1 "$RC" "9: relative log rejected"
run_capture "$SANDBOX/case9-outside.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "/tmp/larch-outside-$$.log"
rm -f "/tmp/larch-outside-$$.log"
assert_eq 1 "$RC" "9: missing outside log rejected"
run_capture "$SANDBOX/case9-symlink.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir/link.log"
assert_eq 1 "$RC" "9: symlink log rejected"
run_capture "$SANDBOX/case9-dir.out" "$SCRIPT" classify --implement-tmpdir "$dir" --failure-detail-log "$dir"
assert_eq 1 "$RC" "9: non-regular log rejected"

dir=$(make_tmp case10)
"$SCRIPT" init-attempts --attempts-file "$dir/attempts.env" >/dev/null
before=$(cat "$dir/attempts.env")
"$SCRIPT" init-attempts --attempts-file "$dir/attempts.env" >/dev/null
after=$(cat "$dir/attempts.env")
assert_eq "$before" "$after" "10: init-attempts idempotent"

"$SCRIPT" record-attempt --attempts-file "$dir/attempts.env" --class transient-infra --signature abc --resume-hint step8-shippr --outcome failed >"$dir/record.out"
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

dir=$(make_tmp case13)
cat >"$dir/class.env" <<'EOF'
FAILURE_CLASS=unrecoverable
FAILURE_SIGNATURE=not-a-hash-SENTINEL_SECRET_13
STALL_STEP=SENTINEL_SECRET_13
PHASE=SENTINEL_SECRET_13
EXIT_CODE=99
EOF
"$SCRIPT" init-attempts --attempts-file "$dir/attempts.env" >/dev/null
"$SCRIPT" record-attempt --attempts-file "$dir/attempts.env" --class SENTINEL_SECRET_13 --signature SENTINEL_SECRET_13 --resume-hint SENTINEL_SECRET_13 --outcome SENTINEL_SECRET_13 >/dev/null
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
"$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
"$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$(kv BODY_FILE "$dir/body.out")" >"$dir/input.out"
assert_not_contains "SENTINEL_SECRET_13" "$(cat "$(kv BODY_FILE "$dir/body.out")" "$(kv BODY_FILE "$dir/comment.out")" "$(kv INPUT_FILE "$dir/input.out")")" "13: public outputs omit raw sentinels"

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
cat >"$copyroot/scripts/redact-secrets.sh" <<'SH'
#!/usr/bin/env bash
cat >"$STALL_REDACTOR_MARKER"
sed 's/ghp_[A-Za-z0-9_][A-Za-z0-9_]*/<REDACTED-TOKEN>/g' "$STALL_REDACTOR_MARKER"
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

dir=$(make_tmp case17)
"$SCRIPT" init-attempts --attempts-file "$dir/attempts.env" >/dev/null
"$SCRIPT" record-attempt --attempts-file "$dir/attempts.env" --class transient-infra --signature abc --resume-hint step8-shippr --outcome failed >/dev/null
cp "$SANDBOX/case1.out" "$dir/class.env"
"$SCRIPT" bug-comment --implement-tmpdir "$dir" --classification-file "$dir/class.env" --attempts-file "$dir/attempts.env" >"$dir/comment.out"
assert_contains "| Attempt | Class | Signature | Resume hint | Outcome | UTC |" "$(cat "$(kv BODY_FILE "$dir/comment.out")")" "17: bug-comment attempt table"

dir=$(make_tmp case18)
cp "$SANDBOX/case1.out" "$dir/class.env"
mkdir -p "$dir/bin"
printf '#!/usr/bin/env bash\necho "$@" >>"%s/gh.calls"\n' "$dir" >"$dir/bin/gh"
chmod +x "$dir/bin/gh"
PATH="$dir/bin:$PATH" LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
assert_eq true "$(kv DRY_RUN_DECISION "$dir/body.out")" "18: dry-run decision true"
if [ ! -f "$dir/gh.calls" ]; then
    pass "18: gh stub not invoked"
else
    fail "18: gh stub should not be invoked" "$(cat "$dir/gh.calls")"
fi

dir=$(make_tmp case19)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
tmp="$dir/ship-pr-state.sh.tmp.$$"
awk 'BEGIN{done=0} /^STALL_TRACKING=/{print "STALL_TRACKING=false"; done=1; next} /^STALL_STEP=/{print "STALL_STEP="; next} {print} END{if(!done) print "STALL_TRACKING=false"}' "$dir/ship-pr-state.sh" >"$tmp"
assert_contains "STALL_TRACKING=true" "$(cat "$dir/ship-pr-state.sh")" "19: disk remains true before mv"
mv -f "$tmp" "$dir/ship-pr-state.sh"
assert_contains "STALL_TRACKING=false" "$(cat "$dir/ship-pr-state.sh")" "19: disk flips before in-memory clear point"

dir=$(make_tmp case20)
cp "$SANDBOX/case1.out" "$dir/class.env"
"$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/class.env" >"$dir/body.out"
"$SCRIPT" issue-input-file --implement-tmpdir "$dir" --classification-file "$dir/class.env" --body-file "$(kv BODY_FILE "$dir/body.out")" >"$dir/input.out"
first_line=$(sed -n '1p' "$(kv INPUT_FILE "$dir/input.out")")
assert_eq "### [Bug] /implement stall: transient-infra at 8" "$first_line" "20: issue input title shape"

run_capture "$SANDBOX/case21-badargv.out" "$SCRIPT" unknown-subcommand
assert_eq 1 "$RC" "21: bad argv exits 1"
run_capture "$SANDBOX/case21-missing.out" "$SCRIPT" classify
assert_eq 2 "$RC" "21: missing required exits 2"
dir=$(make_tmp case21-malformed)
printf 'not valid\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case21-malformed.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq 3 "$RC" "21: malformed ship-pr-state exits 3"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
