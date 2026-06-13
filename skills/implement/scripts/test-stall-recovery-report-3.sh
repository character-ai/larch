#!/usr/bin/env bash
# test-stall-recovery-report-3.sh — offline harness for stall-recovery-report.sh (part 3 of 3)

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

# New terminal-only / escalation-success reporting seams.
dir=$(make_tmp case23-normalize)
printf 'STALL_TRACKING=false
MERGE_RESULT=already_merged
' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case23-normalize.out" "$SCRIPT" normalize-outcome --implement-tmpdir "$dir"
assert_eq force-merged-externally "$(kv IMPLEMENT_NORMALIZED_OUTCOME "$SANDBOX/case23-normalize.out")" "23: normalize-outcome maps already_merged"
assert_eq true "$(kv IMPLEMENT_OUTCOME_SUCCEEDED "$SANDBOX/case23-normalize.out")" "23: normalize-outcome success allowlist accepts force-merged"
printf 'STALL_TRACKING=true
' >"$dir/finalize-state.sh"
run_capture "$SANDBOX/case23-normalize-stall.out" "$SCRIPT" normalize-outcome --implement-tmpdir "$dir"
assert_eq stalled "$(kv IMPLEMENT_NORMALIZED_OUTCOME "$SANDBOX/case23-normalize-stall.out")" "23: normalize-outcome any stall layer wins"
assert_eq false "$(kv IMPLEMENT_OUTCOME_SUCCEEDED "$SANDBOX/case23-normalize-stall.out")" "23: normalize-outcome rejects active stall"

dir=$(make_tmp case23-compose)
cat >"$dir/stall-recovery-classification.env" <<'EOF'
FAILURE_CLASS=lint-failure
FAILURE_SIGNATURE=abcdef
STALL_STEP=5
PHASE=review
BAIL_REASON=wrapper-validation-failure
EXIT_CODE=1
MATCHED_CLASSIFIER_PATTERN=lint-output
DISPATCHER=codex
EOF
printf 'version=1
created_utc=2026-01-01T00:00:00Z
attempt_count=0
' >"$dir/stall-recovery-attempts.env"
cat >"$dir/stall-recovery-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=lint fix loop missed retry path

Observation: stall-recovery-escalation-ledger.tsv shows a handoff.
EOF
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=lint fix loop missed retry path

Bounded larch-only finding.
EOF
printf 'client-only-token
' >"$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case23-record.out" "$SCRIPT" record-escalation --implement-tmpdir "$dir" --site step5 --trigger main-agent-required --step 5 --phase review --dispatcher lint-fix-loop --exit-code 1
assert_eq true "$(kv ESCALATION_RECORDED "$SANDBOX/case23-record.out")" "23: record-escalation writes canonical ledger"
chmod 444 "$dir/stall-recovery-escalation-ledger.tsv"
run_capture "$SANDBOX/case23-record-nonwritable.out" "$SCRIPT" record-escalation --implement-tmpdir "$dir" --site step5 --trigger main-agent-required --step 5 --phase review --dispatcher lint-fix-loop --exit-code 1
chmod 644 "$dir/stall-recovery-escalation-ledger.tsv"
assert_eq false "$(kv ESCALATION_RECORDED "$SANDBOX/case23-record-nonwritable.out")" "23: record-escalation routes non-writable canonical ledger to fallback"
assert_eq true "$(kv ESCALATION_FALLBACK_WRITTEN "$SANDBOX/case23-record-nonwritable.out")" "23: record-escalation writes fallback for non-writable canonical ledger"
assert_contains 'RECORD_ESCALATION_FAILED=true' "$(cat "$dir/stall-recovery-escalation-record-failure.env")" "23: record-escalation writes marker on canonical ledger write failure"
assert_eq true "$(read_session_key --file "$dir/stall-recovery-escalation-record-failure.env" --key RECORD_ESCALATION_FAILED --default "")" "23: record-escalation marker is parseable KV"
assert_eq canonical-ledger-not-writable "$(read_session_key --file "$dir/stall-recovery-escalation-record-failure.env" --key REASON --default "")" "23: record-escalation marker reason is parseable KV"
run_capture "$SANDBOX/case23-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: compose-report Tier B exits 0"
assert_eq printed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-compose.out")" "23: compose-report prints Tier B"
assert_contains '[Bug] /implement escalation: lint fix loop missed retry path' "$(cat "$dir/out.md")" "23: compose-report root-caused title"
assert_contains '| Larch version | `' "$(cat "$dir/out.md")" "23: compose-report includes larch version"
assert_contains "| Run ID | \`unknown\` |" "$(cat "$dir/out.md")" "23: compose-report includes run id"
assert_contains 'Bounded larch-only finding.' "$(cat "$dir/out.md")" "23: compose-report renders bounded root-cause prose"
assert_not_contains 'client-only-token' "$(cat "$dir/out.md")" "23: compose-report excludes prompt supplement token"

dir_tier_a=$(make_tmp case23-tier-a-parse-marker)
cp "$dir/stall-recovery-classification.env" "$dir_tier_a/stall-recovery-classification.env"
cp "$dir/stall-recovery-attempts.env" "$dir_tier_a/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir_tier_a/stall-recovery-root-cause.md"
run_capture "$SANDBOX/case23-tier-a-parse-marker.out" env LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" compose-report --implement-tmpdir "$dir_tier_a" --report-kind terminal-failure --surface issue-input --output-file "$dir_tier_a/issue-input.md"
assert_eq 0 "$RC" "23: Tier A dry-run compose exits 0"
tier_a_sig=$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case23-tier-a-parse-marker.out")
run_capture "$SANDBOX/case23-tier-a-parse-marker-parse.out" python3 "$REPO_ROOT/python/cli.py" issue parse-input --input-file "$dir_tier_a/issue-input.md" --output-dir "$dir_tier_a/parsed"
assert_eq 0 "$RC" "23: parse-input accepts Tier A issue input"
assert_eq 1 "$(kv ITEMS_TOTAL "$SANDBOX/case23-tier-a-parse-marker-parse.out")" "23: Tier A issue input parses as one item"
assert_contains "<!-- larch-stall:signature=$tier_a_sig -->" "$(cat "$(kv ITEM_1_BODY_FILE "$SANDBOX/case23-tier-a-parse-marker-parse.out")")" "23: parse-input preserves Tier A dedup marker"

