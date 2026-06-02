#!/usr/bin/env bash
# Offline unit tests for scripts/lib-external-launcher-common.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMPDIR_ROOT="$(mktemp -d /tmp/larch-test-lib-ext-launcher-XXXXXX)"
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

PASS=0
FAIL=0
FAILURES=()

pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

assert_returns() {
    local label="$1" expected="$2"
    shift 2
    local rc=0
    "$@" || rc=$?
    if [[ "$rc" -eq "$expected" ]]; then
        pass
    else
        fail "$label: expected return $expected, got $rc"
    fi
}

# Source the library under test.
# shellcheck source=scripts/lib-external-launcher-common.sh
source "$REPO_ROOT/scripts/lib-external-launcher-common.sh"

EMPTY_OUTPUT="$TMPDIR_ROOT/empty.output"
: > "$EMPTY_OUTPUT"

NONEMPTY_OUTPUT="$TMPDIR_ROOT/nonempty.output"
printf 'some review output\n' > "$NONEMPTY_OUTPUT"

# Absent output file: treated as 0 bytes (tool exited before producing output)
ABSENT_OUTPUT="$TMPDIR_ROOT/absent.output"
assert_returns "absent output file returns 0 for valid exit/elapsed" 0 \
    external_is_transient_infra_failure "codex" "7" "0" "$ABSENT_OUTPUT"

# Wrong tool: must return 1
assert_returns "unknown tool returns 1" 1 \
    external_is_transient_infra_failure "claude" "7" "0" "$EMPTY_OUTPUT"

# Codex exit code not in allowlist: must return 1
assert_returns "codex exit 1 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "codex" "1" "0" "$EMPTY_OUTPUT"

assert_returns "codex exit 2 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "codex" "2" "0" "$EMPTY_OUTPUT"

# Cursor exit code not in allowlist: must return 1
assert_returns "cursor exit 1 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "cursor" "1" "0" "$EMPTY_OUTPUT"

assert_returns "cursor exit 3 returns 1 (not transient)" 1 \
    external_is_transient_infra_failure "cursor" "3" "0" "$EMPTY_OUTPUT"

# Codex exit 7 + empty output: must return 0
assert_returns "codex exit 7 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "codex" "7" "0" "$EMPTY_OUTPUT"

assert_returns "codex exit 7 + empty output + 5s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "codex" "7" "5" "$EMPTY_OUTPUT"

# Codex exit 5 + empty output: must return 0
assert_returns "codex exit 5 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "codex" "5" "0" "$EMPTY_OUTPUT"

# Cursor exit 8 + empty output: must return 0
assert_returns "cursor exit 8 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "cursor" "8" "0" "$EMPTY_OUTPUT"

# Cursor exit 4 + empty output: must return 0
assert_returns "cursor exit 4 + empty output + 0s = transient (returns 0)" 0 \
    external_is_transient_infra_failure "cursor" "4" "0" "$EMPTY_OUTPUT"

# Non-empty output file: must return 1 (even with valid exit code and short elapsed)
assert_returns "codex exit 7 + non-empty output returns 1" 1 \
    external_is_transient_infra_failure "codex" "7" "0" "$NONEMPTY_OUTPUT"

assert_returns "cursor exit 8 + non-empty output returns 1" 1 \
    external_is_transient_infra_failure "cursor" "8" "0" "$NONEMPTY_OUTPUT"

assert_returns "codex exit 7 + elapsed=6 still returns 0 when output is empty" 0 \
    external_is_transient_infra_failure "codex" "7" "6" "$EMPTY_OUTPUT"

assert_returns "cursor exit 8 + elapsed=10 still returns 0 when output is empty" 0 \
    external_is_transient_infra_failure "cursor" "8" "10" "$EMPTY_OUTPUT"

assert_classify_kv() {
    local label="$1" want_class="$2" want_reason="$3"
    shift 3
    local out c r
    out=$("$@" 2>/dev/null || true)
    c=$(printf '%s\n' "$out" | awk -F= '/^LAUNCHER_FAILURE_CLASS=/ {print $2; exit}')
    r=$(printf '%s\n' "$out" | awk -F= '/^LAUNCHER_FAILURE_REASON=/ {print $2; exit}')
    if [[ "$c" == "$want_class" && "$r" == "$want_reason" ]]; then
        pass
    else
        fail "$label: expected class=$want_class reason='$want_reason', got class=$c reason='$r' (out=$out)"
    fi
}

