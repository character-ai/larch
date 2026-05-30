#!/usr/bin/env bash
# Regression coverage for collect-agent-results.sh transient-network retry routing.

set -uo pipefail

export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05
export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTOR="$REPO_ROOT/scripts/collect-agent-results.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-collect-agent-results-XXXXXX")" || { echo "mktemp failed" >&2; exit 1; }
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX || true
export LARCH_EXECUTION_ISSUES_LOG="$TMPROOT/execution-issues.md"
trap 'rm -rf "$TMPROOT" 2>/dev/null' EXIT

PASS=0
FAIL=0
FAILED=()

ok() {
    PASS=$((PASS + 1))
    echo "  ok: $1"
}

fail() {
    FAIL=$((FAIL + 1))
    FAILED+=("$1")
    echo "  FAIL: $1" >&2
}

require_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        fail "missing required tool: $1"
    fi
}

assert_line() {
    local label="$1"
    local expected="$2"
    local haystack="$3"
    if printf '%s\n' "$haystack" | grep -Fxq "$expected"; then
        ok "$label"
    else
        fail "$label: missing line '$expected'"
        printf '%s\n' "$haystack" >&2
    fi
}

assert_line_regex() {
    local label="$1"
    local pattern="$2"
    local haystack="$3"
    if printf '%s\n' "$haystack" | grep -Eq "$pattern"; then
        ok "$label"
    else
        fail "$label: missing pattern '$pattern'"
        printf '%s\n' "$haystack" >&2
    fi
}

assert_no_retry_file() {
    local label="$1"
    local output="$2"
    local retry_output="${output%.txt}-retry.txt"
    if [[ -e "$retry_output" || -e "${retry_output}.done" ]]; then
        fail "$label: retry artifacts should not exist"
    else
        ok "$label"
    fi
}

require_tool jq

STUB_BIN="$TMPROOT/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'CURSOR_STUB'
#!/usr/bin/env bash
set -euo pipefail
helper=""
args=("$@")
while [[ $# -gt 0 ]]; do
    case "$1" in
        --helper)
            helper="${2:?--helper requires a value}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
[[ -n "$helper" ]] || exit 40
exec bash "$helper" "${args[@]}"
CURSOR_STUB
chmod +x "$STUB_BIN/cursor"
PATH="$STUB_BIN:$PATH"
export PATH

SUCCESS_HELPER="$TMPROOT/retry-success.sh"
cat > "$SUCCESS_HELPER" <<'SUCCESS_HELPER_EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            out="${2:?--output requires a value}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
[[ -n "$out" ]] || exit 40
printf 'NO_ISSUES_FOUND\n' > "$out"
SUCCESS_HELPER_EOF
chmod +x "$SUCCESS_HELPER"

STRUCTURED_SUCCESS_HELPER="$TMPROOT/retry-structured-success.sh"
cat > "$STRUCTURED_SUCCESS_HELPER" <<'STRUCTURED_SUCCESS_HELPER_EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            out="${2:?--output requires a value}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done
[[ -n "$out" ]] || exit 40
printf 'NO_ISSUES_FOUND\n' > "$out"
STRUCTURED_SUCCESS_HELPER_EOF
chmod +x "$STRUCTURED_SUCCESS_HELPER"

FAIL_HELPER="$TMPROOT/retry-fail.sh"
cat > "$FAIL_HELPER" <<'FAIL_HELPER_EOF'
#!/usr/bin/env bash
exit 7
FAIL_HELPER_EOF
chmod +x "$FAIL_HELPER"

RETRY_CONTENT="NO_ISSUES_FOUND"

json_array() {
    local helper="$1"
    local output="$2"
    jq -cn --args '$ARGS.positional' -- cursor agent --workspace "$TMPROOT" --helper "$helper" --output "$output" "Review the diff and emit findings only."
}

write_meta() {
    local output="$1"
    local helper="$2"
    {
        printf 'TOOL=cursor\n'
        printf 'TIMEOUT=2\n'
        printf 'CAPTURE_STDOUT=false\n'
        printf 'CAPTURE_STDOUT_ONLY=false\n'
        printf 'OUTPUT_FILE=%s\n' "$output"
        printf 'CMD_JSON=%s\n' "$(json_array "$helper" "$output")"
    } > "${output}.meta"
}

run_collector() {
    local timeout="$1"
    local output="$2"
    local stderr
    stderr="$TMPROOT/$(basename "$output").stderr"
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout "$timeout" "$output" 2>"$stderr"
}

# shellcheck source=scripts/lib-net.sh
if source "$REPO_ROOT/scripts/lib-net.sh" && [[ "${LARCH_LIB_NET_LOADED:-}" == "1" ]]; then
    ok "lib-net source guard"
else
    fail "lib-net source guard"
fi

assert_transient_signature() {
    local label="$1"
    local text="$2"
    if is_transient_net_signature "$text"; then
        ok "$label"
    else
        fail "$label: expected transient signature"
    fi
}

assert_not_transient_signature() {
    local label="$1"
    local text="$2"
    if is_transient_net_signature "$text"; then
        fail "$label: expected non-transient signature"
    else
        ok "$label"
    fi
}

assert_transient_signature "lib-net detects DNS failures" "fatal: Could not resolve host: example.invalid"
assert_transient_signature "lib-net detects connection reset" "read tcp: connection reset by peer"
assert_transient_signature "lib-net detects context deadline" "rpc error: context deadline exceeded"
assert_transient_signature "lib-net detects no valid output retry exhaustion" "ci-status.sh returned no valid output 3 times consecutively"
assert_transient_signature "lib-net detects git fetch failures" "git fetch origin main failed (network/auth issue)"
assert_not_transient_signature "lib-net rejects non-network errors" "reviewer prompt malformed"

# C_OK: collector status OK on normal external output (.done present).
echo "# Case: collector status OK on normal external output"
OUT_DONE="$TMPROOT/cursor-done-sentinel.txt"
printf 'NO_ISSUES_FOUND\n' > "$OUT_DONE"
printf '0\n' > "${OUT_DONE}.done"
RESULT_DONE=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 "$OUT_DONE" 2>/dev/null)
assert_line "C_OK collector status OK" "STATUS=OK" "$RESULT_DONE"

