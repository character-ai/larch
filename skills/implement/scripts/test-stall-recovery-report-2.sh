#!/usr/bin/env bash
# test-stall-recovery-report-2.sh — offline harness for stall-recovery-report.sh (part 2 of 3)

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


# Regenerate case1.out needed as a classification fixture by case21 path-containment tests.
classify_fixture case1 8 ci-initial "gh: API rate limit exceeded"

dir=$(make_tmp case20m-normalize-create)
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_NUMBER=123
ISSUE_1_URL=https://github.com/example/repo/issues/123
ISSUE_1_TITLE=created title with spaces
EOF
run_capture "$SANDBOX/case20m-normalize-create.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq 0 "$RC" "20: normalize create exits 0"
assert_eq true "$(kv NORMALIZED "$SANDBOX/case20m-normalize-create.out")" "20: normalize create emits true"
assert_eq 123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_NUMBER --default "")" "20: normalize create writes canonical ISSUE_NUMBER"
assert_eq https://github.com/example/repo/issues/123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_URL --default "")" "20: normalize create writes canonical ISSUE_URL"
assert_eq "" "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_1_TITLE --default "")" "20: normalize create strips raw ISSUE_1 metadata"
assert_eq "" "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_1_URL --default "")" "20: normalize create strips source ISSUE_1_URL"


dir=$(make_tmp case20m2-normalize-newline-injection)
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_NUMBER=123
ISSUE_1_URL=https://github.com/example/repo/issues/123
INJECTED=bad
EOF
run_capture "$SANDBOX/case20m2-normalize-newline-injection.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq true "$(kv NORMALIZED "$SANDBOX/case20m2-normalize-newline-injection.out")" "20: normalize newline-injected URL emits true"
assert_eq 123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_NUMBER --default "")" "20: normalize newline-injected URL keeps issue number"
assert_eq https://github.com/example/repo/issues/123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_URL --default "")" "20: normalize newline-injected URL keeps canonical URL"
assert_eq "" "$(read_session_key --file "$dir/stall-recovery-issue.env" --key INJECTED --default "")" "20: normalize newline-injected URL drops injected key"

dir=$(make_tmp case20m3-normalize-carriage-injection)
printf 'ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUES_DEDUPLICATED=0\nISSUE_1_NUMBER=123\nISSUE_1_URL=https://github.com/example/repo/issues/123\rINJECTED=bad\n' >"$dir/issue.out"
run_capture "$SANDBOX/case20m3-normalize-carriage-injection.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq true "$(kv NORMALIZED "$SANDBOX/case20m3-normalize-carriage-injection.out")" "20: normalize carriage-injected URL emits true"
assert_eq https://github.com/example/repo/issues/123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_URL --default "")" "20: normalize carriage-injected URL keeps canonical URL"
assert_eq "" "$(read_session_key --file "$dir/stall-recovery-issue.env" --key INJECTED --default "")" "20: normalize carriage-injected URL drops injected key"

dir=$(make_tmp case20n-normalize-dedup)
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=0
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=1
ISSUE_1_DUPLICATE=true
ISSUE_1_DUPLICATE_OF_NUMBER=456
ISSUE_1_DUPLICATE_OF_URL=https://github.com/example/repo/issues/456
EOF
run_capture "$SANDBOX/case20n-normalize-dedup.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq true "$(kv NORMALIZED "$SANDBOX/case20n-normalize-dedup.out")" "20: normalize dedup emits true"
assert_eq 456 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_NUMBER --default "")" "20: normalize dedup writes duplicate canonical ISSUE_NUMBER"
assert_eq https://github.com/example/repo/issues/456 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_URL --default "")" "20: normalize dedup writes duplicate canonical ISSUE_URL"

