#!/usr/bin/env bash
# Offline harness for design-step3-mav.sh.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
export LARCH_QUIET_DISABLE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-step3-mav.sh"
PASS=0
FAIL=0
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-design-step3-mav.XXXXXX")"
TMPROOT="$(cd "$TMPROOT" && pwd -P)"
trap 'rm -rf "$TMPROOT"' EXIT
BASH_BIN="$(command -v bash)"
PLUGIN_VERSION="$(awk -F '"' '$2 == "version" { print $4 }' "$ROOT/.claude-plugin/plugin.json")"
case "$(uname -s):$(uname -m)" in
    Darwin:arm64|Darwin:aarch64) LARCH_TARGET=aarch64-apple-darwin ;;
    Darwin:x86_64|Darwin:amd64) LARCH_TARGET=x86_64-apple-darwin ;;
    Linux:arm64|Linux:aarch64) LARCH_TARGET=aarch64-unknown-linux-gnu ;;
    Linux:x86_64|Linux:amd64) LARCH_TARGET=x86_64-unknown-linux-gnu ;;
    *) echo "FAIL: unsupported harness target" >&2; exit 1 ;;
esac
export LARCH_BINARY="$TMPROOT/larch-fixture"
cat >"$LARCH_BINARY" <<EOF2
#!$BASH_BIN
set -u
if [[ "\${1:-}" == --version ]]; then printf '%s\n' 'larch $PLUGIN_VERSION'; exit 0; fi
if [[ "\${1:-}" == bootstrap && "\${2:-}" == self-check ]]; then
    printf '%s\n' '{"schema_version":1,"version":"$PLUGIN_VERSION","target":"$LARCH_TARGET"}'
    exit 0
fi
if [[ "\${1:-}" == render && "\${2:-}" == scope-anchor ]]; then
    exec "$ROOT/target/debug/larch" "\$@"
fi
if [[ "\${1:-}" == session ]]; then
    case "\${2:-}" in
        require-plugin-root|validate-design-tmpdir) exit 0 ;;
    esac
fi
if [[ "\${1:-}" == kv && "\${2:-}" == get ]]; then
    shift 2
    key="" file="" value=""
    while [[ \$# -gt 0 ]]; do
        case "\$1" in
            --key) key="\$2"; shift 2 ;;
            --file) file="\$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    while IFS= read -r line || [[ -n "\$line" ]]; do
        case "\$line" in "\$key="*) value="\${line#*=}" ;; esac
    done <"\$file"
    printf '%s\n' "\$value"
    exit 0
fi
if [[ "\${1:-}" == run-log && "\${2:-}" == append-failure ]]; then
    shift 2
    log="" category="" output_file=""
    while [[ \$# -gt 0 ]]; do
        case "\$1" in
            --log) log="\$2"; shift 2 ;;
            --category) category="\$2"; shift 2 ;;
            --output-file) output_file="\$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "\$log" && -n "\$category" ]] || exit 1
    { printf '### %s\n\n' "\$category"; [[ -f "\$output_file" ]] && cat "\$output_file"; } >>"\$log"
    printf 'APPENDED=true\nLOG=%s\n' "\$log"
    exit 0
fi
if [[ "\${1:-}" == voting && "\${2:-}" == findings-classification-header ]]; then
    printf 'finding_id\tfinding_reviewers\tvoting_result\n'
    exit 0
fi
if [[ "\${1:-}" == plan-review && "\${2:-}" == persist-retally-env ]]; then
    exec "$ROOT/target/debug/larch" "\$@"
fi
if [[ "\${1:-}" == design && "\${2:-}" == read-result-env ]]; then
    exec "$ROOT/target/debug/larch" "\$@"