dir_tier_b_dry=$(make_tmp case23-tier-b-dry-run-no-gh)
cp "$dir/stall-recovery-classification.env" "$dir_tier_b_dry/stall-recovery-classification.env"
cp "$dir/stall-recovery-attempts.env" "$dir_tier_b_dry/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir_tier_b_dry/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir_tier_b_dry/stall-recovery-bounded-root-cause.md"
cp "$dir/stall-recovery-sensitive-corpus.env" "$dir_tier_b_dry/stall-recovery-sensitive-corpus.env"
mkdir -p "$dir_tier_b_dry/bin"
printf '#!/usr/bin/env bash\necho "$@" >>"%s/gh.calls"\nexit 9\n' "$dir_tier_b_dry" >"$dir_tier_b_dry/bin/gh"
chmod +x "$dir_tier_b_dry/bin/gh"
run_capture "$SANDBOX/case23-tier-b-dry-run-no-gh.out" env "PATH=$dir_tier_b_dry/bin:$PATH" LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" compose-report --implement-tmpdir "$dir_tier_b_dry" --report-kind terminal-failure --surface chat-print --output-file "$dir_tier_b_dry/chat.md"
assert_eq 0 "$RC" "23: Tier B dry-run compose exits 0"
assert_eq dry-run "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-tier-b-dry-run-no-gh.out")" "23: Tier B dry-run status"
if [ ! -e "$dir_tier_b_dry/gh.calls" ]; then
    pass "23: Tier B dry-run compose makes no gh calls"
else
    fail "23: Tier B dry-run compose should not call gh" "$(cat "$dir_tier_b_dry/gh.calls")"
fi

dir_tier_b_fail=$(make_tmp case23-tier-b-create-fail)
cp "$dir/stall-recovery-classification.env" "$dir_tier_b_fail/stall-recovery-classification.env"
cp "$dir/stall-recovery-attempts.env" "$dir_tier_b_fail/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir_tier_b_fail/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir_tier_b_fail/stall-recovery-bounded-root-cause.md"
cp "$dir/stall-recovery-sensitive-corpus.env" "$dir_tier_b_fail/stall-recovery-sensitive-corpus.env"
mkdir -p "$dir_tier_b_fail/bin"
cat >"$dir_tier_b_fail/bin/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$GH_STUB_LOG"
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    printf '%s\n' '{"number":1,"body":"different report","pull_request":null}'
    exit 0
fi
if [ "$1" = issue ] && [ "${2:-}" = create ]; then
    echo create failed >&2
    exit 1
fi
echo unexpected gh: "$*" >&2
exit 9
STUB
chmod +x "$dir_tier_b_fail/bin/gh"
run_capture "$SANDBOX/case23-tier-b-create-fail.out" env "PATH=$dir_tier_b_fail/bin:$PATH" "GH_STUB_LOG=$dir_tier_b_fail/gh.calls" LARCH_STALL_RECOVERY_ENABLE_TEST_FILING=1 "$SCRIPT" compose-report --implement-tmpdir "$dir_tier_b_fail" --report-kind terminal-failure --surface chat-print --output-file "$dir_tier_b_fail/chat.md"
assert_eq 0 "$RC" "23: Tier B helper create failure exits 0"
assert_eq fallback-print-required "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-tier-b-create-fail.out")" "23: Tier B helper create failure falls back to chat print"
assert_eq create-failed "$(kv STALL_RECOVERY_REPORT_FALLBACK_REASON "$SANDBOX/case23-tier-b-create-fail.out")" "23: Tier B helper create failure reason"
assert_contains 'issue create' "$(cat "$dir_tier_b_fail/gh.calls")" "23: Tier B helper attempts create before fallback"
assert_contains '[Bug] /implement terminal: lint fix loop missed retry path' "$(cat "$dir_tier_b_fail/chat.md")" "23: Tier B helper fallback leaves chat artifact"
printf 'stale-partial-row' >"$dir/stall-recovery-escalation-ledger.tsv"
run_capture "$SANDBOX/case23-record-newline.out" "$SCRIPT" record-escalation --implement-tmpdir "$dir" --site step5 --trigger main-agent-required --step 5 --phase review --dispatcher lint-fix-loop --exit-code 1
assert_contains $'stale-partial-row\nutc=' "$(cat "$dir/stall-recovery-escalation-ledger.tsv")" "23: record-escalation repairs missing trailing newline"

dir=$(make_tmp case23-ledger-only)
printf 'version=1
created_utc=2026-01-01T00:00:00Z
attempt_count=0
' >"$dir/stall-recovery-attempts.env"
cat >"$dir/stall-recovery-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=ledger only success report

Observation: escalation ledger exists without a terminal classifier.
EOF
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=ledger only success report

Bounded larch-only finding.
EOF
printf 'client-only-token
' >"$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case23-ledger-only-record.out" "$SCRIPT" record-escalation --implement-tmpdir "$dir" --site ship-pr --trigger first-fixer-non-health --step 8 --phase ci-initial --dispatcher ship-pr --exit-code 3
run_capture "$SANDBOX/case23-ledger-only-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: escalation-success composes without classification"
assert_eq printed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-ledger-only-compose.out")" "23: ledger-only report prints"
assert_not_contains "Failure class | \`unrecoverable\`" "$(cat "$dir/out.md")" "23: ledger-only success report does not claim unrecoverable failure"

dir=$(make_tmp case23-ledger-zero-attempts)
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case23-ledger-zero-attempts-record.out" "$SCRIPT" record-escalation --implement-tmpdir "$dir" --site ship-pr --trigger first-fixer-non-health --step 8 --phase ci-initial --dispatcher ship-pr --exit-code 3
run_capture "$SANDBOX/case23-ledger-zero-attempts-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: escalation-success initializes missing attempts"
assert_eq 0 "$(kv attempt_count "$dir/stall-recovery-attempts.env")" "23: escalation-success zero-attempt file is parseable KV"

dir=$(make_tmp case23-tool-failure-only)
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
cat >"$dir/execution-issues.md" <<'EOF'
## Tool Failure: record-escalation

- reason: `canonical-ledger-write-failed`
EOF
run_capture "$SANDBOX/case23-tool-failure-only-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: escalation-success accepts tagged record-escalation Tool Failure evidence"
assert_contains 'tagged record-escalation Tool Failure present' "$(cat "$dir/out.md")" "23: compose-report renders tagged Tool Failure evidence"

dir=$(make_tmp case23-generic-tool-failure-only)
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
cat >"$dir/execution-issues.md" <<'EOF'
## Tool Failure: unrelated-helper

- reason: `failed`
EOF
run_capture "$SANDBOX/case23-generic-tool-failure-only-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: escalation-success rejects generic Tool Failure evidence"

