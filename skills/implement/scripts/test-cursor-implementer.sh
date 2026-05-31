#!/usr/bin/env bash
# test-cursor-implementer.sh — Offline harness for scripts/launch-cursor-implement.sh.
#
# Always-on slice: PATH-stubs `cursor` and verifies launcher flag validation,
# KV-only stdout, argv shape, and cursor-wrap-prompt.sh wrapping.
# Optional local smoke: pass --real-smoke with CURSOR_PRESENT=true to run a
# real cursor-agent prompt. Not wired into Makefile.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/scripts/launch-cursor-implement.sh"
AGENT_PROMPT="$REPO_ROOT/agents/cursor-implementer.md"

[[ -x "$LAUNCHER" ]] || { echo "FAIL: launcher not executable: $LAUNCHER" >&2; exit 1; }
[[ -f "$AGENT_PROMPT" ]] || { echo "FAIL: agent prompt missing: $AGENT_PROMPT" >&2; exit 1; }

if [[ "${1-}" == "--real-smoke" ]]; then
    if [[ "${CURSOR_PRESENT:-false}" != "true" ]]; then
        echo "SKIP: real Cursor smoke requires CURSOR_PRESENT=true"
        exit 0
    fi
    SCRATCH=$(mktemp -d -t cursor-implementer-smoke.XXXXXX)
    trap 'rm -rf "$SCRATCH"' EXIT
    unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
    export LARCH_EXECUTION_ISSUES_LOG="$SCRATCH/execution-issues.md"
    export LARCH_TIMING_LEDGER="$SCRATCH/timing-ledger.tsv"
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

assert_manifest_template_present() {
    local test_id="$1"
    local json_file="$SCRATCH/${test_id}-manifest-template.json"
    if grep -Fq "## Manifest JSON template" "$AGENT_PROMPT" \
       && grep -Fq "## Self-validate before atomic rename" "$AGENT_PROMPT"; then
        pass
    else
        fail "$test_id" "generated prompt missing manifest template/self-validation headings"
    fi
    awk '
        /^## Manifest JSON template$/ { in_section=1; next }
        in_section && /^```json$/ { in_json=1; next }
        in_json && /^```$/ { exit }
        in_json { print }
    ' "$AGENT_PROMPT" > "$json_file"
    if jq -e '
        has("schema_version") and
        has("status") and
        (.files_touched[0] | has("path") and has("lines_added") and has("lines_removed")) and
        has("tests_added_or_modified") and
        has("summary_bullets") and
        has("commit_message") and
        has("todos_left") and
        has("oos_observations") and
        has("bail_reason") and
        (.needs_qa.questions[0] | has("id") and has("text"))
    ' "$json_file" >/dev/null 2>&1; then
        pass
    else
        fail "$test_id" "inline manifest JSON template is missing canonical fields: $(cat "$json_file" 2>/dev/null)"
    fi
}

assert_subprocess_guard_absent() {
    local test_id="$1"
    if grep -Fq "persistent interactive subprocess sessions" "$AGENT_PROMPT"; then
        fail "$test_id" "cursor implementer prompt unexpectedly contains Codex Hard guard #9 (Cursor generator sed strip regressed)"
    else
        pass
    fi
}

