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
assert_grep "outer launcher metadata" "OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-codex-review.sh" "${OUTPUT}.meta"
assert_grep "outer prompt metadata" "OUTER_LAUNCHER_PROMPT_FILE=${OUTPUT}.prompt" "${OUTPUT}.meta"
assert_grep "dirty-tree sidecar status" "STATUS=" "${OUTPUT}.dirty-tree"
assert_grep "dirty-tree sidecar mode" "MODE=baseline" "${OUTPUT}.dirty-tree"
# Issue #1529: the preamble is applied to the outgoing PROMPT (last argv
# token before the closing newline) but NOT to the OUTPUT.prompt sidecar
# (which stays the user-original body so collect-agent-results.sh empty-output
# retry replays via --prompt-file without double-prepending). Argv contains the
# preamble; sidecar does not.
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV"; then
    pass
else
    fail "issue #1529 codex argv must carry the HARD CONSTRAINTS preamble"
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

if [[ "$(grep -Fxc -- '-m' "$ARGV")" == "1" ]] && grep -Fxq -- 'stub-model' "$ARGV"; then
    pass
else
    fail "model args should include one -m and literal stub-model"
fi

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

# Issue #1529: empty-output retry idempotency. The first run wrote
# "review prompt" to ${OUTPUT}.prompt (user-original, no preamble).
# Replaying via --prompt-file pointing at that sidecar must produce an argv
# with EXACTLY ONE preamble — not two. Catches a regression where the
# launcher would also write the preamble into the sidecar (which would make
# the replay double-prepend).
RETRY_OUTPUT="$TMPDIR/retry-output.txt"
RETRY_ARGV="$TMPDIR/retry-argv.txt"
RETRY_COUNT="$TMPDIR/retry-count.txt"
PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$RETRY_ARGV" \
    CODEX_STUB_COUNT_FILE="$RETRY_COUNT" \
    "$LAUNCHER" --output "$RETRY_OUTPUT" --timeout 5 --prompt-file "${OUTPUT}.prompt" >/dev/null
PREAMBLE_COUNT_RETRY=$(grep -Fc -- 'HARD CONSTRAINTS — your role is read-only review' "$RETRY_ARGV" || true)
# `grep -F` per-line: the preamble's first line is on one argv-line because
# the prompt is one shell argv. So count must be exactly 1.
if [[ "$PREAMBLE_COUNT_RETRY" == "1" ]]; then
    pass
else
    fail "retry replay via --prompt-file must produce exactly 1 preamble in argv; got $PREAMBLE_COUNT_RETRY"
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
# Issue #1529: --prompt-file's bytes are preserved verbatim in the sidecar
# (no preamble there — retry-replay safety) and the preamble is applied to
# the outgoing argv only.
EXPECTED_PROMPT_ARG="$TMPDIR/expected-prompt-arg.txt"
printf 'from prompt file\n\n' > "$EXPECTED_PROMPT_ARG"
if cmp -s "$EXPECTED_PROMPT_ARG" "$PROMPT_SIDECAR"; then
    pass
else
    fail "--prompt-file should preserve original bytes verbatim in OUTPUT.prompt sidecar"
fi
if grep -Fq -- 'HARD CONSTRAINTS — your role is read-only review' "$ARGV_PROMPT_FILE"; then
    pass
else
    fail "--prompt-file run must still apply the HARD CONSTRAINTS preamble to the codex argv"
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
    pass
else
    fail "--agent-file run must apply the HARD CONSTRAINTS preamble to the codex argv"
fi
if grep -Fq -- 'Structure, KISS, and Maintainability' "${AGENT_OUTPUT}.prompt"; then
    pass
else
    fail "--agent-file OUTPUT.prompt sidecar must contain specialist-rendered body"
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
if [[ "$AGENT_PREAMBLE_COUNT_RETRY" == "1" ]]; then
    pass