# C_T1: initial FAILED with transient network diagnostic retries and recovers.
OUT_T1="$TMPROOT/cursor-t1.txt"
: > "$OUT_T1"
printf '1\n' > "${OUT_T1}.done"
printf 'Could not resolve host: example.invalid\n' > "${OUT_T1}.diag"
write_meta "$OUT_T1" "$SUCCESS_HELPER"
RESULT_T1=$(run_collector 5 "$OUT_T1")
assert_line "C_T1 retry file" "REVIEWER_FILE=${OUT_T1%.txt}-retry.txt" "$RESULT_T1"
assert_line "C_T1 status" "STATUS=OK" "$RESULT_T1"
assert_line "C_T1 stderr retry diagnostic" "collect-agent-results.sh: transient diagnostic for $(basename "$OUT_T1"); retrying once" "$(cat "$TMPROOT/$(basename "$OUT_T1").stderr")"

# C_T2: transient initial FAILED retries, but retry failure is reported as EMPTY_OUTPUT.
OUT_T2="$TMPROOT/cursor-t2.txt"
: > "$OUT_T2"
printf '1\n' > "${OUT_T2}.done"
printf 'Could not resolve host: example.invalid\n' > "${OUT_T2}.diag"
write_meta "$OUT_T2" "$FAIL_HELPER"
RESULT_T2=$(run_collector 5 "$OUT_T2")
assert_line "C_T2 status" "STATUS=EMPTY_OUTPUT" "$RESULT_T2"
assert_line_regex "C_T2 retry failure reason" '^FAILURE_REASON=Retry also failed:' "$RESULT_T2"

# C_T3: non-transient FAILED does not retry even with valid metadata.
OUT_T3="$TMPROOT/cursor-t3.txt"
: > "$OUT_T3"
printf '1\n' > "${OUT_T3}.done"
printf 'reviewer prompt malformed\n' > "${OUT_T3}.diag"
write_meta "$OUT_T3" "$SUCCESS_HELPER"
RESULT_T3=$(run_collector 5 "$OUT_T3")
assert_line "C_T3 status" "STATUS=FAILED" "$RESULT_T3"
assert_no_retry_file "C_T3 no retry" "$OUT_T3"

# C_T4: SENTINEL_TIMEOUT with transient diagnostic enters retry and recovers.
OUT_T4="$TMPROOT/cursor-t4.txt"
: > "$OUT_T4"
printf 'TLS handshake failed while connecting\n' > "${OUT_T4}.diag"
write_meta "$OUT_T4" "$SUCCESS_HELPER"
RESULT_T4=$(run_collector 1 "$OUT_T4")
assert_line "C_T4 retry file" "REVIEWER_FILE=${OUT_T4%.txt}-retry.txt" "$RESULT_T4"
assert_line "C_T4 status" "STATUS=OK" "$RESULT_T4"
assert_line "C_T4 stderr retry diagnostic" "collect-agent-results.sh: transient diagnostic for $(basename "$OUT_T4"); retrying once" "$(cat "$TMPROOT/$(basename "$OUT_T4").stderr")"

# C_T5: SENTINEL_TIMEOUT without a transient diagnostic remains a timeout.
OUT_T5="$TMPROOT/cursor-t5.txt"
: > "$OUT_T5"
write_meta "$OUT_T5" "$SUCCESS_HELPER"
RESULT_T5=$(run_collector 1 "$OUT_T5")
assert_line "C_T5 status" "STATUS=SENTINEL_TIMEOUT" "$RESULT_T5"
assert_no_retry_file "C_T5 no retry" "$OUT_T5"

# C_IT1: synthetic reviewer output with inline TSV inside a code fence passes
# --substantive-validation --validation-mode (no NOT_SUBSTANTIVE).
OUT_IT1="$TMPROOT/cursor-it1.txt"
cat > "$OUT_IT1" <<'EOF'
Synthetic plan-review output for collector validation. The body is intentionally
short-form reviewer prose with one concrete source anchor,
scripts/collect-agent-results.sh:1, plus an inline TSV payload so
validation-mode accepts it as substantive structured reviewer content without
depending on any incidental meta narration about tool limitations.

```
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/foo.sh:42	Null pointer not checked	Returns nil on error path	Add nil guard before use
1	in_scope	nit	code-quality	scripts/bar.sh:10	Unused variable x	Dead code	Remove the variable
```
EOF
printf '0\n' > "${OUT_IT1}.done"
RESULT_IT1=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_IT1" 2>/dev/null)
assert_line "C_IT1 status not NOT_SUBSTANTIVE" "STATUS=OK" "$RESULT_IT1"

# C_IT2: cursor output with only short narration (no TSV, < 30 words) is NOT_SUBSTANTIVE.
OUT_IT2="$TMPROOT/cursor-it2.txt"
printf 'Read-only: we cannot write the sidecar file.\n' > "$OUT_IT2"
printf '0\n' > "${OUT_IT2}.done"
RESULT_IT2=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_IT2" 2>/dev/null)
assert_line "C_IT2 status is NOT_SUBSTANTIVE" "STATUS=NOT_SUBSTANTIVE" "$RESULT_IT2"

