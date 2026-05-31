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

if (( FAIL > 0 )); then
    printf 'FAIL: test-lib-external-launcher-common.sh — %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    for f in "${FAILURES[@]}"; do
        printf '  %s\n' "$f" >&2
    done
    exit 1
fi

printf 'PASS: test-lib-external-launcher-common.sh — %s assertions passed\n' "$PASS"