_sidecar_auth="$TMPDIR_ROOT/sidecar-auth.txt"
printf 'Password not found\n' > "$_sidecar_auth"
_sidecar_parse="$TMPDIR_ROOT/sidecar-parse.txt"
printf 'invalid json\n' > "$_sidecar_parse"

assert_classify_kv "exit 0 → none/empty" "none" "" \
    external_classify_launch_failure 0 "/dev/null" "non-auth" 1 "cursor" "$NONEMPTY_OUTPUT"

assert_classify_kv "binary missing" "health" "binary-missing" \
    external_classify_launch_failure 127 "/dev/null" "unclassified" 0 "cursor" ""

assert_classify_kv "auth verdict" "health" "auth" \
    external_classify_launch_failure 1 "$_sidecar_auth" "auth" 1 "cursor" "$EMPTY_OUTPUT"

assert_classify_kv "health-probe cursor+8+empty" "health" "health-probe" \
    external_classify_launch_failure 8 "$TMPDIR_ROOT/empty.sidecar" "non-auth" 1 "cursor" "$EMPTY_OUTPUT"

assert_classify_kv "timeout 124" "other" "timeout" \
    external_classify_launch_failure 124 "/dev/null" "non-auth" 1 "cursor" "$EMPTY_OUTPUT"

assert_classify_kv "parse sidecar" "other" "parse" \
    external_classify_launch_failure 1 "$_sidecar_parse" "non-auth" 1 "cursor" "$EMPTY_OUTPUT"

assert_classify_kv "generic non-zero" "other" "unknown" \
    external_classify_launch_failure 99 "/dev/null" "non-auth" 1 "cursor" "$NONEMPTY_OUTPUT"

# --- external_is_quota_failure (#3378) ---
_sidecar_quota="$TMPDIR_ROOT/sidecar-quota.txt"
printf "You've hit your usage limit. Try again at 3:00 PM.\n" > "$_sidecar_quota"
_sidecar_ratelimit="$TMPDIR_ROOT/sidecar-ratelimit.txt"
printf 'Error: 429 Too Many Requests (rate-limit)\n' > "$_sidecar_ratelimit"
_sidecar_nonquota="$TMPDIR_ROOT/sidecar-nonquota.txt"
printf 'ordinary failure, no limit text\n' > "$_sidecar_nonquota"

assert_returns "quota: codex usage-limit matches" 0 \
    external_is_quota_failure "codex" "$_sidecar_quota"
assert_returns "quota: cursor usage-limit matches" 0 \
    external_is_quota_failure "cursor" "$_sidecar_quota"
assert_returns "quota: 429 rate-limit matches" 0 \
    external_is_quota_failure "codex" "$_sidecar_ratelimit"
assert_returns "quota: non-quota text returns 1" 1 \
    external_is_quota_failure "codex" "$_sidecar_nonquota"
assert_returns "quota: unsupported tool returns 1" 1 \
    external_is_quota_failure "claude" "$_sidecar_quota"
assert_returns "quota: unreadable sidecar returns 1" 1 \
    external_is_quota_failure "codex" "$TMPDIR_ROOT/does-not-exist.txt"
# Auth and quota signatures are disjoint: an auth sidecar is not a quota match.
assert_returns "quota: auth sidecar is not a quota match" 1 \
    external_is_quota_failure "codex" "$_sidecar_auth"

# --- external_classify_launch_failure quota branch (#3378) ---
assert_classify_kv "quota sidecar → health/quota" "health" "quota" \
    external_classify_launch_failure 1 "$_sidecar_quota" "non-auth" 1 "codex" "$EMPTY_OUTPUT"
assert_classify_kv "quota in output file → health/quota" "health" "quota" \
    external_classify_launch_failure 1 "$TMPDIR_ROOT/empty.sidecar" "non-auth" 1 "cursor" "$_sidecar_quota"

