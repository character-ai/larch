#!/usr/bin/env bash
# shellcheck disable=SC2030,SC2031
# test-implement-admission.sh — Offline regression harness for implement-admission.sh.
#
# Uses a PATH-prepended gh stub. Run: bash scripts/test-implement-admission.sh
# Wired via Makefile target test-implement-admission.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/implement-admission.sh"
[[ -x "$SCRIPT" ]] || { echo "FAIL: $SCRIPT missing or not executable" >&2; exit 1; }

PASS=0
FAIL=0
fail() { echo "FAIL: $1" >&2; FAIL=$((FAIL + 1)); }

TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-impl-adm-XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

make_gh_stub() {
    local d="$1"
    mkdir -p "$d"
    cat > "$d/gh" << 'STUB'
#!/usr/bin/env bash
set +e
[[ -n "${STUB_LOG:-}" ]] && printf 'gh %q' "$1" >>"$STUB_LOG" && printf ' %q' "${@:2}" >>"$STUB_LOG" && echo >>"$STUB_LOG"

if [[ "$1" == "repo" && "$2" == "view" ]]; then
  echo "${STUB_REPO_VIEW_OUT:-o/r}"
  exit "${STUB_REPO_VIEW_EXIT:-0}"
fi

if [[ "$1" == "issue" && "$2" == "view" ]]; then
  if [[ -n "${STUB_VIEW_FAIL_COUNT_FILE:-}" ]]; then
    c=$(cat "$STUB_VIEW_FAIL_COUNT_FILE" 2>/dev/null || echo 0)
    c=$((c + 1))
    echo "$c" > "$STUB_VIEW_FAIL_COUNT_FILE"
    max="${STUB_VIEW_FAIL_MAX:-1}"
    if [[ "$c" -le "$max" ]]; then
      echo "transient gh failure" >&2
      exit 1
    fi
  elif [[ "${STUB_VIEW_FAIL:-0}" == "1" ]]; then
    echo "hard gh failure" >&2
    exit 1
  fi
  json=""
  i=1
  while [[ $i -le $# ]]; do
    if [[ "${!i}" == "--json" ]]; then
      j=$((i + 1))
      json="${!j:-}"
      break
    fi
    i=$((i + 1))
  done
  case "$json" in
    body)
      printf '%s\n' "${STUB_ISSUE_BODY_ONLY:-{\"body\":\"\"}}" | jq -r '.body // ""' 2>/dev/null || printf '\n'
      exit 0
      ;;
    state)
      printf '%s\n' "${STUB_VIEW_JSON}" | jq -r '.state // ""' 2>/dev/null || printf '\n'
      exit 0
      ;;
    *)
      printf '%s\n' "${STUB_VIEW_JSON}"
      exit 0
      ;;
  esac
fi

# Native dependencies API (blocker-helpers native_open_blockers)
if [[ "$1" == "api" ]]; then
  url=""
  for a in "$@"; do
    case "$a" in repos/*/*/issues/*/dependencies/blocked_by) url="$a"; break ;; esac
  done
  if [[ -n "$url" ]]; then
    exit_rc="${STUB_API_BLOCKED_BY_EXIT:-0}"
    if [[ "$exit_rc" -ne 0 ]]; then
      echo "api blocked_by failed" >&2
      exit "$exit_rc"
    fi
    json="${STUB_API_BLOCKED_BY_JSON:-[]}"
    printf '%s' "$json" | jq -r '.[] | select(.state == "open") | .number' 2>/dev/null || true
    exit 0
  fi
  # Comments fetch (prose path) — return empty array
  if printf '%s ' "$@" | grep -q 'issues/.*/comments'; then
    printf '%s\n' "${STUB_COMMENTS_JSON:-[]}"
    exit 0
  fi
fi

echo "stub: unhandled argv: $*" >&2
exit 99
STUB
    chmod +x "$d/gh"
}