dir=$(make_tmp case23-fallback-only)
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
printf 'utc=2026-01-01T00:00:00Z\tsite=step5\ttrigger=main-agent-required\tstep=5\tphase=review\tdispatcher=lint-fix-loop\texit_code=1\tfailure_detail_log=\n' >"$dir/stall-recovery-escalation-fallback.tsv"
run_capture "$SANDBOX/case23-fallback-only-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: escalation-success composes from fallback ledger only"
assert_eq printed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-fallback-only-compose.out")" "23: fallback-only report prints"
assert_contains '[Bug] /implement escalation: lint fix loop missed retry path (step5:main-agent-required)' "$(cat "$dir/out.md")" "23: fallback-only title uses fallback tokens"
assert_contains "fallback site=\`step5\` trigger=\`main-agent-required\`" "$(cat "$dir/out.md")" "23: fallback-only body renders fallback tokens"

dir=$(make_tmp case23-marker-only)
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
printf 'RECORD_ESCALATION_FAILED=true\nREASON=canonical-ledger-write-failed\n' >"$dir/stall-recovery-escalation-record-failure.env"
run_capture "$SANDBOX/case23-marker-only-compose.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: escalation-success composes from record-failure marker only"
assert_eq printed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-marker-only-compose.out")" "23: marker-only report prints"
assert_contains 'record-failure marker present' "$(cat "$dir/out.md")" "23: marker-only body renders marker evidence"

dir=$(make_tmp case23-escalation-success-no-evidence)
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case23-escalation-success-no-evidence.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: escalation-success fails closed without evidence"

dir=$(make_tmp case23-ledger-sanitize)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
printf 'utc=now\tsite=/var/tmp/test-repo\ttrigger=secret-branch\n' >"$dir/stall-recovery-escalation-ledger.tsv"
run_capture "$SANDBOX/case23-ledger-sanitize.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: malformed ledger tokens do not fail Tier B"
assert_contains "site=\`redacted\` trigger=\`redacted\`" "$(cat "$dir/out.md")" "23: malformed ledger tokens are sanitized"
assert_not_contains '/var/tmp/test-repo' "$(cat "$dir/out.md")" "23: malformed ledger site path is not printed"

while IFS= read -r token; do
    [ -n "$token" ] || continue
    safe_name=$(printf '%s' "$token" | tr -c '[:alnum:]' '_')
    dir=$(make_tmp "case23-token-$safe_name")
    write_state "$dir" 8 ci-initial "$token"
    run_capture "$SANDBOX/case23-token-$safe_name.out" "$SCRIPT" classify --implement-tmpdir "$dir"
    assert_eq "$token" "$(kv BAIL_REASON "$SANDBOX/case23-token-$safe_name.out")" "23: config bail token renders $token"
done < <(
    python3 - <<PYTOKENS
import sys
sys.path.insert(0, "$REPO_ROOT/python")
import config
for item in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
    print(item)
PYTOKENS
)
dir=$(make_tmp case23-token-compound)
write_state "$dir" 8 ci-initial "ci-local-unfixable:lint_1,test-2"
run_capture "$SANDBOX/case23-token-compound.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq "ci-local-unfixable:lint_1,test-2" "$(kv BAIL_REASON "$SANDBOX/case23-token-compound.out")" "23: ci-local compound renders"
write_state "$dir" 8 ci-initial "ci-local-unfixable:../../secret"
run_capture "$SANDBOX/case23-token-compound-bad.out" "$SCRIPT" classify --implement-tmpdir "$dir"
assert_eq redacted "$(kv BAIL_REASON "$SANDBOX/case23-token-compound-bad.out")" "23: ci-local unsafe suffix redacts"

dir=$(make_tmp case23-sensitive-shapes)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
printf 'CLIENT_URL=https://client.example.test/private
' >"$dir/stall-recovery-sensitive-corpus.env"
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=lint fix loop referenced https://client.example.test/private

Bounded finding.
EOF
run_capture "$SANDBOX/case23-sensitive-value.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: sensitive KEY=value extraction rejects bounded prose"
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=lint fix loop referenced an absolute path

Bounded finding at /Users/example/project/file.txt.
EOF
run_capture "$SANDBOX/case23-sensitive-path.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: sensitive shape rejects absolute paths"
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=main-agent-required handoff is report-safe

Bounded finding mentions BAIL_REASON=main-agent-required.
EOF
run_capture "$SANDBOX/case23-allowlisted-assignment.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: allowlisted operational assignment passes sensitive scan"
printf 'other-token\n' >"$dir/stall-recovery-sensitive-corpus.env"
printf 'feature text mentions https://client.example.test/private
' >"$dir/plan.txt"
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=plan echoed client URL

Bounded finding mentions https://client.example.test/private.
EOF
run_capture "$SANDBOX/case23-sensitive-plan-evidence.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: sensitive scan derives URL corpus from plan evidence"

cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=plan echoed client repo path

Bounded finding mentions docs/private-plan.md.
EOF
printf 'plan names docs/private-plan.md
' >"$dir/plan.txt"
run_capture "$SANDBOX/case23-sensitive-relative-path.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: sensitive scan rejects repo-relative paths"

dir=$(make_tmp case23-sensitive-raw-evidence)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
printf 'other-token\n' >"$dir/stall-recovery-sensitive-corpus.env"
printf 'Client-specific marker prose remains private.\n' >"$dir/stall-recovery-escalation-record-failure.env"
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=raw evidence echoed

Client-specific marker prose remains private.
EOF
run_capture "$SANDBOX/case23-sensitive-raw-evidence.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: sensitive scan rejects raw evidence text"

cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=short repo token echoed

Bounded finding mentions qa.
EOF
printf 'qa
' >"$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case23-sensitive-short-token.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: sensitive scan rejects two-character sensitive token"

dir=$(make_tmp case23-path-confinement)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
outside="$SANDBOX/outside-ledger.tsv"
printf 'utc=now\tsite=step5\ttrigger=main-agent-required
' >"$outside"
run_capture "$SANDBOX/case23-path-confinement.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --escalation-ledger-file "$outside" --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: compose-report rejects outside ledger path"
missing_outside="$SANDBOX/outside-attempts.env"
rm -f "$missing_outside"
run_capture "$SANDBOX/case23-attempts-confinement.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --attempts-file "$missing_outside" --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: compose-report rejects missing attempts path outside tmpdir"

dir=$(make_tmp case23-operator)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env" 2>/dev/null || cat >"$dir/stall-recovery-classification.env" <<'EOF'
FAILURE_CLASS=unrecoverable
STALL_STEP=8
PHASE=ci-initial
EOF
printf 'version=1
created_utc=2026-01-01T00:00:00Z
attempt_count=0
' >"$dir/stall-recovery-attempts.env"
cat >"$dir/stall-recovery-root-cause.md" <<'EOF'
verdict=operator-action
confidence=medium
summary=operator stopped the run