# --- external_failure_verdict (#3378) ---
assert_verdict() {
    local label="$1" expected="$2"
    shift 2
    local got
    got=$("$@" 2>/dev/null || true)
    if [[ "$got" == "$expected" ]]; then
        pass
    else
        fail "$label: expected '$expected', got '$got'"
    fi
}
_sidecar_codex_auth="$TMPDIR_ROOT/sidecar-codex-auth.txt"
printf 'Error: not logged in\n' > "$_sidecar_codex_auth"
assert_verdict "verdict: auth precedence → auth-retries-exhausted" "auth-retries-exhausted" \
    external_failure_verdict "codex" "$_sidecar_codex_auth"
assert_verdict "verdict: quota → quota" "quota" \
    external_failure_verdict "codex" "$_sidecar_quota"
assert_verdict "verdict: generic readable → non-auth" "non-auth" \
    external_failure_verdict "codex" "$_sidecar_nonquota"
assert_verdict "verdict: no readable sidecar → unclassified" "unclassified" \
    external_failure_verdict "codex" "$TMPDIR_ROOT/does-not-exist.txt"
# Cursor passes two sidecars; quota detected in the second (.diag) sidecar.
assert_verdict "verdict: quota in second sidecar → quota" "quota" \
    external_failure_verdict "cursor" "$_sidecar_nonquota" "$_sidecar_quota"

# --- external_launcher_mirror_quota_from_events (#3390) ---
# codex exec --json reports usage-limit/quota on its stdout events stream, not the
# stderr sidecar; the launcher mirrors that signal into the sidecar so the
# sidecar-scanning classifiers catch it and skip the {5,7} transient-retry loop.
_events_quota="$TMPDIR_ROOT/events-quota.jsonl"
printf '%s\n' "{\"type\":\"error\",\"message\":\"You've hit your usage limit. Try again at Jun 7th, 2026 8:22 AM.\"}" > "$_events_quota"
printf '%s\n' "{\"type\":\"turn.failed\",\"error\":{\"message\":\"You've hit your usage limit.\"}}" >> "$_events_quota"
_events_clean="$TMPDIR_ROOT/events-clean.jsonl"
printf '%s\n' "{\"type\":\"item.completed\",\"item\":{\"text\":\"ordinary review output\"}}" > "$_events_clean"

# Empty sidecar + quota on the events stream → marker mirrored; sidecar now
# classifies as quota and the verdict resolves to quota end-to-end.
_mirror_sidecar="$TMPDIR_ROOT/mirror.sidecar"
: > "$_mirror_sidecar"
assert_returns "mirror: returns 0 on quota events" 0 \
    external_launcher_mirror_quota_from_events "$_events_quota" "$_mirror_sidecar"
assert_returns "mirror: empty sidecar classifies as quota after mirror" 0 \
    external_is_quota_failure "codex" "$_mirror_sidecar"
assert_verdict "mirror: verdict resolves to quota after mirror" "quota" \
    external_failure_verdict "codex" "$_mirror_sidecar"
# The mirrored marker must not collide with the auth classifier.
assert_returns "mirror: mirrored marker is not an auth match" 1 \
    external_is_auth_failure "codex" "$_mirror_sidecar"

# Idempotent: a sidecar already carrying the signature gets no second marker line.
_mirror_idem="$TMPDIR_ROOT/mirror-idem.sidecar"
printf "You've hit your usage limit already.\n" > "$_mirror_idem"
external_launcher_mirror_quota_from_events "$_events_quota" "$_mirror_idem"
if grep -Fq 'codex exec --json events stream' "$_mirror_idem" 2>/dev/null; then
    fail "mirror: must not append a marker when the sidecar already carries the signature"
else
    pass
fi

# Non-quota events → sidecar untouched and still not a quota match.
_mirror_clean="$TMPDIR_ROOT/mirror-clean.sidecar"
: > "$_mirror_clean"
external_launcher_mirror_quota_from_events "$_events_clean" "$_mirror_clean"
assert_returns "mirror: non-quota events leave sidecar non-quota" 1 \
    external_is_quota_failure "codex" "$_mirror_clean"
if [[ -s "$_mirror_clean" ]]; then
    fail "mirror: non-quota events must not write to the sidecar"
else
    pass
fi