SCRATCH=$(mktemp -d -t cursor-implementer-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$SCRATCH/execution-issues.md"
export LARCH_TIMING_LEDGER="$SCRATCH/timing-ledger.tsv"

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

assert_manifest_template_present "manifest-template"
assert_subprocess_guard_absent "subprocess-guard-absent"

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
if [[ -n "${STUB_LOCK_PATH:-}" && -n "${STUB_LOCK_SEEN_FILE:-}" && -d "$STUB_LOCK_PATH" ]]; then
    printf 'present\n' > "$STUB_LOCK_SEEN_FILE"
fi
stub_count=0
if [[ -n "${STUB_COUNT_FILE:-}" && -f "$STUB_COUNT_FILE" ]]; then
    stub_count=$(cat "$STUB_COUNT_FILE")
fi
stub_count=$((stub_count + 1))
if [[ -n "${STUB_COUNT_FILE:-}" ]]; then
    printf '%s\n' "$stub_count" > "$STUB_COUNT_FILE"
fi
if [[ -n "${STUB_AUTH_FAIL_UNTIL:-}" && "$stub_count" -le "$STUB_AUTH_FAIL_UNTIL" ]]; then
    printf 'auth-error: Password not found\n' >&2
    exit 1
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

LOCK_USER="larch-test-cursor-impl-$$"
LOCK_PATH="/tmp/larch-cursor-serial-${LOCK_USER}.lock"
LOCK_SEEN="$SCRATCH/cursor-lock-seen.txt"
rm -rf "$LOCK_PATH"
LOCK_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    USER="$LOCK_USER" \
    STUB_ARGV_FILE="$SCRATCH/cursor-lock-argv.txt" \
    STUB_PROMPT_FILE="$SCRATCH/cursor-lock-prompt.txt" \
    STUB_MANIFEST_PATH="$SCRATCH/cursor-lock-manifest.json" \
    STUB_LOCK_PATH="$LOCK_PATH" \
    STUB_LOCK_SEEN_FILE="$LOCK_SEEN" \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_SESSION_ID="cursor-lock-$LOCK_USER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/cursor-lock-transcript.txt" \
        --sidecar-log "$SCRATCH/cursor-lock-sidecar.log" \
        --manifest-path "$SCRATCH/cursor-lock-manifest.json" \
        --qa-pending-path "$SCRATCH/cursor-lock-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$LOCK_OUT" == *"LAUNCHER_EXIT=0"* && "$(cat "$LOCK_SEEN" 2>/dev/null)" == "present" ]]; then
    pass
else
    fail 5a "Cursor implementer should hold /tmp serial lock while spawning cursor; out=$LOCK_OUT"
fi
rm -rf "$LOCK_PATH"

RETRY_COUNT="$SCRATCH/cursor-retry-count.txt"
RETRY_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$SCRATCH/cursor-retry-argv.txt" \
    STUB_PROMPT_FILE="$SCRATCH/cursor-retry-prompt.txt" \
    STUB_MANIFEST_PATH="$SCRATCH/cursor-retry-manifest.json" \
    STUB_COUNT_FILE="$RETRY_COUNT" \
    STUB_AUTH_FAIL_UNTIL=1 \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_SESSION_ID="cursor-retry-$$" \
    LARCH_EXTERNAL_AUTH_RETRIES=2 \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/cursor-retry-transcript.txt" \
        --sidecar-log "$SCRATCH/cursor-retry-sidecar.log" \
        --manifest-path "$SCRATCH/cursor-retry-manifest.json" \
        --qa-pending-path "$SCRATCH/cursor-retry-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$RETRY_OUT" == *"LAUNCHER_EXIT=0"* && "$(cat "$RETRY_COUNT" 2>/dev/null)" == "2" ]]; then
    pass
else
    fail 5b "Cursor implementer should retry one auth failure; count=$(cat "$RETRY_COUNT" 2>/dev/null) out=$RETRY_OUT"
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