fi
if [[ "\${1:-}" == plan-review && "\${2:-}" == tally ]]; then
    shift 2
    ballot="" design="" voter="" classification=""
    while [[ \$# -gt 0 ]]; do
        case "\$1" in
            --ballot-file) ballot="\$2"; shift 2 ;;
            --design-tmpdir) design="\$2"; shift 2 ;;
            --voter) voter="\${2#*:}"; shift 2 ;;
            --findings-classification-out) classification="\$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    : >"\$design/accepted-plan-findings.md"
    : >"\$design/rejected-findings.md"
    : >"\$design/oos.md"
    if grep -Eq '^FINDING_1:[[:space:]]*YES' "\$voter"; then
        cp "\$ballot" "\$design/accepted-plan-findings.md"
    fi
    printf 'finding_id\tfinding_reviewers\tvoting_result\n' >"\$classification"
    printf '# Plan Review Voting Tally\n' >"\$design/voting-tally.md"
    printf 'TALLY_PLAN_REVIEW_STATUS=ok\nVOTING_TALLY_FILE=%s/voting-tally.md\n' "\$design"
    exit 0
fi
exit 2
EOF2
chmod +x "$LARCH_BINARY"

pass() { printf '  ok: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf 'FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if printf '%s\n' "$haystack" | command grep -Fq "$needle"; then
        pass "$label"
    else
        fail "$label missing: $needle"
    fi
}

assert_file_contains() {
    local file="$1" needle="$2" label="$3"
    if ( command grep -Fq "$needle" "$file" ); then
        pass "$label"
    else
        fail "$label missing: $needle"
    fi
}

make_session_env() {
    local dir="$1"
    local env_file="$dir/session-env.sh"
    cat >"$env_file" <<EOF2
export DESIGN_TMPDIR='$dir'
export CLAUDE_PLUGIN_ROOT='$ROOT'
export ISSUE_NUMBER='1'
EOF2
    printf '%s\n' "$env_file"
}

write_ballot() {
    local dir="$1"
    cat >"$dir/ballot.txt" <<'BALLOT'
### FINDING_1: Fix parser
- **Reviewer**: Cursor-Arch
- focus-area = correctness
- Concern: parser misses bad input.
BALLOT
}

run_subject() {
    local dir="$1" phase="$2" env_file
    env_file="$(make_session_env "$dir")"
    CLAUDE_PLUGIN_ROOT="$ROOT" "$SUBJECT" \
        --session-env-path "$env_file" \
        --claude-pid test \
        --plugin-root "$ROOT" \
        --phase "$phase"
}

make_result_envs() {
    local dir="$1" status="${2:-main-agent-vote-required}" round="${3:-2}"
    cat >"$dir/.step3-plan-review-result.env" <<EOF2
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUNDS_COMPLETED=1
STEP3_REVIEW_ROUND_NUM=$round
EOF2
    cat >"$dir/.step3-review-result.env" <<EOF2
LOOP_STATUS=main-agent-vote-required
STEP3_REVIEW_LOOP_STATUS=$status
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUND_NUM=$round
EOF2
}

echo '=== pause gate contract ==='
D_PAUSE="$TMPROOT/pause"
mkdir -p "$D_PAUSE"
: >"$D_PAUSE/.pause-requested"
FAKE_PLUGIN="$TMPROOT/fake-plugin"
mkdir -p "$FAKE_PLUGIN/scripts"
# The wrappers reach the Rust session verbs through the verified bootstrap.
cat >"$FAKE_PLUGIN/scripts/larch.sh" <<'LARCH_STUB'
#!/usr/bin/env bash
set -uo pipefail
case "${1:-} ${2:-}" in
  "session require-plugin-root"|"session validate-design-tmpdir") exit 0 ;;
  "design pause-save")
    shift 2
    printf '%s' "PAUSE_STUB_ARGS="
    previous=""
    for argument in "$@"; do
      if [ "$previous" = "--issue" ] && [ -z "$argument" ]; then
        exit 7
      fi
      printf '<%s>' "$argument"
      previous="$argument"
    done
    printf '\n'
    exit 0
    ;;