else
    fail "--agent-file replay via --prompt-file must produce exactly 1 preamble in argv; got $AGENT_PREAMBLE_COUNT_RETRY"
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
    LCR_OUT="$TMPDIR/lcr-codex-review-output.txt"
    LCR_ARGV="$TMPDIR/lcr-argv.txt"
    LCR_COUNT="$TMPDIR/lcr-count.txt"
    LCR_STDERR="$TMPDIR/lcr.stderr"

    set +e
    LARCH_TOKEN_SESSION_ID="$LCR_SESSION" \
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
        fail "launch-codex-review.sh smoke exited rc=$LCR_RC; stderr=$(cat "$LCR_STDERR" 2>/dev/null)"
    else
        LCR_LEDGER=$(LARCH_TOKEN_SESSION_ID="$LCR_SESSION" \
            "$REPO_ROOT/scripts/token-ledger.sh" dump | sed -n '1p')
        EXPECTED_TOTAL=42
        if [[ -s "$LCR_LEDGER" ]] \
           && jq -e --argjson total "$EXPECTED_TOTAL" \
               'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_review" and .total==$total)' \
               "$LCR_LEDGER" >/dev/null 2>&1; then
            pass
        else
            fail "launch-codex-review.sh did not record vendor=codex raw=codex_review total=$EXPECTED_TOTAL; ledger=$LCR_LEDGER content=$(cat "$LCR_LEDGER" 2>/dev/null) stderr=$(cat "$LCR_STDERR" 2>/dev/null)"
        fi
        rm -f "$LCR_LEDGER"
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
set +e
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
if command -v shasum >/dev/null 2>&1; then
    CH_SLUG=$(printf '%s' "$CH_SESSION" | shasum -a 256 | awk '{print $1}')
else
    CH_SLUG=$(printf '%s' "$CH_SESSION" | sha256sum | awk '{print $1}')
fi
# Use a subprocess to discover the TMPDIR that check-step-token-budget.sh will
# see (this test overrides $TMPDIR locally without exporting it, so the ledger
# must land in the subprocess-visible temp root, not the test's local override).
_CH_TMPROOT=$(bash -c 'printf "%s" "${TMPDIR:-/tmp}"')
CH_LEDGER="${_CH_TMPROOT}/larch-tokens-${CH_SLUG}.jsonl"
printf '{"type":"vendor","vendor":"codex","total":9999}\n' > "$CH_LEDGER"

CH_OUTPUT="$TMPDIR/cap-hit-codex-review.txt"
CH_COUNT="$TMPDIR/cap-hit-codex-count.txt"

PATH="$STUB_BIN:$PATH" \
    CODEX_STUB_ARGV_LOG="$TMPDIR/cap-hit-codex-argv.txt" \
    CODEX_STUB_COUNT_FILE="$CH_COUNT" \
    LARCH_CODEX_MODEL="stub-model" \
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
set +e
"$LAUNCHER" --output "$TMPDIR/diff-file-accept.txt" --timeout 5 --prompt "x" \
    --diff-file "/nonexistent/branch.diff" >/dev/null 2>"$TMPDIR/diff-file-accept.stderr"
set -e
if grep -Fq "unknown flag: --diff-file" "$TMPDIR/diff-file-accept.stderr" 2>/dev/null; then
    fail "--diff-file flag not recognized by launch-codex-review.sh (got 'unknown flag' rejection)"
else
    pass
fi

# --diff-file specialist integration: when --agent-file + --diff-file are combined,
# the rendered prompt references the diff file path and omits the 'git diff main...HEAD' instruction.
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
if grep -Fq -- "git diff main...HEAD" "$DF_ARGV" 2>/dev/null; then
    fail "--diff-file specialist: 'git diff main...HEAD' must NOT appear when --diff-file is set"
else
    pass
fi

if (( FAIL > 0 )); then
    printf 'FAIL: test-launch-codex-review.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-launch-codex-review.sh - %s assertions passed\n' "$PASS"
