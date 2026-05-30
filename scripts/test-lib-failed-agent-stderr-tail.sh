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

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
    printf '  - %s\n' "${FAILED[@]}" >&2
    exit 1
fi
exit 0