Observation: operator action.
EOF
run_capture "$SANDBOX/case23-operator.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface issue-input --output-file "$dir/out.md"
assert_eq skipped_operator_action "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-operator.out")" "23: operator-action skips filing"
if [ -f "$dir/stall-recovery-operator-action.env" ]; then
    pass "23: operator-action sentinel written"
else
    fail "23: operator-action sentinel missing"
fi
assert_eq true "$(read_session_key --file "$dir/stall-recovery-operator-action.env" --key STALL_RECOVERY_OPERATOR_ACTION --default "")" "23: operator-action sentinel is parseable KV"
assert_eq operator-action "$(read_session_key --file "$dir/stall-recovery-operator-action-record.md" --key VERDICT --default "")" "23: operator-action record is parseable KV"

dir=$(make_tmp case23-issue-input-status)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
run_capture "$SANDBOX/case23-issue-input-status.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface issue-input --output-file "$dir/out.md"
assert_eq printed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case23-issue-input-status.out")" "23: issue-input composition uses documented report status"

run_capture "$SANDBOX/case23-legacy-bug-body-gated.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES "$SCRIPT" bug-body --implement-tmpdir "$dir" --classification-file "$dir/stall-recovery-classification.env"
assert_eq 1 "$RC" "23: legacy bug-body is gated outside test compatibility"
assert_contains "bug-body is test-only" "$(cat "$SANDBOX/case23-legacy-bug-body-gated.out.err")" "23: legacy bug-body gate explains compose-report replacement"
run_capture "$SANDBOX/case23-legacy-bug-comment-gated.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES "$SCRIPT" bug-comment
assert_eq 1 "$RC" "23: legacy bug-comment is gated outside test compatibility"
assert_contains "bug-comment is test-only" "$(cat "$SANDBOX/case23-legacy-bug-comment-gated.out.err")" "23: legacy bug-comment gate explains compose-report replacement"
run_capture "$SANDBOX/case23-legacy-issue-input-gated.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES "$SCRIPT" issue-input-file
assert_eq 1 "$RC" "23: legacy issue-input-file is gated outside test compatibility"
assert_contains "issue-input-file is test-only" "$(cat "$SANDBOX/case23-legacy-issue-input-gated.out.err")" "23: legacy issue-input-file gate explains compose-report replacement"

dir=$(make_tmp case23-issue-input-raw-bail)
cat >"$dir/stall-recovery-classification.env" <<EOF
FAILURE_CLASS=unrecoverable
FAILURE_SIGNATURE=abcdef
STALL_STEP=8
PHASE=ship
BAIL_REASON=redacted
BAIL_REASON_RAW=operator supplied $GHP_TOKEN_CASE13 during handoff
EXIT_CODE=4
MATCHED_CLASSIFIER_PATTERN=terminal-bail
DISPATCHER=ship-pr
EOF
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
run_capture "$SANDBOX/case23-issue-input-raw-bail.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface issue-input --output-file "$dir/out.md"
assert_eq 0 "$RC" "23: Tier A raw bail report composes"
assert_contains 'operator supplied' "$(cat "$dir/out.md")" "23: Tier A preserves raw bail intent"
assert_not_contains "$GHP_TOKEN_CASE13" "$(cat "$dir/out.md")" "23: Tier A redacts secret token from raw bail"

dir=$(make_tmp case23-terminal-missing-classification)
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case23-terminal-missing-classification.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: terminal-failure compose fails closed without classification"
assert_contains "--classification-file missing" "$(cat "$SANDBOX/case23-terminal-missing-classification.out.err")" "23: terminal-failure missing classification error"

dir=$(make_tmp case23-issue-input-denied)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
consumer_root="$SANDBOX/consumer-root"
mkdir -p "$consumer_root"
run_capture "$SANDBOX/case23-issue-input-denied.out" env CLAUDE_PROJECT_DIR="$consumer_root" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface issue-input --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: issue-input denied outside larch dev clone"

dir=$(make_tmp case23-header-only-root-cause)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
cat >"$dir/stall-recovery-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=header only
EOF
cat >"$dir/stall-recovery-bounded-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=header only
EOF
run_capture "$SANDBOX/case23-header-only-root-cause.out" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/out.md"
assert_eq 1 "$RC" "23: root-cause validation rejects header-only artifacts"

dir=$(make_tmp case23-normalize-memory)
printf 'STALL_TRACKING=false\nMERGE_RESULT=merged\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case23-normalize-memory.out" "$SCRIPT" normalize-outcome --implement-tmpdir "$dir" --in-memory-stall-tracking true
assert_eq stalled "$(kv IMPLEMENT_NORMALIZED_OUTCOME "$SANDBOX/case23-normalize-memory.out")" "23: normalize-outcome honors in-memory stall tracking"
assert_eq true "$(kv IMPLEMENT_MEMORY_STALL_TRACKING "$SANDBOX/case23-normalize-memory.out")" "23: normalize-outcome emits memory stall layer"

dir=$(make_tmp case23-normalize-forked-ci-failed)
printf 'FORKED_TARGET=true\nSTALL_TRACKING=false\nCI_PASSED=false\n' >"$dir/ship-pr-state.sh"
run_capture "$SANDBOX/case23-normalize-forked-ci-failed.out" "$SCRIPT" normalize-outcome --implement-tmpdir "$dir"
assert_eq forked-dry-run "$(kv IMPLEMENT_NORMALIZED_OUTCOME "$SANDBOX/case23-normalize-forked-ci-failed.out")" "23: normalize-outcome preserves forked outcome"
assert_eq true "$(kv IMPLEMENT_OUTCOME_SUCCEEDED "$SANDBOX/case23-normalize-forked-ci-failed.out")" "23: forked dry-run succeeds without CI_PASSED"

dir=$(make_tmp case24-public-signature)
cat >"$dir/stall-recovery-classification.env" <<'EOF'
FAILURE_CLASS=dispatch-failure
FAILURE_SIGNATURE=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
STALL_STEP=2
PHASE=implementation
BAIL_REASON=wrapper-validation-failure
EXIT_CODE=4
MATCHED_CLASSIFIER_PATTERN=dispatch-output
DISPATCHER=codex
EOF
printf 'version=1
created_utc=2026-01-01T00:00:00Z
attempt_count=0
' >"$dir/stall-recovery-attempts.env"
cat >"$dir/stall-recovery-root-cause.md" <<'EOF'
verdict=larch-defect
confidence=high
summary=dispatcher envelope regression

