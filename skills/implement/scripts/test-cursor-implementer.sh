#!/usr/bin/env bash
# test-cursor-implementer.sh — Offline harness for scripts/launch-cursor-implement.sh.
#
# Always-on slice: PATH-stubs `cursor` and verifies launcher flag validation,
# KV-only stdout, argv shape, and cursor-wrap-prompt.sh wrapping.
# Optional local smoke: pass --real-smoke with CURSOR_HEALTHY=true to run a
# real cursor-agent prompt. Not wired into Makefile.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/scripts/launch-cursor-implement.sh"
AGENT_PROMPT="$REPO_ROOT/agents/cursor-implementer.md"

[[ -x "$LAUNCHER" ]] || { echo "FAIL: launcher not executable: $LAUNCHER" >&2; exit 1; }
[[ -f "$AGENT_PROMPT" ]] || { echo "FAIL: agent prompt missing: $AGENT_PROMPT" >&2; exit 1; }

if [[ "${1-}" == "--real-smoke" ]]; then
    if [[ "${CURSOR_HEALTHY:-false}" != "true" ]]; then
        echo "SKIP: real Cursor smoke requires CURSOR_HEALTHY=true"
        exit 0
    fi
    SCRATCH=$(mktemp -d -t cursor-implementer-smoke.XXXXXX)
    trap 'rm -rf "$SCRATCH"' EXIT
    PLAN="$SCRATCH/plan.md"
    FEATURE="$SCRATCH/feature.txt"
    printf 'Write a bailed test manifest only.\n' > "$PLAN"
    printf 'Real Cursor smoke.\n' > "$FEATURE"
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/transcript.txt" \
        --sidecar-log "$SCRATCH/sidecar.log" \
        --manifest-path "$SCRATCH/manifest.json" \
        --qa-pending-path "$SCRATCH/qa-pending.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 120
    exit 0
fi

PASS_COUNT=0
FAIL_COUNT=0
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }

SCRATCH=$(mktemp -d -t cursor-implementer-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

# Tighten run-external-agent.sh's poll cadence so the wrapper does not pay a
# 10s sleep per stub invocation. Production callers (real Cursor) inherit the
# default 10s. See scripts/run-external-agent.md.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

PLAN="$SCRATCH/plan.md"
FEATURE="$SCRATCH/feature.txt"
ANSWERS="$SCRATCH/answers.json"
printf 'fake plan\n' > "$PLAN"
printf 'fake feature\n' > "$FEATURE"
printf '{"answers":[{"id":"q1","text":"yes"}]}\n' > "$ANSWERS"

# Test 1: missing required flags exits 2.
EXIT=0
"$LAUNCHER" >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 1 "missing flags should exit 2, got $EXIT"; fi

# Test 2: bad timeout exits 2.
EXIT=0
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t2-transcript.txt" \
    --sidecar-log "$SCRATCH/t2-sidecar.log" \
    --manifest-path "$SCRATCH/t2-manifest.json" \
    --qa-pending-path "$SCRATCH/t2-qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout nope >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 2 "bad timeout should exit 2, got $EXIT"; fi

# Test 2b: zero timeout exits 2 and reports the positive-integer contract.
EXIT=0
TIMEOUT_ZERO_OUTPUT="$SCRATCH/t2b-output.txt"
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t2b-transcript.txt" \
    --sidecar-log "$SCRATCH/t2b-sidecar.log" \
    --manifest-path "$SCRATCH/t2b-manifest.json" \
    --qa-pending-path "$SCRATCH/t2b-qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 0 >"$TIMEOUT_ZERO_OUTPUT" 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq "must be a positive integer" "$TIMEOUT_ZERO_OUTPUT"; then
    pass
else
    fail 2b "zero timeout should exit 2 with positive-integer error, got $EXIT: $(cat "$TIMEOUT_ZERO_OUTPUT")"
fi

# Test 2c/2d: multi-digit zero timeouts exit 2 and report the same contract.
for timeout_value in 00 000; do
    EXIT=0
    TIMEOUT_ZERO_OUTPUT="$SCRATCH/t2-${timeout_value}-output.txt"
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/t2-${timeout_value}-transcript.txt" \
        --sidecar-log "$SCRATCH/t2-${timeout_value}-sidecar.log" \
        --manifest-path "$SCRATCH/t2-${timeout_value}-manifest.json" \
        --qa-pending-path "$SCRATCH/t2-${timeout_value}-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout "$timeout_value" >"$TIMEOUT_ZERO_OUTPUT" 2>&1 || EXIT=$?
    if [[ "$EXIT" == "2" ]] && grep -Fq "must be a positive integer" "$TIMEOUT_ZERO_OUTPUT"; then
        pass
    else
        fail "multi-zero-$timeout_value" "timeout $timeout_value should exit 2 with positive-integer error, got $EXIT: $(cat "$TIMEOUT_ZERO_OUTPUT")"
    fi
done

# Test 3: missing plan-file exits 2.
EXIT=0
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t3-transcript.txt" \
    --sidecar-log "$SCRATCH/t3-sidecar.log" \
    --manifest-path "$SCRATCH/t3-manifest.json" \
    --qa-pending-path "$SCRATCH/t3-qa.json" \
    --plan-file "$SCRATCH/missing-plan.md" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 30 >/dev/null 2>"$SCRATCH/t3-stderr.txt" || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq -- "plan file not found" "$SCRATCH/t3-stderr.txt"; then
    pass
else
    fail 3 "missing plan should exit 2 with stderr literal 'plan file not found', got $EXIT"
fi

# Test 3a: missing feature-file exits 2.
EXIT=0
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t3a-transcript.txt" \
    --sidecar-log "$SCRATCH/t3a-sidecar.log" \
    --manifest-path "$SCRATCH/t3a-manifest.json" \
    --qa-pending-path "$SCRATCH/t3a-qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$SCRATCH/missing-feature.txt" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 30 >/dev/null 2>"$SCRATCH/t3a-stderr.txt" || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq -- "feature file not found" "$SCRATCH/t3a-stderr.txt"; then
    pass
else
    fail 3a "missing feature should exit 2 with stderr literal 'feature file not found', got $EXIT"
fi

# Test 3b: missing agent-prompt exits 2.
EXIT=0
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t3b-transcript.txt" \
    --sidecar-log "$SCRATCH/t3b-sidecar.log" \
    --manifest-path "$SCRATCH/t3b-manifest.json" \
    --qa-pending-path "$SCRATCH/t3b-qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$FEATURE" \
    --agent-prompt "$SCRATCH/missing-agent-prompt.md" \
    --timeout 30 >/dev/null 2>"$SCRATCH/t3b-stderr.txt" || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq -- "agent prompt not found" "$SCRATCH/t3b-stderr.txt"; then
    pass
else
    fail 3b "missing agent-prompt should exit 2 with stderr literal 'agent prompt not found', got $EXIT"
fi

# Test 3c: --answers-file pointing at non-existent path exits 2.
EXIT=0
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t3c-transcript.txt" \
    --sidecar-log "$SCRATCH/t3c-sidecar.log" \
    --manifest-path "$SCRATCH/t3c-manifest.json" \
    --qa-pending-path "$SCRATCH/t3c-qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 30 \
    --answers-file "$SCRATCH/missing-answers.json" >/dev/null 2>"$SCRATCH/t3c-stderr.txt" || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq -- "--answers-file given but path does not exist" "$SCRATCH/t3c-stderr.txt"; then
    pass
else
    fail 3c "missing answers-file should exit 2 with stderr literal '--answers-file given but path does not exist', got $EXIT"
fi

STUB_BIN="$SCRATCH/bin"
mkdir -p "$STUB_BIN"
STUB_CURSOR="$STUB_BIN/cursor"
cat > "$STUB_CURSOR" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
last=""
: "${STUB_ARGV_FILE:?}"
: "${STUB_PROMPT_FILE:?}"
: "${STUB_MANIFEST_PATH:?}"
if [[ -n "${STUB_TOKEN_SESSION_FILE:-}" ]]; then
    printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$STUB_TOKEN_SESSION_FILE"
fi
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$STUB_ARGV_FILE"
    last="$arg"
done
printf '%s' "$last" > "$STUB_PROMPT_FILE"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'stub cursor stdout\n'
EOF
chmod +x "$STUB_CURSOR"

TRANSCRIPT="$SCRATCH/transcript.txt"
SIDECAR="$SCRATCH/sidecar.log"
MANIFEST="$SCRATCH/manifest.json"
QA_PENDING="$SCRATCH/qa-pending.json"
ARGV_FILE="$SCRATCH/cursor-argv.txt"
PROMPT_FILE="$SCRATCH/cursor-prompt.txt"
TOKEN_SESSION_FILE="$SCRATCH/cursor-token-session.txt"
IMPLEMENT_TMPDIR_FIXTURE="$SCRATCH/implement-tmpdir"
mkdir -p "$IMPLEMENT_TMPDIR_FIXTURE"
printf 'mock-cursor-session\n' > "$IMPLEMENT_TMPDIR_FIXTURE/session-id"
printf 'SOURCE_FILE=/tmp/mock.jsonl\n' > "$IMPLEMENT_TMPDIR_FIXTURE/claude-source.env"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$ARGV_FILE" \
    STUB_PROMPT_FILE="$PROMPT_FILE" \
    STUB_MANIFEST_PATH="$MANIFEST" \
    STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_FILE" \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_FIXTURE" \
    LARCH_TOKEN_SESSION_ID="stale-cursor-session" \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$TRANSCRIPT" \
        --sidecar-log "$SIDECAR" \
        --manifest-path "$MANIFEST" \
        --qa-pending-path "$QA_PENDING" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)

