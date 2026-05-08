#!/usr/bin/env bash
# Offline regression harness for scripts/launch-codex-review.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
LAUNCHER="$REPO_ROOT/scripts/launch-codex-review.sh"
TMPDIR="$(mktemp -d /tmp/larch-test-launch-codex-review-XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

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
cat > "$STUB_BIN/codex" <<'STUB_CODEX'
#!/usr/bin/env bash
set -euo pipefail
: "${CODEX_STUB_ARGV_LOG:?}"
: "${CODEX_STUB_COUNT_FILE:?}"
if [[ -n "${CODEX_STUB_TOKEN_SESSION_FILE:-}" ]]; then
    printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$CODEX_STUB_TOKEN_SESSION_FILE"
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
chmod +x "$STUB_BIN/codex"

OUTDIR_REAL="$TMPDIR/out-real"
mkdir -p "$OUTDIR_REAL"
OUTDIR_LINK="$TMPDIR/out-link"
ln -s "$OUTDIR_REAL" "$OUTDIR_LINK"
OUTPUT="$OUTDIR_LINK/../out-link/review.txt"
ARGV="$TMPDIR/argv.txt"
COUNT="$TMPDIR/count.txt"
TOKEN_SESSION_FILE="$TMPDIR/token-session.txt"
IMPLEMENT_TMPDIR_FIXTURE="$TMPDIR/implement-tmpdir"
mkdir -p "$IMPLEMENT_TMPDIR_FIXTURE"
printf 'mock-codex-review-session\n' > "$IMPLEMENT_TMPDIR_FIXTURE/session-id"
printf 'SOURCE_FILE=/tmp/mock.jsonl\n' > "$IMPLEMENT_TMPDIR_FIXTURE/claude-source.env"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV" \
    CODEX_STUB_COUNT_FILE="$COUNT" \
    CODEX_STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_FILE" \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_FIXTURE" \
    LARCH_TOKEN_SESSION_ID="stale-codex-review-session" \
    LARCH_CODEX_MODEL="stub-model" \
    "$LAUNCHER" --output "$OUTPUT" --timeout 5 --prompt "review prompt" >/dev/null

assert_eq "stub invoked once" "1" "$(cat "$COUNT")"
assert_eq "token session id rehydrated" "mock-codex-review-session" "$(cat "$TOKEN_SESSION_FILE")"
assert_eq "argv 1" "exec" "$(sed -n '1p' "$ARGV")"
assert_eq "argv 2" "--full-auto" "$(sed -n '2p' "$ARGV")"
assert_eq "argv 3" "-C" "$(sed -n '3p' "$ARGV")"
assert_eq "argv 4" "$REPO_ROOT" "$(sed -n '4p' "$ARGV")"
assert_eq "argv 5 add-dir flag" "--add-dir" "$(sed -n '5p' "$ARGV")"
assert_eq "argv 6 canonical output dir" "$(cd "$OUTDIR_REAL" && pwd -P)" "$(sed -n '6p' "$ARGV")"
assert_grep "outer launcher metadata" "OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-codex-review.sh" "${OUTPUT}.meta"
assert_grep "outer prompt metadata" "OUTER_LAUNCHER_PROMPT_FILE=${OUTPUT}.prompt" "${OUTPUT}.meta"
assert_grep "dirty-tree sidecar status" "STATUS=" "${OUTPUT}.dirty-tree"
assert_grep "dirty-tree sidecar mode" "MODE=baseline" "${OUTPUT}.dirty-tree"

if [[ "$(grep -Fxc -- '-m' "$ARGV")" == "1" ]] && grep -Fxq -- 'stub-model' "$ARGV"; then
    pass
else
    fail "model args should include one -m and literal stub-model"
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
if [[ "$RC" -ne 0 ]] && [[ ! -e "$TMPDIR/count-bad.txt" ]] && [[ ! -e "$TMPDIR/bad-model.txt.done" ]]; then
    pass
else
    fail "newline model should fail before invoking codex or producing .done (rc=$RC count=$(cat "$TMPDIR/count-bad.txt" 2>/dev/null))"
fi
assert_grep "newline model diagnostic" "[[:cntrl:]]" "$TMPDIR/bad-model.stderr"
if [[ ! -e "$TMPDIR/bad-model.txt.done" ]]; then
    pass
else
    fail "newline model should not publish public done"
fi

PROMPT_FILE="$TMPDIR/prompt-file.txt"
ARGV_PROMPT_FILE="$TMPDIR/argv-prompt-file.txt"
COUNT_PROMPT_FILE="$TMPDIR/count-prompt-file.txt"
printf 'from prompt file\n\n' > "$PROMPT_FILE"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$ARGV_PROMPT_FILE" \
    CODEX_STUB_COUNT_FILE="$COUNT_PROMPT_FILE" \
    "$LAUNCHER" --output "$TMPDIR/prompt-file-output.txt" --timeout 5 --prompt-file "$PROMPT_FILE" >/dev/null
EXPECTED_PROMPT_ARG="$TMPDIR/expected-prompt-arg.txt"
printf 'from prompt file\n\n' > "$EXPECTED_PROMPT_ARG"
if [[ "$(cat "$COUNT_PROMPT_FILE")" == "1" ]] && cmp -s "$EXPECTED_PROMPT_ARG" "${TMPDIR}/prompt-file-output.txt.prompt"; then
    pass
else
    fail "--prompt-file should preserve prompt bytes and still launch through Codex"
fi

if (( FAIL > 0 )); then
    printf 'FAIL: test-launch-codex-review.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-codex-review.sh - %s assertions passed\n' "$PASS"