The dispatcher returned a malformed envelope in the retry path.
EOF
cp "$dir/stall-recovery-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
printf 'client-only-token
' >"$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case24-issue-input.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES CLAUDE_PROJECT_DIR="$REPO_ROOT" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface issue-input --output-file "$dir/issue.md"
assert_eq 0 "$RC" "24: non-legacy issue-input composition exits 0"
assert_eq "" "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-issue-input.out")" "24: issue-input composition emits no branchable status"
assert_eq a123f505e4cef146b80a49ca0a4a93e0a3ea2c123a59ba471c6e6e056116d038 "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-issue-input.out")" "24: public signature golden vector"
assert_contains '<!-- larch-stall:signature=a123f505e4cef146b80a49ca0a4a93e0a3ea2c123a59ba471c6e6e056116d038 -->' "$(cat "$dir/issue.md")" "24: Tier A artifact includes public marker"
assert_not_contains 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' "$(cat "$dir/issue.md")" "24: public marker does not use retry failure signature"

dir2=$(make_tmp case24-public-signature-stability)
cp "$dir/stall-recovery-classification.env" "$dir2/stall-recovery-classification.env"
cp "$dir/stall-recovery-attempts.env" "$dir2/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir2/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir2/stall-recovery-bounded-root-cause.md"
printf 'RUN_ID=run-specific-id
BRANCH_NAME=feature/specific-branch
' >"$dir2/session-env.sh"
run_capture "$SANDBOX/case24-stability.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES CLAUDE_PROJECT_DIR="$REPO_ROOT" "$SCRIPT" compose-report --implement-tmpdir "$dir2" --report-kind terminal-failure --surface issue-input --output-file "$dir2/issue.md"
assert_eq "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-issue-input.out")" "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-stability.out")" "24: terminal public signature ignores repo/run fields"

dir3=$(make_tmp case24-public-signature-exclusions)
cp "$dir/stall-recovery-attempts.env" "$dir3/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir3/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir3/stall-recovery-bounded-root-cause.md"
awk '
    /^MATCHED_CLASSIFIER_PATTERN=/ { print "MATCHED_CLASSIFIER_PATTERN=lint-output"; next }
    /^DISPATCHER=/ { print "DISPATCHER=cursor"; next }
    { print }
    END { print "SKILL=consumer-specific-skill" }
' "$dir/stall-recovery-classification.env" >"$dir3/stall-recovery-classification.env"
printf 'utc=2026-01-01T00:00:00Z\tsite=ship-pr\ttrigger=first-fixer-non-health\tstep=8\tphase=ci-initial\tdispatcher=ship-pr\texit_code=3\n' >"$dir3/stall-recovery-escalation-ledger.tsv"
printf 'RECORD_ESCALATION_FAILED=true\nREASON=secret-terminal-marker\n' >"$dir3/stall-recovery-escalation-record-failure.env"
run_capture "$SANDBOX/case24-exclusions.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES CLAUDE_PROJECT_DIR="$REPO_ROOT" "$SCRIPT" compose-report --implement-tmpdir "$dir3" --report-kind terminal-failure --surface issue-input --output-file "$dir3/issue.md"
assert_eq "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-issue-input.out")" "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-exclusions.out")" "24: terminal public signature ignores dispatcher, matched classifier, skill, and escalation data"

dir4=$(make_tmp case24-public-signature-bail-inclusion)
cp "$dir/stall-recovery-attempts.env" "$dir4/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir4/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir4/stall-recovery-bounded-root-cause.md"
awk '
    /^BAIL_REASON=/ { print "BAIL_REASON=main-agent-required"; next }
    { print }
' "$dir/stall-recovery-classification.env" >"$dir4/stall-recovery-classification.env"
run_capture "$SANDBOX/case24-bail-inclusion.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES CLAUDE_PROJECT_DIR="$REPO_ROOT" "$SCRIPT" compose-report --implement-tmpdir "$dir4" --report-kind terminal-failure --surface issue-input --output-file "$dir4/issue.md"
if [ "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-issue-input.out")" != "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-bail-inclusion.out")" ]; then
    pass "24: terminal public signature changes with safe bail token"
else
    fail "24: terminal public signature changes with safe bail token"
fi

dir=$(make_tmp case24-tier-b-dry-run)
cp "$SANDBOX/case24-public-signature/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case24-tier-b-dry-run.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/chat.md"
assert_eq dry-run "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-b-dry-run.out")" "24: Tier B dry-run emits dry-run status"
assert_contains '<!-- larch-stall:signature=' "$(cat "$dir/chat.md")" "24: Tier B artifact includes public marker"

dir=$(make_tmp case24-tier-b-file)
mkdir -p "$dir/bin"
cat >"$dir/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$GH_LOG"
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    printf '%s\n' '{"number":1,"body":"different","pull_request":null}'
    exit 0
fi
if [ "$1" = issue ] && [ "${2:-}" = create ]; then
    printf '%s\n' 'https://github.com/character-ai/larch/issues/99'
    exit 0
fi
exit 9
EOF
chmod +x "$dir/bin/gh"
cp "$SANDBOX/case24-public-signature/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case24-tier-b-file.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/chat.md"
assert_eq filed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-b-file.out")" "24: Tier B create success emits filed"
assert_eq https://github.com/character-ai/larch/issues/99 "$(kv STALL_RECOVERY_REPORT_URL "$SANDBOX/case24-tier-b-file.out")" "24: Tier B create success emits URL"
assert_contains 'issue create -R character-ai/larch --title' "$(cat "$dir/gh.log")" "24: Tier B passes title to cross-repo filer"
assert_contains "dispatcher envelope regression" "$(cat "$dir/stall-recovery-bounded-root-cause-public.md")" "24: Tier B writes bounded root-cause slice"
assert_not_contains "stall-recovery-root-cause.md" "$(cat "$dir/gh.log")" "24: Tier B does not pass raw root-cause file"

dir=$(make_tmp case24-tier-b-dedup)
mkdir -p "$dir/bin"
cat >"$dir/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$GH_LOG"
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    printf '%s\n' '{"number":7,"body":"duplicate <!-- larch-stall:signature=a123f505e4cef146b80a49ca0a4a93e0a3ea2c123a59ba471c6e6e056116d038 -->","pull_request":null}'
    exit 0