esac
printf '%s\n' "unexpected larch command: $*" >&2
exit 64
LARCH_STUB
chmod +x "$FAKE_PLUGIN/scripts/larch.sh"
cat >"$D_PAUSE/session-env.sh" <<EOF2
export DESIGN_TMPDIR='$D_PAUSE'
export ISSUE_NUMBER='42'
EOF2
_pause_out=$(CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" "$SUBJECT" --session-env-path "$D_PAUSE/session-env.sh" --claude-pid test --plugin-root "$FAKE_PLUGIN" --phase pre)
assert_contains "$_pause_out" 'PAUSE_STUB_ARGS=<--design-tmpdir>' 'pause gate execs pause-save before MAV work'
assert_contains "$_pause_out" '<--issue><42>' 'pause gate forwards issue number'
cat >"$D_PAUSE/session-env-missing-issue.sh" <<EOF2
export DESIGN_TMPDIR='$D_PAUSE'
export ISSUE_NUMBER=''
EOF2
set +e
_pause_missing_rc=0
CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" "$SUBJECT" --session-env-path "$D_PAUSE/session-env-missing-issue.sh" --claude-pid test --plugin-root "$FAKE_PLUGIN" --phase pre >/dev/null 2>&1 || _pause_missing_rc=$?
set -e
if [ "$_pause_missing_rc" -eq 7 ]; then pass 'pause gate surfaces missing ISSUE_NUMBER failure'; else fail "pause missing issue rc=$_pause_missing_rc"; fi

echo '=== pre phase safe env and evidence ==='
D_PRE="$TMPROOT/pre"
mkdir -p "$D_PRE"
printf 'anchor says BALLOT_PATH=/tmp/evil\n' >"$D_PRE/anchor.txt"
cat >"$D_PRE/.step3-plan-review-result.env" <<EOF2
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
STEP3_REVIEW_ROUND_NUM=4
SCOPE_ANCHOR_FILE=$D_PRE/secondary-anchor.txt
EOF2
cat >"$D_PRE/.step3-review-result.env" <<EOF2
STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
SCOPE_ANCHOR_FILE=$D_PRE/anchor.txt
EOF2
_pre_out=$(run_subject "$D_PRE" pre)
assert_contains "$_pre_out" 'SCOPE_ANCHOR_EVIDENCE: Plan-review scope anchor' 'pre prefixes rendered scope evidence'
assert_contains "$_pre_out" 'SCOPE_ANCHOR_EVIDENCE: anchor says BALLOT_PATH=/tmp/evil' 'pre prefixes KV-looking anchor content'
assert_contains "$_pre_out" 'DESIGN_STEP3_MAV_KV_BEGIN' 'pre emits trusted KV begin'
assert_contains "$_pre_out" "BALLOT_PATH=$D_PRE/ballot.txt" 'pre emits ballot path in trusted section'
assert_contains "$_pre_out" "SCOPE_ANCHOR_FILE=$D_PRE/anchor.txt" 'primary result env wins for scope anchor'
assert_contains "$_pre_out" 'STEP3_RESUME_ROUND=4' 'secondary fills absent resume round key'

D_FALLBACK="$TMPROOT/session-fallback"
mkdir -p "$D_FALLBACK"
cat >"$D_FALLBACK/session-env.sh" <<EOF2
export DESIGN_TMPDIR='$D_FALLBACK'
export CLAUDE_PLUGIN_ROOT='$ROOT'
export ISSUE_NUMBER='1'
export ROUND_NUM='7'
EOF2
_fallback_out=$(CLAUDE_PLUGIN_ROOT="$ROOT" "$SUBJECT" --session-env-path "$D_FALLBACK/session-env.sh" --claude-pid test --plugin-root "$ROOT" --phase pre)
assert_contains "$_fallback_out" 'STEP3_RESUME_ROUND=7' 'session env supplies fallback round when result envs are absent'

D_SYM="$TMPROOT/symlink"
mkdir -p "$D_SYM"
printf 'ROUND_NUM=1\n' >"$D_SYM/target.env"
ln -s "$D_SYM/target.env" "$D_SYM/.step3-review-result.env"
set +e
_sym_rc=0
run_subject "$D_SYM" pre >/dev/null 2>&1 || _sym_rc=$?
set -e
if [ "$_sym_rc" -ne 0 ]; then pass 'pre rejects symlinked primary result env'; else fail 'pre should reject symlinked primary result env'; fi

D_BROKEN_SYM="$TMPROOT/broken-symlink"
mkdir -p "$D_BROKEN_SYM"
ln -s /tmp/larch-missing-step3-review-result.env "$D_BROKEN_SYM/.step3-review-result.env"
printf 'ROUND_NUM=9\n' >"$D_BROKEN_SYM/.step3-plan-review-result.env"
set +e
_broken_sym_rc=0
run_subject "$D_BROKEN_SYM" pre >/dev/null 2>&1 || _broken_sym_rc=$?
set -e
if [ "$_broken_sym_rc" -ne 0 ]; then pass 'pre rejects broken symlink primary result env'; else fail 'pre should reject broken symlink primary result env'; fi

D_RENDER_FAIL="$TMPROOT/render-fail"
mkdir -p "$D_RENDER_FAIL"
printf 'outside\n' >"$TMPROOT/outside-anchor.txt"
printf 'SCOPE_ANCHOR_FILE=%s\n' "$TMPROOT/outside-anchor.txt" >"$D_RENDER_FAIL/.step3-review-result.env"
set +e
_render_rc=0
run_subject "$D_RENDER_FAIL" pre >/dev/null 2>&1 || _render_rc=$?
set -e
if [ "$_render_rc" -ne 0 ]; then pass 'pre propagates scope renderer failure'; else fail 'pre should fail for outside scope anchor'; fi

echo '=== post phase routing ==='
D_POST="$TMPROOT/post-accepted"
mkdir -p "$D_POST/plan-review/round-2"
make_result_envs "$D_POST" main-agent-vote-required 2
write_ballot "$D_POST"
printf 'FINDING_1: YES\n' >"$D_POST/voter-main-agent.txt"
printf '1\n' >"$D_POST/plan-review/round-2/round-start-s"
_post_out=$(run_subject "$D_POST" post)
assert_contains "$_post_out" 'TALLY_PLAN_REVIEW_STATUS=ok' 'post emits ok tally status'
assert_contains "$_post_out" 'ACCEPTED_COUNT=1' 'post counts accepted finding'
assert_contains "$_post_out" 'PHASE=awaiting-apply' 'post routes accepted loop round to awaiting-apply'
if [ "$(cat "$D_POST/.step3-round-2.phase")" = 'awaiting-apply' ]; then pass 'post writes awaiting-apply phase file'; else fail 'post awaiting-apply phase file wrong'; fi
if [ -s "$D_POST/plan-review/round-2/findings-classification.tsv" ]; then pass 'post writes round-local findings classification'; else fail 'post missing findings classification'; fi
assert_file_contains "$D_POST/execution-issues.md" '0-judge plan-review panel' 'post appends 0-judge warning'
_warn_before=$(wc -l <"$D_POST/execution-issues.md")
_post_again=$(run_subject "$D_POST" post)
_warn_after=$(wc -l <"$D_POST/execution-issues.md")
if [ "$_warn_before" -eq "$_warn_after" ]; then pass 'post warning append is idempotent'; else fail 'post warning appended more than once'; fi

D_ZERO="$TMPROOT/post-zero"
mkdir -p "$D_ZERO/plan-review/round-3"
make_result_envs "$D_ZERO" main-agent-vote-required 3
write_ballot "$D_ZERO"
printf 'FINDING_1: NO\n' >"$D_ZERO/voter-main-agent.txt"
_zero_out=$(run_subject "$D_ZERO" post)
assert_contains "$_zero_out" 'ACCEPTED_COUNT=0' 'post counts zero accepted findings'
assert_contains "$_zero_out" 'PHASE=awaiting-continuation' 'post routes zero accepted loop round to awaiting-continuation'
if [ "$(cat "$D_ZERO/.step3-round-3.phase")" = 'awaiting-continuation' ]; then pass 'post writes awaiting-continuation phase file'; else fail 'post awaiting-continuation phase file wrong'; fi

D_ERR="$TMPROOT/post-error"
mkdir -p "$D_ERR"
printf 'stale anchor\n' >"$D_ERR/stale-scope-anchor.txt"
cat >"$D_ERR/.step3-plan-review-result.env" <<EOF2
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
SCOPE_ANCHOR_FILE=$D_ERR/stale-scope-anchor.txt
ACCEPTED_COUNT=3
IMPORTANT_ACCEPTED_COUNT=2
EOF2
cat >"$D_ERR/.step3-review-result.env" <<EOF2
LOOP_STATUS=main-agent-vote-required
STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUND_NUM=4
SCOPE_ANCHOR_FILE=$D_ERR/stale-scope-anchor.txt
IMPORTANT_ACCEPTED_COUNT=2
EOF2
cat >"$D_ERR/accepted-plan-findings.md" <<'EOF2'
### FINDING_99: Partial failed re-tally accepted
- **Concern**: should be cleared
EOF2
write_ballot "$D_ERR"
_err_out=$(run_subject "$D_ERR" post)
assert_contains "$_err_out" 'NEXT_ACTION=step3b-bypass' 'post emits NEXT_ACTION on tally-error'
assert_contains "$_err_out" 'TALLY_PLAN_REVIEW_STATUS=tally-error' 'post handles missing voter as tally-error'
assert_contains "$_err_out" 'PHASE=unchanged' 'post does not route phase on tally-error'
assert_file_contains "$D_ERR/.step3-review-result.env" 'TALLY_PLAN_REVIEW_STATUS=tally-error' 'post persists tally-error to review env'
assert_file_contains "$D_ERR/.step3-review-result.env" 'NEXT_ACTION=step3b-bypass' 'post persists NEXT_ACTION to review env'
if [ ! -e "$D_ERR/.step3-round-4.phase" ]; then pass 'post does not write phase file on tally-error'; else fail 'post should not write phase on tally-error'; fi
assert_file_contains "$D_ERR/execution-issues.md" '0-judge plan-review panel' 'post appends warning on tally-error'
if ( command grep -q '^SCOPE_ANCHOR_FILE=' "$D_ERR/.step3-plan-review-result.env" ); then fail 'tally-error must omit scope anchor from plan-review result env'; else pass 'tally-error omits scope anchor from plan-review result env'; fi
if ( command grep -q '^SCOPE_ANCHOR_FILE=' "$D_ERR/.step3-review-result.env" ); then fail 'tally-error must omit scope anchor from review result env'; else pass 'tally-error omits scope anchor from review result env'; fi
assert_file_contains "$D_ERR/.step3-plan-review-result.env" 'ACCEPTED_COUNT=0' 'tally-error zeros ACCEPTED_COUNT in plan-review env'
assert_file_contains "$D_ERR/.step3-review-result.env" 'IMPORTANT_ACCEPTED_COUNT=0' 'tally-error zeros IMPORTANT_ACCEPTED_COUNT in review env'
if [ ! -s "$D_ERR/accepted-plan-findings.md" ]; then pass 'tally-error clears partial accepted-plan-findings.md'; else fail 'tally-error should clear partial accepted-plan-findings.md'; fi
if [ -s "$D_ERR/plan-review/round-4/findings-classification.tsv" ]; then pass 'tally-error writes canonical findings-classification header'; else fail 'tally-error missing findings-classification header'; fi

D_MAL="$TMPROOT/post-malformed"
mkdir -p "$D_MAL"
make_result_envs "$D_MAL" main-agent-vote-required 5
write_ballot "$D_MAL"
printf 'not a valid vote\n' >"$D_MAL/voter-main-agent.txt"
_mal_before=$(cat "$D_MAL/voter-main-agent.txt")
_mal_out=$(run_subject "$D_MAL" post)
_mal_after=$(cat "$D_MAL/voter-main-agent.txt")
assert_contains "$_mal_out" 'TALLY_PLAN_REVIEW_STATUS=ok' 'post preserves readable malformed voter as tally input'
if [ "$_mal_before" = "$_mal_after" ]; then pass 'post leaves readable malformed voter file unchanged'; else fail 'post should preserve malformed voter file'; fi

D_SINGLE="$TMPROOT/post-single"
mkdir -p "$D_SINGLE"
cat >"$D_SINGLE/.step3-review-result.env" <<'EOF2'
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUND_NUM=6
EOF2
write_ballot "$D_SINGLE"
printf 'FINDING_1: YES\n' >"$D_SINGLE/voter-main-agent.txt"
_single_out=$(run_subject "$D_SINGLE" post)
assert_contains "$_single_out" 'PHASE=unchanged' 'legacy single mode preserves phase unchanged'
if compgen -G "$D_SINGLE/.step3-round-*.phase" >/dev/null; then fail 'legacy single mode should not create phase file'; else pass 'legacy single mode does not create phase file'; fi

D_ROUND="$TMPROOT/post-round-precedence"
mkdir -p "$D_ROUND/plan-review/round-8" "$D_ROUND/plan-review/round-9"
cat >"$D_ROUND/.step3-review-result.env" <<'EOF2'
LOOP_STATUS=main-agent-vote-required
STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
ROUND_NUM=8
ROUNDS_COMPLETED=9
EOF2
write_ballot "$D_ROUND"
printf 'FINDING_1: YES\n' >"$D_ROUND/voter-main-agent.txt"
_round_out=$(run_subject "$D_ROUND" post)
if [ -s "$D_ROUND/plan-review/round-8/findings-classification.tsv" ]; then pass 'ROUND_NUM takes precedence for round artifact output'; else fail 'ROUND_NUM precedence missing round-8 classification'; fi
if [ ! -s "$D_ROUND/plan-review/round-9/findings-classification.tsv" ]; then pass 'ROUNDS_COMPLETED does not override ROUND_NUM for artifacts'; else fail 'ROUNDS_COMPLETED should not receive classification when ROUND_NUM is set'; fi

echo '=== per-round warning sentinel ==='
D_WARN2="$TMPROOT/warn-round-2"
mkdir -p "$D_WARN2/plan-review/round-2"
make_result_envs "$D_WARN2" main-agent-vote-required 2
write_ballot "$D_WARN2"
printf 'FINDING_1: YES\n' >"$D_WARN2/voter-main-agent.txt"
run_subject "$D_WARN2" post >/dev/null
D_WARN3="$TMPROOT/warn-round-3"
mkdir -p "$D_WARN3/plan-review/round-3"
make_result_envs "$D_WARN3" main-agent-vote-required 3
write_ballot "$D_WARN3"
printf 'FINDING_1: YES\n' >"$D_WARN3/voter-main-agent.txt"
run_subject "$D_WARN3" post >/dev/null
if [ -f "$D_WARN2/.step3-main-agent-adjudication-warning-appended-r2" ] && [ -f "$D_WARN3/.step3-main-agent-adjudication-warning-appended-r3" ]; then
    pass 'warning sentinel is per artifact round'
else
    fail 'warning sentinel should be keyed by artifact round'
fi
if [ -f "$D_WARN2/step3-main-agent-adjudication-r2.warning.log" ] && [ -f "$D_WARN3/step3-main-agent-adjudication-r3.warning.log" ]; then
    pass 'warning log is per artifact round'
else
    fail 'warning log should be keyed by artifact round'
fi

echo '=== loop mode invalid resume round ==='
D_BAD_RESUME="$TMPROOT/bad-resume"
mkdir -p "$D_BAD_RESUME"
cat >"$D_BAD_RESUME/.step3-review-result.env" <<'EOF2'
LOOP_STATUS=main-agent-vote-required
STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
EOF2
write_ballot "$D_BAD_RESUME"
printf 'FINDING_1: YES\n' >"$D_BAD_RESUME/voter-main-agent.txt"
set +e
_bad_resume_rc=0
run_subject "$D_BAD_RESUME" post >/dev/null 2>&1 || _bad_resume_rc=$?
set -e
if [ "$_bad_resume_rc" -eq 1 ]; then pass 'post aborts loop mode with invalid resume round'; else fail "post should exit 1 for invalid resume round, got $_bad_resume_rc"; fi

echo '=== launcher transport stub ==='
D_LAUNCHER="$TMPROOT/launcher"
mkdir -p "$D_LAUNCHER"
make_result_envs "$D_LAUNCHER" main-agent-vote-required 2
write_ballot "$D_LAUNCHER"
_launcher_env="$(make_session_env "$D_LAUNCHER")"
FAKE_LAUNCHER="$TMPROOT/fake-design-run.sh"
cat >"$FAKE_LAUNCHER" <<EOF2
#!/usr/bin/env bash
script="\$1"
shift
exec "$ROOT/skills/design/scripts/\$script" "\$@"
EOF2
chmod +x "$FAKE_LAUNCHER"
_launcher_out=$("$FAKE_LAUNCHER" design-step3-mav.sh \
    --session-env-path "$_launcher_env" \
    --claude-pid test \
    --plugin-root "$ROOT" \
    --phase pre)
assert_contains "$_launcher_out" 'DESIGN_STEP3_MAV_KV_BEGIN' 'launcher stub reaches MAV pre subject'

echo '=== prose regression pins ==='
SKILL_FILE="$ROOT/skills/design/SKILL.md"
PLAN_REVIEW_FILE="$ROOT/skills/design/references/plan-review-runtime.md"
APPROVAL_GATES_FILE="$ROOT/skills/design/references/approval-gates.md"
assert_file_contains "$SKILL_FILE" 'design-step3-mav.sh --phase pre' 'SKILL delegates MAV pre phase'
assert_file_contains "$SKILL_FILE" "\"\$HOME/.cache/larch/sessions/design-run-\$PPID.sh\" design-step3-mav.sh --phase pre" 'SKILL pins MAV pre launcher fence'
assert_file_contains "$SKILL_FILE" "\"\$HOME/.cache/larch/sessions/design-run-\$PPID.sh\" design-step3-mav.sh --phase post" 'SKILL pins MAV post launcher fence'
assert_file_contains "$SKILL_FILE" 'DESIGN_STEP3_MAV_KV_BEGIN' 'SKILL parses MAV trusted sentinel'
assert_file_contains "$PLAN_REVIEW_FILE" 'design-step3-mav.sh --phase pre' 'plan-review delegates MAV pre phase'
if ( command grep -Fq '_RETALLY_SCOPE_ANCHOR_IN' "$SKILL_FILE" "$PLAN_REVIEW_FILE" "$APPROVAL_GATES_FILE" ); then fail 'prose should not contain prompt-side retally anchor binding'; else pass 'prose removed prompt-side retally anchor binding'; fi
# shellcheck disable=SC2016 # Literal prose probe.
if ( command grep -Fq 'end_s=$(date +%s)' "$SKILL_FILE" "$PLAN_REVIEW_FILE" ); then fail 'prose should not contain prompt-side raw date timing'; else pass 'prose removed prompt-side raw date timing'; fi

TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    printf 'PASS: test-design-step3-mav.sh - %s/%s assertions\n' "$PASS" "$TOTAL"
else
    printf 'FAIL: test-design-step3-mav.sh - %s/%s assertions failed\n' "$FAIL" "$TOTAL" >&2
    exit 1
fi