run_case() {
    local name="$1" expect_rc="$2" stub_dir="$3"
    shift 3
    export PATH="$stub_dir:$PATH"
    unset IMPLEMENT_TMPDIR RUN_ID || true
    local out rc
    out=$(env -u IMPLEMENT_TMPDIR -u RUN_ID "$SCRIPT" "$@" 2>&1) || rc=$?
    rc=${rc:-0}
    if [[ "$rc" != "$expect_rc" ]]; then
        fail "$name: expected exit $expect_rc got $rc; output=$out"
        unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
          STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
          STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
        return
    fi
    case "$expect_rc" in
        0)
            if ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=pass'; then
                fail "$name: missing ADMISSION_RESULT=pass in stdout; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            ;;
        2)
            if ! printf '%s' "$out" | grep -Fq 'ADMISSION_ERROR='; then
                fail "$name: exit 2 missing ADMISSION_ERROR= on stdout; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            ;;
        4)
            if ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=has-blockers'; then
                fail "$name: exit 4 missing ADMISSION_RESULT=has-blockers; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            if ! printf '%s' "$out" | grep -Fq 'BLOCKERS='; then
                fail "$name: exit 4 missing BLOCKERS= on stdout; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            ;;
        5|7)
            local exp_result
            if [[ "$expect_rc" == "5" ]]; then
                exp_result='ADMISSION_RESULT=managed-prefix'
            else
                exp_result='ADMISSION_RESULT=report-title'
            fi
            if ! printf '%s' "$out" | grep -Fq "$exp_result"; then
                fail "$name: exit $expect_rc missing $exp_result in stdout; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            if ! printf '%s' "$out" | grep -Fq 'TITLE='; then
                fail "$name: exit $expect_rc missing TITLE= on stdout; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            ;;
        6)
            if ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=audit-report-label'; then
                fail "$name: exit 6 missing ADMISSION_RESULT=audit-report-label; output=$out"
                unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
                  STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
                  STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
                return
            fi
            ;;
    esac
    PASS=$((PASS + 1))
    echo "PASS: $name"
    unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
      STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
      STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
}

# --- pass (no blockers) ---
sd="$TMPROOT/s1"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[DESIGNED] Plain feature","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
run_case "pass-open-no-blockers" 0 "$sd" --issue 42 --repo o/r

sd="$TMPROOT/s1z"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[DESIGNED] Plain feature","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
run_case "pass-leading-zeros-normalized" 0 "$sd" --issue 042 --repo o/r

# --- closed ---
sd="$TMPROOT/s2"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"x","state":"CLOSED","labels":[]}'
run_case "closed-exit-2" 2 "$sd" --issue 3 --repo o/r

# --- managed prefix ---
sd="$TMPROOT/s3"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[IMPLEMENTING] my work","state":"OPEN","labels":[]}'
run_case "managed-prefix-implementing-exit-5" 5 "$sd" --issue 3 --repo o/r

sd="$TMPROOT/s3-done"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[DONE] shipped","state":"OPEN","labels":[]}'
run_case "managed-prefix-done-exit-5" 5 "$sd" --issue 3 --repo o/r

sd="$TMPROOT/s3-stalled"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[STALLED] blocked","state":"OPEN","labels":[]}'
run_case "managed-prefix-stalled-exit-5" 5 "$sd" --issue 3 --repo o/r

sd="$TMPROOT/s3-designing"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[DESIGNING] active design","state":"OPEN","labels":[]}'
run_case "managed-prefix-designing-exit-5" 5 "$sd" --issue 3 --repo o/r

sd="$TMPROOT/s3-legacy-in-progress"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[IN PROGRESS] legacy run","state":"OPEN","labels":[]}'
run_case "managed-prefix-legacy-in-progress-exit-5" 5 "$sd" --issue 3 --repo o/r