EXPECTED=$(printf 'LAUNCHER_EXIT=0\nMANIFEST_WRITTEN=true\nQA_PENDING_WRITTEN=false\nTRANSCRIPT=%s\nSIDECAR_LOG=%s' "$TRANSCRIPT" "$SIDECAR")
if [[ "$OUT" == "$EXPECTED" ]]; then
    pass
else
    fail 4 "launcher stdout contract mismatch; got: $OUT"
fi

if [[ "$(cat "$TOKEN_SESSION_FILE")" == "mock-cursor-session" ]]; then
    pass
else
    fail 4a "launcher did not overwrite stale LARCH_TOKEN_SESSION_ID from IMPLEMENT_TMPDIR/session-id"
fi

if [[ -s "$TRANSCRIPT" ]] && grep -Fq 'stub cursor stdout' "$TRANSCRIPT"; then
    pass
else
    fail 5 "stub Cursor stdout was not captured to transcript"
fi

# Semantic relative-order argv check (insertion-tolerant for the issue #1358
# `--api-key` argv slot). The line numbers shifted from absolute `5p..10p` to
# whatever positions sed produces post-`--api-key` insertion, so assert
# presence + ordering instead.
_argv_line_of() {
    # Print the first line number containing the exact token, or 0 if absent.
    local needle="$1"
    grep -Fxn -- "$needle" "$ARGV_FILE" | awk -F: 'NR==1 {print $1; exit}'
}
_OFMT_LINE=$(_argv_line_of "--output-format")
_JSON_LINE=$(_argv_line_of "json")
_MODEL_LINE=$(_argv_line_of "--model")
_MODEL_VAL_LINE=$(_argv_line_of "stub-model")
_WS_LINE=$(_argv_line_of "--workspace")
_WS_VAL_LINE=$(_argv_line_of "$REPO_ROOT")
if [[ -n "$_OFMT_LINE" && -n "$_JSON_LINE" && -n "$_MODEL_LINE" && -n "$_MODEL_VAL_LINE" && -n "$_WS_LINE" && -n "$_WS_VAL_LINE" ]] \
   && [[ "$_OFMT_LINE" -lt "$_JSON_LINE" ]] \
   && [[ "$_JSON_LINE" -lt "$_MODEL_LINE" ]] \
   && [[ "$_MODEL_LINE" -lt "$_MODEL_VAL_LINE" ]] \
   && [[ "$_MODEL_VAL_LINE" -lt "$_WS_LINE" ]] \
   && [[ "$_WS_LINE" -lt "$_WS_VAL_LINE" ]]; then
    pass
else
    fail 6 "Cursor argv shape should include --output-format json, model args, then --workspace before prompt"
fi

# Test 6b: with CURSOR_API_KEY unset/empty, --api-key MUST NOT appear in argv.
# Pins the conditional auth-flag insertion behavior (lib-cursor-auth.sh
# emits no flag on empty key, preserving cursor login keychain fallback).
if grep -Fxq -- '--api-key' "$ARGV_FILE"; then
    fail 6b "Cursor argv must not include --api-key when CURSOR_API_KEY is unset/empty"
else
    pass
fi

if grep -Fxq -- '--' "$ARGV_FILE"; then
    fail 7 "Cursor argv must not include a -- separator before the prompt"
else
    pass
fi

if grep -Fq ' /max-mode on. Prompt: ' "$PROMPT_FILE"; then
    pass
else
    fail 8 "Cursor prompt was not wrapped with cursor-wrap-prompt.sh prefix"