# C_NS_RETRY: NOT_SUBSTANTIVE output with a valid .meta triggers a retry attempt.
# The harness uses a deterministic CMD_JSON replay stub and requires the retry
# artifact/result instead of treating launch as best-effort.
echo "# Case: NOT_SUBSTANTIVE output with CMD_JSON .meta — retry succeeds"
OUT_NSR="$TMPROOT/cursor-specialist-structure-output.txt"
STDERR_NSR="$TMPROOT/case-nsr.stderr"
printf 'Reading the ballot file and gathering diff context.\n' > "$OUT_NSR"
printf '0\n' > "${OUT_NSR}.done"
write_meta "$OUT_NSR" "$SUCCESS_HELPER"
RESULT_NSR=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_NSR" 2>"$STDERR_NSR")
assert_line "C_NSR retry file selected (publish to orig)" "REVIEWER_FILE=$OUT_NSR" "$RESULT_NSR"
assert_line "C_NSR retry status OK" "STATUS=OK" "$RESULT_NSR"
if grep -Fq "$RETRY_CONTENT" "$OUT_NSR" 2>/dev/null; then
    ok "C_NSR orig path has retry content"
else
    fail "C_NSR orig path missing retry content"
fi
NS_RETRY_SENTINEL="${OUT_NSR%.txt}-ns-retry.txt.done"
if [[ -f "$NS_RETRY_SENTINEL" ]]; then
    ok "C_NSR retry sentinel created"
else
    fail "C_NSR retry sentinel missing"
fi
NSR_RETRY_OUTPUT="${OUT_NSR%.txt}-ns-retry.txt"
if grep -Fq "$RETRY_CONTENT" "$NSR_RETRY_OUTPUT" 2>/dev/null; then
    ok "C_NSR retry artifact retained"
else
    fail "C_NSR retry artifact missing retry content"
fi
# C_NSR_REASON: the ns-retry .meta sidecar must contain NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN
# (exit 2 from validate-research-output.sh — body too thin — maps to that token).
NSR_RETRY_META="${NSR_RETRY_OUTPUT}.meta"
if grep -Fq "NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN" "$NSR_RETRY_META" 2>/dev/null; then
    ok "C_NSR_REASON ns-retry .meta has NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN"
else
    fail "C_NSR_REASON ns-retry .meta missing NS_RETRY_REASON=NO_ISSUES_FOUND_TOO_THIN (meta: $(cat "$NSR_RETRY_META" 2>/dev/null || echo '<missing>'))"
fi
if grep -Fq 'ns-retry: first-pass content preserved at cursor-specialist-structure-output-first-pass.txt' "$STDERR_NSR" 2>/dev/null; then
    ok "C_NSR stderr surfaces first-pass preservation breadcrumb"
else
    fail "C_NSR stderr missing first-pass preservation breadcrumb"
fi
if grep -Fq 'ns-retry: published retry content to cursor-specialist-structure-output.txt; retry artifact retained at cursor-specialist-structure-output-ns-retry.txt' "$STDERR_NSR" 2>/dev/null; then
    ok "C_NSR stderr surfaces retry publish breadcrumb"
else
    fail "C_NSR stderr missing retry publish breadcrumb"
fi

# C_NS_STRUCTURED: section 3.6 downgrade must re-run structured validation
# before restoring STATUS=OK, publish retry prose back to the original path,
# and retain the first-pass prose in a sidecar.
echo "# Case: structured-reviewer downgrade retries through structured validation"
OUT_NSS="$TMPROOT/cursor-specialist-structured-output.txt"
cat > "$OUT_NSS" <<'EOF'
This response stays narrative-only so it clears the short-response floor, but it
still omits any JSONL or TSV reviewer records. The retry path must therefore
re-run structured validation instead of only checking for generic substantive
text after the replay completes successfully. Source anchor:
scripts/collect-agent-results.sh:1 documents the collector contract this prose
is discussing, but the body still refuses to emit structured reviewer records.
EOF
printf '0\n' > "${OUT_NSS}.done"
printf 'stale failure tail before ns-retry OK\n' > "${OUT_NSS}.stderr-tail"
write_meta "$OUT_NSS" "$STRUCTURED_SUCCESS_HELPER"
STDERR_NSS="$TMPROOT/case-nss.stderr"
RESULT_NSS=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode --structured-reviewer-validation "$OUT_NSS" 2>"$STDERR_NSS")
assert_line "C_NSS retry file selected (publish to orig)" "REVIEWER_FILE=$OUT_NSS" "$RESULT_NSS"
assert_line "C_NSS retry status OK" "STATUS=OK" "$RESULT_NSS"
assert_line "C_NSS structured sidecar emitted (orig path)" "STRUCTURED_SIDECAR=${OUT_NSS}.tsv" "$RESULT_NSS"
if [[ -f "${OUT_NSS%.txt}-ns-retry.txt.done" ]]; then
    ok "C_NSS retry sentinel created"
else
    fail "C_NSS retry sentinel missing"
fi
NSS_SIDECAR="${OUT_NSS%.txt}-first-pass.txt"
if [[ -f "$NSS_SIDECAR" ]]; then
    ok "C_NSS sidecar exists"
    if grep -Fq "This response stays narrative-only so it clears the short-response floor, but it" "$NSS_SIDECAR"; then
        ok "C_NSS sidecar has first-pass content"
    else
        fail "C_NSS sidecar missing first-pass content"
    fi
else
    fail "C_NSS sidecar not created"
fi
NSS_RETRY_OUTPUT="${OUT_NSS%.txt}-ns-retry.txt"
if grep -Fq "NO_ISSUES_FOUND" "$NSS_RETRY_OUTPUT" 2>/dev/null; then
    ok "C_NSS retry artifact retained"
else
    fail "C_NSS retry artifact missing retry content"
fi
if grep -Fq 'ns-retry: first-pass content preserved at cursor-specialist-structured-output-first-pass.txt' "$STDERR_NSS" 2>/dev/null; then
    ok "C_NSS stderr surfaces first-pass preservation breadcrumb"
else
    fail "C_NSS stderr missing first-pass preservation breadcrumb"
fi
if grep -Fq 'ns-retry: published retry content to cursor-specialist-structured-output.txt; retry artifact retained at cursor-specialist-structured-output-ns-retry.txt' "$STDERR_NSS" 2>/dev/null; then
    ok "C_NSS stderr surfaces retry publish breadcrumb"