dir=$(make_tmp case20n2-normalize-dedup-invalid-url-keeps-create)
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=1
ISSUE_1_NUMBER=123
ISSUE_1_URL=https://github.com/example/repo/issues/123
ISSUE_1_DUPLICATE=true
ISSUE_1_DUPLICATE_OF_NUMBER=456
ISSUE_1_DUPLICATE_OF_URL=not-a-url
EOF
run_capture "$SANDBOX/case20n2-normalize-dedup-invalid-url-keeps-create.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq true "$(kv NORMALIZED "$SANDBOX/case20n2-normalize-dedup-invalid-url-keeps-create.out")" "20: normalize invalid dedup URL keeps valid create metadata"
assert_eq 123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_NUMBER --default "")" "20: normalize invalid dedup URL keeps create ISSUE_NUMBER"
assert_eq https://github.com/example/repo/issues/123 "$(read_session_key --file "$dir/stall-recovery-issue.env" --key ISSUE_URL --default "")" "20: normalize invalid dedup URL keeps create ISSUE_URL"

dir=$(make_tmp case20n3-normalize-dedup-missing-url)
printf 'ISSUE_NUMBER=stale\n' >"$dir/stall-recovery-issue.env"
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=0
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=1
ISSUE_1_DUPLICATE=true
ISSUE_1_DUPLICATE_OF_NUMBER=456
ISSUE_1_DUPLICATE_OF_URL=not-a-url
EOF
run_capture "$SANDBOX/case20n3-normalize-dedup-missing-url.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq false "$(kv NORMALIZED "$SANDBOX/case20n3-normalize-dedup-missing-url.out")" "20: normalize dedup without valid URL emits false"
assert_eq issue-url-missing "$(kv REASON "$SANDBOX/case20n3-normalize-dedup-missing-url.out")" "20: normalize dedup without valid URL reports missing URL"
if [ ! -e "$dir/stall-recovery-issue.env" ]; then
    pass "20: normalize dedup without valid URL removes stale env"
else
    fail "20: normalize dedup without valid URL removes stale env" "$(cat "$dir/stall-recovery-issue.env")"
fi

dir=$(make_tmp case20o-normalize-failure)
printf 'ISSUE_NUMBER=stale\n' >"$dir/stall-recovery-issue.env"
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=0
ISSUES_FAILED=1
ISSUES_DEDUPLICATED=0
ISSUE_1_FAILED=true
ISSUE_1_ERROR=network
EOF
run_capture "$SANDBOX/case20o-normalize-failure.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq 0 "$RC" "20: normalize failed issue exits 0"
assert_eq false "$(kv NORMALIZED "$SANDBOX/case20o-normalize-failure.out")" "20: normalize failed issue emits false"
assert_eq issues-failed-nonzero "$(kv REASON "$SANDBOX/case20o-normalize-failure.out")" "20: normalize failed issue reports failed counter"
if [ ! -e "$dir/stall-recovery-issue.env" ]; then
    pass "20: normalize failed issue removes stale env"
else
    fail "20: normalize failed issue removes stale env" "$(cat "$dir/stall-recovery-issue.env")"
fi

dir=$(make_tmp case20p-normalize-item-failure)
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_FAILED=true
ISSUE_1_NUMBER=789
ISSUE_1_URL=https://github.com/example/repo/issues/789
EOF
run_capture "$SANDBOX/case20p-normalize-item-failure.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq false "$(kv NORMALIZED "$SANDBOX/case20p-normalize-item-failure.out")" "20: normalize item failure emits false"
assert_eq issue-1-failed "$(kv REASON "$SANDBOX/case20p-normalize-item-failure.out")" "20: normalize item failure reports item failure"
if [ ! -e "$dir/stall-recovery-issue.env" ]; then
    pass "20: normalize item failure omits env"
else
    fail "20: normalize item failure omits env" "$(cat "$dir/stall-recovery-issue.env")"
fi

dir=$(make_tmp case20q-normalize-exit-failure)
printf 'ISSUE_NUMBER=stale\n' >"$dir/stall-recovery-issue.env"
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_NUMBER=999
ISSUE_1_URL=https://github.com/example/repo/issues/999
EOF
run_capture "$SANDBOX/case20q-normalize-exit-failure.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 2
assert_eq false "$(kv NORMALIZED "$SANDBOX/case20q-normalize-exit-failure.out")" "20: normalize issue nonzero exit emits false"
assert_eq issue-exit-code "$(kv REASON "$SANDBOX/case20q-normalize-exit-failure.out")" "20: normalize issue nonzero exit reports reason"
if [ ! -e "$dir/stall-recovery-issue.env" ]; then
    pass "20: normalize issue nonzero exit removes stale env"
