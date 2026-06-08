#!/usr/bin/env bash
# Offline harness for scripts/lib-failed-agent-stderr-tail.sh.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-lib-failed-agent-stderr-tail.XXXXXX")" || { echo "mktemp failed" >&2; exit 1; }
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
FAILED=()

ok() { PASS=$((PASS + 1)); echo "  ok: $1"; }
fail() { FAIL=$((FAIL + 1)); FAILED+=("$1"); echo "  FAIL: $1" >&2; }

# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh disable=SC1091
source "$REPO_ROOT/scripts/lib-failed-agent-stderr-tail.sh"

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then ok "$label"; else fail "$label: expected '$expected', got '$actual'"; fi
}

assert_file_absent() {
    local label="$1" path="$2"
    if [[ -e "$path" ]]; then fail "$label: expected absent $path"; else ok "$label"; fi
}

assert_file_present() {
    local label="$1" path="$2"
    if [[ -s "$path" ]]; then ok "$label"; else fail "$label: expected non-empty $path"; fi
}

# --- default 30 lines ---
src="$TMPROOT/lines.txt"
for i in $(seq 1 40); do printf 'line-%s\n' "$i"; done >"$src"
out=$(render_failed_agent_stderr_tail "$src")
line_count=$(printf '%s' "$out" | grep -c '^line-' || true)
assert_eq "default 30 lines" "30" "$line_count"

# --- env override ---
export LARCH_FAILED_AGENT_STDERR_TAIL_LINES=5
out=$(render_failed_agent_stderr_tail "$src")
line_count=$(printf '%s' "$out" | grep -c '^line-' || true)
assert_eq "env override lines" "5" "$line_count"
unset LARCH_FAILED_AGENT_STDERR_TAIL_LINES

# --- 0 disables ---
export LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0
out=$(render_failed_agent_stderr_tail "$src" || true)
assert_eq "zero disables render" "" "$out"
base="$TMPROOT/zero-out"
write_failed_agent_stderr_tail "$src" "$base" || true
assert_file_absent "zero disables sidecar" "${base}.stderr-tail"
unset LARCH_FAILED_AGENT_STDERR_TAIL_LINES

# --- non-numeric env fallback ---
export LARCH_FAILED_AGENT_STDERR_TAIL_LINES=abc
assert_eq "non-numeric lines fallback" "30" "$(failed_agent_stderr_tail_lines)"
out=$(render_failed_agent_stderr_tail "$src")
line_count=$(printf '%s' "$out" | grep -c '^line-' || true)
assert_eq "non-numeric render still tails 30" "30" "$line_count"
unset LARCH_FAILED_AGENT_STDERR_TAIL_LINES

export LARCH_FAILED_AGENT_STDERR_TAIL_LINES=30abc
assert_eq "suffix non-numeric lines fallback" "30" "$(failed_agent_stderr_tail_lines)"
out=$(render_failed_agent_stderr_tail "$src")
line_count=$(printf '%s' "$out" | grep -c '^line-' || true)
assert_eq "suffix non-numeric render still tails 30" "30" "$line_count"
unset LARCH_FAILED_AGENT_STDERR_TAIL_LINES

# --- 5 KB byte cap ---
huge="$TMPROOT/huge.txt"
printf 'x%.0s' {1..20000} >"$huge"
out=$(render_failed_agent_stderr_tail "$huge")
assert_eq "byte cap length" "5120" "${#out}"

# --- pipefail safety under set -e -o pipefail ---
pipefail_caller() {
    set -e -o pipefail
    local outf="$1"
    write_failed_agent_stderr_tail "$huge" "$outf"
}
pipefail_caller "$TMPROOT/pipefail-out"
assert_file_present "pipefail caller writes sidecar" "${TMPROOT}/pipefail-out.stderr-tail"

# --- redaction ---
secret_src="$TMPROOT/secret.txt"
printf 'before sk-ant-api03-abcdefghijklmnopqrstuvwxyz after\n' >"$secret_src"
out=$(render_failed_agent_stderr_tail "$secret_src")
if printf '%s' "$out" | grep -Fq '<REDACTED-TOKEN>'; then
    ok "redaction applied"