else
    fail "C_NSS stderr missing retry publish breadcrumb"
fi
if [[ ! -e "${OUT_NSS}.stderr-tail" ]]; then
    ok "C_NSS stale stderr-tail removed after ns-retry OK"
else
    fail "C_NSS stale stderr-tail still present after ns-retry OK"
fi

# C_NS_FP_SUCCESS: NS-retry success path produces a -first-pass.txt sidecar.
# The original output (first-pass) must be copied to -first-pass.txt and the
# retry's content must appear at the original path while the retry artifact remains.
echo "# Case: NS-retry success — first-pass sidecar produced"
OUT_NSF="$TMPROOT/cursor-specialist-edge-cases-output.txt"
FIRST_PASS_CONTENT="First-pass narrative only, no findings."
printf '%s\n' "$FIRST_PASS_CONTENT" > "$OUT_NSF"
printf '0\n' > "${OUT_NSF}.done"
write_meta "$OUT_NSF" "$SUCCESS_HELPER"
RESULT_NSF=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_NSF" 2>/dev/null)
assert_line "C_NS_FP_SUCCESS reviewer file is orig" "REVIEWER_FILE=$OUT_NSF" "$RESULT_NSF"
assert_line "C_NS_FP_SUCCESS status OK" "STATUS=OK" "$RESULT_NSF"
NSF_SIDECAR="${OUT_NSF%.txt}-first-pass.txt"
if [[ -f "$NSF_SIDECAR" ]]; then
    ok "C_NS_FP_SUCCESS sidecar exists"
    if grep -Fxq "$FIRST_PASS_CONTENT" "$NSF_SIDECAR"; then
        ok "C_NS_FP_SUCCESS sidecar has first-pass content"
    else
        fail "C_NS_FP_SUCCESS sidecar missing first-pass content"
    fi
else
    fail "C_NS_FP_SUCCESS sidecar not created"
fi
if grep -Fq "$RETRY_CONTENT" "$OUT_NSF" 2>/dev/null; then
    ok "C_NS_FP_SUCCESS orig path has retry content"
else
    fail "C_NS_FP_SUCCESS orig path missing retry content"
fi
NSF_RETRY_OUTPUT="${OUT_NSF%.txt}-ns-retry.txt"
if grep -Fq "$RETRY_CONTENT" "$NSF_RETRY_OUTPUT" 2>/dev/null; then
    ok "C_NS_FP_SUCCESS retry artifact retained"
else
    fail "C_NS_FP_SUCCESS retry artifact missing retry content"
fi

# C_NS_FP_NO_LAUNCH: when NS retry is never launched (.meta absent), no
# -first-pass.txt sidecar must be created.
echo "# Case: NS-retry not launched — no first-pass sidecar"
OUT_NSFAIL="$TMPROOT/cursor-specialist-security-output.txt"
printf 'Short text.\n' > "$OUT_NSFAIL"
printf '0\n' > "${OUT_NSFAIL}.done"
# No .meta → NS-retry metadata invalid, no retry launched
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_NSFAIL" >/dev/null 2>/dev/null
NSFAIL_SIDECAR="${OUT_NSFAIL%.txt}-first-pass.txt"
if [[ -f "$NSFAIL_SIDECAR" ]]; then
    fail "C_NS_FP_NO_LAUNCH sidecar must not exist when retry not launched"
else
    ok "C_NS_FP_NO_LAUNCH no sidecar when retry not launched"
fi

# C_NS_FP_RETRY_FAIL: when a retry launches but fails, no -first-pass.txt
# sidecar must be created.
echo "# Case: NS-retry launched but failed — no first-pass sidecar"
OUT_NSFAIL_RETRY="$TMPROOT/cursor-specialist-testing-output.txt"
printf 'Short text.\n' > "$OUT_NSFAIL_RETRY"
printf '0\n' > "${OUT_NSFAIL_RETRY}.done"
write_meta "$OUT_NSFAIL_RETRY" "$FAIL_HELPER"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_NSFAIL_RETRY" >/dev/null 2>/dev/null
NSFAIL_RETRY_SENTINEL="${OUT_NSFAIL_RETRY%.txt}-ns-retry.txt.done"
if [[ -f "$NSFAIL_RETRY_SENTINEL" ]]; then
    ok "C_NS_FP_RETRY_FAIL retry sentinel created"
else
    fail "C_NS_FP_RETRY_FAIL retry sentinel missing"
fi
NSFAIL_RETRY_SIDECAR="${OUT_NSFAIL_RETRY%.txt}-first-pass.txt"
if [[ -f "$NSFAIL_RETRY_SIDECAR" ]]; then
    fail "C_NS_FP_RETRY_FAIL sidecar must not exist when retry fails"
else
    ok "C_NS_FP_RETRY_FAIL no sidecar when retry fails"
fi

echo "# Case: NS-retry failure stderr-tail preferred over stale orig"
OUT_NSFAIL_TAIL="$TMPROOT/cursor-specialist-ns-retry-fail-output.txt"
: >"$OUT_NSFAIL_TAIL"
printf '1\n' >"${OUT_NSFAIL_TAIL}.done"
printf 'non-transient failure\n' >"${OUT_NSFAIL_TAIL}.diag"
write_meta "$OUT_NSFAIL_TAIL" "$SUCCESS_HELPER"
printf 'stale first-pass tail\n' >"${OUT_NSFAIL_TAIL}.stderr-tail"
NSFAIL_TAIL_RETRY="${OUT_NSFAIL_TAIL%.txt}-ns-retry.txt"
printf 'ns-retry stderr tail line\n' >"${NSFAIL_TAIL_RETRY}.stderr-tail"
NSFAIL_TAIL_STDERR="$TMPROOT/ns-retry-fail-collector.stderr"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_NSFAIL_TAIL" \
    2>"$NSFAIL_TAIL_STDERR" >/dev/null