fi

if [[ -s "${TRANSCRIPT}.prompt" ]] && grep -Fq 'Begin by inspecting the current branch state' "${TRANSCRIPT}.prompt"; then
    pass
else
    fail 8a "prompt sidecar should contain the composed implementer prompt"
fi
if [[ -s "${TRANSCRIPT}.meta" ]] \
   && grep -Fxq "OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-cursor-implement.sh" "${TRANSCRIPT}.meta" \
   && grep -Fxq "OUTER_LAUNCHER_PROMPT_FILE=${TRANSCRIPT}.prompt" "${TRANSCRIPT}.meta" \
   && grep -Fxq "OUTER_LAUNCHER_WORKDIR=$REPO_ROOT" "${TRANSCRIPT}.meta"; then
    pass
else
    fail 8b "meta sidecar should include OUTER_LAUNCHER forward-compat keys"
fi
if [[ -f "${TRANSCRIPT}.done" && ! -f "${TRANSCRIPT}.inner.done" ]]; then
    pass
else
    fail 8c "public .done should be published after inner sentinel is consumed"
fi

# Test 9: positive leading-zero timeout (010) is accepted; exit 0 + standard
# five-line stdout envelope. Pins acceptance of the leading-zero positive
# form so a future refactor tightening the digit-only `case` validation to
# e.g. `^[1-9][0-9]*$` (which would reject `010`) breaks CI here. Note: the
# stub exits immediately, so this assertion does NOT prove that downstream
# treats `010` as decimal 10 vs. octal 8 — it only pins contract stability
# at the launcher boundary.
T9_TRANSCRIPT="$SCRATCH/t9-transcript.txt"
T9_SIDECAR="$SCRATCH/t9-sidecar.log"
T9_MANIFEST="$SCRATCH/t9-manifest.json"
T9_QA="$SCRATCH/t9-qa.json"
T9_ARGV="$SCRATCH/t9-argv.txt"
T9_PROMPT="$SCRATCH/t9-prompt.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$T9_ARGV" \
    STUB_PROMPT_FILE="$T9_PROMPT" \
    STUB_MANIFEST_PATH="$T9_MANIFEST" \
    LARCH_CURSOR_MODEL="stub-model" \
    "$LAUNCHER" \
        --transcript-path "$T9_TRANSCRIPT" \
        --sidecar-log "$T9_SIDECAR" \
        --manifest-path "$T9_MANIFEST" \
        --qa-pending-path "$T9_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 010)

T9_EXPECTED=$(printf 'LAUNCHER_EXIT=0\nMANIFEST_WRITTEN=true\nQA_PENDING_WRITTEN=false\nTRANSCRIPT=%s\nSIDECAR_LOG=%s' "$T9_TRANSCRIPT" "$T9_SIDECAR")
if [[ "$OUT" == "$T9_EXPECTED" ]]; then
    pass
else
    fail 9 "leading-zero timeout 010 should be accepted with standard envelope; got: $OUT"
fi

# Test 10: --answers-file adds the resume invocation block to the wrapped prompt.
RESUME_TRANSCRIPT="$SCRATCH/resume-transcript.txt"
RESUME_SIDECAR="$SCRATCH/resume-sidecar.log"
RESUME_MANIFEST="$SCRATCH/resume-manifest.json"
RESUME_QA="$SCRATCH/resume-qa.json"
RESUME_ARGV="$SCRATCH/resume-argv.txt"
RESUME_PROMPT="$SCRATCH/resume-prompt.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$RESUME_ARGV" \
    STUB_PROMPT_FILE="$RESUME_PROMPT" \
    STUB_MANIFEST_PATH="$RESUME_MANIFEST" \
    LARCH_CURSOR_MODEL="stub-model" \
    "$LAUNCHER" \
        --transcript-path "$RESUME_TRANSCRIPT" \
        --sidecar-log "$RESUME_SIDECAR" \
        --manifest-path "$RESUME_MANIFEST" \
        --qa-pending-path "$RESUME_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30 \
        --answers-file "$ANSWERS")

if grep -Fq '## Resume invocation' "$RESUME_PROMPT" && grep -Fq "$ANSWERS" "$RESUME_PROMPT"; then
    pass
else
    fail 10 "resume invocation block missing from composed prompt"
fi