sd="$TMPROOT/s3-legacy-planned"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[PLANNED] legacy design","state":"OPEN","labels":[]}'
run_case "managed-prefix-legacy-planned-exit-5" 5 "$sd" --issue 3 --repo o/r

# --- designed prefix passes both gates ---
sd="$TMPROOT/s3-designed"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[DESIGNED] ready to implement","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
run_case "designed-prefix-pass" 0 "$sd" --issue 3 --repo o/r

# --- no-prefix fails missing-designed-prefix gate ---
sd="$TMPROOT/s3-no-prefix"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"Plain feature without design","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
(
  export PATH="$sd:$PATH"
  out=$(env -u IMPLEMENT_TMPDIR -u RUN_ID "$SCRIPT" --issue 3 --repo o/r 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 5 ]]; then
    fail "no-prefix-missing-designed: expected exit 5 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=missing-designed-prefix'; then
    fail "no-prefix-missing-designed: missing ADMISSION_RESULT=missing-designed-prefix in $out"
  elif ! printf '%s' "$out" | grep -Fq 'TITLE='; then
    fail "no-prefix-missing-designed: missing TITLE= in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: no-prefix-missing-designed-prefix-exit-5"
  fi
)

# --- report title ---
sd="$TMPROOT/s4"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[Weekly Report] Q1","state":"OPEN","labels":[]}'
run_case "report-title-exit-7" 7 "$sd" --issue 3 --repo o/r

# --- audit-report label ---
sd="$TMPROOT/s5"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"Audit thing","state":"OPEN","labels":[{"name":"audit-report"}]}'
run_case "audit-report-label-exit-6" 6 "$sd" --issue 3 --repo o/r

# --- blockers ---
sd="$TMPROOT/s6"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"blocked","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[{"number":77,"state":"open"}]'
run_case "native-blocker-exit-4" 4 "$sd" --issue 10 --repo o/r

# --- prose-only open blockers (native API empty) ---
sd="$TMPROOT/s6b"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"prose deps","state":"OPEN","labels":[],"body":"Blocked by #88"}'
export STUB_ISSUE_BODY_ONLY='{"body":"Blocked by #88"}'
export STUB_API_BLOCKED_BY_JSON='[]'
run_case "prose-blocker-exit-4" 4 "$sd" --issue 10 --repo o/r
out_pb=$(PATH="$sd:$PATH" env -u IMPLEMENT_TMPDIR -u RUN_ID \
  STUB_VIEW_JSON='{"title":"prose deps","state":"OPEN","labels":[],"body":"Blocked by #88"}' \
  STUB_ISSUE_BODY_ONLY='{"body":"Blocked by #88"}' \
  STUB_API_BLOCKED_BY_JSON='[]' \
  "$SCRIPT" --issue 10 --repo o/r 2>&1) || true
if ! printf '%s' "$out_pb" | grep -Fq 'BLOCKERS=88'; then
  fail "prose-blocker: expected BLOCKERS=88 on stdout, got: $out_pb"
else
  PASS=$((PASS + 1))
  echo "PASS: prose-blocker-blockers-kv"
fi

# --- sentinel resume (RUN_ID must match parent-issue nonce) ---
sd="$TMPROOT/s7"
make_gh_stub "$sd"
sent="$TMPROOT/s7/tmp"
mkdir -p "$sent"
printf 'ISSUE_NUMBER=5\nRUN_ID=rid\nADOPTED=true\n' > "$sent/parent-issue.md"
export STUB_VIEW_JSON='{"title":"[IMPLEMENTING] sentinel","state":"OPEN","labels":[]}'
# Sentinel short-circuits managed-title / audit-label gates but still runs
# all_open_blockers before emitting RESUME=true.
(
  export IMPLEMENT_TMPDIR="$sent"
  export RUN_ID=rid
  export PATH="$sd:$PATH"
  out=$("$SCRIPT" --issue 5 --repo o/r 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 0 ]]; then
    fail "sentinel-pass: expected 0 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=pass'; then
    fail "sentinel-pass: missing ADMISSION_RESULT=pass in $out"
  elif ! printf '%s' "$out" | grep -Fq 'RESUME=true'; then
    fail "sentinel-pass: missing RESUME=true in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: sentinel-aware-pass"
  fi
)