else
    fail "20: normalize issue nonzero exit removes stale env" "$(cat "$dir/stall-recovery-issue.env")"
fi

dir=$(make_tmp case20r-normalize-missing-exit-code)
printf 'ISSUE_NUMBER=stale\n' >"$dir/stall-recovery-issue.env"
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_NUMBER=999
ISSUE_1_URL=https://github.com/example/repo/issues/999
EOF
run_capture "$SANDBOX/case20r-normalize-missing-exit-code.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out"
assert_eq 0 "$RC" "20: normalize missing issue exit code exits 0"
assert_eq false "$(kv NORMALIZED "$SANDBOX/case20r-normalize-missing-exit-code.out")" "20: normalize missing issue exit code emits false"
assert_eq issue-exit-code-missing "$(kv REASON "$SANDBOX/case20r-normalize-missing-exit-code.out")" "20: normalize missing issue exit code reports reason"
if [ ! -e "$dir/stall-recovery-issue.env" ]; then
    pass "20: normalize missing issue exit code removes stale env"
else
    fail "20: normalize missing issue exit code removes stale env" "$(cat "$dir/stall-recovery-issue.env")"
fi

dir=$(make_tmp case20s-normalize-write-failed)
stub_bin="$dir/stub-bin"
mkdir -p "$stub_bin"
cat >"$stub_bin/mktemp" <<'EOF'
#!/usr/bin/env bash
count_file=${LARCH_MKTEMP_STUB_COUNT:?}
template=${1:?}
count=$(cat "$count_file" 2>/dev/null || printf '0')
count=$((count + 1))
printf '%s\n' "$count" >"$count_file"
if [ "$count" -eq 2 ]; then
    exit 1
fi
path=${template%XXXXXX}stub$count
: >"$path" || exit 1
printf '%s\n' "$path"
EOF
chmod +x "$stub_bin/mktemp"
printf 'ISSUE_NUMBER=stale\n' >"$dir/stall-recovery-issue.env"
cat >"$dir/issue.out" <<'EOF'
ISSUES_CREATED=1
ISSUES_FAILED=0
ISSUES_DEDUPLICATED=0
ISSUE_1_NUMBER=999
ISSUE_1_URL=https://github.com/example/repo/issues/999
EOF
PATH="$stub_bin:$PATH" LARCH_MKTEMP_STUB_COUNT="$dir/mktemp.count" run_capture "$SANDBOX/case20s-normalize-write-failed.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0
assert_eq 0 "$RC" "20: normalize write failure exits 0"
assert_eq false "$(kv NORMALIZED "$SANDBOX/case20s-normalize-write-failed.out")" "20: normalize write failure emits false"
assert_eq write-failed "$(kv REASON "$SANDBOX/case20s-normalize-write-failed.out")" "20: normalize write failure reports reason"
if [ ! -e "$dir/stall-recovery-issue.env" ]; then
    pass "20: normalize write failure removes stale env"
else
    fail "20: normalize write failure removes stale env" "$(cat "$dir/stall-recovery-issue.env")"
fi

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

dir=$(make_tmp case21-normalize-issue-stdout-outside)
outside_stdout=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-normalize-stdout-outside.XXXXXX")
printf 'ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUES_DEDUPLICATED=0\nISSUE_1_NUMBER=1\nISSUE_1_URL=https://github.com/x/y/issues/1\n' >"$outside_stdout"
run_capture "$SANDBOX/case21-normalize-issue-stdout-outside.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$outside_stdout" --issue-exit-code 0
assert_eq 1 "$RC" "21: normalize-issue-env rejects issue-stdout-file outside tmpdir"
assert_contains "--issue-stdout-file outside implement tmpdir" "$(cat "$SANDBOX/case21-normalize-issue-stdout-outside.out.err")" "21: normalize-issue-env outside stdout stderr"
rm -f "$outside_stdout"
outside_normalize_out=$(mktemp "${TMPDIR:-/tmp}/stall-recovery-normalize-out-outside.XXXXXX")
printf 'ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUES_DEDUPLICATED=0\nISSUE_1_NUMBER=1\nISSUE_1_URL=https://github.com/x/y/issues/1\n' >"$dir/issue.out"
run_capture "$SANDBOX/case21-normalize-output-outside.out" "$SCRIPT" normalize-issue-env --implement-tmpdir "$dir" --issue-stdout-file "$dir/issue.out" --issue-exit-code 0 --output-file "$outside_normalize_out"
assert_eq 1 "$RC" "21: normalize-issue-env rejects output-file outside tmpdir"
assert_contains "--output-file outside implement tmpdir" "$(cat "$SANDBOX/case21-normalize-output-outside.out.err")" "21: normalize-issue-env outside output stderr"
rm -f "$outside_normalize_out"