fi
if [ "$1" = api ] && [ "${2:-}" = --method ]; then
    input=""
    prev=""
    for arg in "$@"; do
        if [ "$prev" = --input ]; then input=$arg; fi
        prev=$arg
    done
    [ -n "$input" ] && cp "$input" "$GH_COMMENT_CAPTURE"
    printf '%s\n' '{"html_url":"https://github.com/character-ai/larch/issues/7#issuecomment-100"}'
    exit 0
fi
exit 9
EOF
chmod +x "$dir/bin/gh"
cp "$SANDBOX/case24-public-signature/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case24-tier-b-dedup.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/chat.md"
assert_eq dedup-comment "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-b-dedup.out")" "24: Tier B dedup emits dedup-comment"
assert_eq https://github.com/character-ai/larch/issues/7#issuecomment-100 "$(kv STALL_RECOVERY_REPORT_URL "$SANDBOX/case24-tier-b-dedup.out")" "24: Tier B dedup emits comment URL"
assert_contains '+1 occurrence' "$(cat "$dir/comment.json")" "24: Tier B dedup posts bounded occurrence comment"
assert_not_contains 'issue create' "$(cat "$dir/gh.log")" "24: Tier B dedup does not create duplicate"

badroot="$SANDBOX/case24-bad-plugin-root"
mkdir -p "$badroot/skills/implement/scripts" "$badroot/scripts" "$badroot/python" "$badroot/.claude-plugin"
cp "$SCRIPT" "$badroot/skills/implement/scripts/stall-recovery-report.sh"
cp "$SCRIPT_DIR/stall-recovery-report-allowlists.tsv" "$badroot/skills/implement/scripts/"
cp "$SCRIPT_DIR/stall-recovery-report.md" "$badroot/skills/implement/scripts/"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$badroot/scripts/"
cp "$REPO_ROOT/scripts/lib-larch-dev-clone.sh" "$badroot/scripts/"
cp "$REPO_ROOT/scripts/file-failure-report-cross-repo.sh" "$badroot/scripts/"
cp "$REPO_ROOT/scripts/resolve-upstream-larch-repo.sh" "$badroot/scripts/"
cp "$REPO_ROOT"/python/*.py "$badroot/python/"
printf '{"repository":"https://example.com/not/larch"}\n' >"$badroot/.claude-plugin/plugin.json"
chmod +x "$badroot/skills/implement/scripts/stall-recovery-report.sh" "$badroot/scripts/file-failure-report-cross-repo.sh" "$badroot/scripts/resolve-upstream-larch-repo.sh"
dir=$(make_tmp case24-tier-b-resolver-failure)
cp "$SANDBOX/case24-public-signature/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case24-public-signature/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case24-public-signature/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
run_capture "$SANDBOX/case24-tier-b-resolver-failure.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES "$badroot/skills/implement/scripts/stall-recovery-report.sh" compose-report --implement-tmpdir "$dir" --report-kind terminal-failure --surface chat-print --output-file "$dir/chat.md"
assert_eq fallback-print-required "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-b-resolver-failure.out")" "24: Tier B resolver failure falls back"
assert_eq upstream-repo-unresolved "$(kv STALL_RECOVERY_REPORT_FALLBACK_REASON "$SANDBOX/case24-tier-b-resolver-failure.out")" "24: Tier B resolver failure reason"

dir=$(make_tmp case24-normalize-comment-url)
cat >"$dir/file.env" <<'EOF'
FILE_FAILURE_REPORT_STATUS=dedup-comment
FILE_FAILURE_REPORT_URL=https://github.com/owner/repo/issues/7#issuecomment-99
EOF
run_capture "$SANDBOX/case24-normalize-comment-url.out" "$SCRIPT" normalize-file-failure-report-env --implement-tmpdir "$dir" --file-failure-report-env "$dir/file.env"
assert_eq dedup-comment "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-normalize-comment-url.out")" "24: helper status maps dedup-comment"
assert_eq https://github.com/owner/repo/issues/7#issuecomment-99 "$(kv STALL_RECOVERY_REPORT_URL "$SANDBOX/case24-normalize-comment-url.out")" "24: helper URL maps canonical URL"
assert_eq "" "$(kv STALL_RECOVERY_REPORT_ISSUE_URL "$SANDBOX/case24-normalize-comment-url.out")" "24: comment URL does not populate issue URL alias"

TIER_A_MARKER_HASH=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

make_tier_a_dedup_case() {
    local name=$1 dir
    dir=$(make_tmp "$name")
    mkdir -p "$dir/bin"
    cat >"$dir/body.md" <<EOF
### [Bug] /implement stall: fixture

<!-- larch-stall:signature=$TIER_A_MARKER_HASH -->

Tier A body.
EOF
    cat >"$dir/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$GH_LOG"
if [ "$1" = repo ] && [ "${2:-}" = view ]; then
    printf '%s\n' 'owner/current-repo'
    exit 0
fi
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    case "${GH_STUB_CASE:-no-match}" in
        no-match)
            printf '%s\n' '{"number":1,"body":"different","pull_request":null}'
            ;;
        lookup-fail)
            printf '%s\n' 'lookup failed' >&2
            exit 2
            ;;
        dedup)
            printf '{"number":7,"body":"duplicate <!-- larch-stall:signature=%s -->","pull_request":null}\n' "$GH_MARKER_HASH"
            ;;
    esac
    exit 0
fi
if [ "$1" = api ] && [ "${2:-}" = --method ]; then
    printf '%s\n' '{"html_url":"https://github.com/owner/current-repo/issues/7#issuecomment-101"}'
    exit 0
fi
exit 9
EOF
    chmod +x "$dir/bin/gh"
    printf '%s\n' "$dir"
}

dir=$(make_tier_a_dedup_case case24-tier-a-dedup-no-match)
run_capture "$SANDBOX/case24-tier-a-dedup-no-match.out" env PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" GH_STUB_CASE=no-match GH_MARKER_HASH="$TIER_A_MARKER_HASH" "$SCRIPT" dedup-tier-a-report --implement-tmpdir "$dir" --body-file "$dir/body.md"
assert_eq no-match "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-a-dedup-no-match.out")" "24: Tier A dedup no-match status"
assert_not_contains 'FILE_FAILURE_REPORT_STATUS=' "$(cat "$SANDBOX/case24-tier-a-dedup-no-match.out")" "24: Tier A dedup stdout is normalized"
assert_contains 'repos/owner/current-repo/issues?state=open&per_page=100' "$(cat "$dir/gh.log")" "24: Tier A dedup binds current repo"

dir=$(make_tier_a_dedup_case case24-tier-a-dedup-lookup-fail)
run_capture "$SANDBOX/case24-tier-a-dedup-lookup-fail.out" env PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" GH_STUB_CASE=lookup-fail GH_MARKER_HASH="$TIER_A_MARKER_HASH" "$SCRIPT" dedup-tier-a-report --implement-tmpdir "$dir" --body-file "$dir/body.md"
assert_eq lookup-failed-open "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-a-dedup-lookup-fail.out")" "24: Tier A dedup lookup failure fails open"
assert_eq lookup-failed "$(kv STALL_RECOVERY_REPORT_FALLBACK_REASON "$SANDBOX/case24-tier-a-dedup-lookup-fail.out")" "24: Tier A dedup lookup failure reason"

dir=$(make_tier_a_dedup_case case24-tier-a-dedup-comment)
run_capture "$SANDBOX/case24-tier-a-dedup-comment.out" env PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" GH_STUB_CASE=dedup GH_MARKER_HASH="$TIER_A_MARKER_HASH" "$SCRIPT" dedup-tier-a-report --implement-tmpdir "$dir" --body-file "$dir/body.md"
assert_eq dedup-comment "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-a-dedup-comment.out")" "24: Tier A dedup duplicate status"
assert_eq https://github.com/owner/current-repo/issues/7#issuecomment-101 "$(kv STALL_RECOVERY_REPORT_URL "$SANDBOX/case24-tier-a-dedup-comment.out")" "24: Tier A dedup duplicate URL"

dir=$(make_tier_a_dedup_case case24-tier-a-dedup-dry-run)
run_capture "$SANDBOX/case24-tier-a-dedup-dry-run.out" env PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" dedup-tier-a-report --implement-tmpdir "$dir" --body-file "$dir/body.md"
assert_eq dry-run "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-a-dedup-dry-run.out")" "24: Tier A dedup dry-run status"
if [ ! -e "$dir/gh.log" ]; then
    pass "24: Tier A dedup dry-run makes no gh calls"
else
    fail "24: Tier A dedup dry-run makes no gh calls" "$(cat "$dir/gh.log")"
fi

dir=$(make_tier_a_dedup_case case24-tier-a-dedup-dry-run-decision)
run_capture "$SANDBOX/case24-tier-a-dedup-dry-run-decision.out" env PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" DRY_RUN_DECISION=true "$SCRIPT" dedup-tier-a-report --implement-tmpdir "$dir" --body-file "$dir/body.md"
assert_eq dry-run "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case24-tier-a-dedup-dry-run-decision.out")" "24: Tier A dedup honors DRY_RUN_DECISION"
if [ ! -e "$dir/gh.log" ]; then
    pass "24: Tier A dedup DRY_RUN_DECISION makes no gh calls"
else
    fail "24: Tier A dedup DRY_RUN_DECISION makes no gh calls" "$(cat "$dir/gh.log")"
fi

dir=$(make_tmp case24-escalation-signature-a)
cp "$SANDBOX/case23-compose/stall-recovery-classification.env" "$dir/stall-recovery-classification.env"
cp "$SANDBOX/case23-compose/stall-recovery-attempts.env" "$dir/stall-recovery-attempts.env"
cp "$SANDBOX/case23-compose/stall-recovery-root-cause.md" "$dir/stall-recovery-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-bounded-root-cause.md" "$dir/stall-recovery-bounded-root-cause.md"
cp "$SANDBOX/case23-compose/stall-recovery-sensitive-corpus.env" "$dir/stall-recovery-sensitive-corpus.env"
printf 'utc=2026-01-01T00:00:00Z\tsite=step5\ttrigger=main-agent-required\tstep=5\tphase=review\n' >"$dir/stall-recovery-escalation-ledger.tsv"
run_capture "$SANDBOX/case24-escalation-signature-a.out" env LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" compose-report --implement-tmpdir "$dir" --report-kind escalation-success --surface chat-print --output-file "$dir/chat.md"
dir2=$(make_tmp case24-escalation-signature-b)
cp "$dir/stall-recovery-classification.env" "$dir2/stall-recovery-classification.env"
cp "$dir/stall-recovery-attempts.env" "$dir2/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir2/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir2/stall-recovery-bounded-root-cause.md"
cp "$dir/stall-recovery-sensitive-corpus.env" "$dir2/stall-recovery-sensitive-corpus.env"
printf 'utc=2026-01-01T00:00:00Z\tsite=ship-pr\ttrigger=main-agent-required\tstep=5\tphase=review\n' >"$dir2/stall-recovery-escalation-ledger.tsv"
run_capture "$SANDBOX/case24-escalation-signature-b.out" env LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" compose-report --implement-tmpdir "$dir2" --report-kind escalation-success --surface chat-print --output-file "$dir2/chat.md"
if [ "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-escalation-signature-a.out")" != "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-escalation-signature-b.out")" ]; then
    pass "24: escalation public signature changes with sanitized site"
else
    fail "24: escalation public signature changes with sanitized site"
fi

dir3=$(make_tmp case24-escalation-signature-trigger)
cp "$dir/stall-recovery-classification.env" "$dir3/stall-recovery-classification.env"
cp "$dir/stall-recovery-attempts.env" "$dir3/stall-recovery-attempts.env"
cp "$dir/stall-recovery-root-cause.md" "$dir3/stall-recovery-root-cause.md"
cp "$dir/stall-recovery-bounded-root-cause.md" "$dir3/stall-recovery-bounded-root-cause.md"
cp "$dir/stall-recovery-sensitive-corpus.env" "$dir3/stall-recovery-sensitive-corpus.env"
printf 'utc=2026-01-01T00:00:00Z\tsite=step5\ttrigger=first-fixer-non-health\tstep=5\tphase=review\n' >"$dir3/stall-recovery-escalation-ledger.tsv"
run_capture "$SANDBOX/case24-escalation-signature-trigger.out" env LARCH_STALL_RECOVERY_DRY_RUN=1 "$SCRIPT" compose-report --implement-tmpdir "$dir3" --report-kind escalation-success --surface chat-print --output-file "$dir3/chat.md"
if [ "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-escalation-signature-a.out")" != "$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case24-escalation-signature-trigger.out")" ]; then
    pass "24: escalation public signature changes with sanitized trigger"
else
    fail "24: escalation public signature changes with sanitized trigger"
fi



dir=$(make_tmp case25-generic-profile)
cat >"$dir/design-failure-terminal-state.env" <<EOF
DESIGN_FAILURE_VERSION=1
DESIGN_FAILURE_KIND=terminal
FAILURE_OUTCOME=failed-judge-panel
STALL_STEP=judge-panel
PHASE=judge-panel
SITE=decompose-panel
TRIGGER=decompose-panel-retry-exhausted
BAIL_REASON=decompose-panel-retry-exhausted
EXIT_CODE=1
FAILURE_DETAIL_LOG=
SOURCE_SCRIPT=split-path
EOF
run_capture "$SANDBOX/case25-validate-token.out" "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" validate-token --token-kind step --value judge-panel
assert_eq true "$(kv VALID "$SANDBOX/case25-validate-token.out")" "25: generic validate-token accepts design step"
if "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" validate-token --token-kind step --value not-a-step >/"$SANDBOX/case25-invalid-token.out" 2>/dev/null; then
    fail "25: generic validate-token rejects unknown step"
else
    pass "25: generic validate-token rejects unknown step"
fi
run_capture "$SANDBOX/case25-validate-terminal.out" "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" validate-terminal-state --primary-state-file "$dir/design-failure-terminal-state.env"
assert_eq true "$(kv VALID "$SANDBOX/case25-validate-terminal.out")" "25: validate-terminal-state accepts design state"
run_capture "$SANDBOX/case25-classify.out" "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" classify --primary-state-file "$dir/design-failure-terminal-state.env"
assert_contains 'CLASSIFICATION_FILE=' "$(cat "$SANDBOX/case25-classify.out")" "25: generic classify emits classification file"
[ -f "$dir/design-failure-classification.env" ] || fail "25: generic classify writes prefixed classification"
cat >"$dir/design-failure-root-cause.md" <<EOF
verdict=larch-defect
confidence=medium
summary=Decompose panel retry exhausted

Evidence cites bounded design state.
EOF
cp "$dir/design-failure-root-cause.md" "$dir/design-failure-bounded-root-cause.md"
: >"$dir/design-failure-sensitive-corpus.env"
run_capture "$SANDBOX/case25-compose.out" env LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" compose-report --report-kind terminal-failure --surface chat-print
assert_contains '[Bug] /design terminal:' "$(cat "$dir/design-failure-chat-print.md")" "25: generic title says /design"
assert_contains '## /design terminal-failure report' "$(cat "$dir/design-failure-chat-print.md")" "25: generic body says /design"
assert_contains 'larch-stall:signature=' "$(cat "$dir/design-failure-chat-print.md")" "25: generic marker present"
mkdir -p "$dir/bin"
cat >"$dir/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s
' "$*" >>"$GH_LOG"
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    printf '%s
' '{"number":1,"body":"different","pull_request":null}'
    exit 0
fi
if [ "$1" = issue ] && [ "${2:-}" = create ]; then
    printf '%s
' 'https://github.com/character-ai/larch/issues/125'
    exit 0
fi
exit 9
EOF
chmod +x "$dir/bin/gh"
run_capture "$SANDBOX/case25-compose-file.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" compose-report --report-kind terminal-failure --surface chat-print
assert_eq filed "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case25-compose-file.out")" "25: generic Tier B filing uses prefixed artifacts"
assert_eq https://github.com/character-ai/larch/issues/125 "$(kv STALL_RECOVERY_REPORT_URL "$SANDBOX/case25-compose-file.out")" "25: generic Tier B filing emits URL"
assert_contains 'issue create -R character-ai/larch --title [Bug] /design terminal:' "$(cat "$dir/gh.log")" "25: generic Tier B filing passes design title"
design_marker_hash=$(grep -Eo '<!-- larch-stall:signature=[0-9a-f]{64} -->' "$dir/design-failure-chat-print.md" | head -n 1 | sed 's/^<!-- larch-stall:signature=//; s/ -->$//')
cat >"$dir/bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s
' "$*" >>"$GH_LOG"
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    printf '{"number":125,"body":"duplicate <!-- larch-stall:signature=%s -->","pull_request":null}
' "$DESIGN_MARKER_HASH"
    exit 0
fi
if [ "$1" = api ] && [ "${2:-}" = --method ]; then
    input=""
    prev=""
    for arg in "$@"; do
        if [ "$prev" = --input ]; then input=$arg; fi
        prev=$arg
    done
    [ -n "$input" ] && cp "$input" "$GH_COMMENT_CAPTURE"
    printf '%s
' '{"html_url":"https://github.com/character-ai/larch/issues/125#issuecomment-25"}'
    exit 0
fi
exit 9
EOF
chmod +x "$dir/bin/gh"
: >"$dir/gh.log"
run_capture "$SANDBOX/case25-compose-dedup.out" env -u LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES PATH="$dir/bin:$PATH" GH_LOG="$dir/gh.log" DESIGN_MARKER_HASH="$design_marker_hash" GH_COMMENT_CAPTURE="$dir/comment.json" "$SCRIPT" --profile generic --artifact-prefix design-failure --implement-tmpdir "$dir" compose-report --report-kind terminal-failure --surface chat-print
assert_eq dedup-comment "$(kv STALL_RECOVERY_REPORT_STATUS "$SANDBOX/case25-compose-dedup.out")" "25: generic Tier B dedup validates prefixed corpus"
assert_eq https://github.com/character-ai/larch/issues/125#issuecomment-25 "$(kv STALL_RECOVERY_REPORT_URL "$SANDBOX/case25-compose-dedup.out")" "25: generic Tier B dedup emits comment URL"
assert_contains '+1 occurrence' "$(cat "$dir/comment.json")" "25: generic Tier B dedup posts occurrence comment"
assert_not_contains 'issue create' "$(cat "$dir/gh.log")" "25: generic Tier B dedup skips create"

impl_dir=$(make_tmp case25-implement-defaults)
cat >"$impl_dir/ship-pr-state.sh" <<EOF
STALL_TRACKING=true
STALL_STEP=5
PHASE=review
BAIL_REASON=main-agent-required
EXIT_CODE=1
DISPATCHER=claude
EOF
run_capture "$SANDBOX/case25-implement-classify.out" "$SCRIPT" classify --implement-tmpdir "$impl_dir"
[ -f "$impl_dir/stall-recovery-classification.env" ] || fail "25: implement default classification filename remains stall-recovery"
[ ! -e "$impl_dir/design-failure-classification.env" ] || fail "25: implement default must not write design prefix"
pass "25: implement default filenames remain unchanged"

sig_impl=$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case23-compose.out" 2>/dev/null || true)
sig_design=$(kv REPORT_DEDUP_SIGNATURE "$SANDBOX/case25-compose.out")
[ -z "$sig_impl" ] || [ "$sig_impl" != "$sig_design" ] || fail "25: generic signatures include skill/profile separation"
pass "25: generic signatures include skill/profile separation"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