# Missing or empty events file → no-op (returns 0), sidecar untouched. A genuine
# 0-output transient blip must stay transient-retryable.
_mirror_noevents="$TMPDIR_ROOT/mirror-noevents.sidecar"
: > "$_mirror_noevents"
assert_returns "mirror: missing events file is a no-op (returns 0)" 0 \
    external_launcher_mirror_quota_from_events "$TMPDIR_ROOT/does-not-exist.jsonl" "$_mirror_noevents"
_events_empty="$TMPDIR_ROOT/events-empty.jsonl"
: > "$_events_empty"
assert_returns "mirror: empty events file is a no-op (returns 0)" 0 \
    external_launcher_mirror_quota_from_events "$_events_empty" "$_mirror_noevents"
if [[ -s "$_mirror_noevents" ]]; then
    fail "mirror: missing/empty events must not write to the sidecar"
else
    pass
fi

# /dev/null sidecar → no-op (returns 0); the not-writable path must not error.
assert_returns "mirror: /dev/null sidecar is a no-op (returns 0)" 0 \
    external_launcher_mirror_quota_from_events "$_events_quota" "/dev/null"

PLUGIN_ROOT="$TMPDIR_ROOT/plugin-root"
mkdir -p "$PLUGIN_ROOT/scripts"
cat > "$PLUGIN_ROOT/scripts/parse-codex-usage.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
mode="${LARCH_TEST_PARSE_MODE:-success}"
case "$mode" in
    success)
        printf 'INPUT=7\nCACHED_INPUT=3\nOUTPUT=2\nTOTAL=12\n'
        ;;
    fail)
        printf 'parse-codex-usage.sh: jq failed\n' >&2
        exit 1
        ;;
    *)
        exit 2
        ;;
esac
EOF
chmod +x "$PLUGIN_ROOT/scripts/parse-codex-usage.sh"
cat > "$PLUGIN_ROOT/scripts/token-ledger.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${LARCH_TEST_LEDGER_CALLS:?}"
EOF
chmod +x "$PLUGIN_ROOT/scripts/token-ledger.sh"

RECORD_SIDECAR="$TMPDIR_ROOT/usage.sidecar"
RECORD_FILE="$TMPDIR_ROOT/usage.token-record"
LEDGER_CALLS="$TMPDIR_ROOT/ledger-calls.txt"
EVENTS_FILE="$TMPDIR_ROOT/events.jsonl"
printf '{"type":"token_usage","input_tokens":10,"cached_input_tokens":3,"output_tokens":2}\n' > "$EVENTS_FILE"

LARCH_TEST_PARSE_MODE=success \
    external_launcher_record_usage_from_events "$PLUGIN_ROOT" "$EVENTS_FILE" "$RECORD_SIDECAR" "codex_review" "$RECORD_FILE"
if [[ "$(cat "$RECORD_FILE" 2>/dev/null)" == $'TOOL=codex\nINPUT=7\nOUTPUT=2\nCACHE_READ=3\nTOTAL=12\nRAW=codex_review' ]]; then
    pass
else
    fail "token-record sidecar content mismatch: $(cat "$RECORD_FILE" 2>/dev/null)"
fi

LARCH_TEST_PARSE_MODE=success LARCH_TEST_LEDGER_CALLS="$LEDGER_CALLS" \
    external_launcher_record_usage_from_events "$PLUGIN_ROOT" "$EVENTS_FILE" "$RECORD_SIDECAR" "codex_ci_fix"
if grep -Fqx 'record-vendor codex input=7 cache_read=3 output=2 total=12 raw=codex_ci_fix' "$LEDGER_CALLS" 2>/dev/null; then
    pass
else
    fail "ledger mode args mismatch: $(cat "$LEDGER_CALLS" 2>/dev/null)"
fi

rm -f "$RECORD_FILE"
LARCH_TEST_PARSE_MODE=fail \
    external_launcher_record_usage_from_events "$PLUGIN_ROOT" "$EVENTS_FILE" "$RECORD_SIDECAR" "codex_review" "$RECORD_FILE"
if grep -Fq 'parse-codex-usage.sh: jq failed' "$RECORD_SIDECAR" 2>/dev/null && [[ ! -e "$RECORD_FILE" ]]; then
    pass