# --- sentinel resume without RUN_ID in parent-issue (older tmpdirs) ---
sd="$TMPROOT/s7a"
make_gh_stub "$sd"
sent_nr="$TMPROOT/s7a/tmp"
mkdir -p "$sent_nr"
printf 'ISSUE_NUMBER=5\nADOPTED=true\n' > "$sent_nr/parent-issue.md"
export STUB_VIEW_JSON='{"title":"[IMPLEMENTING] no-runid-sentinel","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
(
  export IMPLEMENT_TMPDIR="$sent_nr"
  export PATH="$sd:$PATH"
  unset RUN_ID
  out=$("$SCRIPT" --issue 5 --repo o/r 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 0 ]]; then
    fail "sentinel-no-runid: expected 0 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=pass'; then
    fail "sentinel-no-runid: missing ADMISSION_RESULT=pass in $out"
  elif ! printf '%s' "$out" | grep -Fq 'RESUME=true'; then
    fail "sentinel-no-runid: missing RESUME=true in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: sentinel-resume-without-runid-line"
  fi
)

# --- resume path honors open blockers ---
sd="$TMPROOT/s7block"
make_gh_stub "$sd"
sent_bl="$TMPROOT/s7block/tmp"
mkdir -p "$sent_bl"
printf 'ISSUE_NUMBER=5\nRUN_ID=rid2\nADOPTED=true\n' > "$sent_bl/parent-issue.md"
export STUB_VIEW_JSON='{"title":"[IMPLEMENTING] resume-blocked","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[{"number":99,"state":"open"}]'
(
  export IMPLEMENT_TMPDIR="$sent_bl"
  export RUN_ID=rid2
  export PATH="$sd:$PATH"
  out=$("$SCRIPT" --issue 5 --repo o/r 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 4 ]]; then
    fail "sentinel-blockers: expected exit 4 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=has-blockers'; then
    fail "sentinel-blockers: missing ADMISSION_RESULT=has-blockers in $out"
  elif ! printf '%s' "$out" | grep -Fq 'BLOCKERS='; then
    fail "sentinel-blockers: missing BLOCKERS= in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: sentinel-resume-blockers-exit-4"
  fi
)

# --- stale tmpdir: parent RUN_ID mismatches env -> full gate (managed prefix) ---
sd="$TMPROOT/s7b"
make_gh_stub "$sd"
sentb="$TMPROOT/s7b/tmp"
mkdir -p "$sentb"
printf 'ISSUE_NUMBER=5\nRUN_ID=session-a\nADOPTED=true\n' > "$sentb/parent-issue.md"
export STUB_VIEW_JSON='{"title":"[IMPLEMENTING] stale","state":"OPEN","labels":[]}'
(
  export IMPLEMENT_TMPDIR="$sentb"
  export RUN_ID=session-b
  export PATH="$sd:$PATH"
  out=$("$SCRIPT" --issue 5 --repo o/r 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 5 ]]; then
    fail "sentinel-stale-runid: expected exit 5 (managed prefix) got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'TITLE='; then
    fail "sentinel-stale-runid: missing TITLE= in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: sentinel-stale-runid-falls-through"
  fi
)

# --- fail-open: native deps API errors -> still pass ---
sd="$TMPROOT/s8"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[DESIGNED] ok","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_EXIT=1
run_case "fail-open-api-blocked-by" 0 "$sd" --issue 1 --repo o/r