dir=$(make_tmp case22-clear-success)
write_state "$dir" 8 ci-initial "adopted-issue-closed" "BAIL_FAILURE_DETAIL_LOG=$dir/failure.log"
run_capture "$SANDBOX/case22-clear-success.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall success exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-success.out")" "22: clear-stall success emits CLEARED=true"
assert_eq false "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall sets STALL_TRACKING=false on disk"
if grep -q '^STALL_STEP=$' "$dir/ship-pr-state.sh"; then
    pass "22: clear-stall clears STALL_STEP on disk"
else
    fail "22: clear-stall clears STALL_STEP on disk"
fi
assert_eq ci-initial "$(read_session_key --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: clear-stall preserves PHASE"
assert_eq 4 "$(read_session_key --file "$dir/ship-pr-state.sh" --key EXIT_CODE --default "")" "22: clear-stall preserves EXIT_CODE"
assert_eq adopted-issue-closed "$(read_session_key --file "$dir/ship-pr-state.sh" --key BAIL_REASON --default "")" "22: clear-stall preserves BAIL_REASON"
assert_eq "$dir/failure.log" "$(read_session_key --file "$dir/ship-pr-state.sh" --key BAIL_FAILURE_DETAIL_LOG --default "")" "22: clear-stall preserves BAIL_FAILURE_DETAIL_LOG"

dir=$(make_tmp case22-clear-absent)
run_capture "$SANDBOX/case22-clear-absent.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall absent state exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-absent.out")" "22: clear-stall absent state emits CLEARED=true"
if [ ! -e "$dir/ship-pr-state.sh" ]; then
    pass "22: clear-stall absent state skips optional ship-pr-state.sh"
else
    fail "22: clear-stall absent state should not create ship-pr-state.sh" "$(cat "$dir/ship-pr-state.sh")"
fi


dir=$(make_tmp case22-clear-all-layers)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
MERGE_RESULT=merged
EOF
cat >"$dir/finalize-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
EOF
cat >"$dir/session-env.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
run_capture "$SANDBOX/case22-clear-all-layers.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall all layers exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-all-layers.out")" "22: clear-stall all layers emits CLEARED=true"
for layer in ship-pr-state.sh finalize-state.sh session-env.sh; do
    assert_eq false "$(read_session_key --file "$dir/$layer" --key STALL_TRACKING --default "")" "22: clear-stall clears $layer STALL_TRACKING"
    if grep -q '^STALL_STEP=$' "$dir/$layer"; then
        pass "22: clear-stall clears $layer STALL_STEP"
    else
        fail "22: clear-stall clears $layer STALL_STEP"
    fi
done
run_capture "$SANDBOX/case22-clear-normalize-false.out" "$SCRIPT" normalize-outcome --implement-tmpdir "$dir" --in-memory-stall-tracking false
assert_eq merged "$(kv IMPLEMENT_NORMALIZED_OUTCOME "$SANDBOX/case22-clear-normalize-false.out")" "22: normalize-outcome succeeds after explicit recovery clear"
assert_eq true "$(kv IMPLEMENT_OUTCOME_SUCCEEDED "$SANDBOX/case22-clear-normalize-false.out")" "22: normalize-outcome success after durable clear"
run_capture "$SANDBOX/case22-clear-normalize-true.out" "$SCRIPT" normalize-outcome --implement-tmpdir "$dir" --in-memory-stall-tracking true
assert_eq stalled "$(kv IMPLEMENT_NORMALIZED_OUTCOME "$SANDBOX/case22-clear-normalize-true.out")" "22: normalize-outcome still honors ambient memory stall"

