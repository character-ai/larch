#!/usr/bin/env bash
# Regression test for launch-cursor-review.sh sentinel ownership and retry metadata.
#
# Wired into: make test-launch-cursor-review (Makefile shard test-harnesses-2).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
LAUNCHER="$REPO_ROOT/scripts/launch-cursor-review.sh"
TMPDIR="$(mktemp -d /tmp/larch-test-launch-cursor-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

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
printf '{"result":"%s","usage":{"inputTokens":1,"outputTokens":2,"cacheReadTokens":3,"cacheWriteTokens":4}}\n' "${CURSOR_STUB_RESULT:-POST-PROCESSED OK}"
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
assert_grep "case B outer launcher" "^OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-cursor-review.sh$" "${OUT_B}.meta"
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
assert_grep "case F stderr" "launch-cursor-review.sh: --prompt, --agent-file, and --prompt-file are mutually exclusive" "$ERR_F"
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
assert_grep "case G timeout stderr" "launch-cursor-review.sh: --timeout must be >= 1" "$ERR_G_TIMEOUT"
assert_no_artifacts "case G timeout no side effects" "$OUT_G_TIMEOUT"

# Case G2 (FINDING_4 of /review round 1): zero-padded timeout must be rejected
# before side effects, matching launch-cursor-implement.sh / launch-gemini-review.sh
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
    assert_grep "case G2 (timeout=$bad_timeout) stderr" "launch-cursor-review.sh: --timeout must be >= 1" "$ERR_G_PAD"
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

# Issue #1529: Cursor review argv carries the read-only flag set --mode plan
# + --sandbox enabled, --trust is preserved, and --force is gone.
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
if grep -Fxq -- '--sandbox' "$ARGV_LOG_AK1" && grep -Fxq -- 'enabled' "$ARGV_LOG_AK1"; then
    AK1_SAND_LINE=$(grep -Fxn -- '--sandbox' "$ARGV_LOG_AK1" | awk -F: 'NR==1 {print $1; exit}')
    AK1_ENAB_LINE=$(grep -Fxn -- 'enabled' "$ARGV_LOG_AK1" | awk -F: 'NR==1 {print $1; exit}')
    if [[ -n "$AK1_SAND_LINE" && -n "$AK1_ENAB_LINE" ]] && (( AK1_ENAB_LINE == AK1_SAND_LINE + 1 )); then
        pass
    else
        fail "issue #1529 --sandbox and enabled must be adjacent argv tokens; sandbox_line=$AK1_SAND_LINE enabled_line=$AK1_ENAB_LINE"
    fi
else
    fail "issue #1529 Cursor argv must include --sandbox enabled (override config)"
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
if grep -Fq -- '--mode plan --sandbox enabled' "$ARGV_LOG_AK1"; then
    pass
else
    fail "issue #1529 preamble in argv must reference --mode plan --sandbox enabled"
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

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-launch-cursor-review.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-cursor-review.sh - %s assertions passed\n' "$PASS"
