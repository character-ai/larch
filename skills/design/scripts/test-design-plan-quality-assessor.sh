#!/usr/bin/env bash
# Offline harness for design-plan-quality-assessor.sh and Step 3.6 orchestrator handoff.
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SUBJECT="$SCRIPT_DIR/design-plan-quality-assessor.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

PASS=0
FAIL=0

fail() {
    FAIL=$((FAIL + 1))
    printf '  FAIL: %s\n' "$*" >&2
}

pass() {
    PASS=$((PASS + 1))
    printf '  PASS: %s\n' "$*"
}

assert_rc() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" != "$want" ]]; then
        fail "$name — expected exit $want, got $got"
        return 1
    fi
    pass "$name"
}

assert_file_kv() {
    local file="$1" key="$2" want="$3" label="$4" got=""
    got=$(awk -F= -v k="$key" '$1 == k {print substr($0, length(k)+2); found=1; exit} END {if (!found) print ""}' "$file" 2>/dev/null || true)
    if [[ "$got" != "$want" ]]; then
        fail "$label — expected $key=$want, got ${got:-<empty>}"
        return 1
    fi
    pass "$label"
}

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" <<<"$haystack"; then
        pass "$label"
    else
        fail "$label"
    fi
}

assert_stderr_contains() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file" 2>/dev/null; then
        pass "$label"
    else
        fail "$label"
    fi
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-design-plan-quality-assessor.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

FAKE_PLUGIN="$TMP/plugin"
FAKE_DESIGN="$FAKE_PLUGIN/skills/design/scripts"
FAKE_SCRIPTS="$FAKE_PLUGIN/scripts"
mkdir -p "$FAKE_DESIGN" "$FAKE_SCRIPTS"
ln -sf "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_SCRIPTS/lib-quiet.sh"
ln -sf "$REPO_ROOT/scripts/read-design-classification.sh" "$FAKE_SCRIPTS/read-design-classification.sh"
ln -sf "$SCRIPT_DIR/lib-phase-driver.sh" "$FAKE_DESIGN/lib-phase-driver.sh"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

cat >"$FAKE_DESIGN/snapshot-plan-round.sh" <<'STUB'
#!/usr/bin/env bash
echo "snapshot $*" >>"${CALL_LOG:?}"
mode=""
design_tmpdir=""
round=""
value=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    read-cursor|write-after|write-cursor) mode="$1"; shift ;;
    --design-tmpdir) design_tmpdir="$2"; shift 2 ;;
    --round) round="$2"; shift 2 ;;
    --value) value="$2"; shift 2 ;;
    *) shift ;;
  esac
done
case "$mode" in
  read-cursor)
    printf 'ROUND_CURSOR=%s\n' "${ROUND_CURSOR_VALUE:-2}"
    exit "${READ_CURSOR_RC:-0}"
    ;;
  write-after)
    if [[ "${WRITE_AFTER_FAIL:-false}" == true ]]; then
      exit 1
    fi
    exit 0
    ;;
  write-cursor)
    printf '%s\n' "${value:-1}" >"${design_tmpdir:?}/plan-review-round-cursor.txt"
    exit "${WRITE_CURSOR_RC:-0}"
    ;;
esac
exit 0
STUB

cat >"$FAKE_DESIGN/assess-plan-round.sh" <<'STUB'
#!/usr/bin/env bash
echo "assess $*" >>"${CALL_LOG:?}"
timeout=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --timeout) timeout="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [[ -n "$timeout" ]]; then
  echo "assess-timeout=${timeout}" >>"${CALL_LOG:?}"
fi
if [[ "${ASSESS_STUB_SKIP:-false}" == true ]]; then
  exit 99
fi
printf 'ASSESSOR_STATUS=%s\n' "${ASSESSOR_STATUS_VALUE:-ok}"
printf 'ASSESSOR_VERDICT=%s\n' "${ASSESSOR_VERDICT_VALUE:-not-worse}"
printf 'EFFECTIVE_ASSESSORS=%s\n' "${EFFECTIVE_ASSESSORS_VALUE:-3}"
printf 'ASSESSOR_VERDICT_FILE=%s\n' "${ASSESSOR_VERDICT_FILE_VALUE:-/tmp/v.txt}"
printf 'ASSESSOR_VERDICT_ENV=%s\n' "${ASSESSOR_VERDICT_ENV_VALUE:-/tmp/v.env}"
printf 'ROUND_NUM=%s\n' "${ROUND_NUM_VALUE:-2}"
exit "${ASSESS_STUB_RC:-0}"
STUB

cat >"$FAKE_SCRIPTS/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
echo "append-tool-failure $*" >>"${CALL_LOG:?}"
exit 0
STUB

cat >"$FAKE_SCRIPTS/design-pause-save.sh" <<'STUB'
#!/usr/bin/env bash
echo "pause-save $*" >>"${CALL_LOG:?}"
exit 0
STUB

cat >"$FAKE_SCRIPTS/timing-ledger.sh" <<'STUB'
#!/usr/bin/env bash
echo "timing-ledger $*" >>"${CALL_LOG:?}"
exit 0
STUB