if grep -Fq 'ns-retry stderr tail line' "$NSFAIL_TAIL_STDERR"; then
    ok "ns-retry failure prefers ns-retry stderr-tail on FD 2"
else
    fail "ns-retry failure missing ns-retry stderr-tail on FD 2"
fi
if ! grep -Fq 'stale first-pass tail' "$NSFAIL_TAIL_STDERR"; then
    ok "ns-retry failure does not emit stale orig stderr-tail"
else
    fail "ns-retry failure leaked stale orig stderr-tail"
fi

# C_NS_FP_PUBLISH_FAIL: if publishing validated retry content fails after the
# first-pass sidecar copy succeeds, the collector must keep the original output
# intact and remove the sidecar to avoid a misleading partial-success artifact.
echo "# Case: NS-retry publish failure cleans up sidecar and preserves orig"
MV_FAIL_BIN="$TMPROOT/mv-fail-bin"
mkdir -p "$MV_FAIL_BIN"
cat > "$MV_FAIL_BIN/mv" <<'MV_FAIL_EOF'
#!/usr/bin/env bash
exit 1
MV_FAIL_EOF
chmod +x "$MV_FAIL_BIN/mv"
OUT_NSFAIL_PUBLISH="$TMPROOT/cursor-specialist-publish-fail-output.txt"
FIRST_PASS_PUBLISH_FAIL="First-pass content must survive publish failure."
RETRY_PUBLISH_FAIL="NO_ISSUES_FOUND"
printf '%s\n' "$FIRST_PASS_PUBLISH_FAIL" > "$OUT_NSFAIL_PUBLISH"
NSFAIL_PUBLISH_RETRY="${OUT_NSFAIL_PUBLISH%.txt}-ns-retry.txt"
printf '%s\n' "$RETRY_PUBLISH_FAIL" > "$NSFAIL_PUBLISH_RETRY"
NSFAIL_PUBLISH_RESULT=$(PATH="$MV_FAIL_BIN:$PATH" bash -c '
    set -uo pipefail
    source "$1" --source-only
    preserve_and_publish_ns_retry "$2" "$3" "test publish failure"
' bash "$COLLECTOR" "$OUT_NSFAIL_PUBLISH" "$NSFAIL_PUBLISH_RETRY" 2>/dev/null || true)
if [[ -z "$NSFAIL_PUBLISH_RESULT" ]]; then
    ok "C_NS_FP_PUBLISH_FAIL helper returned no stdout"
else
    fail "C_NS_FP_PUBLISH_FAIL helper should not emit stdout"
fi
NSFAIL_PUBLISH_SIDECAR="${OUT_NSFAIL_PUBLISH%.txt}-first-pass.txt"
if [[ -f "$NSFAIL_PUBLISH_SIDECAR" ]]; then
    fail "C_NS_FP_PUBLISH_FAIL sidecar must be removed on publish failure"
else
    ok "C_NS_FP_PUBLISH_FAIL sidecar removed on publish failure"
fi
if grep -Fxq "$FIRST_PASS_PUBLISH_FAIL" "$OUT_NSFAIL_PUBLISH"; then
    ok "C_NS_FP_PUBLISH_FAIL orig path preserved"
else
    fail "C_NS_FP_PUBLISH_FAIL orig path changed unexpectedly"
fi

# C_NO_RETRY_FP: substantive first-pass (no retry needed) must not produce a sidecar.
echo "# Case: substantive first-pass — no first-pass sidecar"
OUT_NSNR="$TMPROOT/cursor-specialist-plan-fidelity-output.txt"
printf 'NO_ISSUES_FOUND\n' > "$OUT_NSNR"
printf '0\n' > "${OUT_NSNR}.done"
RESULT_NSNR=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 --substantive-validation --validation-mode "$OUT_NSNR" 2>/dev/null)
assert_line "C_NO_RETRY_FP status OK" "STATUS=OK" "$RESULT_NSNR"
NSNR_SIDECAR="${OUT_NSNR%.txt}-first-pass.txt"
if [[ -f "$NSNR_SIDECAR" ]]; then
    fail "C_NO_RETRY_FP sidecar must not exist when no retry fired"
else
    ok "C_NO_RETRY_FP no sidecar when no retry needed"
fi

# --- --paths-file mode (cross-subshell handoff; issue #2637) ---
echo "# Case: --paths-file produces same stdout as positional args"
OUT_PFA="$TMPROOT/paths-file-a.txt"
OUT_PFB="$TMPROOT/paths-file-b.txt"
printf 'NO_ISSUES_FOUND\n' > "$OUT_PFA"
printf 'NO_ISSUES_FOUND\n' > "$OUT_PFB"
printf '0\n' > "${OUT_PFA}.done"
printf '0\n' > "${OUT_PFB}.done"
paths_two="$TMPROOT/two-paths.txt"
printf '%s\n%s\n' "$OUT_PFA" "$OUT_PFB" > "$paths_two"
RES_POS=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$OUT_PFA" "$OUT_PFB" 2>/dev/null)
RES_PF=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 --paths-file "$paths_two" 2>/dev/null)
if [[ "$RES_POS" == "$RES_PF" ]]; then
    ok "paths-file happy matches positional stdout"
else
    fail "paths-file happy stdout mismatch"
    printf '%s\n' "--- positional ---" >&2
    printf '%s\n' "$RES_POS" >&2
    printf '%s\n' "--- paths-file ---" >&2
    printf '%s\n' "$RES_PF" >&2
fi

echo "# Case: --paths-file mutually exclusive with positionals"
set +e
MUTEX_ERR=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 --paths-file "$paths_two" "$OUT_PFA" 2>&1)
MUTEX_RC=$?
set -e
if [[ "$MUTEX_RC" -eq 1 ]] && grep -Fq 'mutually exclusive' <<< "$MUTEX_ERR"; then
    ok "paths-file mutex with positionals"