MODEL_TRANSCRIPT="$SCRATCH/model-preflight-transcript.txt"
MODEL_SIDECAR="$SCRATCH/model-preflight-sidecar.log"
MODEL_MANIFEST="$SCRATCH/model-preflight-manifest.json"
MODEL_QA="$SCRATCH/model-preflight-qa.json"
MODEL_STDOUT="$SCRATCH/model-preflight-stdout.txt"
printf 'STALE-SENTINEL-1514\n' > "$MODEL_SIDECAR"
printf '{"status":"complete"}\n' > "$MODEL_MANIFEST"
printf '{"questions":[]}\n' > "$MODEL_QA"
MODEL_EXIT=0
(
    cd "$REPO_ROOT"
    LARCH_CURSOR_MODEL=$'bad\nmodel' "$LAUNCHER" \
        --transcript-path "$MODEL_TRANSCRIPT" \
        --sidecar-log "$MODEL_SIDECAR" \
        --manifest-path "$MODEL_MANIFEST" \
        --qa-pending-path "$MODEL_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30
) >"$MODEL_STDOUT" 2>&1 || MODEL_EXIT=$?
MODEL_LAUNCHER_EXIT=$(awk -F= '$1=="LAUNCHER_EXIT"{print $2; exit}' "$MODEL_STDOUT")
if [[ "$MODEL_EXIT" == "0" ]] \
   && [[ -n "$MODEL_LAUNCHER_EXIT" && "$MODEL_LAUNCHER_EXIT" != "0" ]] \
   && grep -Fxq 'MANIFEST_WRITTEN=false' "$MODEL_STDOUT" \
   && grep -Fxq 'QA_PENDING_WRITTEN=false' "$MODEL_STDOUT" \
   && grep -Fq 'LARCH_CURSOR_MODEL' "$MODEL_SIDECAR" \
   && ! grep -Fq 'STALE-SENTINEL-1514' "$MODEL_SIDECAR"; then
    pass
else
    fail "model-preflight" "model args failure should exit wrapper 0 with non-zero LAUNCHER_EXIT, false manifest flags, and truncated diagnostic sidecar; exit=$MODEL_EXIT stdout=$(cat "$MODEL_STDOUT") sidecar=$(cat "$MODEL_SIDECAR" 2>/dev/null)"
fi

TENV_TRANSCRIPT="$SCRATCH/tenv-transcript.txt"
TENV_SIDECAR="$SCRATCH/tenv-sidecar.log"
TENV_MANIFEST="$SCRATCH/tenv-manifest.json"
TENV_QA="$SCRATCH/tenv-qa.json"
TENV_ARGV="$SCRATCH/tenv-argv.txt"
TENV_PROMPT="$SCRATCH/tenv-prompt.txt"
TENV_LEDGER="$SCRATCH/tenv-timing.tsv"
cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$TENV_ARGV" \
    STUB_PROMPT_FILE="$TENV_PROMPT" \
    STUB_MANIFEST_PATH="$TENV_MANIFEST" \
    LARCH_CURSOR_MODEL="stub-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    LARCH_TIMING_LEDGER="$TENV_LEDGER" \
    LARCH_TIMING_TASK_KIND="--prompt" \
    "$LAUNCHER" \
        --transcript-path "$TENV_TRANSCRIPT" \
        --sidecar-log "$TENV_SIDECAR" \
        --manifest-path "$TENV_MANIFEST" \
        --qa-pending-path "$TENV_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30 >/dev/null