else
    fail "redaction applied"
fi

path_src="$TMPROOT/path.txt"
printf 'error under /Users/alice/myproject/scripts/foo.sh\n' >"$path_src"
out=$(render_failed_agent_stderr_tail "$path_src")
if printf '%s' "$out" | grep -Fq '<OPERATOR_REPO_PATH>'; then
    ok "tmpdir path redaction applied"
else
    fail "tmpdir path redaction applied"
fi
if printf '%s' "$out" | grep -Fq '/Users/alice'; then
    fail "raw home path leaked in tail"
else
    ok "raw home path not in tail"
fi

# --- atomic write + stale removal ---
out_base="$TMPROOT/atomic"
write_failed_agent_stderr_tail "$secret_src" "$out_base"
assert_file_present "atomic write" "${out_base}.stderr-tail"
export LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0
write_failed_agent_stderr_tail "$secret_src" "$out_base" || true
assert_file_absent "stale tail removed on disable" "${out_base}.stderr-tail"
unset LARCH_FAILED_AGENT_STDERR_TAIL_LINES

# --- signature stability / divergence ---
tail_a="$TMPROOT/sig-a.stderr-tail"
tail_b="$TMPROOT/sig-b.stderr-tail"
printf 'error in /tmp/foo123/bar.txt exit 2\n' >"$tail_a"
printf 'error in /tmp/foo456/bar.txt exit 2\n' >"$tail_b"
printf 'totally different message\n' >"$TMPROOT/sig-c.stderr-tail"
sig_ab_a=$(failed_agent_stderr_signature "$tail_a")
sig_ab_b=$(failed_agent_stderr_signature "$tail_b")
sig_c=$(failed_agent_stderr_signature "$TMPROOT/sig-c.stderr-tail")
if [[ "$sig_ab_a" == "$sig_ab_b" ]]; then ok "signature stable same root cause"; else fail "signature stable same root cause"; fi
if [[ "$sig_ab_a" != "$sig_c" ]]; then ok "signature distinct root causes"; else fail "signature distinct root causes"; fi

tail_http_a="$TMPROOT/sig-http-a.stderr-tail"
tail_http_b="$TMPROOT/sig-http-b.stderr-tail"
printf 'HTTP 401 unauthorized\n' >"$tail_http_a"
printf 'HTTP 403 unauthorized\n' >"$tail_http_b"
sig_http_a=$(failed_agent_stderr_signature "$tail_http_a")
sig_http_b=$(failed_agent_stderr_signature "$tail_http_b")
if [[ "$sig_http_a" == "$sig_http_b" ]]; then
    ok "signature collapses HTTP status digit runs"
else
    fail "signature collapses HTTP status digit runs"
fi

# --- pipefail option restored after render ---
nopipefail_after_render() {
    set -e
    set +o pipefail
    render_failed_agent_stderr_tail "$huge" >/dev/null
    case "$(set -o 2>/dev/null)" in
        *pipefail*off*) printf 'off' ;;
        *) printf 'on' ;;
    esac
}
pipefail_state=$(nopipefail_after_render)
assert_eq "pipefail restored off for caller" "off" "$pipefail_state"

# --- HOME metacharacters in session-path normalization ---
old_home="${HOME:-}"
export HOME="/tmp/user.name#branch"
home_tail="$TMPROOT/home-meta.stderr-tail"
printf 'failed in %s/claude-implement-ABC/plan.txt\n' "$HOME/.cache/larch/sessions" >"$home_tail"
home_sig=$(failed_agent_stderr_signature "$home_tail")
if [[ -n "$home_sig" ]]; then
    ok "signature with dotted HOME"
else
    fail "signature with dotted HOME"
fi
export HOME="/tmp/user#repo"
home_tail2="$TMPROOT/home-hash.stderr-tail"
printf 'failed in %s/design-XYZ/output.txt\n' "$HOME/.cache/larch/sessions" >"$home_tail2"
home_sig2=$(failed_agent_stderr_signature "$home_tail2")
if [[ -n "$home_sig2" ]]; then
    ok "signature with hash in HOME"