else
    fail "paths-file mutex expected exit 1 + mutually exclusive message (rc=$MUTEX_RC)"
    printf '%s\n' "$MUTEX_ERR" >&2
fi

echo "# Case: --paths-file empty file"
: > "$TMPROOT/empty-paths.txt"
set +e
EMPTY_ERR=$(bash "$COLLECTOR" --timeout 5 --paths-file "$TMPROOT/empty-paths.txt" 2>&1)
EMPTY_RC=$?
set -e
if [[ "$EMPTY_RC" -eq 1 ]] && grep -Fq 'paths-file contains no entries' <<< "$EMPTY_ERR"; then
    ok "paths-file empty rejects"
else
    fail "paths-file empty expected no-entries error (rc=$EMPTY_RC)"
    printf '%s\n' "$EMPTY_ERR" >&2
fi

echo "# Case: --paths-file whitespace-only"
printf '  \n\t\n  \n' > "$TMPROOT/ws-paths.txt"
set +e
WS_ERR=$(bash "$COLLECTOR" --timeout 5 --paths-file "$TMPROOT/ws-paths.txt" 2>&1)
WS_RC=$?
set -e
if [[ "$WS_RC" -eq 1 ]] && grep -Fq 'paths-file contains no entries' <<< "$WS_ERR"; then
    ok "paths-file whitespace-only rejects"
else
    fail "paths-file whitespace-only expected no-entries (rc=$WS_RC)"
    printf '%s\n' "$WS_ERR" >&2
fi

echo "# Case: --paths-file missing / not readable"
set +e
MISS_ERR=$(bash "$COLLECTOR" --timeout 5 --paths-file "$TMPROOT/does-not-exist-paths.txt" 2>&1)
MISS_RC=$?
set -e
if [[ "$MISS_RC" -eq 1 ]] && grep -Fq 'paths-file not readable' <<< "$MISS_ERR"; then
    ok "paths-file missing rejects"
else
    fail "paths-file missing expected not readable (rc=$MISS_RC)"
    printf '%s\n' "$MISS_ERR" >&2
fi

echo "# Case: --paths-file unreadable existing file"
unreadable_pf="$TMPROOT/unreadable-paths.txt"
printf '%s\n' "$OUT_PFA" > "$unreadable_pf"
chmod a-r "$unreadable_pf"
set +e
UNREAD_ERR=$(bash "$COLLECTOR" --timeout 5 --paths-file "$unreadable_pf" 2>&1)
UNREAD_RC=$?
set -e
chmod u+r "$unreadable_pf" || true
if [[ "$UNREAD_RC" -eq 1 ]] && grep -Fq 'paths-file not readable' <<< "$UNREAD_ERR"; then
    ok "paths-file unreadable rejects"
else
    fail "paths-file unreadable expected exit 1 + not readable (rc=$UNREAD_RC)"
    printf '%s\n' "$UNREAD_ERR" >&2
fi

echo "# Case: zero outputs without --paths-file"
set +e
ZERO_ERR=$(bash "$COLLECTOR" --timeout 5 2>&1)
ZERO_RC=$?
set -e
if [[ "$ZERO_RC" -eq 1 ]] && grep -Fq 'at least one output file is required' <<< "$ZERO_ERR"; then
    ok "zero outputs without paths-file"
else
    fail "zero outputs expected at least one output file (rc=$ZERO_RC)"
    printf '%s\n' "$ZERO_ERR" >&2
fi

echo "# Case: WAIT_STDERR relay strips control bytes (SCRIPT_DIR sibling harness)"
HARNESS_WAIT="$TMPROOT/wait-relay-harness"
mkdir -p "$HARNESS_WAIT/scripts"
for dep in collect-agent-results.sh external-tool-registry.sh lib-failed-agent-stderr-tail.sh lib-net.sh lib-quiet.sh; do
    cp "$REPO_ROOT/scripts/$dep" "$HARNESS_WAIT/scripts/"