else
    fail "fail-closed parse should append sidecar diagnostic without writing token-record"
fi

MISSING_EVENTS="$TMPDIR_ROOT/missing-events.jsonl"
rm -f "$MISSING_EVENTS"
MISSING_SIDECAR="$TMPDIR_ROOT/missing-events.sidecar"
rm -f "$MISSING_SIDECAR"
LARCH_TEST_PARSE_MODE=fail \
    external_launcher_record_usage_from_events "$PLUGIN_ROOT" "$MISSING_EVENTS" "$MISSING_SIDECAR" "codex_review"
if grep -Fq 'parse-codex-usage.sh: jq failed' "$MISSING_SIDECAR" 2>/dev/null; then
    pass
else
    fail "missing/empty events parse should still append sidecar diagnostic"
fi

# external_launcher_append_outer_meta: optional STDERR_SINK= line.
APPEND_META="$TMPDIR_ROOT/append-outer.meta"
printf 'TOOL=cursor\nTIMEOUT=5\n' > "$APPEND_META"
external_launcher_append_outer_meta "$APPEND_META" "/repo/scripts/launch-review.sh" "/tmp/out.prompt" "/tmp/work" "" "/tmp/custom.stderr.log"
if grep -Fxq 'STDERR_SINK=/tmp/custom.stderr.log' "$APPEND_META"; then
    pass
else
    fail "append_outer_meta with stderr_sink must write STDERR_SINK= line"
fi
if grep -Fxq 'OUTER_LAUNCHER_RISK=high' "$APPEND_META"; then
    pass
else
    fail "append_outer_meta empty 5th risk arg must record OUTER_LAUNCHER_RISK=high"
fi

APPEND_META_NO_SINK="$TMPDIR_ROOT/append-outer-no-sink.meta"
printf 'TOOL=cursor\nTIMEOUT=5\n' > "$APPEND_META_NO_SINK"
external_launcher_append_outer_meta "$APPEND_META_NO_SINK" "/repo/scripts/launch-review.sh" "/tmp/out.prompt" "/tmp/work"
if grep -q '^STDERR_SINK=' "$APPEND_META_NO_SINK" 2>/dev/null; then
    fail "append_outer_meta without stderr_sink must omit STDERR_SINK= line"
else
    pass
fi

run_health_gate_case() {
    local label="$1" tool="$2" env_timeout="$3" session_timeout="$4" implement_timeout="$5" present_line="$6" checker_rc="$7" timeout_rc="$8"
    local case_dir="$TMPDIR_ROOT/health-$label"
    local rc_file="$case_dir/rc"
    local call_file="$case_dir/checker-call"
    mkdir -p "$case_dir/scripts" "$case_dir/bin"
    cp "$REPO_ROOT/scripts/lib-external-launcher-common.sh" "$case_dir/scripts/lib-external-launcher-common.sh"
    cp "$REPO_ROOT/scripts/read-session-env-key.sh" "$case_dir/scripts/read-session-env-key.sh"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$case_dir/scripts/lib-quiet.sh"
    chmod +x "$case_dir/scripts/read-session-env-key.sh"
    cat > "$case_dir/scripts/check-reviewers.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
{
    printf 'ARGS=%s\n' "$*"
    printf 'AUTH_RETRIES=%s\n' "${LARCH_EXTERNAL_AUTH_RETRIES:-}"
} >> "${LARCH_TEST_CHECKER_CALL:?}"
if [[ -n "${LARCH_TEST_PRESENT_LINE:-}" ]]; then
    printf '%s\n' "$LARCH_TEST_PRESENT_LINE"
fi
exit "${LARCH_TEST_CHECKER_RC:-0}"
EOF
    chmod +x "$case_dir/scripts/check-reviewers.sh"
    cat > "$case_dir/bin/timeout" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${LARCH_TEST_TIMEOUT_RC:-}" ]]; then
    exit "$LARCH_TEST_TIMEOUT_RC"
fi
shift
exec "$@"
EOF
    chmod +x "$case_dir/bin/timeout"

    if [[ -n "$session_timeout" ]]; then
        printf 'LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=%s\n' "$session_timeout" > "$case_dir/session-env-path.env"
    fi
    if [[ -n "$implement_timeout" ]]; then
        mkdir -p "$case_dir/implement"
        printf 'LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=%s\n' "$implement_timeout" > "$case_dir/implement/session-env.sh"
    fi

    set +e
    LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT="$env_timeout" \
        LARCH_TEST_PRESENT_LINE="$present_line" \
        LARCH_TEST_CHECKER_RC="$checker_rc" \
        LARCH_TEST_TIMEOUT_RC="$timeout_rc" \
        LARCH_TEST_CHECKER_CALL="$call_file" \
        SESSION_ENV_PATH="$case_dir/session-env-path.env" \
        IMPLEMENT_TMPDIR="$case_dir/implement" \
        PATH="$case_dir/bin:$PATH" \
        bash -c 'source "$1"; external_launch_health_gate "$2"' bash "$case_dir/scripts/lib-external-launcher-common.sh" "$tool" \
        >"$case_dir/stdout" 2>"$case_dir/stderr"
    printf '%s\n' "$?" > "$rc_file"
    set -e
    printf '%s' "$case_dir"
}