else
    fail "signature with hash in HOME"
fi
if [[ -n "$old_home" ]]; then export HOME="$old_home"; else unset HOME; fi

# --- empty / missing source ---
set +e
render_failed_agent_stderr_tail "$TMPROOT/missing.txt" >/dev/null
rc=$?
set -e
if [[ "$rc" -ne 0 ]]; then ok "missing source non-zero"; else fail "missing source non-zero"; fi

# --- select_failed_agent_stderr_source modes ---
merged_out="$TMPROOT/merged.txt"
printf 'agent stderr\n' >"$merged_out"
printf 'wrapper diag\n' >"${merged_out}.diag"
sidecar="${merged_out}.sidecar"
printf 'sidecar stderr\n' >"$sidecar"
sel=$(select_failed_agent_stderr_source "$merged_out" true false)
assert_eq "merged prefers output" "$merged_out" "$sel"
sel=$(select_failed_agent_stderr_source "$merged_out" false true)
assert_eq "stdout-only prefers diag" "${merged_out}.diag" "$sel"
sel=$(select_failed_agent_stderr_source "$merged_out" false false)
assert_eq "default prefers sidecar" "$sidecar" "$sel"

explicit_sink="$TMPROOT/explicit-sink.log"
printf 'explicit sink stderr\n' >"$explicit_sink"
sel=$(select_failed_agent_stderr_source "$merged_out" false false "$explicit_sink")
assert_eq "default prefers explicit sink over sidecar" "$explicit_sink" "$sel"

empty_sink="$TMPROOT/empty-sink.log"
: >"$empty_sink"
sel=$(select_failed_agent_stderr_source "$merged_out" false false "$empty_sink")
assert_eq "default empty explicit sink falls back to sidecar" "$sidecar" "$sel"

sel=$(select_failed_agent_stderr_source "$merged_out" true false "$explicit_sink")
assert_eq "capture-stdout ignores explicit sink" "$merged_out" "$sel"

sel=$(select_failed_agent_stderr_source "$merged_out" false true "$explicit_sink")
assert_eq "capture-stdout-only ignores explicit sink" "${merged_out}.diag" "$sel"

# ===========================================================================
# #3713 vendor-agent failure-diagnostics carrier
# ===========================================================================
assert_contains() {
    local label="$1" path="$2" needle="$3" rc=0
    grep -Fq "$needle" "$path" 2>/dev/null || rc=$?
    if [ "$rc" -eq 0 ]; then ok "$label"; else fail "$label: '$needle' absent in $path"; fi
}
assert_absent() {
    local label="$1" path="$2" needle="$3" rc=0
    grep -Fq "$needle" "$path" 2>/dev/null || rc=$?
    if [ "$rc" -eq 0 ]; then fail "$label: '$needle' present in $path"; else ok "$label"; fi
}

VF="$TMPROOT/vf"; mkdir -p "$VF"

# --- write_failure_diag composes labeled sections; filters success bulk ---
o="$VF/codex-output.txt"
printf 'health-probe fast-fail: codex unhealthy\nexit code 7\n' > "$o.diag"
printf 'plain codex stderr\nError: quota exceeded usage limit\n' > "$o.sidecar"
printf 'success transcript that must not leak\nrandom prose\n' > "$o"
if write_failure_diag "$o"; then ok "write_failure_diag rc=0"; else fail "write_failure_diag rc!=0"; fi
assert_file_present "carrier written" "$o.failure-diag"
assert_contains "carrier has sidecar section" "$o.failure-diag" "===== sidecar ====="
assert_contains "carrier has diag section" "$o.failure-diag" "===== diag ====="
assert_contains "carrier keeps quota line" "$o.failure-diag" "quota exceeded usage limit"