# --- fork-mode explicit repo (no gh repo view in admission when --repo set) ---
sd="$TMPROOT/s9"
make_gh_stub "$sd"
export STUB_LOG="$TMPROOT/s9/gh.log"
export STUB_VIEW_JSON='{"title":"[DESIGNED] fork ctx","state":"OPEN","labels":[]}'
: > "$STUB_LOG"
export STUB_REPO_VIEW_EXIT=99
(
  export PATH="$sd:$PATH"
  out=$("$SCRIPT" --issue 2 --repo upstream/extra 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 0 ]]; then
    fail "fork-mode: expected exit 0 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=pass'; then
    fail "fork-mode: missing ADMISSION_RESULT=pass in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: fork-mode-admission-pass"
  fi
)
if grep -qE 'repo[[:space:]]+view' "$STUB_LOG" 2>/dev/null; then
  fail "fork-mode: gh repo view should not run when --repo passed"
else
  PASS=$((PASS + 1))
  echo "PASS: fork-mode-no-repo-view"
fi
unset STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT STUB_LOG || true

# --- default repo: gh repo view when --repo omitted ---
sd="$TMPROOT/s-repo-default"
make_gh_stub "$sd"
export STUB_LOG="$TMPROOT/s-repo-default/gh.log"
: > "$STUB_LOG"
export STUB_REPO_VIEW_OUT='owner/name'
export STUB_VIEW_JSON='{"title":"[DESIGNED] Default REPO path","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
(
  export PATH="$sd:$PATH"
  out=$("$SCRIPT" --issue 55 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 0 ]]; then
    fail "default-repo: expected exit 0 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -Fq 'ADMISSION_RESULT=pass'; then
    fail "default-repo: missing ADMISSION_RESULT=pass in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: default-repo-admission-pass"
  fi
)
if ! grep -qE 'repo[[:space:]]+view' "$STUB_LOG" 2>/dev/null; then
  fail "default-repo: expected gh repo view in stub log"
else
  PASS=$((PASS + 1))
  echo "PASS: default-repo-invokes-repo-view"
fi
if ! grep -Fq 'owner/name' "$STUB_LOG" 2>/dev/null; then
  fail "default-repo: expected resolved repo in gh stub log"
else
  PASS=$((PASS + 1))
  echo "PASS: default-repo-issue-view-uses-resolved-repo"
fi
unset STUB_LOG STUB_REPO_VIEW_OUT || true

# --- malformed issue JSON (jq parse) ---
sd="$TMPROOT/s-bad-json"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"truncated'
run_case "malformed-issue-json-exit-2" 2 "$sd" --issue 1 --repo o/r

# --- gh view fails twice ---
sd="$TMPROOT/s10"
make_gh_stub "$sd"
export STUB_VIEW_FAIL_COUNT_FILE="$TMPROOT/s10/cnt"
echo 0 > "$STUB_VIEW_FAIL_COUNT_FILE"
export STUB_VIEW_FAIL_MAX=1
export STUB_VIEW_JSON='{"title":"[DESIGNED] late","state":"OPEN","labels":[]}'
run_case "retry-then-success" 0 "$sd" --issue 9 --repo o/r

# --- argv validation emits ADMISSION_ERROR= (exit 2) ---
sd="$TMPROOT/s12"
make_gh_stub "$sd"
run_case "missing-issue-flag-value" 2 "$sd" --issue
run_case "missing-repo-flag-value" 2 "$sd" --issue 1 --repo
run_case "non-numeric-issue" 2 "$sd" --issue abc --repo o/r
run_case "issue-zero-rejected" 2 "$sd" --issue 0 --repo o/r

# --- hard gh failure ---
sd="$TMPROOT/s11"
make_gh_stub "$sd"
export STUB_VIEW_FAIL=1
run_case "gh-hard-fail-exit-2" 2 "$sd" --issue 1 --repo o/r

if [[ "$FAIL" -ne 0 ]]; then
  echo "Completed with $FAIL failure(s), $PASS pass(es)" >&2
  exit 1
fi
echo "All $PASS assertions passed."
exit 0
