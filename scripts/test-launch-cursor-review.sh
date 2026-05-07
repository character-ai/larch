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
    for suffix in "" ".prompt" ".sidecar" ".done" ".inner.done" ".meta" ".diag" ".json"; do
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
assert_equals "case B prompt sidecar" "original prompt" "$(cat "${OUT_B}.prompt")"

# Case C: --prompt-file preserves trailing newlines through the wrapper prompt.
OUT_C="$TMPDIR/cursor-c.txt"
PROMPT_C="$TMPDIR/cursor-c.prompt"
PROMPT_LOG_C="$TMPDIR/cursor-c.prompt-log"
printf 'line one\n\n' > "$PROMPT_C"
PATH="$STUB_BIN:$PATH" CURSOR_STUB_PROMPT_LOG="$PROMPT_LOG_C" \
    "$LAUNCHER" --output "$OUT_C" --timeout 5 --prompt-file "$PROMPT_C" >/dev/null 2>"$TMPDIR/case-c.stderr"
EXPECTED_C="$TMPDIR/cursor-c.expected"
printf ' /max-mode on. Prompt: line one\n\n' > "$EXPECTED_C"
if cmp -s "$EXPECTED_C" "$PROMPT_LOG_C"; then
    pass
else
    fail "case C wrapped prompt did not preserve trailing newlines"
fi

# Case D: deterministic post-wrapper trap path promotes an existing inner
# sentinel and may leave raw JSON because normal post-processing was interrupted.
OUT_D="$TMPDIR/cursor-d.txt"
set +e
PATH="$STUB_BIN:$PATH" LARCH_TEST_TRAP_AFTER_INNER_DONE='exit 143' \
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
assert_grep "case G timeout stderr" "launch-cursor-review.sh: --timeout must be a positive integer" "$ERR_G_TIMEOUT"
assert_no_artifacts "case G timeout no side effects" "$OUT_G_TIMEOUT"

if [[ "$FAIL" -ne 0 ]]; then
    printf 'FAIL: test-launch-cursor-review.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAIL_DETAILS[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-cursor-review.sh - %s assertions passed\n' "$PASS"