# --- events.jsonl folded to failure-shaped lines only ---
o2="$VF/codex2.txt"
printf '{"type":"item.completed","ok":true}\n{"type":"turn.failed","error":"rate limit reached"}\n{"type":"noise","data":"hello world plain"}\n' > "$o2.events.jsonl"
write_failure_diag "$o2" >/dev/null 2>&1 || true
assert_file_present "events carrier written" "$o2.failure-diag"
assert_contains "events keeps turn.failed" "$o2.failure-diag" "turn.failed"
assert_absent "events drops non-error noise" "$o2.failure-diag" "hello world plain"

# --- no sources → return 1, no carrier ---
o3="$VF/empty.txt"
if write_failure_diag "$o3"; then fail "empty write_failure_diag should rc!=0"; else ok "empty write_failure_diag rc!=0"; fi
assert_file_absent "no carrier when no sources" "$o3.failure-diag"

# --- append-with-header on existing carrier ---
printf 'second attempt diag\n' > "$o.diag"
write_failure_diag "$o" >/dev/null 2>&1 || true
assert_contains "carrier append-with-header" "$o.failure-diag" "additional failure diagnostics"

# --- resolve prefers carrier, falls back, returns 1 when empty ---
assert_eq "resolve prefers carrier" "$o.failure-diag" "$(resolve_failure_diagnostic_source "$o")"
o4="$VF/r4.txt"; printf 'sidecar only\n' > "$o4.sidecar"
assert_eq "resolve falls back to sidecar" "$o4.sidecar" "$(resolve_failure_diagnostic_source "$o4")"
o5="$VF/r5.txt"
if resolve_failure_diagnostic_source "$o5" >/dev/null; then fail "resolve empty should rc!=0"; else ok "resolve empty rc!=0"; fi

# --- external_stream_reset archives + truncates; /dev/null no-op ---
o6="$VF/r6.txt"; printf 'attempt-1 sidecar\n' > "$o6.sidecar"
external_stream_reset "$o6.sidecar" "$o6.sidecar.history" "attempt 1"
assert_file_present "reset archived history" "$o6.sidecar.history"
if [[ ! -s "$o6.sidecar" ]]; then ok "reset truncated target to empty"; else fail "reset did not truncate target"; fi
if external_stream_reset "/dev/null" "$o6.sidecar.history" "noop"; then ok "reset /dev/null no-op rc=0"; else fail "reset /dev/null returned nonzero"; fi

# --- append_vendor_failure_diagnostics: per-slot redacted part + empty backstop ---
o7="$VF/r7.txt"; printf 'codex crashed Error fatal\n' > "$o7.failure-diag"
append_vendor_failure_diagnostics --source "$o7.failure-diag" --site "lib-test codex" --tmpdir "$VF" --exit-code 7
parts=$(find "$VF/vendor-failure-diagnostics.parts" -name 'part.*' 2>/dev/null | wc -l | tr -d ' ')
assert_eq "one vendor part written" "1" "$parts"
append_vendor_failure_diagnostics --source "/nonexistent" --site "empty" --tmpdir "$VF" --exit-code 124
parts2=$(find "$VF/vendor-failure-diagnostics.parts" -name 'part.*' 2>/dev/null | wc -l | tr -d ' ')
assert_eq "backstop still writes a part" "2" "$parts2"
cat "$VF"/vendor-failure-diagnostics.parts/part.* > "$VF/merged-parts.txt" 2>/dev/null || true
assert_contains "backstop synthesized line" "$VF/merged-parts.txt" "no diagnostics captured (exit 124)"

# --- resolve_execution_issues_log precedence (inline so PASS/FAIL counters apply) ---
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH DESIGN_TMPDIR REVIEW_TMPDIR
export IMPLEMENT_TMPDIR="$VF"
assert_eq "log resolver IMPLEMENT_TMPDIR" "$VF/execution-issues.md" "$(resolve_execution_issues_log)"
export LARCH_EXECUTION_ISSUES_LOG="$VF/custom.md"
assert_eq "log resolver override wins" "$VF/custom.md" "$(resolve_execution_issues_log)"
unset LARCH_EXECUTION_ISSUES_LOG IMPLEMENT_TMPDIR

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
    printf '  - %s\n' "${FAILED[@]}" >&2
    exit 1
fi
exit 0