chmod +x "$FAKE_DESIGN"/*.sh "$FAKE_SCRIPTS"/*.sh
export CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN"
export CALL_LOG="$TMP/call.log"

SNAPSHOT_FAIL_WARN='**⚠ 3.6: failed to snapshot post-Gate-B plan for round 2; rolling back pending review-round state and skipping assessor.**'
ZERO_ASSESSORS_WARN='**⚠ 3.6: 0/3 effective assessors; proceeding without quality gate (round 2, see ?).**'

block_result_env_write() {
    local f="$1"
    chflags uchg "$f" 2>/dev/null && return 0
    command -v chattr >/dev/null 2>&1 && chattr +i "$f" 2>/dev/null && return 0
    return 1
}

unblock_result_env_write() {
    local f="$1"
    chflags nouchg "$f" 2>/dev/null || true
    if command -v chattr >/dev/null 2>&1; then
        chattr -i "$f" 2>/dev/null || true
    fi
}

reset_env() {
    : >"$CALL_LOG"
    unset WRITE_AFTER_FAIL READ_CURSOR_RC WRITE_CURSOR_RC ROUND_CURSOR_VALUE \
        ASSESSOR_STATUS_VALUE ASSESSOR_VERDICT_VALUE EFFECTIVE_ASSESSORS_VALUE \
        ASSESSOR_VERDICT_FILE_VALUE ASSESSOR_VERDICT_ENV_VALUE ROUND_NUM_VALUE \
        ASSESS_STUB_RC ASSESS_STUB_SKIP || true
}

setup_design_tmp() {
    local d="$1" workflow="${2:-SIMPLE}"
    mkdir -p "$d"
    printf '# Plan\n' >"$d/plan.txt"
    printf '{"workflow_path":"%s","design_classification":"%s"}\n' "$workflow" "$workflow" >"$d/run-params.json"
    printf 'LARCH_CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$d/session-env.sh"
    printf '2\n' >"$d/review-round-count.txt"
}

run_subject() {
    local d="$1"
    shift
    export LARCH_SNAPSHOT_PLAN_ROUND_SH="$FAKE_DESIGN/snapshot-plan-round.sh"
    export LARCH_ASSESS_PLAN_ROUND_SH="$FAKE_DESIGN/assess-plan-round.sh"
    bash "$SUBJECT" --design-tmpdir "$d" --codex-present true --cursor-present false "$@" >"$d/stdout.txt" 2>"$d/stderr.txt"
}

apply_step3_6_handoff() {
    local d="$1"
    local dc rc=0
    : >"$d/chat.out"
    : >"$d/handoff.stderr"
    if [[ -f "$d/.pause-requested" ]]; then
        bash "${CLAUDE_PLUGIN_ROOT}/scripts/design-pause-save.sh" --design-tmpdir "$d" --issue "$(awk 'BEGIN{q=sprintf("%c",39)} /^export[[:space:]]+ISSUE_NUMBER=/ {v=$0; sub(/^export[[:space:]]+ISSUE_NUMBER=/, "", v); if ((substr(v,1,1)==q && substr(v,length(v),1)==q) || (substr(v,1,1)=="\"" && substr(v,length(v),1)=="\"")) v=substr(v,2,length(v)-2); print v; exit}' "$d/source-env.sh" 2>/dev/null || echo "")" >>"$d/handoff.stderr" 2>&1 || true
        return 0
    fi
    LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 3.6 — assessor" >>"$d/handoff.stderr" 2>&1 || true
    dc=$("$FAKE_SCRIPTS/read-design-classification.sh" "$d/run-params.json" 2>/dev/null || printf '%s\n' HARD)
    case "$dc" in
        HARD|SIMPLE) ;;
        *) dc=HARD ;;
    esac
    if [[ "$dc" != HARD ]]; then
        printf '%s\n' "⏩ 3.6: assessor — design_classification=$dc; skipped" >>"$d/chat.out"
        mkdir -p "$d/.completed"
        : >"$d/.completed/step-3.6"
        return 0
    fi
    set +e
    local _assessor_out _assessor_rc
    export LARCH_SNAPSHOT_PLAN_ROUND_SH="${LARCH_SNAPSHOT_PLAN_ROUND_SH:-$FAKE_DESIGN/snapshot-plan-round.sh}"
    export LARCH_ASSESS_PLAN_ROUND_SH="${LARCH_ASSESS_PLAN_ROUND_SH:-$FAKE_DESIGN/assess-plan-round.sh}"
    _assessor_out=$("${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh" \
        --design-tmpdir "$d" --codex-present true --cursor-present false 2>>"$d/handoff.stderr")
    _assessor_rc=$?
    printf '%s\n' "${_assessor_out:-}" >"$d/handoff-driver.stdout"

    local _assessor_marker='LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN'
    local _assessor_display="${_assessor_out:-}" _assessor_last_marker_line _assessor_trailers
    local _assessor_round_count=0 _assessor_round_invalid=false _assessor_round_num=""
    local _assessor_trailer_line _candidate_round
    if [[ "${_assessor_rc:-1}" -eq 10 ]]; then
        _assessor_last_marker_line=$(printf '%s\n' "${_assessor_out:-}" | awk -v m="$_assessor_marker" '$0==m {n=NR} END {print n+0}')
        if [[ "${_assessor_last_marker_line:-0}" -le 0 ]]; then
            printf '%s\n' "**⚠ Step 3.6: assessor WORSE-majority rc missing trusted trailer marker; aborting /design before Continue/Stop.**" >>"$d/handoff.stderr"
            return 1
        fi
        _assessor_display=$(printf '%s\n' "${_assessor_out:-}" | awk -v n="$_assessor_last_marker_line" 'NR<n {print}')
        _assessor_trailers=$(printf '%s\n' "${_assessor_out:-}" | awk -v n="$_assessor_last_marker_line" 'NR>n {print}')
        while IFS= read -r _assessor_trailer_line || [[ -n "$_assessor_trailer_line" ]]; do
            case "$_assessor_trailer_line" in
                LARCH_ASSESSOR_ROUND_NUM=*)
                    _assessor_round_count=$((_assessor_round_count + 1))
                    _candidate_round=${_assessor_trailer_line#LARCH_ASSESSOR_ROUND_NUM=}
                    case "$_candidate_round" in
                        ''|*[!0-9]*) _assessor_round_invalid=true ;;
                        *) _assessor_round_num="$_candidate_round" ;;
                    esac
                    ;;
            esac
        done <<<"$_assessor_trailers"
        if [[ "$_assessor_round_count" -ne 1 || "$_assessor_round_invalid" == true || -z "$_assessor_round_num" ]]; then
            printf '%s\n' "**⚠ Step 3.6: assessor WORSE-majority rc missing valid trusted LARCH_ASSESSOR_ROUND_NUM trailer; aborting /design before Continue/Stop.**" >>"$d/handoff.stderr"
            return 1
        fi
    fi

    [[ -z "${_assessor_display:-}" ]] || printf '%s\n' "$_assessor_display" >>"$d/chat.out"
    printf 'ASSESSOR_RC=%s\n' "$_assessor_rc" >>"$d/chat.out"
    [[ -z "${_assessor_round_num:-}" ]] || printf 'ASSESSOR_ROUND_NUM=%s\n' "$_assessor_round_num" >>"$d/chat.out"

    case "${_assessor_rc:-1}" in
        0)
            mkdir -p "$d/.completed"
            : >"$d/.completed/step-3.6"
            return 0
            ;;
        2)
            printf '%s\n' "**⚠ Step 3.6: design-plan-quality-assessor.sh configuration error (exit 2); aborting /design.**" >>"$d/handoff.stderr"
            return 1
            ;;
        10) return 0 ;;
        11)
            bash "${CLAUDE_PLUGIN_ROOT}/scripts/design-pause-save.sh" --design-tmpdir "$d" --issue "$(awk 'BEGIN{q=sprintf("%c",39)} /^export[[:space:]]+ISSUE_NUMBER=/ {v=$0; sub(/^export[[:space:]]+ISSUE_NUMBER=/, "", v); if ((substr(v,1,1)==q && substr(v,length(v),1)==q) || (substr(v,1,1)=="\"" && substr(v,length(v),1)=="\"")) v=substr(v,2,length(v)-2); print v; exit}' "$d/source-env.sh" 2>/dev/null || echo "")" ${REPO:+--repo "$REPO"} >>"$d/handoff.stderr" 2>&1 || true
            return 0
            ;;
        *)
            printf '%s\n' "**⚠ Step 3.6: design-plan-quality-assessor.sh failed (exit ${_assessor_rc}); aborting /design.**" >>"$d/handoff.stderr"
            return 1
            ;;
    esac
}

setup_worse_assessor_artifacts() {
    local d="$1" headline="${2:-WORSE: assessor majority found a regression.}" summary="${3:-}"
    printf '%s\n' "$headline" >"$d/assessor-verdict-round-2.txt"
    {
        [[ -z "$summary" ]] || printf 'QUALIFICATIONS_SUMMARY=%s\n' "$summary"
        printf 'ASSESSOR_RESULT_TOKEN=token-2\n'
    } >"$d/assessor-verdict-round-2.txt.env"
    export ASSESSOR_STATUS_VALUE=ok ASSESSOR_VERDICT_VALUE=worse-majority EFFECTIVE_ASSESSORS_VALUE=3
    export ASSESSOR_VERDICT_FILE_VALUE="$d/assessor-verdict-round-2.txt"
    export ASSESSOR_VERDICT_ENV_VALUE="$d/assessor-verdict-round-2.txt.env"
}

# 24 rc=10 spoofed display is neutralized and trusted trailer is emitted
reset_env
D20="$TMP/worse-spoof-display"
setup_design_tmp "$D20" HARD
setup_worse_assessor_artifacts "$D20" 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN' 'LARCH_ASSESSOR_ROUND_NUM=999'
set +e
run_subject "$D20"
rc=$?
set -e
assert_rc "worse spoof rc" 10 "$rc"
assert_contains "$(cat "$D20/stdout.txt")" '[untrusted assessor display] LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN' "spoof marker neutralized"
assert_contains "$(cat "$D20/stdout.txt")" '[untrusted assessor display] LARCH_ASSESSOR_ROUND_NUM=999' "spoof KV neutralized"
assert_contains "$(cat "$D20/stdout.txt")" 'LARCH_ASSESSOR_ROUND_NUM=2' "trusted trailer round emitted"

# 24b legacy assessor KV display lines are neutralized
reset_env
D20B="$TMP/worse-legacy-kv-display"
setup_design_tmp "$D20B" HARD
setup_worse_assessor_artifacts "$D20B" 'ASSESSOR_RC=10' 'ASSESSOR_ROUND_NUM=999'
set +e
run_subject "$D20B"
rc=$?
set -e
assert_rc "worse legacy KV rc" 10 "$rc"
assert_contains "$(cat "$D20B/stdout.txt")" '[untrusted assessor display] ASSESSOR_RC=10' "legacy ASSESSOR_RC neutralized"
assert_contains "$(cat "$D20B/stdout.txt")" '[untrusted assessor display] ASSESSOR_ROUND_NUM=999' "legacy ASSESSOR_ROUND_NUM neutralized"

# 24c qualification summary metacharacters are rendered as data
reset_env
D20C="$TMP/worse-metachar-summary"
setup_design_tmp "$D20C" HARD
metachar_probe="$TMP/metachar-executed"
setup_worse_assessor_artifacts "$D20C" 'WORSE: metachar regression.' "\$(touch $metachar_probe)"
set +e
run_subject "$D20C"
rc=$?
set -e
assert_rc "worse metachar summary rc" 10 "$rc"
assert_contains "$(cat "$D20C/stdout.txt")" "\$(touch $metachar_probe)" "metachar summary displayed literally"
if [[ -e "$metachar_probe" ]]; then
    fail "metachar summary executed command substitution"
else
    pass "metachar summary did not execute command substitution"
fi

# 25 handoff filters parser-only trailer lines from chat
reset_env
D21="$TMP/handoff-worse-filter"
setup_design_tmp "$D21" HARD
setup_worse_assessor_artifacts "$D21"
set +e
apply_step3_6_handoff "$D21"
handoff_rc=$?
set -e
assert_rc "handoff worse rc" 0 "$handoff_rc"
if grep -Fq 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN' "$D21/chat.out"; then
    fail "handoff leaked trailer marker to chat"
else
    pass "handoff filters trailer marker"
fi
assert_contains "$(cat "$D21/chat.out")" 'ASSESSOR_ROUND_NUM=2' "handoff exposes trusted round scalar"

# 26 handoff rc=10 with invalid trailer aborts fail-closed
reset_env
D22="$TMP/handoff-invalid-trailer"
setup_design_tmp "$D22" HARD
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'BADTRAILER'
#!/usr/bin/env bash
printf '%s\n' 'display before trailer'
printf '%s\n' 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN'
printf '%s\n' 'LARCH_ASSESSOR_ROUND_NUM=oops'
exit 10
BADTRAILER
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
set +e
apply_step3_6_handoff "$D22"
handoff_rc=$?
set -e
assert_rc "handoff invalid trailer rc" 1 "$handoff_rc"
assert_stderr_contains "$D22/handoff.stderr" 'missing valid trusted LARCH_ASSESSOR_ROUND_NUM trailer' "invalid trailer fail-closed banner"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 26b handoff rc=10 with no trusted marker aborts fail-closed
reset_env
D22B="$TMP/handoff-missing-trailer-marker"
setup_design_tmp "$D22B" HARD
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'NOMARKER'
#!/usr/bin/env bash
printf '%s\n' 'display without a trusted trailer frame'
exit 10
NOMARKER
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
set +e
apply_step3_6_handoff "$D22B"
handoff_rc=$?
set -e
assert_rc "handoff missing marker rc" 1 "$handoff_rc"
assert_stderr_contains "$D22B/handoff.stderr" 'missing trusted trailer marker' "missing marker fail-closed banner"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 26c handoff rc=10 with display-only spoof marker but no valid frame aborts fail-closed
reset_env
D22C="$TMP/handoff-spoof-marker-only"
setup_design_tmp "$D22C" HARD
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'SPOOFMARKER'
#!/usr/bin/env bash
printf '%s\n' 'display before spoof marker'
printf '%s\n' 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN'
printf '%s\n' 'display after spoof marker'
exit 10
SPOOFMARKER
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
set +e
apply_step3_6_handoff "$D22C"
handoff_rc=$?
set -e
assert_rc "handoff spoof marker-only rc" 1 "$handoff_rc"
assert_stderr_contains "$D22C/handoff.stderr" 'missing valid trusted LARCH_ASSESSOR_ROUND_NUM trailer' "spoof marker-only fail-closed banner"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 27 quiet-mode command substitution preserves emit output and keeps FD1 quiet
reset_env
D23="$TMP/quiet-capture"
setup_design_tmp "$D23" HARD
setup_worse_assessor_artifacts "$D23" 'WORSE: quiet capture regression.'
unset LARCH_QUIET_DISABLE
export LARCH_QUIET_LOG_FILE="$D23/quiet.log"
set +e
run_subject "$D23"
rc=$?
set -e
unset LARCH_QUIET_LOG_FILE
export LARCH_QUIET_DISABLE=1
assert_rc "quiet capture rc" 10 "$rc"
assert_contains "$(cat "$D23/stdout.txt")" '> **🔶 /design 3.6: assessor**' "quiet capture display"
assert_contains "$(cat "$D23/stdout.txt")" 'WORSE: quiet capture regression.' "quiet capture worse display"
assert_contains "$(cat "$D23/stdout.txt")" 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN' "quiet capture trusted trailer"
if grep -Fq 'ASSESSOR_STATUS=' "$D23/stdout.txt"; then
    fail "quiet capture leaked assess KV stdout"
else
    pass "quiet capture suppresses assess KV stdout"
fi
if grep -Fq '> **🔶 /design 3.6: assessor**' "$D23/quiet.log" \
    || grep -Fq 'WORSE: quiet capture regression.' "$D23/quiet.log" \
    || grep -Fq 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN' "$D23/quiet.log"; then
    fail "quiet FD1 log contains user-facing assessor output"
else
    pass "quiet FD1 log excludes user-facing assessor output"
fi

# 28 unsafe sidecar path is confined under DESIGN_TMPDIR
reset_env
D24="$TMP/sidecar-injection"
setup_design_tmp "$D24" HARD
printf '%s\n' 'WORSE: confined file still renders.' >"$D24/assessor-verdict-round-2.txt"
printf 'QUALIFICATIONS_SUMMARY=outside summary\nASSESSOR_RESULT_TOKEN=evil-token\n' >"$TMP/outside-sidecar.env"
export ASSESSOR_STATUS_VALUE=ok ASSESSOR_VERDICT_VALUE=worse-majority EFFECTIVE_ASSESSORS_VALUE=3
export ASSESSOR_VERDICT_FILE_VALUE="$D24/assessor-verdict-round-2.txt"
export ASSESSOR_VERDICT_ENV_VALUE="$TMP/outside-sidecar.env"
set +e
run_subject "$D24"
rc=$?
set -e
assert_rc "sidecar injection rc" 10 "$rc"
assert_contains "$(cat "$D24/stdout.txt")" 'ignoring unsafe ASSESSOR_VERDICT_ENV path' "sidecar injection warning"
if grep -Fq 'evil-token' "$D24/stdout.txt" || grep -Fq 'outside summary' "$D24/stdout.txt"; then
    fail "unsafe sidecar content leaked"
else
    pass "unsafe sidecar content not displayed"
fi

# 1 argv: missing --design-tmpdir
reset_env
set +e
bash "$SUBJECT" --codex-present true --cursor-present false >"$TMP/usage.out" 2>"$TMP/usage.err"
rc=$?
set -e
assert_rc "missing design-tmpdir" 2 "$rc"

# 2 argv: unknown flag
reset_env
D0="$TMP/unknown-flag"
setup_design_tmp "$D0"
set +e
bash "$SUBJECT" --design-tmpdir "$D0" --codex-present true --cursor-present false --bogus >"$D0/stdout.txt" 2>"$D0/stderr.txt"
rc=$?
set -e
assert_rc "unknown flag" 2 "$rc"

# 3 non-HARD skip
reset_env
D1="$TMP/simple-skip"
setup_design_tmp "$D1" SIMPLE
set +e
run_subject "$D1"
rc=$?
set -e
assert_rc "non-HARD skip rc" 0 "$rc"
assert_file_kv "$D1/.step3.6-assessor.env" ASSESSOR_STATUS skipped "non-HARD status"
assert_file_kv "$D1/.step3.6-assessor.env" WORKFLOW_PATH SIMPLE "non-HARD workflow"
if grep -Fq 'assess ' "$CALL_LOG"; then fail "assess stub called on SIMPLE"; else pass "assess not called on SIMPLE"; fi

# 3b handoff SIMPLE skip breadcrumb
reset_env
D1B="$TMP/handoff-simple"
setup_design_tmp "$D1B" SIMPLE
set +e
apply_step3_6_handoff "$D1B"
handoff_rc=$?
set -e
assert_rc "handoff SIMPLE rc" 0 "$handoff_rc"
assert_contains "$(cat "$D1B/chat.out")" 'skipped' "handoff SIMPLE skip breadcrumb"
if [[ -f "$D1B/.completed/step-3.6" ]]; then
    pass "handoff SIMPLE writes step-3.6 sentinel"
else
    fail "handoff SIMPLE missing step-3.6 sentinel"
fi
if grep -Fq 'timing-ledger mark design Step 3.6' "$CALL_LOG" && ! grep -Fq 'assess ' "$CALL_LOG"; then
    pass "handoff SIMPLE timing before assessor skip"
else
    fail "handoff SIMPLE timing/skip ordering"
fi

# 3c handoff pause happens before SIMPLE classification and assessor driver
reset_env
D1C="$TMP/handoff-pause-before-simple"
setup_design_tmp "$D1C" SIMPLE
printf 'export ISSUE_NUMBER=88\n' >"$D1C/source-env.sh"
: >"$D1C/.pause-requested"
set +e
apply_step3_6_handoff "$D1C"
handoff_rc=$?
set -e
assert_rc "handoff pause before SIMPLE rc" 0 "$handoff_rc"
if grep -Fq 'pause-save --design-tmpdir' "$CALL_LOG" \
    && ! grep -Fq 'timing-ledger' "$CALL_LOG" \
    && ! grep -Fq 'assess ' "$CALL_LOG"; then
    pass "handoff pause before SIMPLE classification"
else
    fail "handoff pause before SIMPLE classification"
fi

# 4 HARD happy path
reset_env
D2="$TMP/hard-happy"
setup_design_tmp "$D2" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=2
set +e
run_subject "$D2"
rc=$?
set -e
assert_rc "HARD happy rc" 0 "$rc"
assert_file_kv "$D2/.step3.6-assessor.env" ASSESSOR_STATUS ok "HARD happy status"
assert_file_kv "$D2/.step3.6-assessor.env" ASSESSOR_VERDICT not-worse "HARD happy verdict"
assert_contains "$(cat "$D2/stdout.txt")" '> **🔶 /design 3.6: assessor**' "HARD happy display banner"

# 4b HARD worse-majority happy path
reset_env
D2B="$TMP/hard-worse-majority"
setup_design_tmp "$D2B" HARD
export ASSESSOR_VERDICT_VALUE=worse-majority EFFECTIVE_ASSESSORS_VALUE=3 ASSESSOR_STATUS_VALUE=ok
set +e
run_subject "$D2B"
rc=$?
set -e
assert_rc "HARD worse-majority rc" 10 "$rc"
assert_file_kv "$D2B/.step3.6-assessor.env" ASSESSOR_STATUS ok "HARD worse-majority status"
assert_file_kv "$D2B/.step3.6-assessor.env" ASSESSOR_VERDICT worse-majority "HARD worse-majority verdict"
assert_file_kv "$D2B/.step3.6-assessor.env" EFFECTIVE_ASSESSORS 3 "HARD worse-majority effective"
assert_contains "$(cat "$D2B/stdout.txt")" 'LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN' "HARD worse-majority trailer marker"
assert_contains "$(cat "$D2B/stdout.txt")" 'LARCH_ASSESSOR_ROUND_NUM=2' "HARD worse-majority trailer round"

# 4c HARD round 1 write-after then assess skipped
reset_env
D2C="$TMP/hard-round1"
setup_design_tmp "$D2C" HARD
export ROUND_CURSOR_VALUE=1 ASSESSOR_STATUS_VALUE=skipped ASSESSOR_VERDICT_VALUE=skipped \
    EFFECTIVE_ASSESSORS_VALUE=0 ROUND_NUM_VALUE=1
set +e
run_subject "$D2C"
rc=$?
set -e
assert_rc "HARD round1 rc" 0 "$rc"
if grep -Fq 'write-after' "$CALL_LOG"; then pass "round1 write-after invoked"; else fail "round1 write-after not invoked"; fi
assert_file_kv "$D2C/.step3.6-assessor.env" ASSESSOR_STATUS skipped "round1 assess skipped status"
assert_file_kv "$D2C/.step3.6-assessor.env" ASSESSOR_VERDICT skipped "round1 assess skipped verdict"

# 5 write-after failure
reset_env
D3="$TMP/write-after-fail"
setup_design_tmp "$D3" HARD
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2
set +e
run_subject "$D3"
rc=$?
set -e
assert_rc "write-after fail rc" 0 "$rc"
assert_file_kv "$D3/.step3.6-assessor.env" ASSESSOR_STATUS write-after-failed "write-after status"
count=$(cat "$D3/review-round-count.txt" 2>/dev/null || echo "")
if [[ "$count" == "1" ]]; then pass "rollback count"; else fail "rollback count — expected 1, got $count"; fi
if grep -Fq 'append-tool-failure' "$CALL_LOG"; then pass "append-tool-failure called"; else fail "append-tool-failure not called"; fi
warn_in_env=$(awk -F= '$1=="WARN"{print substr($0,6); exit}' "$D3/.step3.6-assessor.env" || true)
if [[ "$warn_in_env" == "$SNAPSHOT_FAIL_WARN" ]]; then pass "write-after WARN in env"; else fail "write-after WARN in env"; fi
if grep -Fq 'assess ' "$CALL_LOG"; then fail "assess not called on write-after failure"; else pass "assess not called on write-after failure"; fi
if grep -Fq 'write-cursor' "$CALL_LOG"; then pass "write-cursor rollback invoked"; else fail "write-cursor rollback not invoked"; fi
cursor_file=$(cat "$D3/plan-review-round-cursor.txt" 2>/dev/null || echo "")
if [[ "$cursor_file" == "2" ]]; then pass "rollback cursor file"; else fail "rollback cursor file — expected 2, got ${cursor_file:-<empty>}"; fi

# 6 EFFECTIVE_ASSESSORS=0
reset_env
D4="$TMP/zero-assessors"
setup_design_tmp "$D4" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=0 ASSESSOR_STATUS_VALUE=degraded-default-open
set +e
run_subject "$D4"
rc=$?
set -e
assert_rc "zero assessors rc" 0 "$rc"
if grep -Fxq "WARN=$ZERO_ASSESSORS_WARN" "$D4/.step3.6-assessor.env"; then pass "0/3 WARN in env"; else fail "0/3 WARN in env"; fi

# 7 handoff: write-after WARN in chat on file parse
reset_env
D5="$TMP/handoff-write-after"
setup_design_tmp "$D5" HARD
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2
set +e
apply_step3_6_handoff "$D5"
handoff_rc=$?
set -e
assert_rc "handoff write-after rc" 0 "$handoff_rc"
assert_contains "$(cat "$D5/chat.out")" "$SNAPSHOT_FAIL_WARN" "handoff chat write-after WARN"

# 8 handoff: 0/3 WARN in chat on file parse
reset_env
D6="$TMP/handoff-zero"
setup_design_tmp "$D6" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=0 ASSESSOR_STATUS_VALUE=degraded-default-open
set +e
apply_step3_6_handoff "$D6"
handoff_rc=$?
set -e
assert_rc "handoff zero assessors rc" 0 "$handoff_rc"
assert_contains "$(cat "$D6/chat.out")" '0/3 effective assessors' "handoff chat 0/3 WARN"

# 8b handoff 0/3 WARN dedup on file parse
reset_env
D6B="$TMP/handoff-zero-dedup"
setup_design_tmp "$D6B" HARD
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=0 ASSESSOR_STATUS_VALUE=degraded-default-open
set +e
apply_step3_6_handoff "$D6B"
handoff_rc=$?
set -e
assert_rc "handoff zero dedup rc" 0 "$handoff_rc"
zero_chat_count=$(grep -Fc "$ZERO_ASSESSORS_WARN" "$D6B/chat.out" 2>/dev/null || echo 0)
if [[ "$zero_chat_count" -eq 1 ]]; then
    pass "handoff single 0/3 WARN in chat on file parse"
else
    fail "handoff single 0/3 WARN in chat on file parse — expected 1, got $zero_chat_count"
fi

# 8c handoff 0/3 WARN via stdout fallback only
reset_env
D6C="$TMP/handoff-zero-stdout"
setup_design_tmp "$D6C" HARD
printf 'ASSESSOR_STATUS=skipped\n' >"$TMP/outside-assessor-zero.env"
ln -sf "$TMP/outside-assessor-zero.env" "$D6C/.step3.6-assessor.env"
export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=0 ASSESSOR_STATUS_VALUE=degraded-default-open
set +e
apply_step3_6_handoff "$D6C"
handoff_rc=$?
set -e
assert_rc "handoff zero stdout rc" 0 "$handoff_rc"
assert_contains "$(cat "$D6C/chat.out")" "> **🔶 /design 3.6: assessor**" "handoff symlink display captured"

# 9 symlink refusal
reset_env
D7="$TMP/symlink"
setup_design_tmp "$D7" HARD
printf 'ASSESSOR_STATUS=skipped\n' >"$TMP/outside-assessor.env"
ln -sf "$TMP/outside-assessor.env" "$D7/.step3.6-assessor.env"
export ASSESSOR_VERDICT_VALUE=not-worse
: >"$D7/chat.out"
: >"$D7/handoff.stderr"
set +e
apply_step3_6_handoff "$D7"
handoff_rc=$?
set -e
assert_rc "handoff symlink rc" 0 "$handoff_rc"
if grep -Fq 'refusing symlink .step3.6-assessor.env' "$D7/handoff.stderr" 2>/dev/null \
    || grep -Fq 'refusing to write symlink result env' "$D7/handoff.stderr" 2>/dev/null; then
    pass "symlink refusal on handoff stderr"
else
    fail "symlink refusal on handoff stderr"
fi
if grep -Fq '> **🔶 /design 3.6: assessor**' "$D7/handoff-driver.stdout" 2>/dev/null; then
    pass "symlink display captured"
else
    fail "symlink display captured"
fi

# 9b handoff symlink + write-after: driver WARN in chat via stdout merge
reset_env
D7B="$TMP/handoff-symlink-warn"
setup_design_tmp "$D7B" HARD
printf 'ASSESSOR_STATUS=skipped\n' >"$TMP/outside-assessor-b.env"
ln -sf "$TMP/outside-assessor-b.env" "$D7B/.step3.6-assessor.env"
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2
set +e
apply_step3_6_handoff "$D7B"
handoff_rc=$?
set -e
assert_rc "handoff symlink write-after rc" 0 "$handoff_rc"
assert_contains "$(cat "$D7B/chat.out")" "> **🔶 /design 3.6: assessor**" "handoff symlink write-after display captured"

# 10 result-env keys
for key in ASSESSOR_STATUS ASSESSOR_VERDICT EFFECTIVE_ASSESSORS ASSESSOR_VERDICT_FILE ASSESSOR_VERDICT_ENV ROUND_NUM WORKFLOW_PATH; do
    grep -q "^${key}=" "$D2/.step3.6-assessor.env" || fail "missing $key in result env"
done
pass "result-env key presence"

# 11 handoff abort: driver exit 2 via stub wrapper
reset_env
D8="$TMP/handoff-exit2"
setup_design_tmp "$D8" HARD
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'BAD'
#!/usr/bin/env bash
exit 2
BAD
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
set +e
apply_step3_6_handoff "$D8"
handoff_rc=$?
set -e
assert_rc "handoff exit 2" 1 "$handoff_rc"
assert_stderr_contains "$D8/handoff.stderr" 'configuration error (exit 2)' "handoff config error banner"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 12 handoff abort: empty mandatory keys
reset_env
D9="$TMP/handoff-empty"
setup_design_tmp "$D9" HARD
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'EMPTY'
#!/usr/bin/env bash
exit 0
EMPTY
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
rm -f "$D9/.step3.6-assessor.env"
set +e
apply_step3_6_handoff "$D9"
handoff_rc=$?
set -e
assert_rc "handoff empty keys settled rc" 0 "$handoff_rc"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 13 handoff abort: driver exit 1 catch-all
reset_env
D10="$TMP/handoff-exit1"
setup_design_tmp "$D10" HARD
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'BAD1'
#!/usr/bin/env bash
exit 1
BAD1
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
set +e
apply_step3_6_handoff "$D10"
handoff_rc=$?
set -e
assert_rc "handoff exit 1" 1 "$handoff_rc"
assert_stderr_contains "$D10/handoff.stderr" 'design-plan-quality-assessor.sh failed (exit' "handoff catch-all banner"
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 14 pause checkpoint before snapshot/assess
reset_env
D11="$TMP/pause-checkpoint"
setup_design_tmp "$D11" HARD
printf 'export ISSUE_NUMBER=77\n' >"$D11/source-env.sh"
: >"$D11/.pause-requested"
set +e
run_subject "$D11"
rc=$?
set -e
assert_rc "pause checkpoint rc" 11 "$rc"
assert_contains "$(cat "$D11/stdout.txt")" 'pause requested' "pause note emitted"
if grep -Fq 'snapshot ' "$CALL_LOG" || grep -Fq 'assess ' "$CALL_LOG"; then
    fail "pause should happen before snapshot/assess"
else
    pass "pause before snapshot/assess"
fi
assert_file_kv "$D11/.step3.6-assessor.env" ASSESSOR_STATUS paused "pause writes paused status"

# 14b handoff rc=11 threads explicit repo to pause-save
reset_env
D11B="$TMP/handoff-pause-repo"
setup_design_tmp "$D11B" HARD
printf 'export ISSUE_NUMBER=78\n' >"$D11B/source-env.sh"
cat >"$FAKE_DESIGN/design-plan-quality-assessor.sh" <<'PAUSE11'
#!/usr/bin/env bash
printf '%s\n' '**⏸ /design Step 3.6: pause requested; saving design state.**'
exit 11
PAUSE11
chmod +x "$FAKE_DESIGN/design-plan-quality-assessor.sh"
export REPO=upstream/repo
set +e
apply_step3_6_handoff "$D11B"
handoff_rc=$?
set -e
unset REPO
assert_rc "handoff pause repo rc" 0 "$handoff_rc"
if grep -Fq 'pause-save --design-tmpdir' "$CALL_LOG" && grep -Fq -- '--repo upstream/repo' "$CALL_LOG"; then
    pass "handoff rc=11 threads repo"
else
    fail "handoff rc=11 missing repo passthrough"
fi
cp "$SUBJECT" "$FAKE_DESIGN/design-plan-quality-assessor.sh"

# 15 handoff: single WARN in chat when file parse succeeds
reset_env
D12="$TMP/handoff-warn-dedup"
setup_design_tmp "$D12" HARD
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2
set +e
apply_step3_6_handoff "$D12"
handoff_rc=$?
set -e
assert_rc "handoff warn dedup rc" 0 "$handoff_rc"
warn_chat_count=$(grep -Fc "$SNAPSHOT_FAIL_WARN" "$D12/chat.out" 2>/dev/null || echo 0)
if [[ "$warn_chat_count" -eq 1 ]]; then
    pass "handoff single WARN in chat on file parse"
else
    fail "handoff single WARN in chat on file parse — expected 1, got $warn_chat_count"
fi

# 16 result-env write failure: stale regular file removed, stdout fallback used
reset_env
D13="$TMP/stale-env-write-fail"
setup_design_tmp "$D13" HARD
printf 'ASSESSOR_STATUS=ok\nASSESSOR_VERDICT=worse-majority\nEFFECTIVE_ASSESSORS=3\n' >"$D13/.step3.6-assessor.env"
if ! block_result_env_write "$D13/.step3.6-assessor.env"; then
    pass "stale env write-fail — chflags/chattr unavailable; skipped"
else
    export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=2
    set +e
    run_subject "$D13"
    rc=$?
    set -e
    unblock_result_env_write "$D13/.step3.6-assessor.env"
    assert_rc "stale env write-fail rc" 0 "$rc"
    assert_contains "$(cat "$D13/stdout.txt")" 'result env write failed' "stdout fallback warning"
    assert_contains "$(cat "$D13/stdout.txt")" 'result env write failed' "write-failure WARN on stdout"
    if [[ -f "$D13/.step3.6-assessor.env" ]] && grep -q 'worse-majority' "$D13/.step3.6-assessor.env" 2>/dev/null; then
        pass "stale file retained when rm blocked; stdout fallback still emitted"
    else
        pass "stale env removed after write failure"
    fi
fi

# 16b handoff stale env write-fail: stdout routing and WARN win over immutable file
reset_env
D13B="$TMP/handoff-stale-write-fail"
setup_design_tmp "$D13B" HARD
printf 'ASSESSOR_STATUS=ok\nASSESSOR_VERDICT=worse-majority\nEFFECTIVE_ASSESSORS=3\n' >"$D13B/.step3.6-assessor.env"
if ! block_result_env_write "$D13B/.step3.6-assessor.env"; then
    pass "handoff stale write-fail — chflags/chattr unavailable; skipped"
else
    export ASSESSOR_VERDICT_VALUE=not-worse EFFECTIVE_ASSESSORS_VALUE=2
    set +e
    apply_step3_6_handoff "$D13B"
    handoff_rc=$?
    set -e
    unblock_result_env_write "$D13B/.step3.6-assessor.env"
    assert_rc "handoff stale write-fail rc" 0 "$handoff_rc"
    assert_contains "$(cat "$D13B/chat.out")" "> **🔶 /design 3.6: assessor**" "handoff stale display captured"
fi

# 17 assess non-zero exit fail-closed
reset_env
D14="$TMP/assess-fail"
setup_design_tmp "$D14" HARD
export ASSESS_STUB_RC=1
set +e
run_subject "$D14"
rc=$?
set -e
assert_rc "assess fail rc" 0 "$rc"
assert_file_kv "$D14/.step3.6-assessor.env" ASSESSOR_STATUS assess-failed "assess-failed status"
assert_contains "$(cat "$D14/stdout.txt")" 'assess-plan-round.sh failed' "assess fail WARN on stdout"

# 17b handoff assess-failed WARN in chat on file parse
reset_env
D14B="$TMP/handoff-assess-fail"
setup_design_tmp "$D14B" HARD
export ASSESS_STUB_RC=1
set +e
apply_step3_6_handoff "$D14B"
handoff_rc=$?
set -e
assert_rc "handoff assess-fail rc" 0 "$handoff_rc"
assert_contains "$(cat "$D14B/chat.out")" 'assess-plan-round.sh failed' "handoff chat assess-failed WARN"

# 18 read-cursor failure WARN
reset_env
D15="$TMP/read-cursor-fail"
setup_design_tmp "$D15" HARD
export READ_CURSOR_RC=1
set +e
run_subject "$D15"
rc=$?
set -e
assert_rc "read-cursor fail rc" 0 "$rc"
assert_file_kv "$D15/.step3.6-assessor.env" ASSESSOR_STATUS cursor-read-failed "read-cursor fail status"
assert_contains "$(cat "$D15/stdout.txt")" 'read-cursor failed' "read-cursor fail WARN on stdout"
if grep -Fq 'assess ' "$CALL_LOG"; then fail "assess not called on read-cursor failure"; else pass "assess not called on read-cursor failure"; fi

# 18b handoff read-cursor failure WARN in chat
reset_env
D15B="$TMP/handoff-read-cursor-fail"
setup_design_tmp "$D15B" HARD
export READ_CURSOR_RC=1
set +e
apply_step3_6_handoff "$D15B"
handoff_rc=$?
set -e
assert_rc "handoff read-cursor fail rc" 0 "$handoff_rc"
assert_contains "$(cat "$D15B/chat.out")" 'read-cursor failed' "handoff chat read-cursor WARN"

# 19 workflow_path missing with HARD classification
reset_env
D16="$TMP/workflow-missing-hard"
setup_design_tmp "$D16" HARD
printf '{"design_classification":"HARD"}\n' >"$D16/run-params.json"
set +e
run_subject "$D16"
rc=$?
set -e
assert_rc "missing workflow_path HARD rc" 0 "$rc"
assert_file_kv "$D16/.step3.6-assessor.env" WORKFLOW_PATH HARD "missing workflow_path aligns HARD"
if grep -Fq 'assess ' "$CALL_LOG"; then pass "missing workflow_path runs HARD assess"; else fail "missing workflow_path HARD lane"; fi

# 19b workflow_path vs design_classification mismatch
reset_env
D16B="$TMP/wp-dc-mismatch"
setup_design_tmp "$D16B" SIMPLE
printf '{"workflow_path":"SIMPLE","design_classification":"HARD"}\n' >"$D16B/run-params.json"
set +e
run_subject "$D16B"
rc=$?
set -e
assert_rc "wp dc mismatch rc" 0 "$rc"
assert_contains "$(cat "$D16B/stdout.txt")" 'workflow_path=SIMPLE disagrees with design_classification=HARD' "mismatch WARN on stdout"
assert_file_kv "$D16B/.step3.6-assessor.env" WORKFLOW_PATH HARD "driver aligns lane to HARD classification"
set +e
apply_step3_6_handoff "$D16B"
handoff_rc=$?
set -e
assert_rc "wp dc mismatch handoff rc" 0 "$handoff_rc"
assert_contains "$(cat "$D16B/chat.out")" '> **🔶 /design 3.6: assessor**' "orchestrator HARD banner after classification alignment"
assert_contains "$(cat "$D16B/chat.out")" 'workflow_path=SIMPLE disagrees with design_classification=HARD' "handoff chat mismatch WARN"

# 20 handoff runtime qualified invoke (CALL_LOG proves driver ran)
reset_env
D17="$TMP/qualified-runtime"
setup_design_tmp "$D17" HARD
set +e
apply_step3_6_handoff "$D17"
handoff_rc=$?
set -e
assert_rc "qualified runtime handoff rc" 0 "$handoff_rc"
if grep -Fq 'snapshot read-cursor' "$CALL_LOG" && grep -Fq 'assess ' "$CALL_LOG"; then
    pass 'handoff qualified runtime invoke'
else
    fail 'handoff qualified runtime invoke'
fi

# 21 write-cursor rollback failure still decrements count
reset_env
D18="$TMP/write-cursor-rollback-fail"
setup_design_tmp "$D18" HARD
export WRITE_AFTER_FAIL=true ROUND_CURSOR_VALUE=2 WRITE_CURSOR_RC=1
printf '2\n' >"$D18/review-round-count.txt"
set +e
run_subject "$D18"
rc=$?
set -e
assert_rc "write-cursor rollback fail rc" 0 "$rc"
count=$(cat "$D18/review-round-count.txt" 2>/dev/null || echo "")
if [[ "$count" == "1" ]]; then pass "rollback fail still decrements count"; else fail "rollback fail still decrements count — expected 1, got $count"; fi
assert_contains "$(cat "$D18/stdout.txt")" 'write-cursor rollback failed' "write-cursor rollback fail WARN"

# 23 --timeout forwarded to assess stub
reset_env
D19="$TMP/timeout-forward"
setup_design_tmp "$D19" HARD
set +e
run_subject "$D19" --timeout 42
rc=$?
set -e
assert_rc "timeout forward rc" 0 "$rc"
if grep -Fq 'assess-timeout=42' "$CALL_LOG"; then pass "assess stub received --timeout"; else fail "assess stub missing --timeout"; fi

# 22 driver uses seam bindings (not hardcoded plugin paths in body)
contains_driver() {
    grep -Fq -- "$1" "$SUBJECT" || fail "$2"
}
contains_driver 'LARCH_SNAPSHOT_PLAN_ROUND_SH' 'driver missing SNAPSHOT_SH seam'
contains_driver 'LARCH_ASSESS_PLAN_ROUND_SH' 'driver missing ASSESS_SH seam'
# shellcheck disable=SC2016 # Literal pattern checks unexpanded shell syntax in driver source.
contains_driver '"$SNAPSHOT_SH"' 'driver missing SNAPSHOT_SH usage'
# shellcheck disable=SC2016 # Literal pattern checks unexpanded shell syntax in driver source.
contains_driver '"$ASSESS_SH"' 'driver missing ASSESS_SH usage'
# shellcheck disable=SC2016 # Literal pattern checks unexpanded path token in driver source.
if grep -Fq '$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh' "$SUBJECT" \
    && ! grep -Fq 'LARCH_SNAPSHOT_PLAN_ROUND_SH' "$SUBJECT"; then
    fail 'driver hardcodes snapshot path without seam'
else
    pass 'driver snapshot seam default only'
fi

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-design-plan-quality-assessor.sh (%s failed, %s passed)\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-design-plan-quality-assessor.sh (%s checks)\n' "$PASS"