dir=$(make_tmp case22-clear-finalize-symlink)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
printf 'STALL_TRACKING=true\nSTALL_STEP=8\n' >"$dir/finalize.real"
ln -s "$dir/finalize.real" "$dir/finalize-state.sh"
run_capture "$SANDBOX/case22-clear-finalize-symlink.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: clear-stall symlinked finalize exits 3"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-finalize-symlink.out")" "22: clear-stall symlinked finalize emits CLEARED=false"
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: symlink preflight leaves ship layer unchanged"

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

dir=$(make_tmp case22-clear-dangling-ship)
ln -s "$dir/missing-ship-target" "$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-dangling-ship.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: clear-stall dangling ship-pr-state.sh exits 3"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-dangling-ship.out")" "22: clear-stall dangling ship-pr-state.sh emits CLEARED=false"

dir=$(make_tmp case22-clear-dangling-finalize)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
ln -s "$dir/missing-finalize-target" "$dir/finalize-state.sh"
run_capture "$SANDBOX/case22-clear-dangling-finalize.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: clear-stall dangling finalize-state.sh exits 3"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-dangling-finalize.out")" "22: clear-stall dangling finalize-state.sh emits CLEARED=false"
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: dangling finalize preflight leaves ship layer unchanged"

dir=$(make_tmp case22-clear-dangling-session)
cat >"$dir/ship-pr-state.sh" <<'EOF'
STALL_TRACKING=true
STALL_STEP=8
EOF
ln -s "$dir/missing-session-target" "$dir/session-env.sh"
run_capture "$SANDBOX/case22-clear-dangling-session.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 3 "$RC" "22: clear-stall dangling session-env.sh exits 3"
assert_eq false "$(kv CLEARED "$SANDBOX/case22-clear-dangling-session.out")" "22: clear-stall dangling session-env.sh emits CLEARED=false"
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: dangling session preflight leaves ship layer unchanged"

dir=$(make_tmp case22-clear-append)
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
EXIT_CODE=4
PR_URL=https://example.test/pr/1
EOF
run_capture "$SANDBOX/case22-clear-append.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-append.out")" "22: clear-stall append-when-absent emits CLEARED=true"
assert_eq false "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall append-when-absent writes STALL_TRACKING=false"
if grep -q '^STALL_STEP=$' "$dir/ship-pr-state.sh"; then
    pass "22: clear-stall append-when-absent writes empty STALL_STEP"
else
    fail "22: clear-stall append-when-absent writes empty STALL_STEP"
fi
assert_eq https://example.test/pr/1 "$(read_session_key --file "$dir/ship-pr-state.sh" --key PR_URL --default "")" "22: clear-stall append-when-absent preserves PR_URL"

dir=$(make_tmp case22-clear-empty)
: >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-empty.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall empty state exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-empty.out")" "22: clear-stall empty state emits CLEARED=true"
assert_eq false "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default missing)" "22: clear-stall empty state writes STALL_TRACKING=false"

dir=$(make_tmp case22-clear-comments)
printf '# comment only\n\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-clear-comments.out" "$SCRIPT" clear-stall --implement-tmpdir "$dir"
assert_eq 0 "$RC" "22: clear-stall comment-only state exits 0"
assert_eq true "$(kv CLEARED "$SANDBOX/case22-clear-comments.out")" "22: clear-stall comment-only state emits CLEARED=true"
assert_eq false "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default missing)" "22: clear-stall comment-only state writes STALL_TRACKING=false"

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
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall mv failure leaves STALL_TRACKING=true on disk"

dir=$(make_tmp case22-seed-rewrite)
write_state "$dir" 8 ci-initial "first-fixer-non-health" "BAIL_FAILURE_DETAIL_LOG=$dir/failure.log"
run_capture "$SANDBOX/case22-seed-rewrite.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir" --stall-step 5 --phase review
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-rewrite.out")" "22: seed-terminal-state rewrite emits SEEDED=true"
assert_eq rewrite "$(kv SEED_MODE "$SANDBOX/case22-seed-rewrite.out")" "22: seed-terminal-state rewrite emits SEED_MODE=rewrite"
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state rewrite keeps STALL_TRACKING=true"
assert_eq 5 "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state rewrite refreshes STALL_STEP"
assert_eq review "$(read_session_key --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: seed-terminal-state rewrite refreshes PHASE"
assert_eq 4 "$(read_session_key --file "$dir/ship-pr-state.sh" --key EXIT_CODE --default "")" "22: seed-terminal-state rewrite preserves EXIT_CODE"
assert_eq first-fixer-non-health "$(read_session_key --file "$dir/ship-pr-state.sh" --key BAIL_REASON --default "")" "22: seed-terminal-state rewrite preserves BAIL_REASON"
assert_eq "$dir/failure.log" "$(read_session_key --file "$dir/ship-pr-state.sh" --key BAIL_FAILURE_DETAIL_LOG --default "")" "22: seed-terminal-state rewrite preserves BAIL_FAILURE_DETAIL_LOG"