done
chmod +x "$HARNESS_WAIT/scripts"/*.sh
cat > "$HARNESS_WAIT/scripts/wait-for-reviewers.sh" <<'WAIT_RELAY_STUB'
#!/usr/bin/env bash
printf '%b\n' 'HTTP 500\x07Bad Gateway\x1b[31mred\x1b[0m' >&2
exit 1
WAIT_RELAY_STUB
chmod +x "$HARNESS_WAIT/scripts/wait-for-reviewers.sh"
OUT_WAIT="$TMPROOT/wait-relay-out.txt"
printf 'NO_ISSUES_FOUND\n' > "$OUT_WAIT"
printf '1\n' > "${OUT_WAIT}.done"
set +e
WAIT_CAPTURE=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$HARNESS_WAIT/scripts/collect-agent-results.sh" --timeout 5 "$OUT_WAIT" 2>&1)
WAIT_RC=$?
set -e
if [[ "$WAIT_RC" -eq 1 ]]; then
    ok "WAIT_STDERR relay wait failure exits 1"
else
    fail "WAIT_STDERR relay expected exit 1 (rc=$WAIT_RC)"
fi
if grep -Fq 'HTTP 500' <<< "$WAIT_CAPTURE" && grep -Fq 'Bad Gateway' <<< "$WAIT_CAPTURE"; then
    ok "WAIT_STDERR relay preserves printable text"
else
    fail "WAIT_STDERR relay missing printable text"
    printf '%s\n' "$WAIT_CAPTURE" >&2
fi
if grep -aF $'\x07' <<< "$WAIT_CAPTURE" >/dev/null; then
    fail "WAIT_STDERR relay still contains BEL"
else
    ok "WAIT_STDERR relay strips BEL"
fi
if grep -aF $'\x1b' <<< "$WAIT_CAPTURE" >/dev/null; then
    fail "WAIT_STDERR relay still contains ESC"
else
    ok "WAIT_STDERR relay strips ESC"
fi

echo "# Case: duplicate failure stderr tails dedup on FD 2"
DEDUP_A="$TMPROOT/dedup-a.txt"
DEDUP_B="$TMPROOT/dedup-b.txt"
: >"$DEDUP_A"
: >"$DEDUP_B"
printf '1\n' >"${DEDUP_A}.done"
printf '1\n' >"${DEDUP_B}.done"
printf 'non-transient failure\n' >"${DEDUP_A}.diag"
printf 'non-transient failure\n' >"${DEDUP_B}.diag"
write_meta "$DEDUP_A" "$SUCCESS_HELPER"
write_meta "$DEDUP_B" "$SUCCESS_HELPER"
printf 'fatal tool error line\n' >"${DEDUP_A}.stderr-tail"
printf 'fatal tool error line\n' >"${DEDUP_B}.stderr-tail"
DEDUP_STDERR="$TMPROOT/dedup-collector.stderr"
DEDUP_STDOUT=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$DEDUP_A" "$DEDUP_B" 2>"$DEDUP_STDERR")
if printf '%s\n' "$DEDUP_STDOUT" | grep -Fq 'STATUS=FAILED'; then
    ok "dedup collector stdout unchanged contract"
else
    fail "dedup collector missing FAILED status"
fi
if ! grep -Fq 'fatal tool error' <<<"$DEDUP_STDOUT" \
    && ! grep -Fq 'agent stderr tail' <<<"$DEDUP_STDOUT"; then
    ok "dedup collector stdout free of stderr-tail body"
else
    fail "dedup collector stdout leaked stderr-tail content"
fi
dedup_tail_count=$(grep -c '^--- failed agent stderr tail ---$' "$DEDUP_STDERR" || true)
if [[ "$dedup_tail_count" -eq 1 ]]; then
    ok "dedup single full stderr tail"
else
    fail "dedup expected one stderr tail header (got $dedup_tail_count)"
fi
if grep -Fq 'identical failure to' "$DEDUP_STDERR"; then
    ok "dedup suppression line"
else
    fail "dedup missing suppression line"
fi

echo "# Case: distinct failure signatures emit two stderr tails"
DIST_A="$TMPROOT/dist-a.txt"
DIST_B="$TMPROOT/dist-b.txt"
: >"$DIST_A"
: >"$DIST_B"
printf '1\n' >"${DIST_A}.done"
printf '1\n' >"${DIST_B}.done"
printf 'non-transient failure\n' >"${DIST_A}.diag"
printf 'non-transient failure\n' >"${DIST_B}.diag"
write_meta "$DIST_A" "$SUCCESS_HELPER"
write_meta "$DIST_B" "$SUCCESS_HELPER"
printf 'root cause alpha\n' >"${DIST_A}.stderr-tail"
printf 'totally unrelated beta message\n' >"${DIST_B}.stderr-tail"
DIST_STDERR="$TMPROOT/dist-collector.stderr"
DIST_STDOUT=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$DIST_A" "$DIST_B" 2>"$DIST_STDERR")
if printf '%s\n' "$DIST_STDOUT" | grep -c '^STATUS=' | grep -Fxq '2'; then
    ok "distinct dedup stdout field count unchanged"
else
    ok "distinct dedup stdout emitted"
fi
if ! grep -Fq 'root cause alpha' <<<"$DIST_STDOUT" \
    && ! grep -Fq 'totally unrelated beta' <<<"$DIST_STDOUT"; then
    ok "distinct dedup stdout free of stderr-tail body"
else
    fail "distinct dedup stdout leaked stderr-tail content"
fi
dist_tail_count=$(grep -c '^--- failed agent stderr tail ---$' "$DIST_STDERR" || true)
if [[ "$dist_tail_count" -eq 2 ]]; then
    ok "distinct signatures two stderr tails"
else
    fail "distinct signatures expected two tails (got $dist_tail_count)"
fi

echo "# Case: retry failure stderr-tail preferred over orig"
RETRY_PREF="$TMPROOT/retry-pref.txt"
: >"$RETRY_PREF"
printf '1\n' >"${RETRY_PREF}.done"
printf 'transient network error\n' >"${RETRY_PREF}.diag"
write_meta "$RETRY_PREF" "$FAIL_HELPER"
printf 'stale first pass\n' >"${RETRY_PREF}.stderr-tail"
RETRY_OUT="${RETRY_PREF%.txt}-retry.txt"
printf 'retry still failed\n' >"$RETRY_OUT"
printf 'retry tail line\n' >"${RETRY_OUT}.stderr-tail"
RETRY_PREF_STDERR="$TMPROOT/retry-pref.stderr"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 "$RETRY_PREF" 2>"$RETRY_PREF_STDERR" >/dev/null
if grep -Fq 'retry tail line' "$RETRY_PREF_STDERR"; then
    ok "retry stderr-tail preferred in chat"
else
    fail "retry stderr-tail missing from collector stderr"
fi
if ! grep -Fq 'stale first pass' "$RETRY_PREF_STDERR"; then
    ok "orig stderr-tail not preferred over retry"
else
    fail "orig stderr-tail leaked instead of retry tail"
fi

echo "# Case: transient retry success removes stale orig stderr-tail"
STALE_RM="$TMPROOT/stale-rm.txt"
: >"$STALE_RM"
printf '1\n' >"${STALE_RM}.done"
printf 'Could not resolve host: example.invalid\n' >"${STALE_RM}.diag"
write_meta "$STALE_RM" "$SUCCESS_HELPER"
printf 'failure tail before retry\n' >"${STALE_RM}.stderr-tail"
RESULT_STALE=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05 \
    bash "$COLLECTOR" --timeout 5 "$STALE_RM" 2>/dev/null)
assert_line "stale-rm retry OK" "STATUS=OK" "$RESULT_STALE"
if [[ ! -e "${STALE_RM}.stderr-tail" ]]; then
    ok "stale-rm orig stderr-tail removed after retry OK"
else
    fail "stale-rm orig stderr-tail still present after retry OK"
fi

echo "# Case: on-demand launch-stderr render"
LAUNCH_SRC="$TMPROOT/launch-src.txt"
: >"$LAUNCH_SRC"
printf '1\n' >"${LAUNCH_SRC}.done"
printf 'non-transient failure\n' >"${LAUNCH_SRC}.diag"
write_meta "$LAUNCH_SRC" "$SUCCESS_HELPER"
printf 'launcher stderr line\n' >"${LAUNCH_SRC}.launch-stderr"
LAUNCH_STDERR="$TMPROOT/launch-collector.stderr"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$LAUNCH_SRC" 2>"$LAUNCH_STDERR" >/dev/null
if grep -Fq 'launcher stderr line' "$LAUNCH_STDERR"; then
    ok "launch-stderr rendered to collector FD 2"
else
    fail "launch-stderr not surfaced"
fi
if grep -Fq 'failed agent stderr tail' "$LAUNCH_STDERR"; then
    ok "launch-stderr uses shared stderr-tail fence"
else
    fail "launch-stderr missing shared stderr-tail fence"
fi
launch_tmp_left=$(find "${TMPDIR:-/tmp}" -maxdepth 1 -name 'larch-launch-stderr-tail.*' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$launch_tmp_left" == "0" ]]; then
    ok "launch-stderr temp cleaned up"
else
    fail "launch-stderr temp files leaked ($launch_tmp_left)"
fi

echo "# Case: phase-2 stderr-tail when phase-3 output has no sidecar"
PHASE3="$TMPROOT/waterfall-slot-phase3.txt"
PHASE2="${PHASE3%-phase3.txt}-phase2.txt"
: >"$PHASE3"
: >"$PHASE2"
printf '1\n' >"${PHASE3}.done"
printf 'non-transient failure\n' >"${PHASE3}.diag"
write_meta "$PHASE3" "$SUCCESS_HELPER"
printf 'phase2 root cause tail\n' >"${PHASE2}.stderr-tail"
PHASE_STDERR="$TMPROOT/phase-fallback.stderr"
PHASE_STDOUT=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$PHASE3" 2>"$PHASE_STDERR")
if printf '%s\n' "$PHASE_STDOUT" | grep -Fq 'STATUS=FAILED'; then
    ok "phase fallback stdout unchanged contract"
else
    fail "phase fallback missing FAILED status"
fi
if grep -Fq 'phase2 root cause tail' "$PHASE_STDERR"; then
    ok "phase fallback emits phase-2 stderr-tail"
else
    fail "phase fallback missing phase-2 stderr-tail on FD 2"
fi
if ! grep -Fq 'phase2 root cause tail' <<<"$PHASE_STDOUT"; then
    ok "phase fallback stdout free of stderr-tail body"
else
    fail "phase fallback stdout leaked stderr-tail content"
fi

echo "# Case: phase-3 launch-stderr beats phase-2 stderr-tail"
PHASE3_LS="$TMPROOT/waterfall-slot3-phase3.txt"
PHASE2_LS="${PHASE3_LS%-phase3.txt}-phase2.txt"
: >"$PHASE3_LS"
: >"$PHASE2_LS"
printf '1\n' >"${PHASE3_LS}.done"
printf 'non-transient failure\n' >"${PHASE3_LS}.diag"
write_meta "$PHASE3_LS" "$SUCCESS_HELPER"
printf 'stale phase2 stderr tail\n' >"${PHASE2_LS}.stderr-tail"
printf 'phase3 launcher validation error\n' >"${PHASE3_LS}.launch-stderr"
PHASE_LS_STDERR="$TMPROOT/phase-launch-stderr.stderr"
RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 "$PHASE3_LS" 2>"$PHASE_LS_STDERR" >/dev/null
if grep -Fq 'phase3 launcher validation error' "$PHASE_LS_STDERR"; then
    ok "phase-3 launch-stderr preferred over phase-2 stderr-tail"
else
    fail "phase-3 launch-stderr not surfaced"
fi
if grep -Fq 'stale phase2 stderr tail' "$PHASE_LS_STDERR"; then
    fail "phase-2 stderr-tail should not win over phase-3 launch-stderr"
else
    ok "phase-2 stderr-tail suppressed when phase-3 launch-stderr present"
fi

echo "# Case: --summary-only skips stderr-tail emission"
SUM_ONLY="$TMPROOT/summary-only.txt"
: >"$SUM_ONLY"
printf '1\n' >"${SUM_ONLY}.done"
printf 'non-transient failure\n' >"${SUM_ONLY}.diag"
write_meta "$SUM_ONLY" "$SUCCESS_HELPER"
printf 'should not chat\n' >"${SUM_ONLY}.stderr-tail"
SUM_STDERR="$TMPROOT/summary-only.stderr"
SUM_STDOUT=$(RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 bash "$COLLECTOR" --timeout 5 --summary-only "$SUM_ONLY" 2>"$SUM_STDERR")
if printf '%s\n' "$SUM_STDOUT" | grep -Fq 'STATUS=FAILED'; then
    ok "summary-only stdout still reports failure"
else
    fail "summary-only missing FAILED status"
fi
if [[ ! -s "$SUM_STDERR" ]]; then
    ok "summary-only suppresses stderr-tail chat"
else
    fail "summary-only should not emit stderr tails"
    cat "$SUM_STDERR" >&2
fi

if [[ "$FAIL" -ne 0 ]]; then
    printf '\nFAIL: test-collect-agent-results.sh (%d failure(s))\n' "$FAIL" >&2
    printf ' - %s\n' "${FAILED[@]}" >&2
    exit 1
fi

echo "PASS: test-collect-agent-results.sh - transient collector retry routing pinned"
