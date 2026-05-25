#!/usr/bin/env bash
# Unified offline regression harness for scripts/launch-review.sh.
set -euo pipefail
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR || true

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# launch-review.sh resolves PLUGIN_ROOT from CLAUDE_PLUGIN_ROOT when set; a
# developer/CI environment may point that at a plugin cache tree that lags this
# checkout. Pin the harness to the repo under test so append_launch_failure
# exercises the workspace copy of append-tool-failure.sh (including new flags).
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
TMPROOT="$(mktemp -d /tmp/larch-test-launch-review-XXXXXX)"
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
# shellcheck disable=SC2030
export LARCH_EXECUTION_ISSUES_LOG="$TMPROOT/execution-issues.md"
trap 'rm -rf "$TMPROOT"' EXIT

OVERALL_FAIL=0

assert_tool_validation() {
    local stderr rc
    stderr="$TMPROOT/missing-tool.stderr"
    set +e
    "$REPO_ROOT/scripts/launch-review.sh" --output "$TMPROOT/missing-tool.txt" --timeout 1 --prompt x >/dev/null 2>"$stderr"
    rc=$?
    set -e
    if [[ "$rc" -ne 2 ]] || ! grep -Fq -- "--tool is required (codex|cursor)" "$stderr"; then
        echo "FAIL: missing --tool validation" >&2
        OVERALL_FAIL=1
    fi

    stderr="$TMPROOT/invalid-tool.stderr"
    set +e
    "$REPO_ROOT/scripts/launch-review.sh" --tool nope --output "$TMPROOT/invalid-tool.txt" --timeout 1 --prompt x >/dev/null 2>"$stderr"
    rc=$?
    set -e
    if [[ "$rc" -ne 2 ]] || ! grep -Fq -- "unknown tool: 'nope'; expected codex or cursor" "$stderr"; then
        echo "FAIL: invalid --tool validation" >&2
        OVERALL_FAIL=1
    fi

}

assert_tool_validation

echo 'Running launch-review codex suite'
(
# Offline regression harness for scripts/launch-review.sh --tool codex.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
LARCH_TEST_REPO_ROOT="$REPO_ROOT"
export LARCH_TEST_REPO_ROOT
LAUNCHER="$TMPROOT/bin/launch-review-codex"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" <<'LARCH_REVIEW_CODEX_SHIM'
#!/usr/bin/env bash
exec "$LARCH_TEST_REPO_ROOT/scripts/launch-review.sh" --tool codex "$@"
LARCH_REVIEW_CODEX_SHIM
chmod +x "$LAUNCHER"
# shellcheck disable=SC2030
TMPDIR="$(mktemp -d /tmp/larch-test-launch-review-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
# shellcheck disable=SC2030
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR/execution-issues.md"
export LARCH_TIMING_LEDGER="$TMPDIR/timing-ledger.tsv"

# shellcheck disable=SC2030
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

PASS=0
FAIL=0
FAILURES=()
pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

assert_eq() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then pass; else fail "$label: expected '$expected', got '$actual'"; fi
}

assert_grep() {
    local label="$1"
    local pattern="$2"
    local file="$3"
    if grep -Fq -- "$pattern" "$file"; then pass; else fail "$label: missing '$pattern' in $file"; fi
}

assert_regex() {
    local label="$1"
    local pattern="$2"
    local file="$3"
    if grep -Eq -- "$pattern" "$file"; then pass; else fail "$label: expected $file to match regex $pattern"; fi
}

set +e
"$LAUNCHER" >/dev/null 2>"$TMPDIR/missing.stderr"
RC=$?
set -e
assert_eq "missing flags exit" "2" "$RC"
assert_grep "missing output message" "--output is required" "$TMPDIR/missing.stderr"

for bad_timeout in nope 0 00 000; do
    OUT="$TMPDIR/bad-${bad_timeout}.txt"
    set +e
    "$LAUNCHER" --output "$OUT" --timeout "$bad_timeout" --prompt "x" >/dev/null 2>"$TMPDIR/bad-${bad_timeout}.stderr"
    RC=$?
    set -e
    assert_eq "bad timeout $bad_timeout exit" "2" "$RC"
    assert_grep "bad timeout $bad_timeout message" "must be a positive integer" "$TMPDIR/bad-${bad_timeout}.stderr"
done

# Issue #1480 Bug #2: defensive `--timing-task-kind` validation. Empty or
# flag-like values must be rejected with exit 2 and a clear message, NOT
# silently consumed (which would either pass `--prompt` as the timing-task-kind
# value or hit the unknown-flag branch later, masking the original arg-shape
# defect). The dialectic-execution.md template fix (Bug #1) prevents the LLM
# from constructing this argv shape in the first place; the launcher
# validation is defense in depth.
set +e
"$LAUNCHER" --output "$TMPDIR/bad-empty-tk.txt" --timeout 5 --timing-task-kind "" --prompt "x" >/dev/null 2>"$TMPDIR/bad-empty-tk.stderr"
RC=$?
set -e
assert_eq "empty timing-task-kind exit" "2" "$RC"
assert_grep "empty timing-task-kind message" "non-empty, non-flag-like value" "$TMPDIR/bad-empty-tk.stderr"

set +e
"$LAUNCHER" --output "$TMPDIR/bad-flaglike-tk.txt" --timeout 5 --timing-task-kind --prompt "x" >/dev/null 2>"$TMPDIR/bad-flaglike-tk.stderr"
RC=$?
set -e
assert_eq "flag-like timing-task-kind exit" "2" "$RC"
assert_grep "flag-like timing-task-kind message" "non-empty, non-flag-like value" "$TMPDIR/bad-flaglike-tk.stderr"

STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"
CODEX_DEFAULT_STUB="$STUB_BIN/codex-default"
cat > "$CODEX_DEFAULT_STUB" <<'STUB_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${CODEX_STUB_ARGV_LOG:?}"
: "${CODEX_STUB_COUNT_FILE:?}"
if [[ -n "${CODEX_STUB_TOKEN_SESSION_FILE:-}" ]]; then
    printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$CODEX_STUB_TOKEN_SESSION_FILE"
fi
if [[ -n "${CODEX_STUB_HOME_FILE:-}" ]]; then
    printf '%s\n' "${CODEX_HOME:-}" > "$CODEX_STUB_HOME_FILE"
fi
if [[ -n "${CODEX_STUB_CONFIG_FILE:-}" && -n "${CODEX_HOME:-}" && -f "$CODEX_HOME/config.toml" ]]; then
    cp "$CODEX_HOME/config.toml" "$CODEX_STUB_CONFIG_FILE"
fi
if [[ -n "${CODEX_STUB_LOCK_PATH:-}" && -n "${CODEX_STUB_LOCK_SEEN_FILE:-}" && -d "$CODEX_STUB_LOCK_PATH" ]]; then
    printf 'present\n' > "$CODEX_STUB_LOCK_SEEN_FILE"
fi
count=0
if [[ -f "$CODEX_STUB_COUNT_FILE" ]]; then
    count=$(cat "$CODEX_STUB_COUNT_FILE")
fi
count=$((count + 1))
printf '%s\n' "$count" > "$CODEX_STUB_COUNT_FILE"
output=""
last=""
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"
    if [[ "$last" == "--output-last-message" ]]; then
        output="$arg"
    fi
    last="$arg"
done
[[ -n "$output" ]] || exit 9
printf 'codex review ok\n' > "$output"
printf 'tokens used\n1\n'
STUB_CODEX
chmod +x "$CODEX_DEFAULT_STUB"
ln -sf "$CODEX_DEFAULT_STUB" "$STUB_BIN/codex"

OUTDIR_REAL="$TMPDIR/out-real"
mkdir -p "$OUTDIR_REAL"
OUTDIR_LINK="$TMPDIR/out-link"
ln -s "$OUTDIR_REAL" "$OUTDIR_LINK"
OUTPUT="$OUTDIR_LINK/../out-link/review.txt"
ARGV="$TMPDIR/argv.txt"
COUNT="$TMPDIR/count.txt"
TOKEN_SESSION_FILE="$TMPDIR/token-session.txt"
CODEX_HOME_FILE="$TMPDIR/codex-home.txt"
CODEX_CONFIG_FILE="$TMPDIR/codex-config.toml"
IMPLEMENT_TMPDIR_FIXTURE="$TMPDIR/implement-tmpdir"
mkdir -p "$IMPLEMENT_TMPDIR_FIXTURE"
printf 'mock-codex-review-session\n' > "$IMPLEMENT_TMPDIR_FIXTURE/session-id"
printf 'SOURCE_FILE=/tmp/mock.jsonl\n' > "$IMPLEMENT_TMPDIR_FIXTURE/claude-source.env"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV" \
    CODEX_STUB_COUNT_FILE="$COUNT" \
    CODEX_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_FILE" \
    CODEX_STUB_HOME_FILE="$CODEX_HOME_FILE" \
    CODEX_STUB_CONFIG_FILE="$CODEX_CONFIG_FILE" \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_FIXTURE" \
    LARCH_TOKEN_SESSION_ID="stale-codex-review-session" \
    LARCH_CODEX_MODEL="stub-model" \
    "$LAUNCHER" --output "$OUTPUT" --timeout 5 --prompt "review prompt" >/dev/null

assert_eq "stub invoked once" "1" "$(cat "$COUNT")"
assert_eq "token session id rehydrated" "mock-codex-review-session" "$(cat "$TOKEN_SESSION_FILE")"

# DESIGN_TMPDIR/session-id fallback when IMPLEMENT_TMPDIR is unset (parity with Cursor branch).
DESIGN_TOKEN_ONLY="$TMPDIR/design-token-only"
mkdir -p "$DESIGN_TOKEN_ONLY"
printf 'design-led-session\n' > "$DESIGN_TOKEN_ONLY/session-id"
TOKEN_SESSION_DESIGN="$TMPDIR/token-session-design.txt"
PATH="$STUB_BIN:$PATH" \
    env -u IMPLEMENT_TMPDIR \
    CODEX_STUB_ARGV_LOG="$TMPDIR/argv-design-token.txt" \
    CODEX_STUB_COUNT_FILE="$TMPDIR/count-design-token.txt" \
    CODEX_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_DESIGN" \
    DESIGN_TMPDIR="$DESIGN_TOKEN_ONLY" \
    LARCH_TOKEN_SESSION_ID="stale-should-be-replaced" \
    LARCH_CODEX_MODEL="stub-model" \
    "$LAUNCHER" --output "$TMPDIR/out-design-token.txt" --timeout 5 --prompt "design-token" >/dev/null
assert_eq "design tmpdir session-id export" "design-led-session" "$(cat "$TOKEN_SESSION_DESIGN")"

TOKEN_SESSION_NEITHER="$TMPDIR/token-session-neither.txt"
PATH="$STUB_BIN:$PATH" \
    env -u IMPLEMENT_TMPDIR -u DESIGN_TMPDIR \
    CODEX_STUB_ARGV_LOG="$TMPDIR/argv-neither-tmpdir.txt" \
    CODEX_STUB_COUNT_FILE="$TMPDIR/count-neither-tmpdir.txt" \
    CODEX_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_NEITHER" \
    LARCH_TOKEN_SESSION_ID="explicit-session" \
    LARCH_CODEX_MODEL="stub-model" \
    "$LAUNCHER" --output "$TMPDIR/out-neither-tmpdir.txt" --timeout 5 --prompt "neither" >/dev/null
assert_eq "no implement/design tmpdir preserves explicit LARCH_TOKEN_SESSION_ID" "explicit-session" "$(cat "$TOKEN_SESSION_NEITHER")"

if [[ -s "$CODEX_HOME_FILE" ]] && [[ "$(cat "$CODEX_HOME_FILE")" == /tmp/larch-codex-review-home-* ]]; then
    pass
else
    fail "review launcher did not set CODEX_HOME to a per-invocation /tmp directory"
