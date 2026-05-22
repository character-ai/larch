#!/usr/bin/env bash
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
      printf '%s\n' "${STUB_ISSUE_BODY_ONLY:-{\"body\":\"\"}}"
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
    unset STUB_LOG STUB_VIEW_JSON STUB_VIEW_FAIL STUB_VIEW_FAIL_COUNT_FILE STUB_VIEW_FAIL_MAX \
      STUB_API_BLOCKED_BY_JSON STUB_API_BLOCKED_BY_EXIT STUB_REPO_VIEW_EXIT STUB_REPO_VIEW_OUT \
      STUB_COMMENTS_JSON STUB_ISSUE_BODY_JSON STUB_ISSUE_BODY_ONLY || true
    local out rc
    out=$("$SCRIPT" "$@" 2>&1) || rc=$?
    rc=${rc:-0}
    if [[ "$rc" != "$expect_rc" ]]; then
        fail "$name: expected exit $expect_rc got $rc; output=$out"
        return
    fi
    PASS=$((PASS + 1))
    echo "PASS: $name"
}

# --- pass (no blockers) ---
sd="$TMPROOT/s1"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"Plain feature","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_JSON='[]'
run_case "pass-open-no-blockers" 0 "$sd" --issue 42 --repo o/r

# --- closed ---
sd="$TMPROOT/s2"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"x","state":"CLOSED","labels":[]}'
run_case "closed-exit-2" 2 "$sd" --issue 3 --repo o/r

# --- managed prefix ---
sd="$TMPROOT/s3"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"[IN PROGRESS] my work","state":"OPEN","labels":[]}'
run_case "managed-prefix-exit-5" 5 "$sd" --issue 3 --repo o/r

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

# --- sentinel resume ---
sd="$TMPROOT/s7"
make_gh_stub "$sd"
sent="$TMPROOT/s7/tmp"
mkdir -p "$sent"
printf 'ISSUE_NUMBER=5\nRUN_ID=rid\nADOPTED=true\n' > "$sent/parent-issue.md"
export STUB_VIEW_JSON='{"title":"[IN PROGRESS] sentinel","state":"OPEN","labels":[]}'
# Admission should pass before blocker checks when sentinel matches
(
  export IMPLEMENT_TMPDIR="$sent"
  export PATH="$sd:$PATH"
  out=$("$SCRIPT" --issue 5 --repo o/r 2>&1) || rc=$?
  rc=${rc:-0}
  if [[ "$rc" != 0 ]]; then
    fail "sentinel-pass: expected 0 got $rc out=$out"
  elif ! printf '%s' "$out" | grep -q 'ADMISSION_RESULT=pass'; then
    fail "sentinel-pass: missing ADMISSION_RESULT=pass in $out"
  elif ! printf '%s' "$out" | grep -q 'RESUME=true'; then
    fail "sentinel-pass: missing RESUME=true in $out"
  else
    PASS=$((PASS + 1))
    echo "PASS: sentinel-aware-pass"
  fi
)

# --- fail-open: native deps API errors -> still pass ---
sd="$TMPROOT/s8"
make_gh_stub "$sd"
export STUB_VIEW_JSON='{"title":"ok","state":"OPEN","labels":[]}'
export STUB_API_BLOCKED_BY_EXIT=1
run_case "fail-open-api-blocked-by" 0 "$sd" --issue 1 --repo o/r

# --- fork-mode explicit repo (no gh repo view in admission when --repo set) ---
sd="$TMPROOT/s9"
make_gh_stub "$sd"
export STUB_LOG="$TMPROOT/s9/gh.log"
export STUB_VIEW_JSON='{"title":"fork ctx","state":"OPEN","labels":[]}'
: > "$STUB_LOG"
export STUB_REPO_VIEW_EXIT=99
(
  export PATH="$sd:$PATH"
  "$SCRIPT" --issue 2 --repo upstream/extra || true
)
if grep -qE 'repo[[:space:]]+view' "$STUB_LOG" 2>/dev/null; then
  fail "fork-mode: gh repo view should not run when --repo passed"
else
  PASS=$((PASS + 1))
  echo "PASS: fork-mode-no-repo-view"
fi

# --- gh view fails twice ---
sd="$TMPROOT/s10"
make_gh_stub "$sd"
export STUB_VIEW_FAIL_COUNT_FILE="$TMPROOT/s10/cnt"
echo 0 > "$STUB_VIEW_FAIL_COUNT_FILE"
export STUB_VIEW_FAIL_MAX=1
export STUB_VIEW_JSON='{"title":"late","state":"OPEN","labels":[]}'
run_case "retry-then-success" 0 "$sd" --issue 9 --repo o/r

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