dir=$(make_tmp case22-seed-empty)
: >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-seed-empty.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-empty.out")" "22: seed-terminal-state empty file emits SEEDED=true"
assert_eq seed "$(kv SEED_MODE "$SANDBOX/case22-seed-empty.out")" "22: seed-terminal-state empty file uses SEED_MODE=seed"
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state empty file seeds STALL_TRACKING=true"

dir=$(make_tmp case22-seed-comments)
printf '# header\n\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case22-seed-comments.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir" --stall-step 5 --phase review
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-comments.out")" "22: seed-terminal-state comment-only file emits SEEDED=true"
assert_eq seed "$(kv SEED_MODE "$SANDBOX/case22-seed-comments.out")" "22: seed-terminal-state comment-only file uses SEED_MODE=seed"
assert_eq 5 "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state comment-only file honors stall-step override"

dir=$(make_tmp case22-seed-fresh)
run_capture "$SANDBOX/case22-seed-fresh.out" "$SCRIPT" seed-terminal-state --implement-tmpdir "$dir"
assert_eq true "$(kv SEEDED "$SANDBOX/case22-seed-fresh.out")" "22: seed-terminal-state fresh emits SEEDED=true"
assert_eq seed "$(kv SEED_MODE "$SANDBOX/case22-seed-fresh.out")" "22: seed-terminal-state fresh emits SEED_MODE=seed"
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state fresh sets STALL_TRACKING=true"
assert_eq ci-initial "$(read_session_key --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: seed-terminal-state fresh seeds PHASE=ci-initial"
assert_eq 8 "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state fresh seeds STALL_STEP=8"
assert_eq 4 "$(read_session_key --file "$dir/ship-pr-state.sh" --key EXIT_CODE --default "")" "22: seed-terminal-state fresh seeds EXIT_CODE=4"
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
assert_eq true "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: seed-terminal-state mv failure leaves STALL_TRACKING=true on disk"

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
mkdir -p "$read_stub_root/python/stubs/session"
cp "$REPO_ROOT"/python/*.py "$read_stub_root/python/"
mv "$read_stub_root/python/cli.py" "$read_stub_root/python/real-cli.py"
chmod +x "$read_stub_root/skills/implement/scripts/stall-recovery-report.sh"
cat >"$read_stub_root/python/cli.py" <<'DISPATCHER'
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parent
    if len(sys.argv) >= 3 and sys.argv[1] == "session":
        stub = root / "stubs" / "session" / sys.argv[2]
        if stub.is_file() and os.access(stub, os.X_OK):
            os.execv(str(stub), [str(stub), *sys.argv[3:]])
    os.execv(sys.executable, [sys.executable, str(root / "real-cli.py"), *sys.argv[1:]])

if __name__ == "__main__":
    main()
DISPATCHER
chmod +x "$read_stub_root/python/cli.py"
cat >"$read_stub_root/python/stubs/session/read-key" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
real="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/real-cli.py"
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
exec python3 "$real" session read-key "${args[@]}"
STUB
chmod +x "$read_stub_root/python/stubs/session/read-key"
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
assert_eq false "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_TRACKING --default "")" "22: clear-stall destination read failure exercises post-mv assertion"

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
assert_eq review "$(read_session_key --file "$dir/ship-pr-state.sh" --key PHASE --default "")" "22: seed-terminal-state rewrite applies sanitized phase override"
assert_eq 5 "$(read_session_key --file "$dir/ship-pr-state.sh" --key STALL_STEP --default "")" "22: seed-terminal-state rewrite applies stall-step override on metachar disk"



echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