# Test 11: record-vendor smoke (issue #1351 Gap 1). Stub Cursor emits a
# transcript containing a valid `.usage` block with known counters; after the
# launcher returns, dump the per-session ledger and assert a vendor row with
# raw=cursor_implement, the expected per-counter values, and total=110. Skip
# when jq is unavailable (parallel to launch-cursor-implement.sh's runtime
# `command -v jq` guard around its `.usage` parse).
if command -v jq >/dev/null 2>&1; then
    RV_STUB_BIN="$SCRATCH/rv-bin"
    mkdir -p "$RV_STUB_BIN"
    cat > "$RV_STUB_BIN/cursor" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf '{"result":"stub","usage":{"inputTokens":11,"outputTokens":22,"cacheReadTokens":33,"cacheWriteTokens":44}}\n'
STUB_EOF
    chmod +x "$RV_STUB_BIN/cursor"

    RV_SESSION_ID="rv-cursor-$$"
    RV_TRANSCRIPT="$SCRATCH/rv-transcript.txt"
    RV_SIDECAR="$SCRATCH/rv-sidecar.log"
    RV_MANIFEST="$SCRATCH/rv-manifest.json"
    RV_QA="$SCRATCH/rv-qa.json"

    cd "$REPO_ROOT" && \
        PATH="$RV_STUB_BIN:$PATH" \
        STUB_MANIFEST_PATH="$RV_MANIFEST" \
        LARCH_CURSOR_MODEL="stub-model" \
        LARCH_TOKEN_SESSION_ID="$RV_SESSION_ID" \
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$LAUNCHER" \
            --transcript-path "$RV_TRANSCRIPT" \
            --sidecar-log "$RV_SIDECAR" \
            --manifest-path "$RV_MANIFEST" \
            --qa-pending-path "$RV_QA" \
            --plan-file "$PLAN" \
            --feature-file "$FEATURE" \
            --agent-prompt "$AGENT_PROMPT" \
            --timeout 30 >/dev/null

    RV_LEDGER=$(LARCH_TOKEN_SESSION_ID="$RV_SESSION_ID" "$REPO_ROOT/scripts/token-ledger.sh" dump | sed -n '1p')
    if [[ -f "$RV_LEDGER" ]] && jq -e \
        'select(.type=="vendor" and .vendor=="cursor" and .raw=="cursor_implement" and .input==11 and .output==22 and .cache_read==33 and .cache_create==44 and .total==110)' \
        "$RV_LEDGER" >/dev/null 2>&1; then
        pass
    else
        fail 11 "cursor record-vendor JSONL missing or counters wrong; ledger=$RV_LEDGER content=$(cat "$RV_LEDGER" 2>/dev/null)"
    fi
    rm -f "$RV_LEDGER"
else
    pass  # jq absent — skip per launcher runtime guard parallel
fi

# Test K1 (issue #1358): with CURSOR_API_KEY set, --api-key and the literal
# key value MUST appear as adjacent tokens in recorded argv. Pins the
# lib-cursor-auth.sh argv-injection contract.
K1_TRANSCRIPT="$SCRATCH/k1-transcript.txt"
K1_SIDECAR="$SCRATCH/k1-sidecar.log"
K1_MANIFEST="$SCRATCH/k1-manifest.json"
K1_QA="$SCRATCH/k1-qa.json"
K1_ARGV="$SCRATCH/k1-argv.txt"
K1_PROMPT="$SCRATCH/k1-prompt.txt"
cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$K1_ARGV" \
    STUB_PROMPT_FILE="$K1_PROMPT" \
    STUB_MANIFEST_PATH="$K1_MANIFEST" \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="test-key-12345" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$K1_TRANSCRIPT" \
        --sidecar-log "$K1_SIDECAR" \
        --manifest-path "$K1_MANIFEST" \
        --qa-pending-path "$K1_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30 >/dev/null

K1_API_KEY_LINE=$(grep -Fxn -- '--api-key' "$K1_ARGV" | awk -F: 'NR==1 {print $1; exit}')
K1_API_VAL_LINE=$(grep -Fxn -- 'test-key-12345' "$K1_ARGV" | awk -F: 'NR==1 {print $1; exit}')
if [[ -n "$K1_API_KEY_LINE" && -n "$K1_API_VAL_LINE" ]] && (( K1_API_VAL_LINE == K1_API_KEY_LINE + 1 )); then
    pass
else
    fail K1 "--api-key and value must be adjacent tokens in argv when CURSOR_API_KEY is set; key_line=$K1_API_KEY_LINE val_line=$K1_API_VAL_LINE"