if [[ -f "$TENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" && $6 == "cursor" && $7 == "cursor-implement" { found=1 } END { exit(found ? 0 : 1) }' "$TENV_LEDGER"; then
    pass
else
    fail "timing-env" "env LARCH_TIMING_TASK_KIND=--prompt should fall back to cursor-implement; ledger=$(cat "$TENV_LEDGER" 2>/dev/null)"
fi
if [[ -f "$TENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" { print $7 }' "$TENV_LEDGER" | grep -Fxq -- '--prompt'; then
    fail "timing-env-leak" "env LARCH_TIMING_TASK_KIND=--prompt leaked into cursor implement timing ledger"
else
    pass
fi

DISPATCHER="$REPO_ROOT/skills/implement/scripts/step2-implement.sh"
STEP2_REPO="$SCRATCH/step2-cursor-retry-repo"
mkdir -p "$STEP2_REPO"
git -C "$STEP2_REPO" init -q -b main
git -C "$STEP2_REPO" config user.email "test@example.invalid"
git -C "$STEP2_REPO" config user.name "larch test"
printf 'base\n' > "$STEP2_REPO/README.md"
git -C "$STEP2_REPO" add README.md
git -C "$STEP2_REPO" commit -q -m initial
STEP2_TMP="$SCRATCH/step2-cursor-retry-tmp"
mkdir -p "$STEP2_TMP"
STEP2_LEDGER="$STEP2_TMP/timing.tsv"
STEP2_OUT=$(cd "$STEP2_REPO" && \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_TIMING_LEDGER="$STEP2_LEDGER" \
    LARCH_CURSOR_MODEL=$'bad\nmodel' \
    "$DISPATCHER" --tmpdir "$STEP2_TMP" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder cursor --cursor-present true 2>&1)
STEP2_ROWS=$(awk -F'\t' '$2 == "vendor" && $6 == "cursor" && $7 == "cursor-implement" && $12 != "0" { c++ } END { print c + 0 }' "$STEP2_LEDGER" 2>/dev/null || echo 0)
if [[ "$STEP2_OUT" == *"STATUS=bailed"* ]] \
   && [[ "$STEP2_OUT" == *"REASON=cursor-runtime-failure"* ]] \
   && [[ "$STEP2_OUT" == *"TOOL=cursor"* ]] \
   && [[ "$STEP2_OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$STEP2_ROWS" == "2" ]] \
   && [[ ! -e "$STEP2_TMP/manifest.json" ]]; then
    pass
else
    fail "step2-cursor-retry" "dispatcher should retry cursor preflight failure once then bail cursor-runtime-failure with two non-zero timing rows; rows=$STEP2_ROWS out=$STEP2_OUT ledger=$(cat "$STEP2_LEDGER" 2>/dev/null)"
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

    RV_LEDGER="$SCRATCH/rv-cursor-token-ledger.jsonl"
    cd "$REPO_ROOT" && \
        PATH="$RV_STUB_BIN:$PATH" \
        STUB_MANIFEST_PATH="$RV_MANIFEST" \
        LARCH_CURSOR_MODEL="stub-model" \
        LARCH_TOKEN_SESSION_ID="$RV_SESSION_ID" \
        LARCH_TOKEN_LEDGER="$RV_LEDGER" \
        IMPLEMENT_TMPDIR='' \
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
   && grep -Fq 'security delete-generic-password -a cursor-user' "$K3_SIDECAR" \
   && [[ -s "${K3_TRANSCRIPT}.stderr-tail" ]]; then
    pass
else
    fail K3 "preflight failure on Darwin should emit KV envelope with LAUNCHER_EXIT=2 and actionable SIDECAR_LOG; got stdout=$K3_OUT sidecar=$(cat "$K3_SIDECAR" 2>/dev/null)"
fi

# Test K4 (issue #1480 Bug #2): defensive `--timing-task-kind` validation.
# Empty or flag-like values must be rejected with exit 2 and a clear message.
# Pass `--timing-task-kind` first so the new validation fires before any
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

# Test cap-hit: when the per-step token budget cap is exceeded, the launcher
# exits immediately with LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit
# without invoking the underlying Cursor binary.
CH_SESSION="cap-hit-cursor-$$-$RANDOM"
CH_LEDGER="$SCRATCH/cap-hit-cursor-ledger.jsonl"
"$REPO_ROOT/scripts/token-ledger.sh" --ledger "$CH_LEDGER" record-vendor cursor total=9999 raw=cap_hit_test >/dev/null

CH_ARGV="$SCRATCH/cap-hit-cursor-argv.txt"
CH_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$CH_ARGV" \
    STUB_PROMPT_FILE="$SCRATCH/cap-hit-cursor-prompt.txt" \
    STUB_LAST_ARG_FILE="$SCRATCH/cap-hit-cursor-last-arg.txt" \
    STUB_SEPARATOR_INDEX_FILE="$SCRATCH/cap-hit-cursor-sep.txt" \
    STUB_MANIFEST_PATH="$SCRATCH/cap-hit-cursor-manifest.json" \
    LARCH_TOKEN_SESSION_ID="$CH_SESSION" \
    LARCH_TOKEN_LEDGER="$CH_LEDGER" \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_BUDGET_CAP_IMPLEMENT=1 \
    LARCH_CURSOR_MODEL="stub-cursor-model" \
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/cap-hit-cursor-transcript.txt" \
        --sidecar-log "$SCRATCH/cap-hit-cursor-sidecar.log" \
        --manifest-path "$SCRATCH/cap-hit-cursor-manifest.json" \
        --qa-pending-path "$SCRATCH/cap-hit-cursor-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)

if printf '%s\n' "$CH_OUT" | grep -Fxq 'LAUNCHER_EXIT=0' && \
   printf '%s\n' "$CH_OUT" | grep -Fxq 'MANIFEST_WRITTEN=false' && \
   printf '%s\n' "$CH_OUT" | grep -Fxq 'STATUS=cap_hit'; then
    pass
else
    fail "cap-hit-kv" "cap_hit path must emit LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit; got: $CH_OUT"
fi
if [[ ! -f "$CH_ARGV" ]]; then
    pass
else
    fail "cap-hit-no-invoke" "cap_hit path must not invoke the underlying Cursor binary"
fi

# Test: agent failure leaves ${TRANSCRIPT}.stderr-tail (producer: run-external-agent).
FAIL_TAIL_BIN="$SCRATCH/fail-tail-bin"
mkdir -p "$FAIL_TAIL_BIN"
cat > "$FAIL_TAIL_BIN/cursor" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
printf 'cursor agent failure\n' >&2
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
exit 1
EOF
chmod +x "$FAIL_TAIL_BIN/cursor"
FAIL_TAIL_TRANSCRIPT="$SCRATCH/fail-tail-transcript.txt"
FAIL_TAIL_SIDECAR="$SCRATCH/fail-tail-sidecar.log"
FAIL_TAIL_MANIFEST="$SCRATCH/fail-tail-manifest.json"
FAIL_TAIL_OUT=$(cd "$REPO_ROOT" && \
    PATH="$FAIL_TAIL_BIN:$PATH" \
    STUB_MANIFEST_PATH="$FAIL_TAIL_MANIFEST" \
    IMPLEMENT_TMPDIR='' \
    LARCH_CURSOR_MODEL="stub-cursor-model" \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$FAIL_TAIL_TRANSCRIPT" \
        --sidecar-log "$FAIL_TAIL_SIDECAR" \
        --manifest-path "$FAIL_TAIL_MANIFEST" \
        --qa-pending-path "$SCRATCH/fail-tail-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$FAIL_TAIL_OUT" == *"LAUNCHER_EXIT=1"* ]] \
    && [[ -s "${FAIL_TAIL_TRANSCRIPT}.stderr-tail" ]]; then
    pass
else
    fail "stderr-tail-agent" "cursor agent failure must produce stderr-tail; out=$FAIL_TAIL_OUT"
fi

# Test: model-args failure writes stderr-tail before run-external-agent.
MODEL_ARGS_CURSOR_TRANSCRIPT="$SCRATCH/model-args-cursor-transcript.txt"
MODEL_ARGS_CURSOR_SIDECAR="$SCRATCH/model-args-cursor-sidecar.log"
MODEL_ARGS_CURSOR_OUT=$(cd "$REPO_ROOT" && \
    IMPLEMENT_TMPDIR='' \
    LARCH_CURSOR_MODEL=$'bad\x01model' \
    CURSOR_API_KEY="" \
    LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 \
    LIB_CURSOR_AUTH_TEST_UNAME="Linux" \
    "$LAUNCHER" \
        --transcript-path "$MODEL_ARGS_CURSOR_TRANSCRIPT" \
        --sidecar-log "$MODEL_ARGS_CURSOR_SIDECAR" \
        --manifest-path "$SCRATCH/model-args-cursor-manifest.json" \
        --qa-pending-path "$SCRATCH/model-args-cursor-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$MODEL_ARGS_CURSOR_OUT" == *"LAUNCHER_EXIT=1"* ]] \
    && [[ -s "${MODEL_ARGS_CURSOR_TRANSCRIPT}.stderr-tail" ]]; then
    pass
else
    fail "stderr-tail-model-args" "cursor model-args path must write stderr-tail; out=$MODEL_ARGS_CURSOR_OUT"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-cursor-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-cursor-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