assert_health_gate_rc() {
    local label="$1" want_rc="$2"
    shift 2
    local case_dir rc
    case_dir=$(run_health_gate_case "$label" "$@")
    rc=$(cat "$case_dir/rc")
    if [[ "$rc" == "$want_rc" ]]; then
        pass
    else
        fail "$label: expected health gate rc $want_rc, got $rc (stderr=$(cat "$case_dir/stderr"))"
    fi
    printf '%s' "$case_dir"
}

_hg_case=$(assert_health_gate_rc "health gate codex healthy" 0 codex 5 "" "" "CODEX_PRESENT=true" 0 "")
if grep -Fq 'ARGS=--skip-cursor-probe' "$_hg_case/checker-call" && grep -Fq 'AUTH_RETRIES=1' "$_hg_case/checker-call"; then
    pass
else
    fail "health gate codex healthy should call check-reviewers with skip-cursor and one auth retry"
fi

assert_health_gate_rc "health gate cursor unhealthy false" 1 cursor 5 "" "" "CURSOR_PRESENT=false" 0 "" >/dev/null
assert_health_gate_rc "health gate timeout 124 unhealthy before fail-open" 1 codex 5 "" "" "" 0 124 >/dev/null
assert_health_gate_rc "health gate timeout 143 unhealthy before fail-open" 1 cursor 5 "" "" "" 0 143 >/dev/null

_hg_off=$(assert_health_gate_rc "health gate off without timeout" 0 codex "" "" "" "CODEX_PRESENT=false" 0 "")
if [[ ! -e "$_hg_off/checker-call" ]]; then
    pass
else
    fail "health gate off without timeout must not call check-reviewers"
fi

_hg_zero=$(assert_health_gate_rc "health gate zero opt-out beats session fallback" 0 codex 0 5 5 "CODEX_PRESENT=false" 0 "")
if [[ ! -e "$_hg_zero/checker-call" ]]; then
    pass
else
    fail "health gate zero opt-out must not call check-reviewers"
fi

assert_health_gate_rc "health gate reads SESSION_ENV_PATH" 1 cursor "" 5 "" "CURSOR_PRESENT=false" 0 "" >/dev/null
assert_health_gate_rc "health gate reads IMPLEMENT_TMPDIR session env" 1 codex "" "" 5 "CODEX_PRESENT=false" 0 "" >/dev/null

_hg_non_tool=$(assert_health_gate_rc "health gate ignores non external tool" 0 claude 5 "" "" "CODEX_PRESENT=false" 0 "")
if [[ ! -e "$_hg_non_tool/checker-call" ]]; then
    pass
else
    fail "health gate non-tool must not call check-reviewers"
fi

assert_health_gate_rc "health gate fail-open on unparsable non-timeout result" 0 codex 5 "" "" "" 2 "" >/dev/null

if (( FAIL > 0 )); then
    printf 'FAIL: test-lib-external-launcher-common.sh — %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    for f in "${FAILURES[@]}"; do
        printf '  %s\n' "$f" >&2
    done
    exit 1
fi

printf 'PASS: test-lib-external-launcher-common.sh — %s assertions passed\n' "$PASS"
