#!/usr/bin/env bash
# Hermetic offline harness for scripts/lib-net.sh.
# shellcheck disable=SC2329  # stubs and predicates are invoked via "$@" / by name

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lib-net.XXXXXX")" || { echo "mktemp failed" >&2; exit 1; }
export SLEEP_SCRIPT_DIR="$TMPROOT/bin"
mkdir -p "$SLEEP_SCRIPT_DIR"

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); echo "  ok: $1"; }
fail() { FAIL=$((FAIL + 1)); FAILED+=("$1"); echo "  FAIL: $1" >&2; }

trap 'rm -rf "$TMPROOT"' EXIT

# shellcheck source=scripts/lib-net.sh disable=SC1091
source "$REPO_ROOT/scripts/lib-net.sh"

# Stub sleep-seconds.sh records argv for backoff assertions.
cat > "$SLEEP_SCRIPT_DIR/sleep-seconds.sh" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$1" >> "${SLEEP_LOG:?}"
STUB
chmod +x "$SLEEP_SCRIPT_DIR/sleep-seconds.sh"
export SLEEP_LOG="$TMPROOT/sleep.log"

EXIT_TRANSIENT_LOG="$TMPROOT/exit-transient.log"
exit_transient_net() {
    printf '%s' "$1" >"$EXIT_TRANSIENT_LOG"
    exit 6
}

ship_pr_with_transient_retry() {
    local pred=$1 ff=$2
    with_transient_retry "$@"
    local rc=$_WTR_RC
    local ff_content
    ff_content=$(cat "$ff" 2>/dev/null || true)
    if "$pred" "$ff_content"; then
        exit_transient_net "Transient envelope exhausted"
    fi
    [ "$rc" -eq 0 ] && return 0
    is_transient_net_signature "$ff_content" \
        && exit_transient_net "Transient retries exhausted"
    return "$rc"
}

transient_envelope_predicate_merge_error() {
    local out=$1
    case "$out" in
        *MERGE_RESULT=error*Could\ not\ resolve*) return 0 ;;
    esac
    return 1
}

# $1=fail_file $2=attempt_number $3=rc $4=stderr_text $5=stdout_text
stub_cmd() {
    local ff="$1" _attempt="$2" rc="$3" err="$4" out="$5"
    printf '%s\n' "$err" >>"$ff"
    printf '%s\n' "$out"
    return "$rc"
}

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        ok "$label"
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

# --- is_transient_net_signature ---
assert_transient() {
    local label=$1 text=$2
    if is_transient_net_signature "$text"; then ok "$label"; else fail "$label"; fi
}
assert_not_transient() {
    local label=$1 text=$2
    if is_transient_net_signature "$text"; then fail "$label"; else ok "$label"; fi
}

assert_transient "sig: Could not resolve" "Could not resolve host: api.github.com"
assert_transient "sig: Connection refused" "dial tcp: Connection refused"
assert_transient "sig: TLS handshake" "TLS handshake failure"
assert_transient "sig: HTTP 502" "HTTP 502 Bad Gateway"
assert_transient "sig: context deadline" "context deadline exceeded"
assert_not_transient "sig: empty" ""
assert_not_transient "sig: generic error" "permission denied"

ATTEMPT_LOG="$TMPROOT/attempts.log"
: >"$ATTEMPT_LOG"
bump_attempts() { printf '1\n' >>"$ATTEMPT_LOG"; }
attempt_count() { wc -l <"$ATTEMPT_LOG" | tr -d ' '; }

# --- with_transient_retry: rc=0 first attempt ---
: >"$SLEEP_LOG"
: >"$ATTEMPT_LOG"
wtr_success() {
    bump_attempts
    stub_cmd "$1" "$2" 0 "" "ok-out"
}
ff="$TMPROOT/success.ff"
: >"$ff"
if with_transient_retry transient_envelope_predicate_none "$ff" wtr_success "$ff" 1; then
    wtr_rc=0
else
    wtr_rc=$_WTR_RC
fi
assert_eq "wtr rc=0 short-circuit" 0 "$wtr_rc"
assert_eq "wtr success attempts" 1 "$(attempt_count)"
assert_eq "wtr success out" "ok-out" "$_WTR_OUT"
if [[ ! -s "$SLEEP_LOG" ]]; then
    ok "wtr success no sleep"
else
    fail "wtr success no sleep: $(cat "$SLEEP_LOG")"
fi

# --- rc!=0 transient: 3 attempts, sleep 2 and 4 ---
: >"$SLEEP_LOG"
: >"$ATTEMPT_LOG"
wtr_transient_fail() {
    bump_attempts
    stub_cmd "$1" "$2" 1 "fatal: Could not resolve host" ""
}
ff="$TMPROOT/transient.ff"
if with_transient_retry transient_envelope_predicate_none "$ff" wtr_transient_fail "$ff" 1; then
    wtr_rc=0
else
    wtr_rc=$_WTR_RC
fi
assert_eq "wtr transient final rc" 1 "$wtr_rc"
assert_eq "wtr transient attempts" 3 "$(attempt_count)"
sleep_args=$(tr '\n' ' ' <"$SLEEP_LOG" | sed 's/ $//')
assert_eq "wtr transient backoff" "2 4" "$sleep_args"

# --- rc!=0 non-transient: single attempt ---
: >"$SLEEP_LOG"
: >"$ATTEMPT_LOG"
wtr_hard_fail() {
    bump_attempts
    stub_cmd "$1" "$2" 1 "permission denied" ""
}
ff="$TMPROOT/hard.ff"
if with_transient_retry transient_envelope_predicate_none "$ff" wtr_hard_fail "$ff" 1; then
    wtr_rc=0
else
    wtr_rc=$_WTR_RC
fi
assert_eq "wtr hard fail rc" 1 "$wtr_rc"
assert_eq "wtr hard fail attempts" 1 "$(attempt_count)"

# --- rc=0 envelope-error predicate retry ---
: >"$SLEEP_LOG"
: >"$ATTEMPT_LOG"
wtr_envelope() {
    bump_attempts
    stub_cmd "$1" "$2" 0 "" $'MERGE_RESULT=error\nERROR=Could not resolve host'
}
ff="$TMPROOT/envelope.ff"
if with_transient_retry transient_envelope_predicate_merge_error "$ff" wtr_envelope "$ff" 1; then
    wtr_rc=0
else
    wtr_rc=$_WTR_RC
fi
assert_eq "wtr envelope attempts" 3 "$(attempt_count)"
assert_eq "wtr envelope final rc" 0 "$wtr_rc"

# --- ship_pr_with_transient_retry envelope exhaustion ---
: >"$EXIT_TRANSIENT_LOG"
: >"$ATTEMPT_LOG"
ff="$TMPROOT/ship-envelope.ff"
set +e
( ship_pr_with_transient_retry transient_envelope_predicate_merge_error "$ff" wtr_envelope "$ff" 1 )
ship_rc=$?
set -e
assert_eq "ship_pr envelope exit" 6 "$ship_rc"
assert_eq "ship_pr envelope msg" "Transient envelope exhausted" "$(cat "$EXIT_TRANSIENT_LOG" 2>/dev/null || true)"

if [[ "$FAIL" -eq 0 ]]; then
    echo "lib-net OK"
    exit 0
fi
echo "$FAIL test(s) failed:" >&2
printf '  - %s\n' "${FAILED[@]}" >&2
exit 1