fi
CODEX_HOME_VALUE=$(cat "$CODEX_HOME_FILE" 2>/dev/null || true)
case "$CODEX_HOME_VALUE" in
    "$OUTDIR_REAL"|"$OUTDIR_REAL"/*)
        fail "review CODEX_HOME must be outside CANON_OUTPUT_DIR; got $CODEX_HOME_VALUE"
        ;;
    *)
        pass
        ;;
esac
if [[ -s "$CODEX_CONFIG_FILE" ]] \
   && [[ "$(sed -n '1p' "$CODEX_CONFIG_FILE")" == "instructions = '''" ]] \
   && grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$CODEX_CONFIG_FILE"; then
    pass
else
    fail "review CODEX_HOME config.toml should carry top-level hardening instructions"
fi
assert_grep "codex compact prohibition" "Do not create, edit, delete, or overwrite files, and do not run mutating shell or git commands." "$CODEX_CONFIG_FILE"
assert_eq "argv 1" "exec" "$(sed -n '1p' "$ARGV")"
# Issue #1529: read-only review sandbox replaces --full-auto.
assert_eq "argv 2 sandbox flag" "--sandbox" "$(sed -n '2p' "$ARGV")"
assert_eq "argv 3 sandbox value" "read-only" "$(sed -n '3p' "$ARGV")"
assert_eq "argv 4" "-C" "$(sed -n '4p' "$ARGV")"
assert_eq "argv 5" "$REPO_ROOT" "$(sed -n '5p' "$ARGV")"
assert_eq "argv 6 add-dir flag" "--add-dir" "$(sed -n '6p' "$ARGV")"
assert_eq "argv 7 canonical output dir" "$(cd "$OUTDIR_REAL" && pwd -P)" "$(sed -n '7p' "$ARGV")"
# argv MUST NOT carry --full-auto anymore.
if grep -Fxq -- '--full-auto' "$ARGV"; then
    fail "argv must NOT contain --full-auto under the issue #1529 read-only contract"
else
    pass
fi
assert_grep "outer launcher metadata" "OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-review.sh" "${OUTPUT}.meta"
assert_grep "outer prompt metadata" "OUTER_LAUNCHER_PROMPT_FILE=${OUTPUT}.prompt" "${OUTPUT}.meta"
assert_grep "dirty-tree sidecar status" "STATUS=" "${OUTPUT}.dirty-tree"
assert_grep "dirty-tree sidecar mode" "MODE=baseline" "${OUTPUT}.dirty-tree"
# Issue #1529 / #1708: the hardening preamble is applied through
# CODEX_HOME/config.toml instructions, not the outgoing PROMPT or retry
# sidecar.
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV"; then
    fail "issue #1708 codex argv prompt must NOT carry the HARD CONSTRAINTS preamble"
else
    pass
fi
if grep -Fq -- 'HARD CONSTRAINTS' "${OUTPUT}.prompt"; then
    fail "issue #1529 OUTPUT.prompt sidecar must NOT contain the preamble (retry-replay safety)"
else
    pass
fi
# Sidecar preserves the user-original prompt verbatim ("review prompt").
EXPECTED_SIDECAR="$TMPDIR/expected-sidecar.txt"
printf 'review prompt' > "$EXPECTED_SIDECAR"
if cmp -s "$EXPECTED_SIDECAR" "${OUTPUT}.prompt"; then
    pass
else
    fail "issue #1529 OUTPUT.prompt sidecar must equal the user-original prompt 'review prompt'"
fi
if awk 'prev == "--" && $0 == "review prompt" { found=1 } { prev=$0 } END { exit(found ? 0 : 1) }' "$ARGV"; then
    pass
else
    fail "codex review argv should place -- immediately before the prompt"
fi

if [[ "$(grep -Fxc -- '-m' "$ARGV")" == "1" ]] && grep -Fxq -- 'stub-model' "$ARGV"; then
    pass
else
    fail "model args should include one -m and literal stub-model"
fi
if grep -Fxq -- "projects.\"$REPO_ROOT\".trust_level=\"trusted\"" "$ARGV"; then
    pass
else
    fail "codex review argv should include trusted-project config override"
fi

CODEX_LOCK_USER="larch-test-codex-$$"
CODEX_LOCK_PATH="/tmp/larch-codex-serial-${CODEX_LOCK_USER}.lock"
CODEX_LOCK_SEEN="$TMPDIR/codex-lock-seen.txt"
rm -rf "$CODEX_LOCK_PATH"
PATH="$STUB_BIN:$PATH" \
    USER="$CODEX_LOCK_USER" \
    CODEX_STUB_ARGV_LOG="$TMPDIR/argv-lock.txt" \
    CODEX_STUB_COUNT_FILE="$TMPDIR/count-lock.txt" \
    CODEX_STUB_LOCK_PATH="$CODEX_LOCK_PATH" \
    CODEX_STUB_LOCK_SEEN_FILE="$CODEX_LOCK_SEEN" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    LARCH_CODEX_MODEL="stub-model" \
    "$LAUNCHER" --output "$TMPDIR/codex-lock.txt" --timeout 5 --prompt "review prompt" >/dev/null
if [[ "$(cat "$CODEX_LOCK_SEEN" 2>/dev/null)" == "present" ]]; then
    pass
else
    fail "codex review should hold /tmp serial lock while spawning codex"
fi
rm -rf "$CODEX_LOCK_PATH"

TIMING_ENV_LEDGER="$TMPDIR/lcr-timing-env.tsv"
TIMING_ENV_ARGV="$TMPDIR/argv-timing-env.txt"
TIMING_ENV_COUNT="$TMPDIR/count-timing-env.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$TIMING_ENV_ARGV" \
    CODEX_STUB_COUNT_FILE="$TIMING_ENV_COUNT" \
    LARCH_CODEX_MODEL="stub-model" \
    LARCH_TIMING_LEDGER="$TIMING_ENV_LEDGER" \
    LARCH_TIMING_TASK_KIND="--prompt" \
    "$LAUNCHER" --output "$TMPDIR/timing-env.txt" --timeout 5 --prompt "review prompt" >/dev/null
if [[ -f "$TIMING_ENV_LEDGER" ]] && grep -E "^v1"$'\t'"vendor"$'\t'"[0-9]+"$'\t'"[^"$'\t'"]+"$'\t'"-"$'\t'"codex"$'\t'"codex-review"$'\t' "$TIMING_ENV_LEDGER" >/dev/null; then
    pass
else
    fail "env LARCH_TIMING_TASK_KIND=--prompt should fall back to codex-review; ledger=$(cat "$TIMING_ENV_LEDGER" 2>/dev/null)"
fi
if [[ -f "$TIMING_ENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" { print $7 }' "$TIMING_ENV_LEDGER" | grep -Fxq -- '--prompt'; then
    fail "env LARCH_TIMING_TASK_KIND=--prompt leaked into timing ledger"
else
    pass
fi

ARGV_INJECT="$TMPDIR/argv-inject.txt"
COUNT_INJECT="$TMPDIR/count-inject.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV_INJECT" \
    CODEX_STUB_COUNT_FILE="$COUNT_INJECT" \
    LARCH_CODEX_MODEL="evil --model gpt-injection" \
    "$LAUNCHER" --output "$TMPDIR/inject.txt" --timeout 5 --prompt "review prompt" >/dev/null
if [[ "$(grep -Fxc -- '-m' "$ARGV_INJECT")" == "1" ]] && grep -Fxq -- 'evil --model gpt-injection' "$ARGV_INJECT"; then
    pass
else
    fail "model with spaces should remain one argv token after -m"
fi

set +e
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$TMPDIR/argv-bad.txt" \
    CODEX_STUB_COUNT_FILE="$TMPDIR/count-bad.txt" \
    LARCH_CODEX_MODEL=$'evil\nextra' \
    "$LAUNCHER" --output "$TMPDIR/bad-model.txt" --timeout 5 --prompt "review prompt" >/dev/null 2>"$TMPDIR/bad-model.stderr"
RC=$?
set -e
if [[ "$RC" -ne 0 ]]; then pass; else fail "newline model wrapper must exit non-zero on model-args preflight failure"; fi
if [[ ! -e "$TMPDIR/count-bad.txt" ]]; then pass; else fail "newline model should fail before invoking codex"; fi
if [[ -s "$TMPDIR/bad-model.txt.done" ]]; then
    pass
else
    fail "newline model preflight failure must write non-empty .done sentinel"
fi
if [[ -s "$TMPDIR/bad-model.txt.diag" ]] && grep -Fq 'STATUS=FAILED' "$TMPDIR/bad-model.txt.diag"; then
    pass
else
    fail "newline model preflight failure must write .diag with STATUS=FAILED"
fi
assert_grep "newline model diag diagnostic" "agent-model-args.sh failed" "$TMPDIR/bad-model.txt.diag"
if [[ -s "$TMPDIR/bad-model.txt.meta" ]] && grep -Fq 'CMD_JSON=[]' "$TMPDIR/bad-model.txt.meta"; then
    pass
else
    fail "newline model preflight failure must write stub .meta with CMD_JSON=[]"
fi
if [[ -s "$TMPDIR/bad-model.txt.dirty-tree" ]] && grep -Fq 'STATUS=unknown' "$TMPDIR/bad-model.txt.dirty-tree"; then
    pass
else
    fail "newline model preflight failure must write unknown dirty-tree sidecar"
fi

# Issue #1529 / #1708: empty-output retry idempotency. The first run wrote
# "review prompt" to ${OUTPUT}.prompt (user-original, no preamble).
# Replaying via --prompt-file pointing at that sidecar must keep the argv
# prompt dynamic-only; the static preamble is delivered via fresh CODEX_HOME
# instructions on each launch.
RETRY_OUTPUT="$TMPDIR/retry-output.txt"
RETRY_ARGV="$TMPDIR/retry-argv.txt"
RETRY_COUNT="$TMPDIR/retry-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$RETRY_ARGV" \
    CODEX_STUB_COUNT_FILE="$RETRY_COUNT" \
    "$LAUNCHER" --output "$RETRY_OUTPUT" --timeout 5 --prompt-file "${OUTPUT}.prompt" >/dev/null
PREAMBLE_COUNT_RETRY=$(grep -Fc -- 'HARD CONSTRAINTS — your role is read-only review' "$RETRY_ARGV" || true)
if [[ "$PREAMBLE_COUNT_RETRY" == "0" ]]; then
    pass
else
    fail "retry replay via --prompt-file must not include preamble in argv; got $PREAMBLE_COUNT_RETRY"
fi

PROMPT_FILE="$TMPDIR/prompt-file.txt"
ARGV_PROMPT_FILE="$TMPDIR/argv-prompt-file.txt"
COUNT_PROMPT_FILE="$TMPDIR/count-prompt-file.txt"
printf 'from prompt file\n\n' > "$PROMPT_FILE"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV_PROMPT_FILE" \
    CODEX_STUB_COUNT_FILE="$COUNT_PROMPT_FILE" \
    "$LAUNCHER" --output "$TMPDIR/prompt-file-output.txt" --timeout 5 --prompt-file "$PROMPT_FILE" >/dev/null
PROMPT_SIDECAR="${TMPDIR}/prompt-file-output.txt.prompt"
if [[ "$(cat "$COUNT_PROMPT_FILE")" == "1" ]]; then
    pass
else
    fail "--prompt-file should still launch through Codex exactly once"
fi
# Issue #1529 / #1708: --prompt-file's bytes are preserved verbatim in the
# sidecar (no preamble there) and the preamble is applied through
# CODEX_HOME instructions.
EXPECTED_PROMPT_ARG="$TMPDIR/expected-prompt-arg.txt"
printf 'from prompt file\n\n' > "$EXPECTED_PROMPT_ARG"
if cmp -s "$EXPECTED_PROMPT_ARG" "$PROMPT_SIDECAR"; then
    pass
else
    fail "--prompt-file should preserve original bytes verbatim in OUTPUT.prompt sidecar"
fi
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_PROMPT_FILE"; then
    fail "--prompt-file run must not include the HARD CONSTRAINTS preamble in codex argv"
else
    pass
fi
if grep -Fq -- 'HARD CONSTRAINTS' "$PROMPT_SIDECAR"; then
    fail "--prompt-file run must NOT include the preamble in the sidecar (retry-replay safety)"
else
    pass
fi

AGENT_OUTPUT="$TMPDIR/agent-file-output.txt"
AGENT_ARGV="$TMPDIR/agent-file-argv.txt"
AGENT_COUNT="$TMPDIR/agent-file-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$AGENT_ARGV" \
    CODEX_STUB_COUNT_FILE="$AGENT_COUNT" \
    "$LAUNCHER" --output "$AGENT_OUTPUT" --timeout 5 \
        --agent-file "$REPO_ROOT/agents/reviewer-structure.md" --mode diff >/dev/null
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$AGENT_ARGV"; then
    fail "--agent-file run must not include the HARD CONSTRAINTS preamble in codex argv"
else
    pass
fi
# agent-file sidecar is now a hash+kind sentinel (I/O optimization #1718),
# not the full rendered body.
if grep -Fq -- 'LARCH_PROMPT_SENTINEL=1' "${AGENT_OUTPUT}.prompt"; then
    pass
else
    fail "--agent-file OUTPUT.prompt sidecar must be a hash+kind sentinel (LARCH_PROMPT_SENTINEL=1)"
fi
if grep -Fq -- 'KIND=specialist' "${AGENT_OUTPUT}.prompt"; then
    pass
else
    fail "--agent-file OUTPUT.prompt sidecar must contain KIND=specialist"
fi
if grep -Fq -- 'HASH=' "${AGENT_OUTPUT}.prompt"; then
    pass
else
    fail "--agent-file OUTPUT.prompt sidecar must contain HASH= field"
fi
if grep -Fq -- 'Structure, KISS, and Maintainability' "${AGENT_OUTPUT}.prompt"; then
    fail "--agent-file OUTPUT.prompt sidecar must NOT contain the specialist body (sentinel optimization)"
else
    pass
fi
if grep -Fq -- 'HARD CONSTRAINTS' "${AGENT_OUTPUT}.prompt"; then
    fail "--agent-file OUTPUT.prompt sidecar must NOT include the preamble"
else
    pass
fi
AGENT_RETRY_ARGV="$TMPDIR/agent-file-retry-argv.txt"
AGENT_RETRY_COUNT="$TMPDIR/agent-file-retry-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$AGENT_RETRY_ARGV" \
    CODEX_STUB_COUNT_FILE="$AGENT_RETRY_COUNT" \
    "$LAUNCHER" --output "$TMPDIR/agent-file-retry-output.txt" --timeout 5 \
        --prompt-file "${AGENT_OUTPUT}.prompt" >/dev/null
AGENT_PREAMBLE_COUNT_RETRY=$(grep -Fc -- 'HARD CONSTRAINTS — your role is read-only review' "$AGENT_RETRY_ARGV" || true)
if [[ "$AGENT_PREAMBLE_COUNT_RETRY" == "0" ]]; then
    pass
else
    fail "--agent-file replay via --prompt-file must not include preamble in argv; got $AGENT_PREAMBLE_COUNT_RETRY"
fi

# --commit-count is stored in the specialist sentinel and restored on retry.
AGENT_CC_OUTPUT="$TMPDIR/agent-commit-count-output.txt"
AGENT_CC_ARGV="$TMPDIR/agent-commit-count-argv.txt"
AGENT_CC_COUNT="$TMPDIR/agent-commit-count-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$AGENT_CC_ARGV" \
    CODEX_STUB_COUNT_FILE="$AGENT_CC_COUNT" \
    "$LAUNCHER" --output "$AGENT_CC_OUTPUT" --timeout 5 \
        --agent-file "$REPO_ROOT/agents/reviewer-structure.md" --mode diff --commit-count 3 >/dev/null
if grep -Fq -- 'COMMIT_COUNT=3' "${AGENT_CC_OUTPUT}.prompt"; then
    pass
else
    fail "--commit-count should be stored in specialist sentinel"
fi
# Retry replay with commit-count sentinel: rendered prompt must omit git-log.
AGENT_CC_RETRY_ARGV="$TMPDIR/agent-commit-count-retry-argv.txt"
AGENT_CC_RETRY_COUNT="$TMPDIR/agent-commit-count-retry-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$AGENT_CC_RETRY_ARGV" \
    CODEX_STUB_COUNT_FILE="$AGENT_CC_RETRY_COUNT" \
    "$LAUNCHER" --output "$TMPDIR/agent-commit-count-retry-output.txt" --timeout 5 \
        --prompt-file "${AGENT_CC_OUTPUT}.prompt" >/dev/null 2>/dev/null
# shellcheck disable=SC2016
if grep -Fq -- 'git log $(git merge-base HEAD main)..HEAD --oneline' "$AGENT_CC_RETRY_ARGV" 2>/dev/null; then
    fail "--commit-count 3 retry: git log instruction should be omitted in rendered prompt"
else
    pass
fi

if command -v jq >/dev/null 2>&1; then
    LCR_BIN="$TMPDIR/lcr-bin"
    mkdir -p "$LCR_BIN"
    cat > "$LCR_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${CODEX_STUB_ARGV_LOG:?}"
: "${CODEX_STUB_COUNT_FILE:?}"
count=0
if [[ -f "$CODEX_STUB_COUNT_FILE" ]]; then
    count=$(cat "$CODEX_STUB_COUNT_FILE")
fi
count=$((count + 1))
printf '%s\n' "$count" > "$CODEX_STUB_COUNT_FILE"
output_path=""
last=""
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'stub codex review payload\n' > "$output_path"
printf 'tokens used\n42\n' >&2
STUB_EOF
    chmod +x "$LCR_BIN/codex"

    LCR_SESSION="lcr-codex-review-$$"
    LCR_LEDGER="$TMPDIR/lcr-codex-review-ledger.jsonl"
    LCR_OUT="$TMPDIR/lcr-codex-review-output.txt"
    LCR_ARGV="$TMPDIR/lcr-argv.txt"
    LCR_COUNT="$TMPDIR/lcr-count.txt"
    LCR_STDERR="$TMPDIR/lcr.stderr"

    set +e
    LARCH_TOKEN_SESSION_ID="$LCR_SESSION" \
    LARCH_TOKEN_LEDGER="$LCR_LEDGER" \
    IMPLEMENT_TMPDIR='' \
    PATH="$LCR_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$LCR_ARGV" \
    CODEX_STUB_COUNT_FILE="$LCR_COUNT" \
    LARCH_CODEX_MODEL="stub-model" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$LAUNCHER" \
            --output "$LCR_OUT" \
            --timeout 30 \
            --prompt "review" \
            >/dev/null 2>"$LCR_STDERR"
    LCR_RC=$?
    set -e

    if [[ "$LCR_RC" -ne 0 ]]; then
        fail "launch-review.sh --tool codex smoke exited rc=$LCR_RC; stderr=$(cat "$LCR_STDERR" 2>/dev/null)"
    else
        EXPECTED_TOTAL=42
        if [[ -s "$LCR_LEDGER" ]] \
           && jq -e --argjson total "$EXPECTED_TOTAL" \
               'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_review" and .total==$total)' \
               "$LCR_LEDGER" >/dev/null 2>&1; then
            pass
        else
            fail "launch-review.sh --tool codex did not record vendor=codex raw=codex_review total=$EXPECTED_TOTAL; ledger=$LCR_LEDGER content=$(cat "$LCR_LEDGER" 2>/dev/null) stderr=$(cat "$LCR_STDERR" 2>/dev/null)"
        fi
        rm -f "$LCR_LEDGER"
    fi

    # Issue #1874 regression: verify ### Codex section appears in token-report.sh output.
    # Stub writes "tokens used\n42\n" to STDOUT (not stderr) to exercise the
    # stdout-capture fix (>>"$SIDECAR" 2>&1) in launch-review.sh Codex section.
    LCR_STDOUT_BIN="$TMPDIR/lcr-stdout-bin"
    mkdir -p "$LCR_STDOUT_BIN"
    cat > "$LCR_STDOUT_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'stub codex review payload\n' > "$output_path"
printf 'tokens used\n42\n'
STUB_EOF
    chmod +x "$LCR_STDOUT_BIN/codex"

    LCR_REPORT_SESSION="lcr-codex-report-$$"
    LCR_REPORT_LEDGER="$TMPDIR/lcr-codex-report-ledger.jsonl"
    LCR_REPORT_OUT="$TMPDIR/lcr-codex-report-output.txt"
    LCR_REPORT_STDERR="$TMPDIR/lcr-report.stderr"

    LARCH_TOKEN_SESSION_ID="$LCR_REPORT_SESSION" LARCH_TOKEN_LEDGER="$LCR_REPORT_LEDGER" \
        "$REPO_ROOT/scripts/token-ledger.sh" mark "Step 5 — code review" >/dev/null 2>&1 || true

    set +e
    LARCH_TOKEN_SESSION_ID="$LCR_REPORT_SESSION" \
    LARCH_TOKEN_LEDGER="$LCR_REPORT_LEDGER" \
    IMPLEMENT_TMPDIR='' \
    PATH="$LCR_STDOUT_BIN:$PATH" \
    LARCH_CODEX_MODEL="stub-model" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$LAUNCHER" \
            --output "$LCR_REPORT_OUT" \
            --timeout 30 \
            --prompt "review" \
            >/dev/null 2>"$LCR_REPORT_STDERR"
    LCR_REPORT_RC=$?
    set -e

    if [[ "$LCR_REPORT_RC" -ne 0 ]]; then
        fail "issue#1874 codex-stdout-sidecar: launcher exited rc=$LCR_REPORT_RC; stderr=$(cat "$LCR_REPORT_STDERR" 2>/dev/null)"
    else
        if [[ -s "$LCR_REPORT_LEDGER" ]] \
           && jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_review" and .total==42)' \
               "$LCR_REPORT_LEDGER" >/dev/null 2>&1; then
            pass
        else
            fail "issue#1874 codex-stdout-sidecar: vendor record missing; ledger=$(cat "$LCR_REPORT_LEDGER" 2>/dev/null); stderr=$(cat "$LCR_REPORT_STDERR" 2>/dev/null)"
        fi
        LCR_EMPTY_TRANSCRIPT=$(mktemp "$TMPDIR/lcr-empty-XXXXXX")
        : > "$LCR_EMPTY_TRANSCRIPT"
        CODEX_REPORT_MD=$(LARCH_TOKEN_SESSION_ID="$LCR_REPORT_SESSION" \
            "$REPO_ROOT/scripts/token-report.sh" \
            --ledger "$LCR_REPORT_LEDGER" \
            --transcript "$LCR_EMPTY_TRANSCRIPT" \
            --full --markdown 2>/dev/null || true)
        if printf '%s\n' "$CODEX_REPORT_MD" | grep -Fq '### Codex'; then
            pass
        else
            fail "issue#1874 codex-stdout-sidecar: ### Codex missing from token-report.sh output; got=$(printf '%s' "$CODEX_REPORT_MD")"
        fi
        rm -f "$LCR_REPORT_LEDGER" "$LCR_EMPTY_TRANSCRIPT"
    fi
else
    pass
fi

# --token-budget-cap argv validation
set +e
"$LAUNCHER" --output "$TMPDIR/budget-missing.txt" --timeout 5 --prompt "x" \
    --token-budget-cap >/dev/null 2>"$TMPDIR/budget-missing.stderr"
RC=$?
set -e
assert_eq "token-budget-cap missing value exit" "2" "$RC"
assert_grep "token-budget-cap missing value message" "positive integer" "$TMPDIR/budget-missing.stderr"

for bad_cap in 0 00 000 abc 0.5 -1; do
    set +e
    "$LAUNCHER" --output "$TMPDIR/budget-bad-${bad_cap//[^a-zA-Z0-9_-]/x}.txt" --timeout 5 --prompt "x" \
        --token-budget-cap "$bad_cap" >/dev/null 2>"$TMPDIR/budget-bad-${bad_cap//[^a-zA-Z0-9_-]/x}.stderr"
    RC=$?
    set -e
    assert_eq "token-budget-cap bad value '$bad_cap' exit" "2" "$RC"
    assert_grep "token-budget-cap bad value '$bad_cap' message" "positive integer" "$TMPDIR/budget-bad-${bad_cap//[^a-zA-Z0-9_-]/x}.stderr"
done

# --token-budget-cap accept path: flag recognized (not "unknown flag"), binary
# absence or other required-flag errors cause non-0 exit from later checks.
# PATH stub prevents the launcher from invoking the real codex CLI on dev Macs.
# USER override gives this test a private serial-lock path so parallel clone
# sessions running the same harness do not queue on /tmp/larch-codex-serial-${USER}.lock.
set +e
PATH="$STUB_BIN:$PATH" USER="larch-test-budget-accept-codex-$$" \
    "$LAUNCHER" --output "$TMPDIR/budget-accept.txt" --timeout 5 --prompt "x" \
    --token-budget-cap 9999999 >/dev/null 2>"$TMPDIR/budget-accept.stderr"
set -e
if grep -Fq "unknown flag: --token-budget-cap" "$TMPDIR/budget-accept.stderr" 2>/dev/null; then
    fail "token-budget-cap flag not recognized (got 'unknown flag' rejection)"
else
    pass
fi

# Cap-hit path: when LARCH_TOKEN_BUDGET_CAP_REVIEW=1 and the token ledger
# shows vendor spend >= 1, the launcher writes STATUS=cap_hit to the output
# file and exits 0 without invoking the underlying Codex binary.
CH_SESSION="cap-hit-codex-review-$$-$RANDOM"
CH_LEDGER="$TMPDIR/cap-hit-codex-review-ledger.jsonl"
printf '{"type":"vendor","vendor":"codex","total":9999}\n' > "$CH_LEDGER"

CH_OUTPUT="$TMPDIR/cap-hit-codex-review.txt"
CH_COUNT="$TMPDIR/cap-hit-codex-count.txt"

PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$TMPDIR/cap-hit-codex-argv.txt" \
    CODEX_STUB_COUNT_FILE="$CH_COUNT" \
    LARCH_CODEX_MODEL="stub-model" \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_LEDGER="$CH_LEDGER" \
    LARCH_TOKEN_SESSION_ID="$CH_SESSION" \
    LARCH_TOKEN_BUDGET_CAP_REVIEW=1 \
    "$LAUNCHER" --output "$CH_OUTPUT" --timeout 5 --prompt "cap hit review" >/dev/null 2>&1
rm -f "$CH_LEDGER"

if [[ -f "$CH_OUTPUT" ]] && [[ "$(head -1 "$CH_OUTPUT")" == "STATUS=cap_hit" ]]; then
    pass
else
    fail "cap-hit output first line must be STATUS=cap_hit; got: $(head -1 "$CH_OUTPUT" 2>/dev/null)"
fi
if [[ ! -f "$CH_COUNT" ]]; then
    pass
else
    fail "cap-hit path must not invoke the underlying Codex binary (count file written)"
fi

# --diff-file accept path: flag recognized (not "unknown flag").
# PATH stub prevents the launcher from invoking the real codex CLI on dev Macs.
# USER override gives this test a private serial-lock path so parallel clone
# sessions running the same harness do not queue on /tmp/larch-codex-serial-${USER}.lock.
set +e
PATH="$STUB_BIN:$PATH" USER="larch-test-diff-file-accept-codex-$$" \
    "$LAUNCHER" --output "$TMPDIR/diff-file-accept.txt" --timeout 5 --prompt "x" \
    --diff-file "/nonexistent/branch.diff" >/dev/null 2>"$TMPDIR/diff-file-accept.stderr"
set -e
if grep -Fq "unknown flag: --diff-file" "$TMPDIR/diff-file-accept.stderr" 2>/dev/null; then
    fail "--diff-file flag not recognized by launch-review.sh --tool codex (got 'unknown flag' rejection)"
else
    pass
fi

# --diff-file specialist integration: when --agent-file + --diff-file are combined,
# the rendered prompt references the diff file path and omits the 'git diff $(git merge-base HEAD main)...HEAD' instruction.
DF_TMPFILE="$TMPDIR/test-branch.diff"
printf 'diff --git a/foo.sh b/foo.sh\n--- a/foo.sh\n+++ b/foo.sh\n@@ -1 +1 @@\n-old\n+new\n' > "$DF_TMPFILE"
DF_OUTPUT="$TMPDIR/codex-diff-file-specialist.txt"
DF_ARGV="$TMPDIR/codex-diff-file-specialist-argv.log"
DF_COUNT="$TMPDIR/codex-diff-file-specialist-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$DF_ARGV" \
    CODEX_STUB_COUNT_FILE="$DF_COUNT" \
    "$LAUNCHER" --output "$DF_OUTPUT" --timeout 5 \
        --agent-file "$REPO_ROOT/agents/reviewer-structure.md" \
        --mode diff \
        --diff-file "$DF_TMPFILE" \
        >/dev/null 2>"$TMPDIR/diff-file-specialist.stderr"
if grep -Fq -- "$DF_TMPFILE" "$DF_ARGV" 2>/dev/null; then
    pass
else
    fail "--diff-file specialist: diff file path must appear in rendered prompt argv"
fi
# shellcheck disable=SC2016
if grep -Fq -- 'git diff $(git merge-base HEAD main)...HEAD' "$DF_ARGV" 2>/dev/null; then
    fail "--diff-file specialist: 'git diff \$(git merge-base HEAD main)...HEAD' must NOT appear when --diff-file is set"
else
    pass
fi

# Case SL-transient-retry-codex-7: stub exits 7 with empty output on attempt 1,
# returns valid output on attempt 2. Launcher must retry and exit 0.
SL_TRANSIENT_CODEX7_COUNT="$TMPDIR/sl-transient-codex7-count.txt"
printf '0' > "$SL_TRANSIENT_CODEX7_COUNT"
cat > "$STUB_BIN/codex-transient-7" <<STUB_TRANSIENT_CODEX7
#!/usr/bin/env bash
count=\$(cat "${SL_TRANSIENT_CODEX7_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_TRANSIENT_CODEX7_COUNT}"
if (( count == 1 )); then
    exit 7
fi
# Write valid output on retry (args: exec --sandbox read-only ... --output-last-message FILE -- PROMPT)
last=""
for arg in "\$@"; do
    if [[ "\$last" == "--output-last-message" ]]; then
        printf 'transient-codex-7 retry ok\n' > "\$arg"
        break
    fi
    last="\$arg"
done
printf 'tokens used\n1\n'
STUB_TRANSIENT_CODEX7
chmod +x "$STUB_BIN/codex-transient-7"
ln -sf "$STUB_BIN/codex-transient-7" "$STUB_BIN/codex"
OUT_TRANSIENT_CODEX7="$TMPDIR/transient-codex7.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_TRANSIENT_CODEX7" --timeout 10 --prompt "sl-transient-retry-codex-7" >/dev/null 2>&1
RC_TRANSIENT_CODEX7=$?
set -e
assert_eq "SL-transient-retry-codex-7 exits 0 after transient retry" "0" "$RC_TRANSIENT_CODEX7"
SL_TRANSIENT_CODEX7_ATTEMPTS=$(cat "$SL_TRANSIENT_CODEX7_COUNT" 2>/dev/null || echo "0")
assert_eq "SL-transient-retry-codex-7 stub invoked exactly 2 times" "2" "$SL_TRANSIENT_CODEX7_ATTEMPTS"
rm -f "$SL_TRANSIENT_CODEX7_COUNT"

# Case SL-transient-retry-exhausted: stub exits 7 with empty output on all 3
# attempts. Launcher must give up after 2 retries (3 total attempts) and exit non-zero.
SL_TRANSIENT_EXHAUSTED_COUNT="$TMPDIR/sl-transient-exhausted-count.txt"
printf '0' > "$SL_TRANSIENT_EXHAUSTED_COUNT"
cat > "$STUB_BIN/codex-transient-exhausted" <<STUB_TRANSIENT_EXHAUSTED
#!/usr/bin/env bash
count=\$(cat "${SL_TRANSIENT_EXHAUSTED_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_TRANSIENT_EXHAUSTED_COUNT}"
exit 7
STUB_TRANSIENT_EXHAUSTED
chmod +x "$STUB_BIN/codex-transient-exhausted"
ln -sf "$STUB_BIN/codex-transient-exhausted" "$STUB_BIN/codex"
OUT_TRANSIENT_EXHAUSTED="$TMPDIR/transient-exhausted.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_TRANSIENT_EXHAUSTED" --timeout 10 --prompt "sl-transient-retry-exhausted" >/dev/null 2>&1
RC_TRANSIENT_EXHAUSTED=$?
set -e
assert_eq "SL-transient-retry-exhausted exits non-zero after exhausting retries" "7" "$RC_TRANSIENT_EXHAUSTED"
SL_TRANSIENT_EXHAUSTED_ATTEMPTS=$(cat "$SL_TRANSIENT_EXHAUSTED_COUNT" 2>/dev/null || echo "0")
assert_eq "SL-transient-retry-exhausted stub invoked exactly 3 times (2 retries)" "3" "$SL_TRANSIENT_EXHAUSTED_ATTEMPTS"
rm -f "$SL_TRANSIENT_EXHAUSTED_COUNT"

# Case SL-transient-vs-auth-precedence: stub exits 7 but writes an auth-error
# string to stderr (which propagates to the sidecar via FD inheritance from
# run-external-agent.sh). The launcher must NOT treat this as a transient
# infra failure because the auth-exclusion guard fires first; the auth-retry
# path handles it instead. With LARCH_EXTERNAL_AUTH_RETRIES=2, one auth retry
# occurs (2 attempts total).
SL_TRANSIENT_AUTH_COUNT="$TMPDIR/sl-transient-auth-count.txt"
printf '0' > "$SL_TRANSIENT_AUTH_COUNT"
cat > "$STUB_BIN/codex-transient-auth" <<STUB_TRANSIENT_AUTH
#!/usr/bin/env bash
count=\$(cat "${SL_TRANSIENT_AUTH_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_TRANSIENT_AUTH_COUNT}"
if (( count == 1 )); then
    # Auth-error pattern to sidecar via inherited stderr — disqualifies transient path
    printf 'Error: not logged in\n' >&2
    exit 7
fi
last=""
for arg in "\$@"; do
    if [[ "\$last" == "--output-last-message" ]]; then
        printf 'auth-path ok\n' > "\$arg"
        break
    fi
    last="\$arg"
done
printf 'tokens used\n1\n'
STUB_TRANSIENT_AUTH
chmod +x "$STUB_BIN/codex-transient-auth"
ln -sf "$STUB_BIN/codex-transient-auth" "$STUB_BIN/codex"
OUT_TRANSIENT_AUTH="$TMPDIR/transient-auth.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_AUTH_RETRIES=2 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_TRANSIENT_AUTH" --timeout 10 --prompt "sl-transient-vs-auth-precedence" >/dev/null 2>&1
RC_TRANSIENT_AUTH=$?
set -e
assert_eq "SL-transient-vs-auth-precedence exits 0 via auth retry" "0" "$RC_TRANSIENT_AUTH"
SL_TRANSIENT_AUTH_ATTEMPTS=$(cat "$SL_TRANSIENT_AUTH_COUNT" 2>/dev/null || echo "0")
assert_eq "SL-transient-vs-auth-precedence stub invoked exactly 2 times (auth retry)" "2" "$SL_TRANSIENT_AUTH_ATTEMPTS"
rm -f "$SL_TRANSIENT_AUTH_COUNT"

# Case SL-transient-not-applied: stub exits 1 with non-empty sidecar content.
# Exit code 1 is not in the transient allowlist → no transient retry, exactly
# 1 invocation.
SL_TRANSIENT_NOAPPLY_COUNT="$TMPDIR/sl-transient-noapply-count.txt"
printf '0' > "$SL_TRANSIENT_NOAPPLY_COUNT"
cat > "$STUB_BIN/codex-transient-noapply" <<STUB_TRANSIENT_NOAPPLY
#!/usr/bin/env bash
count=\$(cat "${SL_TRANSIENT_NOAPPLY_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_TRANSIENT_NOAPPLY_COUNT}"
printf 'some output indicating real failure\n' >&2
exit 1
STUB_TRANSIENT_NOAPPLY
chmod +x "$STUB_BIN/codex-transient-noapply"
ln -sf "$STUB_BIN/codex-transient-noapply" "$STUB_BIN/codex"
OUT_TRANSIENT_NOAPPLY="$TMPDIR/transient-noapply.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_TRANSIENT_NOAPPLY" --timeout 10 --prompt "sl-transient-not-applied" >/dev/null 2>&1
RC_TRANSIENT_NOAPPLY=$?
set -e
assert_eq "SL-transient-not-applied exits 1 without transient retry" "1" "$RC_TRANSIENT_NOAPPLY"
SL_TRANSIENT_NOAPPLY_ATTEMPTS=$(cat "$SL_TRANSIENT_NOAPPLY_COUNT" 2>/dev/null || echo "0")
assert_eq "SL-transient-not-applied stub invoked exactly 1 time (exit 1 not in allowlist)" "1" "$SL_TRANSIENT_NOAPPLY_ATTEMPTS"
rm -f "$SL_TRANSIENT_NOAPPLY_COUNT"

# Case SL-transient-obs-exhausted: verify that when the transient-retry loop
# exhausts all retries, the execution-issues header contains the exact retry
# counters (auth-retries=M, transient-retries=N). Uses IMPLEMENT_TMPDIR so
# append_launch_failure actually writes to execution-issues.md.
# With MAX_TRANSIENT_RETRIES=2: start=1, +1 for retry1=2, +1 for retry2=3, then
# 3>2 → break → TRANSIENT_ATTEMPT=3 at failure time.
SL_OBS_EXHAUSTED_COUNT="$TMPDIR/sl-obs-exhausted-count.txt"
printf '0' > "$SL_OBS_EXHAUSTED_COUNT"
cat > "$STUB_BIN/codex-obs-exhausted" <<STUB_OBS_EXHAUSTED
#!/usr/bin/env bash
count=\$(cat "${SL_OBS_EXHAUSTED_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_OBS_EXHAUSTED_COUNT}"
exit 7
STUB_OBS_EXHAUSTED
chmod +x "$STUB_BIN/codex-obs-exhausted"
ln -sf "$STUB_BIN/codex-obs-exhausted" "$STUB_BIN/codex"
IMPL_TMPDIR_OBS_EXHAUSTED="$TMPDIR/obs-exhausted-impl"
mkdir -p "$IMPL_TMPDIR_OBS_EXHAUSTED"
OUT_OBS_EXHAUSTED="$TMPDIR/obs-exhausted.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    IMPLEMENT_TMPDIR="$IMPL_TMPDIR_OBS_EXHAUSTED" \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_OBS_EXHAUSTED" --timeout 10 --prompt "sl-obs-exhausted" >/dev/null 2>&1
RC_OBS_EXHAUSTED=$?
set -e
assert_eq "SL-transient-obs-exhausted exits non-zero after exhausting retries" "7" "$RC_OBS_EXHAUSTED"
EI_OBS_EXHAUSTED="$IMPL_TMPDIR_OBS_EXHAUSTED/execution-issues.md"
OBS_EXHAUSTED_ENTRY_COUNT=$(grep -Ec '^- \*\*Step review Step 2 — codex-review failed' "$EI_OBS_EXHAUSTED" 2>/dev/null || echo 0)
assert_eq "SL-transient-obs-exhausted execution-issues has one failure entry" "1" "$OBS_EXHAUSTED_ENTRY_COUNT"
assert_regex "SL-transient-obs-exhausted exact retry header" '^-\s\*\*Step review Step 2 — codex-review failed \(exit 7 — non-auth — auth-retries=1, transient-retries=3\)\*\*:$' "$EI_OBS_EXHAUSTED"
rm -f "$SL_OBS_EXHAUSTED_COUNT"

# Case SL-transient-obs-fired: verify that when the transient-retry fires and
# the second attempt succeeds, no failure entry is written to execution-issues.
SL_OBS_FIRED_COUNT="$TMPDIR/sl-obs-fired-count.txt"
printf '0' > "$SL_OBS_FIRED_COUNT"
cat > "$STUB_BIN/codex-obs-fired" <<STUB_OBS_FIRED
#!/usr/bin/env bash
count=\$(cat "${SL_OBS_FIRED_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_OBS_FIRED_COUNT}"
if (( count == 1 )); then
    exit 7
fi
last=""
for arg in "\$@"; do
    if [[ "\$last" == "--output-last-message" ]]; then
        printf 'transient-obs-fired retry ok\n' > "\$arg"
        break
    fi
    last="\$arg"
done
printf 'tokens used\n1\n'
STUB_OBS_FIRED
chmod +x "$STUB_BIN/codex-obs-fired"
ln -sf "$STUB_BIN/codex-obs-fired" "$STUB_BIN/codex"
IMPL_TMPDIR_OBS_FIRED="$TMPDIR/obs-fired-impl"
mkdir -p "$IMPL_TMPDIR_OBS_FIRED"
OUT_OBS_FIRED="$TMPDIR/obs-fired.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    IMPLEMENT_TMPDIR="$IMPL_TMPDIR_OBS_FIRED" \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_OBS_FIRED" --timeout 10 --prompt "sl-obs-fired" >/dev/null 2>&1
RC_OBS_FIRED=$?
set -e
assert_eq "SL-transient-obs-fired exits 0 after transient retry succeeds" "0" "$RC_OBS_FIRED"
EI_OBS_FIRED="$IMPL_TMPDIR_OBS_FIRED/execution-issues.md"
OBS_FIRED_ENTRY_COUNT=$(grep -Ec '^- \*\*Step review Step 2 — codex-review failed' "$EI_OBS_FIRED" 2>/dev/null || echo 0)
assert_eq "SL-transient-obs-fired execution-issues has no failure entry on success" "0" "$OBS_FIRED_ENTRY_COUNT"
rm -f "$SL_OBS_FIRED_COUNT"

# Case SL-transient-obs-nontransient: verify that a true non-transient failure
# (exit code not in the transient allowlist, non-empty output file) still logs
# both retry counters. M=1 means no transient retry fired. Stub exits 1 and
# writes ~5KB to the output file; exit 1 is not in the transient allowlist so
# no retry fires.
SL_OBS_NONTRANSIENT_COUNT="$TMPDIR/sl-obs-nontransient-count.txt"
printf '0' > "$SL_OBS_NONTRANSIENT_COUNT"
cat > "$STUB_BIN/codex-obs-nontransient" <<STUB_OBS_NONTRANSIENT
#!/usr/bin/env bash
count=\$(cat "${SL_OBS_NONTRANSIENT_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_OBS_NONTRANSIENT_COUNT}"
# Write ~5KB to the output file to ensure external_is_transient_infra_failure
# returns false on the output-empty check (which would short-circuit before the
# exit-code check; exit 1 already fails the allowlist gate so the order is moot).
last=""
for arg in "\$@"; do
    if [[ "\$last" == "--output-last-message" ]]; then
        dd if=/dev/urandom bs=5120 count=1 2>/dev/null | base64 > "\$arg" || printf '%05120d' 0 > "\$arg"
        break
    fi
    last="\$arg"
done
exit 1
STUB_OBS_NONTRANSIENT
chmod +x "$STUB_BIN/codex-obs-nontransient"
ln -sf "$STUB_BIN/codex-obs-nontransient" "$STUB_BIN/codex"
IMPL_TMPDIR_OBS_NONTRANSIENT="$TMPDIR/obs-nontransient-impl"
mkdir -p "$IMPL_TMPDIR_OBS_NONTRANSIENT"
OUT_OBS_NONTRANSIENT="$TMPDIR/obs-nontransient.txt"
set +e
LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    IMPLEMENT_TMPDIR="$IMPL_TMPDIR_OBS_NONTRANSIENT" \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_OBS_NONTRANSIENT" --timeout 10 --prompt "sl-obs-nontransient" >/dev/null 2>&1
RC_OBS_NONTRANSIENT=$?
set -e
assert_eq "SL-transient-obs-nontransient exits 1 without transient retry" "1" "$RC_OBS_NONTRANSIENT"
OBS_NONTRANSIENT_ATTEMPTS=$(cat "$SL_OBS_NONTRANSIENT_COUNT" 2>/dev/null || echo "0")
assert_eq "SL-transient-obs-nontransient stub invoked exactly 1 time" "1" "$OBS_NONTRANSIENT_ATTEMPTS"
EI_OBS_NONTRANSIENT="$IMPL_TMPDIR_OBS_NONTRANSIENT/execution-issues.md"
OBS_NONTRANSIENT_ENTRY_COUNT=$(grep -Ec '^- \*\*Step review Step 2 — codex-review failed' "$EI_OBS_NONTRANSIENT" 2>/dev/null || echo 0)
assert_eq "SL-transient-obs-nontransient execution-issues has one failure entry" "1" "$OBS_NONTRANSIENT_ENTRY_COUNT"
assert_regex "SL-transient-obs-nontransient exact non-transient header" '^-\s\*\*Step review Step 2 — codex-review failed \(exit 1 — non-auth — auth-retries=1, transient-retries=1\)\*\*:$' "$EI_OBS_NONTRANSIENT"
rm -f "$SL_OBS_NONTRANSIENT_COUNT"

# Restore normal codex stub for remaining tests.
ln -sf "$CODEX_DEFAULT_STUB" "$STUB_BIN/codex"

if (( FAIL > 0 )); then
    printf 'FAIL: test-launch-review.sh --tool codex - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-review.sh --tool codex - %s assertions passed\n' "$PASS"

) || OVERALL_FAIL=1

echo 'Running launch-review cursor suite'
(
# Regression test for launch-review.sh --tool cursor sentinel ownership and retry metadata.
#
# Wired into: make test-launch-review (Makefile shard test-harnesses-2).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
LARCH_TEST_REPO_ROOT="$REPO_ROOT"
export LARCH_TEST_REPO_ROOT
LAUNCHER="$TMPROOT/bin/launch-review-cursor"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" <<'LARCH_REVIEW_CURSOR_SHIM'
#!/usr/bin/env bash
exec "$LARCH_TEST_REPO_ROOT/scripts/launch-review.sh" --tool cursor "$@"
LARCH_REVIEW_CURSOR_SHIM
chmod +x "$LAUNCHER"
# shellcheck disable=SC2030
TMPDIR="$(mktemp -d /tmp/larch-test-launch-cursor-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
# shellcheck disable=SC2030,SC2031
export LARCH_EXECUTION_ISSUES_LOG="$TMPDIR/execution-issues.md"

# shellcheck disable=SC2030,SC2031
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05
export LARCH_CURSOR_MODEL=test-cursor-model

PASS=0
FAIL=0
FAIL_DETAILS=()

pass() {
    PASS=$((PASS + 1))
}

fail() {
    FAIL=$((FAIL + 1))
    FAIL_DETAILS+=("$1")
}

assert_equals() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

assert_grep() {
    local label="$1"
    local pattern="$2"
    local path="$3"
    if grep -q -- "$pattern" "$path"; then
        pass
    else
        fail "$label: expected $path to match $pattern"
    fi
}

assert_regex() {
    local label="$1"
    local pattern="$2"
    local path="$3"
    if grep -Eq -- "$pattern" "$path"; then
        pass
    else
        fail "$label: expected $path to match regex $pattern"
    fi
}

assert_no_artifacts() {
    local label="$1"
    local output="$2"
    local suffix
    for suffix in "" ".prompt" ".sidecar" ".done" ".inner.done" ".meta" ".diag" ".json" ".dirty-tree" ".untracked-baseline"; do
        if [[ -e "${output}${suffix}" ]]; then
            fail "$label: unexpected artifact ${output}${suffix}"
        else
            pass
        fi
    done
}

wait_for_file() {
    local path="$1"
    local limit="${2:-100}"
    local i
    for ((i = 0; i < limit; i++)); do
        [[ -e "$path" ]] && return 0
        sleep 0.05
    done
    return 1
}

STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/cursor" <<'STUB_CURSOR'
#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${CURSOR_STUB_PID_FILE:-}" ]]; then
    printf '%s\n' "$$" > "$CURSOR_STUB_PID_FILE"
fi
if [[ -n "${CURSOR_STUB_PROMPT_LOG:-}" ]]; then
    last=""
    for arg in "$@"; do
        last="$arg"
    done
    printf '%s' "$last" > "$CURSOR_STUB_PROMPT_LOG"
fi
if [[ -n "${CURSOR_STUB_PWD_LOG:-}" ]]; then
    pwd -P > "$CURSOR_STUB_PWD_LOG"
fi
if [[ -n "${CURSOR_STUB_TOKEN_SESSION_FILE:-}" ]]; then
    printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$CURSOR_STUB_TOKEN_SESSION_FILE"
fi
if [[ -n "${CURSOR_STUB_DELAY:-}" ]]; then
    sleep "$CURSOR_STUB_DELAY"
fi
if [[ "${CURSOR_STUB_RESULT+x}" == "x" ]]; then
    result="$CURSOR_STUB_RESULT"
else
    result="POST-PROCESSED OK"
fi
printf '{"result":"%s","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}\n' "$result"
STUB_CURSOR
chmod +x "$STUB_BIN/cursor"

# Case A: on the normal success path, public .done appears only after $OUTPUT
# contains extracted prose rather than the raw Cursor JSON envelope.
OUT_A="$TMPDIR/cursor-a.txt"
(
    PATH="$STUB_BIN:$PATH" CURSOR_STUB_DELAY=0.2 CURSOR_STUB_RESULT="ORDERED PROSE" \
        "$LAUNCHER" --output "$OUT_A" --timeout 5 --prompt "case a"
) >/dev/null 2>"$TMPDIR/case-a.stderr" &
PID_A=$!
if wait_for_file "${OUT_A}.done"; then
    assert_equals "case A output at done" "ORDERED PROSE" "$(cat "$OUT_A")"
    if grep -q '[{}]' "$OUT_A"; then
        fail "case A output should not contain raw JSON braces when .done appears"
    else
        pass
    fi
else
    fail "case A .done did not appear"
fi
wait "$PID_A"
assert_equals "case A done code" "0" "$(cat "${OUT_A}.done")"

# Case B: successful runs enrich .meta with outer-launcher replay keys and
# persist the original unwrapped prompt byte-for-byte.
OUT_B="$TMPDIR/cursor-b.txt"
PATH="$STUB_BIN:$PATH" "$LAUNCHER" --output "$OUT_B" --timeout 5 --prompt "original prompt" >/dev/null 2>"$TMPDIR/case-b.stderr"
assert_grep "case B outer launcher" "^OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-review.sh$" "${OUT_B}.meta"
assert_grep "case B outer prompt" "^OUTER_LAUNCHER_PROMPT_FILE=${OUT_B}.prompt$" "${OUT_B}.meta"
assert_grep "case B workdir" "^OUTER_LAUNCHER_WORKDIR=$(pwd -P)$" "${OUT_B}.meta"
# Issue #1529: the OUTPUT.prompt sidecar holds the user-original prompt
# (no preamble) so collect-agent-results.sh empty-output retry can replay
# via --prompt-file without double-prepending the HARD CONSTRAINTS block.
# The preamble is verified against the actual argv in case C / case AK1
# (which use argv-recording stubs); case B's stub does not record argv,
# so this case only verifies the sidecar contract.
assert_equals "case B prompt sidecar (user-original, no preamble)" "original prompt" "$(cat "${OUT_B}.prompt")"
if grep -Fq -- 'HARD CONSTRAINTS' "${OUT_B}.prompt"; then
    fail "case B prompt sidecar must NOT contain the preamble (retry-replay safety)"
else
    pass
fi
assert_grep "case B dirty-tree sidecar status" "^STATUS=" "${OUT_B}.dirty-tree"
assert_grep "case B dirty-tree sidecar mode" "^MODE=baseline$" "${OUT_B}.dirty-tree"

# Case B2: Cursor JSON envelopes with explicit empty .result are promoted to a
# distinct marker instead of a generic blank reviewer output.
OUT_B2="$TMPDIR/cursor-b2.txt"
PATH="$STUB_BIN:$PATH" CURSOR_STUB_RESULT="" \
    "$LAUNCHER" --output "$OUT_B2" --timeout 5 --prompt "empty result" >/dev/null 2>"$TMPDIR/case-b2.stderr"
assert_equals "case B2 empty Cursor result marker" "CURSOR_EMPTY_RESPONSE" "$(cat "$OUT_B2")"

# Case C: --prompt-file preserves trailing newlines through the wrapper prompt.
# Issue #1529: the wrapper output (last argv to cursor) has the form
# ` /max-mode on. Prompt: <preamble>\n\n<body>`. Verify the wrapper prefix,
# preamble presence, and body tail. Also verify the OUTPUT.prompt sidecar is
# the user-original body verbatim (no preamble — retry-replay safety).
OUT_C="$TMPDIR/cursor-c.txt"
PROMPT_C="$TMPDIR/cursor-c.prompt"
PROMPT_LOG_C="$TMPDIR/cursor-c.prompt-log"
printf 'line one\n\n' > "$PROMPT_C"
PATH="$STUB_BIN:$PATH" CURSOR_STUB_PROMPT_LOG="$PROMPT_LOG_C" \
    "$LAUNCHER" --output "$OUT_C" --timeout 5 --prompt-file "$PROMPT_C" >/dev/null 2>"$TMPDIR/case-c.stderr"
if grep -Fq -- ' /max-mode on. Prompt: ' "$PROMPT_LOG_C"; then
    pass
else
    fail "case C wrapped prompt must contain the /max-mode wrapper prefix"
fi
assert_grep "case C wrapped prompt preamble" "HARD CONSTRAINTS — your role is read-only review" "$PROMPT_LOG_C"
EXPECTED_C_TAIL="$TMPDIR/cursor-c.expected-tail"
printf 'line one\n\n' > "$EXPECTED_C_TAIL"
if tail -c "$(wc -c < "$EXPECTED_C_TAIL" | tr -d ' ')" "$PROMPT_LOG_C" | cmp -s - "$EXPECTED_C_TAIL"; then
    pass
else
    fail "case C wrapped prompt did not preserve trailing newlines at the tail"
fi
# Case C sidecar contract: original bytes preserved, no preamble.
EXPECTED_C_SIDECAR="$TMPDIR/cursor-c.expected-sidecar"
printf 'line one\n\n' > "$EXPECTED_C_SIDECAR"
if cmp -s "$EXPECTED_C_SIDECAR" "${OUT_C}.prompt"; then
    pass
else
    fail "case C OUTPUT.prompt sidecar must equal the user-original --prompt-file bytes (no preamble)"
fi
if grep -Fq -- 'HARD CONSTRAINTS' "${OUT_C}.prompt"; then
    fail "case C OUTPUT.prompt sidecar must NOT contain the preamble (retry-replay safety)"
else
    pass
fi

# Case C2: model-args preflight failure synthesizes .done/.diag/.meta and
# dirty-tree sidecar artifacts (matching the cursor-auth-preflight pattern)
# so collect-agent-results.sh detects failure promptly without waiting for
# the collector timeout.
OUT_C2="$TMPDIR/cursor-c2.txt"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_CURSOR_MODEL=$'bad\nmodel' \
    "$LAUNCHER" --output "$OUT_C2" --timeout 5 --prompt "case c2" >/dev/null 2>"$TMPDIR/case-c2.stderr"
CODE_C2=$?
set -e
if [[ "$CODE_C2" -ne 0 ]]; then
    pass
else
    fail "case C2 wrapper must exit non-zero on model-args preflight failure"
fi
if [[ -s "${OUT_C2}.done" ]]; then
    pass
else
    fail "case C2 preflight failure must write non-empty .done sentinel"
fi
if [[ -s "${OUT_C2}.diag" ]] && grep -Fq 'STATUS=FAILED' "${OUT_C2}.diag"; then
    pass
else
    fail "case C2 preflight failure must write .diag with STATUS=FAILED"
fi
assert_grep "case C2 diag diagnostic" "cursor_launcher_load_model_args failed" "${OUT_C2}.diag"
if [[ -s "${OUT_C2}.meta" ]] && grep -Fq 'CMD_JSON=[]' "${OUT_C2}.meta"; then
    pass
else
    fail "case C2 preflight failure must write stub .meta with CMD_JSON=[]"
fi
if [[ -s "${OUT_C2}.dirty-tree" ]] && grep -Fq 'STATUS=unknown' "${OUT_C2}.dirty-tree"; then
    pass
else
    fail "case C2 preflight failure must write unknown dirty-tree sidecar"
fi

OUT_TOKEN="$TMPDIR/cursor-token.txt"
TOKEN_SESSION_FILE="$TMPDIR/cursor-token-session.txt"
IMPLEMENT_TMPDIR_FIXTURE="$TMPDIR/implement-tmpdir"
mkdir -p "$IMPLEMENT_TMPDIR_FIXTURE"
printf 'mock-cursor-review-session\n' > "$IMPLEMENT_TMPDIR_FIXTURE/session-id"
printf 'SOURCE_FILE=/tmp/mock.jsonl\n' > "$IMPLEMENT_TMPDIR_FIXTURE/claude-source.env"
PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_FILE" \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_FIXTURE" \
    LARCH_TOKEN_SESSION_ID="stale-cursor-review-session" \
    "$LAUNCHER" --output "$OUT_TOKEN" --timeout 5 --prompt "token context" >/dev/null 2>"$TMPDIR/case-token.stderr"
assert_equals "case token session id rehydrated" "mock-cursor-review-session" "$(cat "$TOKEN_SESSION_FILE")"

DESIGN_CURSOR_TOKEN="$TMPDIR/design-cursor-token"
mkdir -p "$DESIGN_CURSOR_TOKEN"
printf 'cursor-design-session\n' > "$DESIGN_CURSOR_TOKEN/session-id"
TOKEN_SESSION_DESIGN_CURSOR="$TMPDIR/cursor-token-design.txt"
PATH="$STUB_BIN:$PATH" \
    env -u IMPLEMENT_TMPDIR \
    CURSOR_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_DESIGN_CURSOR" \
    DESIGN_TMPDIR="$DESIGN_CURSOR_TOKEN" \
    LARCH_TOKEN_SESSION_ID="stale-cursor-design" \
    "$LAUNCHER" --output "$TMPDIR/out-cursor-design-token.txt" --timeout 5 --prompt "cursor design token" >/dev/null 2>"$TMPDIR/case-cursor-design-token.stderr"
assert_equals "cursor design tmpdir session-id export" "cursor-design-session" "$(cat "$TOKEN_SESSION_DESIGN_CURSOR")"

TOKEN_SESSION_CURSOR_NEITHER="$TMPDIR/cursor-token-neither.txt"
PATH="$STUB_BIN:$PATH" \
    env -u IMPLEMENT_TMPDIR -u DESIGN_TMPDIR \
    CURSOR_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_CURSOR_NEITHER" \
    LARCH_TOKEN_SESSION_ID="cursor-explicit-session" \
    "$LAUNCHER" --output "$TMPDIR/out-cursor-neither.txt" --timeout 5 --prompt "cursor neither" >/dev/null 2>"$TMPDIR/case-cursor-neither.stderr"
assert_equals "cursor no tmpdir preserves explicit LARCH_TOKEN_SESSION_ID" "cursor-explicit-session" "$(cat "$TOKEN_SESSION_CURSOR_NEITHER")"

# Case D: deterministic post-wrapper trap path promotes an existing inner
# sentinel and may leave raw JSON because normal post-processing was interrupted.
# Hook is gated behind LARCH_ALLOW_TEST_HOOKS=1 + a hook file path under the
# harness tmpdir, replacing the legacy LARCH_TEST_TRAP_AFTER_INNER_DONE eval
# channel (FINDING_1 of /review round 1 hardening).
OUT_D="$TMPDIR/cursor-d.txt"
HOOK_D="$TMPDIR/case-d.hook"
printf 'exit 143\n' > "$HOOK_D"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_ALLOW_TEST_HOOKS=1 \
    LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE="$HOOK_D" \
    "$LAUNCHER" --output "$OUT_D" --timeout 5 --prompt "case d" >/dev/null 2>"$TMPDIR/case-d.stderr"
CODE_D=$?
set -e
if [[ "$CODE_D" -ne 0 ]]; then
    pass
else
    fail "case D expected signal-driven non-zero exit"
fi
assert_equals "case D promoted done" "0" "$(cat "${OUT_D}.done")"
if grep -q '"result"' "$OUT_D"; then
    pass
else
    fail "case D expected raw JSON to remain on abnormal exit"
fi

# Case D2: hook is rejected when LARCH_ALLOW_TEST_HOOKS != 1, even if the file
# env var is set. Verifies the gate is exact-match (production-safe).
OUT_D2="$TMPDIR/cursor-d2.txt"
HOOK_D2="$TMPDIR/case-d2.hook"
printf 'exit 143\n' > "$HOOK_D2"
set +e
# LARCH_ALLOW_TEST_HOOKS unset (would be the production posture): hook ignored.
PATH="$STUB_BIN:$PATH" \
    LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE="$HOOK_D2" \
    "$LAUNCHER" --output "$OUT_D2" --timeout 5 --prompt "case d2" >/dev/null 2>"$TMPDIR/case-d2.stderr"
CODE_D2=$?
set -e
if [[ "$CODE_D2" -eq 0 ]]; then
    pass
else
    fail "case D2 expected normal exit (hook gated off)"
fi
# .done must reflect the wrapper's normal exit, not 143 from the hook
assert_equals "case D2 hook ignored when ALLOW=unset" "0" "$(cat "${OUT_D2}.done")"

# Case D3: explicit LARCH_ALLOW_TEST_HOOKS=2 (non-"1" value) also rejected.
OUT_D3="$TMPDIR/cursor-d3.txt"
HOOK_D3="$TMPDIR/case-d3.hook"
printf 'exit 143\n' > "$HOOK_D3"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_ALLOW_TEST_HOOKS=2 \
    LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE="$HOOK_D3" \
    "$LAUNCHER" --output "$OUT_D3" --timeout 5 --prompt "case d3" >/dev/null 2>"$TMPDIR/case-d3.stderr"
CODE_D3=$?
set -e
if [[ "$CODE_D3" -eq 0 ]]; then
    pass
else
    fail "case D3 expected normal exit (hook gated off; ALLOW != 1)"
fi
assert_equals "case D3 hook ignored when ALLOW=2" "0" "$(cat "${OUT_D3}.done")"

# Case D4: legacy env var name (without _FILE) is NOT honored, even with ALLOW=1.
# Guards against silent fallback to the old eval-based contract.
OUT_D4="$TMPDIR/cursor-d4.txt"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_ALLOW_TEST_HOOKS=1 \
    LARCH_TEST_TRAP_AFTER_INNER_DONE='exit 143' \
    "$LAUNCHER" --output "$OUT_D4" --timeout 5 --prompt "case d4" >/dev/null 2>"$TMPDIR/case-d4.stderr"
CODE_D4=$?
set -e
if [[ "$CODE_D4" -eq 0 ]]; then
    pass
else
    fail "case D4 expected normal exit (legacy env var not honored)"
fi
assert_equals "case D4 legacy env ignored" "0" "$(cat "${OUT_D4}.done")"

# Case D5: symlinked hook file rejected (defense-in-depth).
OUT_D5="$TMPDIR/cursor-d5.txt"
HOOK_D5_REAL="$TMPDIR/case-d5-real.hook"
HOOK_D5_LINK="$TMPDIR/case-d5-link.hook"
printf 'exit 143\n' > "$HOOK_D5_REAL"
ln -sf "$HOOK_D5_REAL" "$HOOK_D5_LINK"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_ALLOW_TEST_HOOKS=1 \
    LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE="$HOOK_D5_LINK" \
    "$LAUNCHER" --output "$OUT_D5" --timeout 5 --prompt "case d5" >/dev/null 2>"$TMPDIR/case-d5.stderr"
CODE_D5=$?
set -e
if [[ "$CODE_D5" -eq 0 ]]; then
    pass
else
    fail "case D5 expected normal exit (symlinked hook rejected)"
fi
assert_equals "case D5 symlink hook rejected" "0" "$(cat "${OUT_D5}.done")"

# Case E: signaling the launcher while the wrapper child is running causes the
# trap to reap the child before publishing .done.
OUT_E="$TMPDIR/cursor-e.txt"
PID_LOG_E="$TMPDIR/cursor-e.pid"
(
    PATH="$STUB_BIN:$PATH" CURSOR_STUB_DELAY=5 CURSOR_STUB_PID_FILE="$PID_LOG_E" \
        "$LAUNCHER" --output "$OUT_E" --timeout 20 --prompt "case e"
) >/dev/null 2>"$TMPDIR/case-e.stderr" &
LAUNCHER_PID_E=$!
if wait_for_file "$PID_LOG_E"; then
    STUB_PID_E="$(cat "$PID_LOG_E")"
    kill -TERM "$LAUNCHER_PID_E" 2>/dev/null || true
    wait "$LAUNCHER_PID_E" 2>/dev/null || true
    if wait_for_file "${OUT_E}.done"; then
        pass
    else
        fail "case E .done did not appear after signal"
    fi
    if kill -0 "$STUB_PID_E" 2>/dev/null; then
        fail "case E wrapper child still alive after launcher trap"
    else
        pass
    fi
else
    fail "case E cursor stub did not start"
    kill -TERM "$LAUNCHER_PID_E" 2>/dev/null || true
    wait "$LAUNCHER_PID_E" 2>/dev/null || true
fi

# Case F: prompt source flags are mutually exclusive and fail before side effects.
OUT_F="$TMPDIR/cursor-f.txt"
ERR_F="$TMPDIR/case-f.stderr"
set +e
"$LAUNCHER" --output "$OUT_F" --timeout 5 --prompt "x" --prompt-file "$PROMPT_C" >/dev/null 2>"$ERR_F"
CODE_F=$?
set -e
assert_equals "case F exit" "2" "$CODE_F"
assert_grep "case F stderr" "launch-review.sh: --prompt, --agent-file, and --prompt-file are mutually exclusive" "$ERR_F"
assert_no_artifacts "case F no side effects" "$OUT_F"

# Case G: invalid output and timeout validation happen before side effects.
OUT_G_BAD="$TMPDIR/bad output.txt"
ERR_G_BAD="$TMPDIR/case-g-bad.stderr"
set +e
"$LAUNCHER" --output "$OUT_G_BAD" --timeout 5 --prompt "x" >/dev/null 2>"$ERR_G_BAD"
CODE_G_BAD=$?
set -e
assert_equals "case G bad output exit" "1" "$CODE_G_BAD"
assert_grep "case G bad output stderr" "ERROR: --output contains bytes outside" "$ERR_G_BAD"
assert_no_artifacts "case G bad output no side effects" "$OUT_G_BAD"

OUT_G_TIMEOUT="$TMPDIR/cursor-g-timeout.txt"
ERR_G_TIMEOUT="$TMPDIR/case-g-timeout.stderr"
set +e
"$LAUNCHER" --output "$OUT_G_TIMEOUT" --timeout 0 --prompt "x" >/dev/null 2>"$ERR_G_TIMEOUT"
CODE_G_TIMEOUT=$?
set -e
assert_equals "case G timeout exit" "2" "$CODE_G_TIMEOUT"
# `--timeout 0` now passes the digit-only filter and hits the arithmetic floor
# check (FINDING_4 hardening), which emits "--timeout must be >= 1".
assert_grep "case G timeout stderr" "launch-review.sh: --timeout must be >= 1" "$ERR_G_TIMEOUT"
assert_no_artifacts "case G timeout no side effects" "$OUT_G_TIMEOUT"

# Case G2 (FINDING_4 of /review round 1): zero-padded timeout must be rejected
# before side effects, matching launch-cursor-implement.sh floor semantics.
# floor semantics. The legacy `case … '0' …` filter only rejected literal '0';
# `00` and `000` slipped through and triggered side effects + a synthetic .done.
for bad_timeout in 00 000; do
    OUT_G_PAD="$TMPDIR/cursor-g-pad-${bad_timeout}.txt"
    ERR_G_PAD="$TMPDIR/case-g-pad-${bad_timeout}.stderr"
    set +e
    "$LAUNCHER" --output "$OUT_G_PAD" --timeout "$bad_timeout" --prompt "x" >/dev/null 2>"$ERR_G_PAD"
    CODE_G_PAD=$?
    set -e
    assert_equals "case G2 (timeout=$bad_timeout) exit" "2" "$CODE_G_PAD"
    assert_grep "case G2 (timeout=$bad_timeout) stderr" "launch-review.sh: --timeout must be >= 1" "$ERR_G_PAD"
    assert_no_artifacts "case G2 (timeout=$bad_timeout) no side effects" "$OUT_G_PAD"
done

# Case H (FINDING_3 of /review round 1): stale ${OUTPUT}.json from a prior run
# must NOT be reused if the current run's cp into .json fails. The launcher
# clears any prior .json before the cp; on cp success the post-processing block
# runs normally. We verify the pre-cp clear by pre-staging a stale .json and
# confirming its bytes do NOT survive into the current run's $OUTPUT after a
# successful cp + extract.
OUT_H="$TMPDIR/cursor-h.txt"
# Pre-stage a stale .json from a fictitious prior run.
printf '{"result":"STALE-PRIOR-RUN","usage":{"inputTokens":999}}' > "${OUT_H}.json"
PATH="$STUB_BIN:$PATH" "$LAUNCHER" --output "$OUT_H" --timeout 5 --prompt "case h" >/dev/null 2>"$TMPDIR/case-h.stderr"
# After a successful run, $OUTPUT must contain the CURRENT run's extracted
# .result, never the stale prior-run .result. The cursor stub's output and
# resulting extracted prose must not be the stale literal.
if grep -q 'STALE-PRIOR-RUN' "$OUT_H"; then
    fail "case H stale prior-run .json bytes leaked into \$OUTPUT"
else
    pass
fi
# The .json sidecar should now reflect the CURRENT run, not the stale bytes.
if grep -q 'STALE-PRIOR-RUN' "${OUT_H}.json"; then
    fail "case H stale prior-run .json was not cleared"
else
    pass
fi

# Case AK1 (issue #1358): with CURSOR_API_KEY set, --api-key + value appear as
# adjacent tokens in stub argv, AND the persisted CMD_JSON in ${OUTPUT}.meta
# DOES contain the literal key (no redaction — pins FINDING_1's no-redact
# disposition so retry argv reconstruction stays correct).
OUT_AK1="$TMPDIR/cursor-ak1.txt"
ARGV_LOG_AK1="$TMPDIR/cursor-ak1-argv.log"
cat > "$STUB_BIN/cursor-argv-stub" <<'AKSTUB'
#!/usr/bin/env bash
set -euo pipefail
: "${CURSOR_STUB_ARGV_LOG:?}"
for arg in "$@"; do printf '%s\n' "$arg" >> "$CURSOR_STUB_ARGV_LOG"; done
printf '{"result":"AK1 OK","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}\n'
AKSTUB
chmod +x "$STUB_BIN/cursor-argv-stub"
# Re-point `cursor` to the argv-recording stub for this case only.
ln -sf "$STUB_BIN/cursor-argv-stub" "$STUB_BIN/cursor"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="ak1-test-key-789" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK1" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$OUT_AK1" --timeout 5 --prompt "case ak1" >/dev/null 2>"$TMPDIR/case-ak1.stderr"

AK1_KEY_LINE=$(grep -Fxn -- '--api-key' "$ARGV_LOG_AK1" | awk -F: 'NR==1 {print $1; exit}')
AK1_VAL_LINE=$(grep -Fxn -- 'ak1-test-key-789' "$ARGV_LOG_AK1" | awk -F: 'NR==1 {print $1; exit}')
if [[ -n "$AK1_KEY_LINE" && -n "$AK1_VAL_LINE" ]] && (( AK1_VAL_LINE == AK1_KEY_LINE + 1 )); then
    pass
else
    fail "case AK1 --api-key and value must be adjacent in argv when CURSOR_API_KEY set; key_line=$AK1_KEY_LINE val_line=$AK1_VAL_LINE"
fi

# CMD_JSON in .meta MUST contain the literal key (no redaction).
if grep -F 'CMD_JSON=' "${OUT_AK1}.meta" 2>/dev/null | grep -Fq 'ak1-test-key-789'; then
    pass
else
    fail "case AK1 CMD_JSON in .meta must contain the literal key (no redaction)"
fi

# Issue #1529: Cursor review argv carries the read-only flag set --mode plan,
# --trust is preserved, --force and --sandbox enabled are gone (#1583).
if grep -Fxq -- '--mode' "$ARGV_LOG_AK1" && grep -Fxq -- 'plan' "$ARGV_LOG_AK1"; then
    AK1_MODE_LINE=$(grep -Fxn -- '--mode' "$ARGV_LOG_AK1" | awk -F: 'NR==1 {print $1; exit}')
    AK1_PLAN_LINE=$(grep -Fxn -- 'plan' "$ARGV_LOG_AK1" | awk -F: 'NR==1 {print $1; exit}')
    if [[ -n "$AK1_MODE_LINE" && -n "$AK1_PLAN_LINE" ]] && (( AK1_PLAN_LINE == AK1_MODE_LINE + 1 )); then
        pass
    else
        fail "issue #1529 --mode and plan must be adjacent argv tokens; mode_line=$AK1_MODE_LINE plan_line=$AK1_PLAN_LINE"
    fi
else
    fail "issue #1529 Cursor argv must include --mode plan (read-only)"
fi
if grep -Fxq -- '--sandbox' "$ARGV_LOG_AK1"; then
    fail "issue #1583 Cursor argv must NOT include --sandbox (sandbox never passed by default)"
else
    pass
fi
if grep -Fxq -- '--trust' "$ARGV_LOG_AK1"; then
    pass
else
    fail "issue #1529 Cursor argv must still include --trust for headless --print"
fi
if grep -Fxq -- '--force' "$ARGV_LOG_AK1"; then
    fail "issue #1529 Cursor argv must NOT include --force under the read-only contract"
else
    pass
fi

# Issue #1529: empty-output retry idempotency. The OUTPUT.prompt sidecar
# is the user-original; replaying via --prompt-file pointing at that sidecar
# must produce an argv with EXACTLY ONE preamble. Catches a regression where
# the launcher would also write the preamble into the sidecar.
ARGV_LOG_AK1_RETRY="$TMPDIR/cursor-ak1-retry-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="ak1-test-key-789" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK1_RETRY" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$TMPDIR/cursor-ak1-retry.txt" --timeout 5 --prompt-file "${OUT_AK1}.prompt" >/dev/null 2>"$TMPDIR/case-ak1-retry.stderr"
AK1_PREAMBLE_COUNT_RETRY=$(grep -Fc -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_LOG_AK1_RETRY" || true)
if [[ "$AK1_PREAMBLE_COUNT_RETRY" == "1" ]]; then
    pass
else
    fail "issue #1529 cursor retry-replay via --prompt-file must produce exactly 1 preamble in argv; got $AK1_PREAMBLE_COUNT_RETRY"
fi
# Issue #1529: the preamble is applied to the actual cursor argv (last token,
# the wrapped prompt) — NOT to the OUTPUT.prompt sidecar (which stays user-
# original so collect-agent-results.sh empty-output retry can replay via
# --prompt-file without double-prepending the preamble). Verify the argv log
# carries the preamble and the sidecar does not.
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_LOG_AK1"; then
    pass
else
    fail "issue #1529 cursor argv must carry the HARD CONSTRAINTS preamble"
fi
if grep -Fq -- 'Do not create, edit, delete, or overwrite files, and do not run mutating shell or git commands.' "$ARGV_LOG_AK1"; then
    pass
else
    fail "cursor argv preamble must carry compact explicit mutation prohibition"
fi
if grep -Fq -- 'The launcher passes --mode plan to the cursor CLI' "$ARGV_LOG_AK1"; then
    pass
else
    fail "issue #1583 preamble in argv must reference --mode plan enforcement"
fi
if grep -Fq -- 'HARD CONSTRAINTS' "${OUT_AK1}.prompt"; then
    fail "issue #1529 OUTPUT.prompt sidecar must NOT contain the preamble (retry-replay safety)"
else
    pass
fi
# Case AK1 sidecar = user-original prompt verbatim ("case ak1").
if [[ "$(cat "${OUT_AK1}.prompt")" == "case ak1" ]]; then
    pass
else
    fail "issue #1529 OUTPUT.prompt sidecar must equal the user-original prompt"
fi

# Case AK1S: specialist --agent-file mode renders the agent body before the
# hardening preamble is applied, stores only that rendered body in the prompt
# sidecar, and replaying the sidecar via --prompt-file produces exactly one
# preamble.
OUT_AK1S="$TMPDIR/cursor-ak1s.txt"
ARGV_LOG_AK1S="$TMPDIR/cursor-ak1s-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="ak1-test-key-789" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK1S" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$OUT_AK1S" --timeout 5 \
        --agent-file "$REPO_ROOT/agents/reviewer-structure.md" --mode diff \
        >/dev/null 2>"$TMPDIR/case-ak1s.stderr"
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_LOG_AK1S"; then
    pass
else
    fail "case AK1S specialist argv must carry the HARD CONSTRAINTS preamble"
fi
if grep -Fq -- 'Structure, KISS, and Maintainability' "${OUT_AK1S}.prompt"; then
    pass
else
    fail "case AK1S prompt sidecar must contain specialist-rendered body"
fi
if grep -Fq -- 'HARD CONSTRAINTS' "${OUT_AK1S}.prompt"; then
    fail "case AK1S prompt sidecar must NOT contain the hardening preamble"
else
    pass
fi
ARGV_LOG_AK1S_RETRY="$TMPDIR/cursor-ak1s-retry-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="ak1-test-key-789" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK1S_RETRY" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$TMPDIR/cursor-ak1s-retry.txt" --timeout 5 \
        --prompt-file "${OUT_AK1S}.prompt" >/dev/null 2>"$TMPDIR/case-ak1s-retry.stderr"
AK1S_PREAMBLE_COUNT_RETRY=$(grep -Fc -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_LOG_AK1S_RETRY" || true)
if [[ "$AK1S_PREAMBLE_COUNT_RETRY" == "1" ]]; then
    pass
else
    fail "case AK1S specialist replay via --prompt-file must produce exactly 1 preamble in argv; got $AK1S_PREAMBLE_COUNT_RETRY"
fi

# Case AK1B (issue #1583): LARCH_CURSOR_SANDBOX is now a no-op; the env var
# is ignored and the launcher never passes --sandbox regardless of its value.
OUT_AK1B="$TMPDIR/cursor-ak1b.txt"
ARGV_LOG_AK1B="$TMPDIR/cursor-ak1b-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="ak1-test-key-789" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK1B" \
    LARCH_CURSOR_SANDBOX=disabled \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$OUT_AK1B" --timeout 5 --prompt "case ak1b" >/dev/null 2>"$TMPDIR/case-ak1b.stderr"

if grep -Fxq -- '--mode' "$ARGV_LOG_AK1B" && grep -Fxq -- 'plan' "$ARGV_LOG_AK1B"; then
    pass
else
    fail "issue #1583 Cursor argv must still include --mode plan even when LARCH_CURSOR_SANDBOX=disabled"
fi
if grep -Fxq -- '--sandbox' "$ARGV_LOG_AK1B"; then
    fail "issue #1583 Cursor argv must NOT include --sandbox even when LARCH_CURSOR_SANDBOX=disabled"
else
    pass
fi
if grep -Fxq -- '--trust' "$ARGV_LOG_AK1B"; then
    pass
else
    fail "issue #1583 Cursor argv must still include --trust when LARCH_CURSOR_SANDBOX=disabled"
fi
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_LOG_AK1B"; then
    pass
else
    fail "issue #1583 Cursor argv must still carry the HARD CONSTRAINTS preamble when LARCH_CURSOR_SANDBOX=disabled"
fi
if grep -Fq -- 'rejected by the sandbox' "$ARGV_LOG_AK1B"; then
    fail "issue #1583 preamble MUST NOT claim writes are rejected by the sandbox"
else
    pass
fi

# Case AK1C (issue #1583): an unrecognized LARCH_CURSOR_SANDBOX value is now
# silently ignored — no warning emitted, no sandbox in argv.
OUT_AK1C="$TMPDIR/cursor-ak1c.txt"
ARGV_LOG_AK1C="$TMPDIR/cursor-ak1c-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="ak1-test-key-789" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK1C" \
    LARCH_CURSOR_SANDBOX=bogus \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$OUT_AK1C" --timeout 5 --prompt "case ak1c" >/dev/null 2>"$TMPDIR/case-ak1c.stderr"
if grep -Fxq -- '--sandbox' "$ARGV_LOG_AK1C"; then
    fail "issue #1583 unrecognized LARCH_CURSOR_SANDBOX must NOT produce --sandbox in argv"
else
    pass
fi
if grep -Fq -- 'LARCH_CURSOR_SANDBOX=bogus not recognized' "$TMPDIR/case-ak1c.stderr"; then
    fail "issue #1583 launcher must NOT emit a LARCH_CURSOR_SANDBOX warning (env var is ignored)"
else
    pass
fi

# Case AK2 (issue #1358): with CURSOR_API_KEY empty, --api-key MUST NOT appear
# in argv. Restore the standard stub for default cases later if any.
OUT_AK2="$TMPDIR/cursor-ak2.txt"
ARGV_LOG_AK2="$TMPDIR/cursor-ak2-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="" \
    CURSOR_STUB_ARGV_LOG="$ARGV_LOG_AK2" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$OUT_AK2" --timeout 5 --prompt "case ak2" >/dev/null 2>"$TMPDIR/case-ak2.stderr"
if grep -Fxq -- '--api-key' "$ARGV_LOG_AK2"; then
    fail "case AK2 Cursor argv must not include --api-key when CURSOR_API_KEY empty"
else
    pass
fi

# Case AK3 (issue #1358): on Darwin (test-mode injected) with CURSOR_API_KEY
# empty AND injected security RC=1, the launcher synthesizes ${OUTPUT}.done,
# ${OUTPUT}.diag (STATUS=FAILED + cursor-auth-preflight FAILURE_REASON), and
# a stub ${OUTPUT}.meta — so collect-agent-results.sh sees the actionable
# failure within seconds rather than SENTINEL_TIMEOUT.
OUT_AK3="$TMPDIR/cursor-ak3.txt"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC=1 \
    "$LAUNCHER" --output "$OUT_AK3" --timeout 5 --prompt "case ak3" >/dev/null 2>"$TMPDIR/case-ak3.stderr" || true
if [[ -f "${OUT_AK3}.done" ]] && [[ -s "${OUT_AK3}.diag" ]] \
   && grep -Fq 'STATUS=FAILED' "${OUT_AK3}.diag" \
   && grep -Fq 'FAILURE_REASON=cursor-auth-preflight' "${OUT_AK3}.diag"; then
    pass
else
    fail "case AK3 preflight failure must synthesize .done + .diag with STATUS=FAILED + cursor-auth-preflight; .done=$(test -f "${OUT_AK3}.done" && echo present || echo missing) diag=$(cat "${OUT_AK3}.diag" 2>/dev/null)"
fi
if [[ -s "${OUT_AK3}.meta" ]] && grep -Fq 'CMD_JSON=[]' "${OUT_AK3}.meta"; then
    pass
else
    fail "case AK3 preflight failure must synthesize stub .meta with empty CMD_JSON"
fi
if [[ -s "${OUT_AK3}.dirty-tree" ]] \
   && grep -Fq 'STATUS=unknown' "${OUT_AK3}.dirty-tree" \
   && grep -Fq 'REASON=preflight-short-circuit-no-agent-ran' "${OUT_AK3}.dirty-tree"; then
    pass
else
    fail "case AK3 preflight failure must synthesize unknown dirty-tree sidecar (no detector ran; consumers must route to recovery-safe handling, not treat as launcher-proven clean)"
fi

# Case TM (review FINDING_10): the EXIT trap MUST emit a vendor timing
# row to the ledger pointed at by LARCH_TIMING_LEDGER. Without this
# coverage the trap could regress silently — structural prose pins on
# SKILL.md (test-implement-structure.sh assertion 28) do not exercise
# the runtime trap path.
OUT_TM="$TMPDIR/cursor-tm.txt"
TM_LEDGER="$TMPDIR/timing-ledger.tsv"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_TIMING_LEDGER="$TM_LEDGER" \
    LARCH_TIMING_TASK_KIND=cursor-review \
    "$LAUNCHER" --output "$OUT_TM" --timeout 5 --prompt "case tm" >/dev/null 2>"$TMPDIR/case-tm.stderr"
set -e
if [[ -f "$TM_LEDGER" ]]; then
    pass
else
    fail "case TM timing ledger was not written by the EXIT trap"
fi
if [[ -f "$TM_LEDGER" ]] && grep -E "^v1"$'\t'"vendor"$'\t'"[0-9]+"$'\t'"[^"$'\t'"]+"$'\t'"-"$'\t'"cursor"$'\t'"cursor-review"$'\t' "$TM_LEDGER" >/dev/null; then
    pass
else
    fail "case TM ledger missing v1\\tvendor\\t…\\tcursor\\tcursor-review row"
fi
# The output column should be basename only (no leading path components).
if [[ -f "$TM_LEDGER" ]] && awk -F'\t' '$2 == "vendor" { print $11 }' "$TM_LEDGER" | grep -q '^/'; then
    fail "case TM ledger leaked an absolute output path into the basename column"
else
    pass
fi

OUT_TM_ENV="$TMPDIR/cursor-tm-env.txt"
TM_ENV_LEDGER="$TMPDIR/timing-ledger-env.tsv"
set +e
PATH="$STUB_BIN:$PATH" \
    LARCH_TIMING_LEDGER="$TM_ENV_LEDGER" \
    LARCH_TIMING_TASK_KIND="--prompt" \
    "$LAUNCHER" --output "$OUT_TM_ENV" --timeout 5 --prompt "case tm env" >/dev/null 2>"$TMPDIR/case-tm-env.stderr"
set -e
if [[ -f "$TM_ENV_LEDGER" ]] && grep -E "^v1"$'\t'"vendor"$'\t'"[0-9]+"$'\t'"[^"$'\t'"]+"$'\t'"-"$'\t'"cursor"$'\t'"cursor-review"$'\t' "$TM_ENV_LEDGER" >/dev/null; then
    pass
else
    fail "case TM env ledger missing fallback cursor-review row; ledger=$(cat "$TM_ENV_LEDGER" 2>/dev/null)"
fi
if [[ -f "$TM_ENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" { print $7 }' "$TM_ENV_LEDGER" | grep -Fxq -- '--prompt'; then
    fail "case TM env leaked --prompt task-kind into timing ledger"
else
    pass
fi

# Issue #1480 Bug #2: defensive `--timing-task-kind` validation. Empty or
# flag-like values must be rejected with exit 2 and a clear message.
set +e
"$LAUNCHER" --output "$TMPDIR/bad-empty-tk.txt" --timeout 5 --timing-task-kind "" --prompt "x" >/dev/null 2>"$TMPDIR/bad-empty-tk.stderr"
RC=$?
set -e
assert_equals "empty timing-task-kind exit" "2" "$RC"
assert_grep "empty timing-task-kind message" "non-empty, non-flag-like value" "$TMPDIR/bad-empty-tk.stderr"

set +e
"$LAUNCHER" --output "$TMPDIR/bad-flaglike-tk.txt" --timeout 5 --timing-task-kind --prompt "x" >/dev/null 2>"$TMPDIR/bad-flaglike-tk.stderr"
RC=$?
set -e
assert_equals "flag-like timing-task-kind exit" "2" "$RC"
assert_grep "flag-like timing-task-kind message" "non-empty, non-flag-like value" "$TMPDIR/bad-flaglike-tk.stderr"

# --token-budget-cap argv validation
set +e
"$LAUNCHER" --output "$TMPDIR/budget-missing.txt" --timeout 5 --prompt "x" \
    --token-budget-cap >/dev/null 2>"$TMPDIR/budget-missing.stderr"
RC=$?
set -e
assert_equals "token-budget-cap missing value exit" "2" "$RC"
assert_grep "token-budget-cap missing value message" "positive integer" "$TMPDIR/budget-missing.stderr"

for bad_cap in 0 00 000 abc 0.5 -1; do
    set +e
    "$LAUNCHER" --output "$TMPDIR/budget-bad-${bad_cap//[^a-zA-Z0-9_-]/x}.txt" --timeout 5 --prompt "x" \
        --token-budget-cap "$bad_cap" >/dev/null 2>"$TMPDIR/budget-bad-${bad_cap//[^a-zA-Z0-9_-]/x}.stderr"
    RC=$?
    set -e
    assert_equals "token-budget-cap bad value '$bad_cap' exit" "2" "$RC"
    assert_grep "token-budget-cap bad value '$bad_cap' message" "positive integer" "$TMPDIR/budget-bad-${bad_cap//[^a-zA-Z0-9_-]/x}.stderr"
done

# Accept path: flag recognized (not "unknown flag"), binary absence or other
# required-flag errors cause non-0 exit from later checks.
# PATH stub prevents the launcher from invoking the real cursor CLI on dev Macs.
# USER override gives this test a private serial-lock path so parallel clone
# sessions running the same harness do not queue on /tmp/larch-cursor-serial-${USER}.lock.
set +e
PATH="$STUB_BIN:$PATH" USER="larch-test-budget-accept-cursor-$$" \
    "$LAUNCHER" --output "$TMPDIR/budget-accept.txt" --timeout 5 --prompt "x" \
    --token-budget-cap 9999999 >/dev/null 2>"$TMPDIR/budget-accept.stderr"
set -e
if grep -Fq "unknown flag: --token-budget-cap" "$TMPDIR/budget-accept.stderr" 2>/dev/null; then
    fail "token-budget-cap flag not recognized (got 'unknown flag' rejection)"
else
    pass
fi

# --diff-file accept path: flag recognized (not "unknown flag").
# PATH stub prevents the launcher from invoking the real cursor CLI on dev Macs.
# USER override gives this test a private serial-lock path so parallel clone
# sessions running the same harness do not queue on /tmp/larch-cursor-serial-${USER}.lock.
set +e
PATH="$STUB_BIN:$PATH" USER="larch-test-diff-file-accept-cursor-$$" \
    "$LAUNCHER" --output "$TMPDIR/diff-file-accept.txt" --timeout 5 --prompt "x" \
    --diff-file "/nonexistent/branch.diff" >/dev/null 2>"$TMPDIR/diff-file-accept.stderr"
set -e
if grep -Fq "unknown flag: --diff-file" "$TMPDIR/diff-file-accept.stderr" 2>/dev/null; then
    fail "--diff-file flag not recognized by launch-review.sh --tool cursor (got 'unknown flag' rejection)"
else
    pass
fi

# --diff-file specialist integration: when --agent-file + --diff-file are combined,
# the rendered prompt references the diff file path and omits the 'git diff $(git merge-base HEAD main)...HEAD' instruction.
DF_TMPFILE="$TMPDIR/test-branch.diff"
printf 'diff --git a/foo.sh b/foo.sh\n--- a/foo.sh\n+++ b/foo.sh\n@@ -1 +1 @@\n-old\n+new\n' > "$DF_TMPFILE"
OUT_DF="$TMPDIR/cursor-diff-file-specialist.txt"
ARGV_DF="$TMPDIR/cursor-diff-file-specialist-argv.log"
PATH="$STUB_BIN:$PATH" \
    CURSOR_API_KEY="df-test-key" \
    CURSOR_STUB_ARGV_LOG="$ARGV_DF" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
    "$LAUNCHER" --output "$OUT_DF" --timeout 5 \
        --agent-file "$REPO_ROOT/agents/reviewer-structure.md" \
        --mode diff \
        --diff-file "$DF_TMPFILE" \
        >/dev/null 2>"$TMPDIR/diff-file-specialist.stderr"
if grep -Fq -- "$DF_TMPFILE" "$ARGV_DF" 2>/dev/null; then
    pass
else
    fail "--diff-file specialist: diff file path must appear in rendered prompt argv"
fi
# shellcheck disable=SC2016
if grep -Fq -- 'git diff $(git merge-base HEAD main)...HEAD' "$ARGV_DF" 2>/dev/null; then
    fail "--diff-file specialist: 'git diff \$(git merge-base HEAD main)...HEAD' must NOT appear when --diff-file is set"
else
    pass
fi

# Cap-hit path: when LARCH_TOKEN_BUDGET_CAP_REVIEW=1 and the token ledger
# shows vendor spend >= 1, the launcher writes STATUS=cap_hit to the output
# file and exits 0 without invoking the underlying Cursor binary.
CH_SESSION="cap-hit-cursor-review-$$-$RANDOM"
CH_LEDGER="$TMPDIR/cap-hit-cursor-review-ledger.jsonl"
printf '{"type":"vendor","vendor":"cursor","total":9999}\n' > "$CH_LEDGER"

CH_OUTPUT="$TMPDIR/cap-hit-cursor-review.txt"
CH_PID_FILE="$TMPDIR/cap-hit-cursor-pid.txt"

PATH="$STUB_BIN:$PATH" \
    CURSOR_STUB_PID_FILE="$CH_PID_FILE" \
    LARCH_TOKEN_LEDGER="$CH_LEDGER" \
    LARCH_TOKEN_SESSION_ID="$CH_SESSION" \
    LARCH_TOKEN_BUDGET_CAP_REVIEW=1 \
    "$LAUNCHER" --output "$CH_OUTPUT" --timeout 5 --prompt "cap hit review" >/dev/null 2>&1
rm -f "$CH_LEDGER"

if [[ -f "$CH_OUTPUT" ]] && [[ "$(head -1 "$CH_OUTPUT")" == "STATUS=cap_hit" ]]; then
    pass
else
    fail "cap-hit output first line must be STATUS=cap_hit; got: $(head -1 "$CH_OUTPUT" 2>/dev/null)"
fi
if [[ ! -f "$CH_PID_FILE" ]]; then
    pass
else
    fail "cap-hit path must not invoke the underlying Cursor binary (pid file written)"
fi

# ── Serial lock regression (issue #1960) ──────────────────────────────────────
# cursor reads cursor-user/cursor-access-token from the macOS keychain at
# startup even when --api-key is provided; 5 parallel launchers race that read
# and some fail (exit 1, ~10s). The fix serializes cursor starts via a
# POSIX-atomic mkdir lock. These cases use LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME
# to exercise the Darwin path on any OS.
IMPLEMENT_TMPDIR_SL="$TMPDIR/implement-sl"
mkdir -p "$IMPLEMENT_TMPDIR_SL"
SERIAL_LOCK_USER="larch-test-sl-$$"
SERIAL_LOCK_PATH="/tmp/larch-cursor-serial-${SERIAL_LOCK_USER}.lock"
rm -rf "$SERIAL_LOCK_PATH"

# Restore a minimal cursor stub that produces valid JSON output.
cat > "$STUB_BIN/cursor-sl" <<'STUB_SL'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${CURSOR_STUB_DELAY:-}" ]]; then sleep "$CURSOR_STUB_DELAY"; fi
printf '{"result":"SL OK","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}\n'
STUB_SL
chmod +x "$STUB_BIN/cursor-sl"
ln -sf "$STUB_BIN/cursor-sl" "$STUB_BIN/cursor"

# Case SL-parallel: two concurrent launchers with FORCE_UNAME=Darwin and
# DELAY=0 (lock released immediately) both complete successfully — neither
# permanently blocks the other.
OUT_SL_A="$TMPDIR/cursor-sl-a.txt"
OUT_SL_B="$TMPDIR/cursor-sl-b.txt"
set +e
(PATH="$STUB_BIN:$PATH" \
    USER="$SERIAL_LOCK_USER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_SL" \
    "$LAUNCHER" --output "$OUT_SL_A" --timeout 10 --prompt "sl-a" >/dev/null 2>&1) &
PID_SL_A=$!
(PATH="$STUB_BIN:$PATH" \
    USER="$SERIAL_LOCK_USER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_SL" \
    "$LAUNCHER" --output "$OUT_SL_B" --timeout 10 --prompt "sl-b" >/dev/null 2>&1) &
PID_SL_B=$!
wait "$PID_SL_A"; RC_SL_A=$?
wait "$PID_SL_B"; RC_SL_B=$?
set -e
assert_equals "SL-parallel launcher A completes (exit 0)" "0" "$RC_SL_A"
assert_equals "SL-parallel launcher B completes (exit 0)" "0" "$RC_SL_B"
# Lock dir must be gone after both launchers complete (DELAY=0 releases immediately post-spawn).
if [[ -d "$SERIAL_LOCK_PATH" ]]; then
    fail "SL-parallel: lock dir still present after both launchers completed"
else
    pass
fi

# Case SL-failopen: when the lock directory pre-exists (simulates a crashed
# prior run leaving a stale lock) and LARCH_EXTERNAL_SERIAL_LOCK_TRIES=1 caps
# the wait, the launcher fails open and still runs the cursor process.
IMPLEMENT_TMPDIR_SL2="$TMPDIR/implement-sl2"
mkdir -p "$IMPLEMENT_TMPDIR_SL2"
STALE_LOCK_SL="/tmp/larch-cursor-serial-${SERIAL_LOCK_USER}-stale.lock"
rm -rf "$STALE_LOCK_SL"
mkdir "$STALE_LOCK_SL"
OUT_SL2="$TMPDIR/cursor-sl2.txt"
set +e
PATH="$STUB_BIN:$PATH" \
    USER="${SERIAL_LOCK_USER}-stale" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_TRIES=1 \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_SL2" \
    "$LAUNCHER" --output "$OUT_SL2" --timeout 10 --prompt "sl-failopen" >/dev/null 2>&1
RC_SL2=$?
set -e
assert_equals "SL-failopen exits 0 when lock stuck (TRIES=1)" "0" "$RC_SL2"
rmdir "$STALE_LOCK_SL"

# Case SL-stale-recovery: an old global lock directory is removed and
# re-acquired instead of forcing every caller through the fail-open path.
STALE_RECOVERY_USER="${SERIAL_LOCK_USER}-recover"
STALE_RECOVERY_LOCK="/tmp/larch-cursor-serial-${STALE_RECOVERY_USER}.lock"
rm -rf "$STALE_RECOVERY_LOCK"
mkdir "$STALE_RECOVERY_LOCK"
touch -t 200001010000 "$STALE_RECOVERY_LOCK"
_RECOVERED_LOCK=""
USER="$STALE_RECOVERY_USER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_TTL=1 \
    bash -c 'source "$1"; external_serial_lock_acquire _RECOVERED_LOCK cursor; printf "%s" "$_RECOVERED_LOCK"' \
    bash "$REPO_ROOT/scripts/lib-external-launcher-common.sh" > "$TMPDIR/stale-recovered-lock.txt"
if [[ "$(cat "$TMPDIR/stale-recovered-lock.txt")" == "$STALE_RECOVERY_LOCK" ]]; then
    pass
else
    fail "SL-stale-recovery: expected helper to recover stale lock, got $(cat "$TMPDIR/stale-recovered-lock.txt" 2>/dev/null)"
fi
rmdir "$STALE_RECOVERY_LOCK" 2>/dev/null || true

# Case SL-noop-linux: on non-Darwin (simulated via FORCE_UNAME=Linux), no lock
# directory is created in IMPLEMENT_TMPDIR even when it is set.
IMPLEMENT_TMPDIR_SL3="$TMPDIR/implement-sl3"
mkdir -p "$IMPLEMENT_TMPDIR_SL3"
OUT_SL3="$TMPDIR/cursor-sl3.txt"
PATH="$STUB_BIN:$PATH" \
    USER="${SERIAL_LOCK_USER}-linux" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Linux \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_SL3" \
    "$LAUNCHER" --output "$OUT_SL3" --timeout 10 --prompt "sl-noop-linux" >/dev/null 2>"$TMPDIR/case-sl3.stderr"
if [[ -d "/tmp/larch-cursor-serial-${SERIAL_LOCK_USER}-linux.lock" ]]; then
    fail "SL-noop-linux: serial lock dir must NOT be created on non-Darwin"
else
    pass
fi
rm -rf "$SERIAL_LOCK_PATH" "$STALE_LOCK_SL" "/tmp/larch-cursor-serial-${SERIAL_LOCK_USER}-linux.lock"

# Case SL-auth-retry: a cursor stub that writes the verified auth-error string
# to stderr on the first call and exits 1; exits 0 with valid JSON on the second.
# Assert the launcher retried exactly once (total 2 attempts).
SL_AUTH_COUNT="$TMPDIR/sl-auth-count.txt"
printf '0' > "$SL_AUTH_COUNT"
cat > "$STUB_BIN/cursor-auth-retry" <<STUB_AUTH_RETRY
#!/usr/bin/env bash
count=\$(cat "${SL_AUTH_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_AUTH_COUNT}"
if (( count == 1 )); then
    printf "Error: Password not found for account 'cursor-user' and service 'cursor-access-token'\n" >&2
    exit 1
fi
printf '{"result":"auth-retry OK","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB_AUTH_RETRY
chmod +x "$STUB_BIN/cursor-auth-retry"
ln -sf "$STUB_BIN/cursor-auth-retry" "$STUB_BIN/cursor"
OUT_SL_AUTH="$TMPDIR/cursor-sl-auth.txt"
set +e
USER="${SERIAL_LOCK_USER}-auth" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    LARCH_EXTERNAL_AUTH_RETRIES=2 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_SL_AUTH" --timeout 10 --prompt "sl-auth-retry" >/dev/null 2>&1
RC_SL_AUTH=$?
set -e
assert_equals "SL-auth-retry launcher exits 0 after one retry" "0" "$RC_SL_AUTH"
SL_AUTH_ATTEMPTS=$(cat "$SL_AUTH_COUNT" 2>/dev/null || echo "0")
assert_equals "SL-auth-retry stub invoked exactly 2 times" "2" "$SL_AUTH_ATTEMPTS"
rm -f "$SL_AUTH_COUNT"

# Case SL-no-retry: a cursor stub that writes a non-auth error to stderr and
# exits 1. Assert the launcher does NOT retry (exactly 1 attempt) even when
# LARCH_EXTERNAL_AUTH_RETRIES is high.
SL_NORETRY_COUNT="$TMPDIR/sl-noretry-count.txt"
printf '0' > "$SL_NORETRY_COUNT"
cat > "$STUB_BIN/cursor-no-retry" <<STUB_NO_RETRY
#!/usr/bin/env bash
count=\$(cat "${SL_NORETRY_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_NORETRY_COUNT}"
printf "Error: workspace initialization failed (exit code 1)\n" >&2
exit 1
STUB_NO_RETRY
chmod +x "$STUB_BIN/cursor-no-retry"
ln -sf "$STUB_BIN/cursor-no-retry" "$STUB_BIN/cursor"
OUT_SL_NORETRY="$TMPDIR/cursor-sl-noretry.txt"
set +e
USER="${SERIAL_LOCK_USER}-noretry" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    LARCH_EXTERNAL_AUTH_RETRIES=5 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_SL_NORETRY" --timeout 10 --prompt "sl-no-retry" >/dev/null 2>&1
set -e
SL_NORETRY_ATTEMPTS=$(cat "$SL_NORETRY_COUNT" 2>/dev/null || echo "0")
assert_equals "SL-no-retry stub invoked exactly 1 time (non-auth failures must not retry)" "1" "$SL_NORETRY_ATTEMPTS"
rm -f "$SL_NORETRY_COUNT"

# Case SL-exit45-auth: Cursor can emit the macOS security CLI failure in a
# two-line stderr packet. Assert the launcher treats it as auth and retries.
SL_EXIT45_AUTH_COUNT="$TMPDIR/sl-exit45-auth-count.txt"
printf '0' > "$SL_EXIT45_AUTH_COUNT"
cat > "$STUB_BIN/cursor-exit45-auth" <<STUB_EXIT45_AUTH
#!/usr/bin/env bash
count=\$(cat "${SL_EXIT45_AUTH_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_EXIT45_AUTH_COUNT}"
if (( count == 1 )); then
    printf "Error: Security command failed: Security process exited with code: 45\n" >&2
    printf "Security process exited with code: 45\n" >&2
    exit 1
fi
printf '{"result":"exit45-auth OK","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB_EXIT45_AUTH
chmod +x "$STUB_BIN/cursor-exit45-auth"
ln -sf "$STUB_BIN/cursor-exit45-auth" "$STUB_BIN/cursor"
OUT_SL_EXIT45_AUTH="$TMPDIR/cursor-sl-exit45-auth.txt"
set +e
USER="${SERIAL_LOCK_USER}-exit45-auth" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    LARCH_EXTERNAL_AUTH_RETRIES=2 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_SL_EXIT45_AUTH" --timeout 10 --prompt "sl-exit45-auth" >/dev/null 2>&1
RC_SL_EXIT45_AUTH=$?
set -e
assert_equals "SL-exit45-auth launcher exits 0 after one retry" "0" "$RC_SL_EXIT45_AUTH"
SL_EXIT45_AUTH_ATTEMPTS=$(cat "$SL_EXIT45_AUTH_COUNT" 2>/dev/null || echo "0")
assert_equals "SL-exit45-auth stub invoked exactly 2 times" "2" "$SL_EXIT45_AUTH_ATTEMPTS"
rm -f "$SL_EXIT45_AUTH_COUNT"

# Case SL-security-cmd-failed-auth: the outer wrapper line alone is enough to
# classify the failure as retryable auth.
SL_SECURITY_CMD_FAILED_AUTH_COUNT="$TMPDIR/sl-security-cmd-failed-auth-count.txt"
printf '0' > "$SL_SECURITY_CMD_FAILED_AUTH_COUNT"
cat > "$STUB_BIN/cursor-security-cmd-failed-auth" <<STUB_SECURITY_CMD_FAILED_AUTH
#!/usr/bin/env bash
count=\$(cat "${SL_SECURITY_CMD_FAILED_AUTH_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_SECURITY_CMD_FAILED_AUTH_COUNT}"
if (( count == 1 )); then
    printf "Error: Security command failed: Security process exited with code: 45\n" >&2
    exit 1
fi
printf '{"result":"security-cmd-failed-auth OK","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB_SECURITY_CMD_FAILED_AUTH
chmod +x "$STUB_BIN/cursor-security-cmd-failed-auth"
ln -sf "$STUB_BIN/cursor-security-cmd-failed-auth" "$STUB_BIN/cursor"
OUT_SL_SECURITY_CMD_FAILED_AUTH="$TMPDIR/cursor-sl-security-cmd-failed-auth.txt"
set +e
USER="${SERIAL_LOCK_USER}-security-cmd-failed-auth" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    LARCH_EXTERNAL_AUTH_RETRIES=2 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_SL_SECURITY_CMD_FAILED_AUTH" --timeout 10 --prompt "sl-security-cmd-failed-auth" >/dev/null 2>&1
RC_SL_SECURITY_CMD_FAILED_AUTH=$?
set -e
assert_equals "SL-security-cmd-failed-auth launcher exits 0 after one retry" "0" "$RC_SL_SECURITY_CMD_FAILED_AUTH"
SL_SECURITY_CMD_FAILED_AUTH_ATTEMPTS=$(cat "$SL_SECURITY_CMD_FAILED_AUTH_COUNT" 2>/dev/null || echo "0")
assert_equals "SL-security-cmd-failed-auth stub invoked exactly 2 times" "2" "$SL_SECURITY_CMD_FAILED_AUTH_ATTEMPTS"
rm -f "$SL_SECURITY_CMD_FAILED_AUTH_COUNT"

# Case SL-transient-retry-cursor-8: stub exits 8 with empty sidecar on attempt 1,
# returns valid JSON on attempt 2. Launcher must retry and exit 0.
SL_TRANSIENT_CURSOR8_COUNT="$TMPDIR/sl-transient-cursor8-count.txt"
printf '0' > "$SL_TRANSIENT_CURSOR8_COUNT"
cat > "$STUB_BIN/cursor-transient-8" <<STUB_TRANSIENT_CURSOR8
#!/usr/bin/env bash
count=\$(cat "${SL_TRANSIENT_CURSOR8_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_TRANSIENT_CURSOR8_COUNT}"
if (( count == 1 )); then
    exit 8
fi
printf '{"result":"transient-cursor-8 retry ok","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
STUB_TRANSIENT_CURSOR8
chmod +x "$STUB_BIN/cursor-transient-8"
ln -sf "$STUB_BIN/cursor-transient-8" "$STUB_BIN/cursor"
OUT_TRANSIENT_CURSOR8="$TMPDIR/transient-cursor8.txt"
set +e
USER="${SERIAL_LOCK_USER}-transient8" \
    LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_TRANSIENT_CURSOR8" --timeout 10 --prompt "sl-transient-retry-cursor-8" >/dev/null 2>&1
RC_TRANSIENT_CURSOR8=$?
set -e
assert_equals "SL-transient-retry-cursor-8 exits 0 after transient retry" "0" "$RC_TRANSIENT_CURSOR8"
SL_TRANSIENT_CURSOR8_ATTEMPTS=$(cat "$SL_TRANSIENT_CURSOR8_COUNT" 2>/dev/null || echo "0")
assert_equals "SL-transient-retry-cursor-8 stub invoked exactly 2 times" "2" "$SL_TRANSIENT_CURSOR8_ATTEMPTS"
rm -f "$SL_TRANSIENT_CURSOR8_COUNT"

# Case SL-transient-obs-exhausted-cursor: verify that cursor failure logging
# preserves both auth and transient counters when the transient-retry loop
# exhausts all retries.
SL_OBS_CURSOR_EXHAUSTED_COUNT="$TMPDIR/sl-obs-cursor-exhausted-count.txt"
printf '0' > "$SL_OBS_CURSOR_EXHAUSTED_COUNT"
cat > "$STUB_BIN/cursor-obs-exhausted" <<STUB_OBS_CURSOR_EXHAUSTED
#!/usr/bin/env bash
count=\$(cat "${SL_OBS_CURSOR_EXHAUSTED_COUNT}" 2>/dev/null || echo 0)
count=\$((count + 1))
printf '%s' "\$count" > "${SL_OBS_CURSOR_EXHAUSTED_COUNT}"
printf 'cursor transient failure attempt %s\n' "\$count" >&2
exit 8
STUB_OBS_CURSOR_EXHAUSTED
chmod +x "$STUB_BIN/cursor-obs-exhausted"
ln -sf "$STUB_BIN/cursor-obs-exhausted" "$STUB_BIN/cursor"
IMPL_TMPDIR_OBS_CURSOR_EXHAUSTED="$TMPDIR/obs-cursor-exhausted-impl"
mkdir -p "$IMPL_TMPDIR_OBS_CURSOR_EXHAUSTED"
OUT_OBS_CURSOR_EXHAUSTED="$TMPDIR/obs-cursor-exhausted.txt"
set +e
USER="${SERIAL_LOCK_USER}-obs-cursor-exhausted" \
    LARCH_TRANSIENT_RETRY_DELAY=0 \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=0 \
    IMPLEMENT_TMPDIR="$IMPL_TMPDIR_OBS_CURSOR_EXHAUSTED" \
    PATH="$STUB_BIN:$PATH" \
    "$LAUNCHER" --output "$OUT_OBS_CURSOR_EXHAUSTED" --timeout 10 --prompt "sl-transient-obs-exhausted-cursor" >/dev/null 2>&1
RC_OBS_CURSOR_EXHAUSTED=$?
set -e
assert_equals "SL-transient-obs-exhausted-cursor exits non-zero after exhausting retries" "8" "$RC_OBS_CURSOR_EXHAUSTED"
SL_OBS_CURSOR_EXHAUSTED_ATTEMPTS=$(cat "$SL_OBS_CURSOR_EXHAUSTED_COUNT" 2>/dev/null || echo "0")
assert_equals "SL-transient-obs-exhausted-cursor stub invoked exactly 3 times (2 retries)" "3" "$SL_OBS_CURSOR_EXHAUSTED_ATTEMPTS"
EI_OBS_CURSOR_EXHAUSTED="$IMPL_TMPDIR_OBS_CURSOR_EXHAUSTED/execution-issues.md"
OBS_CURSOR_EXHAUSTED_ENTRY_COUNT=$(grep -Ec '^- \*\*Step review Step 2 — cursor-review failed' "$EI_OBS_CURSOR_EXHAUSTED" 2>/dev/null || echo 0)
assert_equals "SL-transient-obs-exhausted-cursor execution-issues has one failure entry" "1" "$OBS_CURSOR_EXHAUSTED_ENTRY_COUNT"
assert_regex "SL-transient-obs-exhausted-cursor exact retry header" '^-\s\*\*Step review Step 2 — cursor-review failed \(exit 8 — non-auth — auth-retries=1, transient-retries=3\)\*\*:$' "$EI_OBS_CURSOR_EXHAUSTED"
rm -f "$SL_OBS_CURSOR_EXHAUSTED_COUNT"

# Restore normal cursor stub for remaining tests.
ln -sf "$STUB_BIN/cursor-sl" "$STUB_BIN/cursor"

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-launch-review.sh --tool cursor - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-review.sh --tool cursor - %s assertions passed\n' "$PASS"

) || OVERALL_FAIL=1

# --plan-file and --feature-file: flag recognition tests (offline, no vendor launch).
# REPO_ROOT may have been shadowed inside subshell groups above; capture afresh here.
_PLAN_FILE_TESTS_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
_PLAN_FILE_TESTS_LAUNCHER="$_PLAN_FILE_TESTS_ROOT/scripts/launch-review.sh"
_plan_file_tests() {
    local fail=0
    local tmpd
    tmpd=$(mktemp -d /tmp/larch-test-launch-review-plan-XXXXXX)
    trap 'rm -rf "$tmpd"' RETURN

    # Codex and Cursor must not reject --plan-file/--feature-file as "unknown flag"
    # (they will fail for other reasons like missing codex/cursor binary, but the
    # flag parsing must accept them). We check stderr does NOT contain "unknown flag".
    for tool in codex cursor; do
        local pf_stderr
        pf_stderr="$tmpd/${tool}-plan.stderr"
        set +e
        "$_PLAN_FILE_TESTS_LAUNCHER" --tool "$tool" --output "$tmpd/${tool}-p.txt" --timeout 1 \
            --agent-file "$_PLAN_FILE_TESTS_ROOT/agents/reviewer-correctness.md" --mode diff \
            --plan-file "/nonexistent/plan.txt" >/dev/null 2>"$pf_stderr"
        set -e
        if grep -Fq "unknown flag: --plan-file" "$pf_stderr" 2>/dev/null; then
            echo "FAIL: plan-file/feature-file: $tool incorrectly rejects --plan-file as unknown flag" >&2
            fail=1
        fi

        local ff_stderr
        ff_stderr="$tmpd/${tool}-feature.stderr"
        set +e
        "$_PLAN_FILE_TESTS_LAUNCHER" --tool "$tool" --output "$tmpd/${tool}-f.txt" --timeout 1 \
            --agent-file "$_PLAN_FILE_TESTS_ROOT/agents/reviewer-correctness.md" --mode diff \
            --feature-file "/nonexistent/feature.txt" >/dev/null 2>"$ff_stderr"
        set -e
        if grep -Fq "unknown flag: --feature-file" "$ff_stderr" 2>/dev/null; then
            echo "FAIL: plan-file/feature-file: $tool incorrectly rejects --feature-file as unknown flag" >&2
            fail=1
        fi
    done

    if [[ "$fail" -eq 0 ]]; then
        echo "PASS: plan-file/feature-file flag recognition"
    fi
    return "$fail"
}
_plan_file_tests || OVERALL_FAIL=1

# CURSOR_CONFIG_DIR isolation: each parallel cursor invocation must receive a
# distinct private config dir (issue #2022).
_cursor_config_dir_tests() {
    local fail=0
    local tmpd
    tmpd=$(mktemp -d /tmp/larch-test-cursor-cfgdir-XXXXXX)
    trap 'rm -rf "$tmpd"' RETURN

    local stub_bin="$tmpd/bin"
    mkdir -p "$stub_bin"

    # Stub cursor that records its CURSOR_CONFIG_DIR to a caller-specified file.
    cat > "$stub_bin/cursor" <<'CFGSTUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${CURSOR_STUB_CFGDIR_LOG:-}" ]]; then
    printf '%s\n' "${CURSOR_CONFIG_DIR:-UNSET}" >> "$CURSOR_STUB_CFGDIR_LOG"
fi
printf '{"result":"cfg-ok","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\n'
CFGSTUB
    chmod +x "$stub_bin/cursor"

    local launcher="$_PLAN_FILE_TESTS_ROOT/scripts/launch-review.sh"
    local log1="$tmpd/cfgdir-inv1.log"
    local log2="$tmpd/cfgdir-inv2.log"
    local out1="$tmpd/cfgdir-out1.txt"
    local out2="$tmpd/cfgdir-out2.txt"

    # Launch two parallel cursor reviewers with the stub.
    PATH="$stub_bin:$PATH" \
        CURSOR_STUB_CFGDIR_LOG="$log1" \
        LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
        "$launcher" --tool cursor --output "$out1" --timeout 10 --prompt "inv1" \
        >/dev/null 2>"$tmpd/cfgdir-err1.txt" &
    local pid1=$!

    PATH="$stub_bin:$PATH" \
        CURSOR_STUB_CFGDIR_LOG="$log2" \
        LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Linux \
        "$launcher" --tool cursor --output "$out2" --timeout 10 --prompt "inv2" \
        >/dev/null 2>"$tmpd/cfgdir-err2.txt" &
    local pid2=$!

    wait "$pid1" 2>/dev/null || true
    wait "$pid2" 2>/dev/null || true

    local dir1 dir2
    dir1=$(head -1 "$log1" 2>/dev/null || echo "MISSING")
    dir2=$(head -1 "$log2" 2>/dev/null || echo "MISSING")

    # Each invocation must have received a CURSOR_CONFIG_DIR.
    if [[ "$dir1" == "UNSET" || "$dir1" == "MISSING" ]]; then
        echo "FAIL: cursor-config-dir: invocation 1 did not receive CURSOR_CONFIG_DIR" >&2
        fail=1
    fi
    if [[ "$dir2" == "UNSET" || "$dir2" == "MISSING" ]]; then
        echo "FAIL: cursor-config-dir: invocation 2 did not receive CURSOR_CONFIG_DIR" >&2
        fail=1
    fi

    # The two invocations must have received distinct config dirs.
    if [[ "$dir1" == "$dir2" ]]; then
        echo "FAIL: cursor-config-dir: invocations 1 and 2 shared CURSOR_CONFIG_DIR='$dir1'" >&2
        fail=1
    fi

    # Neither dir should equal the shared ~/.cursor path.
    local home_cursor="$HOME/.cursor"
    if [[ "$dir1" == "$home_cursor" || "$dir2" == "$home_cursor" ]]; then
        echo "FAIL: cursor-config-dir: CURSOR_CONFIG_DIR must not equal ~/.cursor (got '$dir1', '$dir2')" >&2
        fail=1
    fi

    if [[ "$fail" -eq 0 ]]; then
        echo "PASS: cursor-config-dir isolation (distinct per-invocation CURSOR_CONFIG_DIR)"
    fi
    return "$fail"
}
_cursor_config_dir_tests || OVERALL_FAIL=1

if [[ "$OVERALL_FAIL" -ne 0 ]]; then
    echo "FAIL: test-launch-review.sh" >&2
    exit 1
fi

echo "PASS: test-launch-review.sh"