fi

# Test K2 (issue #1358): with CURSOR_API_KEY whitespace-only, --api-key MUST NOT
# appear. Whitespace-trim equivalence to empty-string case pins lib-cursor-auth's
# Bash-3.2-safe parameter-expansion trim.
K2_TRANSCRIPT="$SCRATCH/k2-transcript.txt"
K2_SIDECAR="$SCRATCH/k2-sidecar.log"
K2_MANIFEST="$SCRATCH/k2-manifest.json"
K2_QA="$SCRATCH/k2-qa.json"
K2_ARGV="$SCRATCH/k2-argv.txt"
K2_PROMPT="$SCRATCH/k2-prompt.txt"
cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$K2_ARGV" \
    STUB_PROMPT_FILE="$K2_PROMPT" \
    STUB_MANIFEST_PATH="$K2_MANIFEST" \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY=$'  \t\n  ' \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$K2_TRANSCRIPT" \
        --sidecar-log "$K2_SIDECAR" \
        --manifest-path "$K2_MANIFEST" \
        --qa-pending-path "$K2_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30 >/dev/null

if grep -Fxq -- '--api-key' "$K2_ARGV"; then
    fail K2 "Cursor argv must not include --api-key when CURSOR_API_KEY is whitespace-only"
else
    pass
fi

# Test K3 (issue #1358): on Darwin (test-mode injected) with CURSOR_API_KEY
# empty AND injected security RC=1 (keychain entry missing), launcher MUST
# emit the standard KV envelope with LAUNCHER_EXIT=2 and route the actionable
# stderr to SIDECAR_LOG so step2-implement.sh surfaces a specific failure
# instead of a generic timeout/missing-manifest message.
K3_TRANSCRIPT="$SCRATCH/k3-transcript.txt"
K3_SIDECAR="$SCRATCH/k3-sidecar.log"
K3_MANIFEST="$SCRATCH/k3-manifest.json"
K3_QA="$SCRATCH/k3-qa.json"
K3_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Darwin" \
    LIB_CURSOR_AUTH_TEST_SECURITY_RC=1 \
    "$LAUNCHER" \
        --transcript-path "$K3_TRANSCRIPT" \
        --sidecar-log "$K3_SIDECAR" \
        --manifest-path "$K3_MANIFEST" \
        --qa-pending-path "$K3_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)

K3_EXPECTED=$(printf 'LAUNCHER_EXIT=2\nMANIFEST_WRITTEN=false\nQA_PENDING_WRITTEN=false\nTRANSCRIPT=%s\nSIDECAR_LOG=%s' "$K3_TRANSCRIPT" "$K3_SIDECAR")
if [[ "$K3_OUT" == "$K3_EXPECTED" ]] \
   && [[ -s "$K3_SIDECAR" ]] \
   && grep -Fq 'cursor-auth-preflight' "$K3_SIDECAR" \
   && grep -Fq 'security delete-generic-password -a cursor-user' "$K3_SIDECAR"; then
    pass
else
    fail K3 "preflight failure on Darwin should emit KV envelope with LAUNCHER_EXIT=2 and actionable SIDECAR_LOG; got stdout=$K3_OUT sidecar=$(cat "$K3_SIDECAR" 2>/dev/null)"
fi

# Test K4 (issue #1480 Bug #2): defensive --timing-task-kind validation.
# Empty or flag-like values must be rejected with exit 2 and a clear message.
# Pass --timing-task-kind first so the new validation fires before any
# unrelated argv check; required flags below the validation are not reached.
K4_RC=0
K4_OUT=$("$LAUNCHER" --timing-task-kind "" 2>&1) || K4_RC=$?
if [[ "$K4_RC" == "2" ]] && grep -Fq "non-empty, non-flag-like value" <<<"$K4_OUT"; then
    pass
else
    fail K4 "empty timing-task-kind should exit 2 with non-empty-non-flag-like message, got rc=$K4_RC: $K4_OUT"
fi

K4b_RC=0
K4b_OUT=$("$LAUNCHER" --timing-task-kind --plan-file 2>&1) || K4b_RC=$?
if [[ "$K4b_RC" == "2" ]] && grep -Fq "non-empty, non-flag-like value" <<<"$K4b_OUT"; then
    pass
else
    fail K4b "flag-like timing-task-kind should exit 2 with non-empty-non-flag-like message, got rc=$K4b_RC: $K4b_OUT"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-cursor-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-cursor-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
