#!/usr/bin/env bash
# test-codex-implementer.sh — Offline harness for scripts/launch-codex-implement.sh.
#
# PATH-stubs `codex` and verifies launcher flag validation, KV-only stdout,
# argv shape, model forwarding, transcript writing, and resume prompt
# composition.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/scripts/launch-codex-implement.sh"
AGENT_PROMPT="$REPO_ROOT/agents/codex-implementer.md"

[[ -x "$LAUNCHER" ]] || { echo "FAIL: launcher not executable: $LAUNCHER" >&2; exit 1; }
[[ -f "$AGENT_PROMPT" ]] || { echo "FAIL: agent prompt missing: $AGENT_PROMPT" >&2; exit 1; }

PASS_COUNT=0
FAIL_COUNT=0
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }

SCRATCH=$(mktemp -d -t codex-implementer-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

# Tighten run-external-agent.sh's poll cadence so the wrapper does not pay a
# 10s sleep per stub invocation. Production callers (real Codex) inherit the
# default 10s. See scripts/run-external-agent.md.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05

PLAN="$SCRATCH/plan.md"
FEATURE="$SCRATCH/feature.txt"
ANSWERS="$SCRATCH/answers.json"
printf 'fake plan\n' > "$PLAN"
printf 'fake feature\n' > "$FEATURE"
printf '{"answers":[{"id":"q1","text":"answer"}]}\n' > "$ANSWERS"

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

# Test 3: missing input file exits 2.
EXIT=0
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t3-transcript.txt" \
    --sidecar-log "$SCRATCH/t3-sidecar.log" \
    --manifest-path "$SCRATCH/t3-manifest.json" \
    --qa-pending-path "$SCRATCH/t3-qa.json" \
    --plan-file "$SCRATCH/missing-plan.md" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 30 >/dev/null 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]]; then pass; else fail 3 "missing plan should exit 2, got $EXIT"; fi

STUB_BIN="$SCRATCH/bin"
mkdir -p "$STUB_BIN"
STUB_CODEX="$STUB_BIN/codex"
cat > "$STUB_CODEX" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_ARGV_FILE:?}"
: "${STUB_PROMPT_FILE:?}"
: "${STUB_LAST_ARG_FILE:?}"
: "${STUB_SEPARATOR_INDEX_FILE:?}"
: "${STUB_MANIFEST_PATH:?}"
output_path=""
separator_seen=false
index=0
separator_index=0
last=""
for arg in "$@"; do
    index=$((index + 1))
    printf '%s\n' "$arg" >> "$STUB_ARGV_FILE"
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    if [[ "$separator_seen" == "true" ]]; then
        printf '%s' "$arg" > "$STUB_PROMPT_FILE"
    fi
    if [[ "$arg" == "--" ]]; then
        separator_seen=true
        separator_index=$index
    fi
    last="$arg"
done
[[ -n "$output_path" ]] || { echo "stub codex missing --output-last-message" >&2; exit 9; }
printf '%s' "$last" > "$STUB_LAST_ARG_FILE"
printf '%s\n%s\n' "$separator_index" "$index" > "$STUB_SEPARATOR_INDEX_FILE"
printf 'stub codex stdout\n' > "$output_path"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'stub codex stdout\n'
EOF
chmod +x "$STUB_CODEX"

TRANSCRIPT="$SCRATCH/transcript.txt"
SIDECAR="$SCRATCH/sidecar.log"
MANIFEST="$SCRATCH/manifest.json"
QA_PENDING="$SCRATCH/qa-pending.json"
ARGV_FILE="$SCRATCH/codex-argv.txt"
PROMPT_FILE="$SCRATCH/codex-prompt.txt"
LAST_ARG_FILE="$SCRATCH/codex-last-arg.txt"
SEPARATOR_INDEX_FILE="$SCRATCH/codex-separator-index.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$ARGV_FILE" \
    STUB_PROMPT_FILE="$PROMPT_FILE" \
    STUB_LAST_ARG_FILE="$LAST_ARG_FILE" \
    STUB_SEPARATOR_INDEX_FILE="$SEPARATOR_INDEX_FILE" \
    STUB_MANIFEST_PATH="$MANIFEST" \
    LARCH_CODEX_MODEL="stub-codex-model" \
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

if [[ -s "$TRANSCRIPT" ]] && grep -Fq 'stub codex stdout' "$TRANSCRIPT"; then
    pass
else
    fail 5 "stub Codex output-last-message payload was not captured to transcript"
fi

if [[ "$(sed -n '1p' "$ARGV_FILE")" == "exec" ]] \
   && [[ "$(sed -n '2p' "$ARGV_FILE")" == "--full-auto" ]] \
   && [[ "$(sed -n '3p' "$ARGV_FILE")" == "-C" ]] \
   && [[ "$(sed -n '4p' "$ARGV_FILE")" == "$REPO_ROOT" ]] \
   && grep -Fxq -- '-m' "$ARGV_FILE" \
   && grep -Fxq -- 'stub-codex-model' "$ARGV_FILE" \
   && grep -Fxq -- '-c' "$ARGV_FILE" \
   && grep -Fxq -- 'model_reasoning_effort="high"' "$ARGV_FILE" \
   && grep -Fxq -- '--output-last-message' "$ARGV_FILE"; then
    pass
else
    fail 6 "Codex argv missing required exec/full-auto/model/output flags: $(tr '\n' ' ' < "$ARGV_FILE")"
fi

SEPARATOR_INDEX=$(sed -n '1p' "$SEPARATOR_INDEX_FILE")
ARG_INDEX=$(sed -n '2p' "$SEPARATOR_INDEX_FILE")
if [[ "$SEPARATOR_INDEX" == "$((ARG_INDEX - 1))" ]] \
   && cmp -s "$LAST_ARG_FILE" "$PROMPT_FILE"; then
    pass
else
    fail 7 "Codex argv should end with -- then the composed prompt as the last positional arg"
fi

RESUME_TRANSCRIPT="$SCRATCH/resume-transcript.txt"
RESUME_SIDECAR="$SCRATCH/resume-sidecar.log"
RESUME_MANIFEST="$SCRATCH/resume-manifest.json"
RESUME_QA="$SCRATCH/resume-qa.json"
RESUME_ARGV="$SCRATCH/resume-argv.txt"
RESUME_PROMPT="$SCRATCH/resume-prompt.txt"
RESUME_LAST_ARG="$SCRATCH/resume-last-arg.txt"
RESUME_SEPARATOR_INDEX="$SCRATCH/resume-separator-index.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$RESUME_ARGV" \
    STUB_PROMPT_FILE="$RESUME_PROMPT" \
    STUB_LAST_ARG_FILE="$RESUME_LAST_ARG" \
    STUB_SEPARATOR_INDEX_FILE="$RESUME_SEPARATOR_INDEX" \
    STUB_MANIFEST_PATH="$RESUME_MANIFEST" \
    LARCH_CODEX_MODEL="stub-codex-model" \
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
    fail 8 "resume invocation block missing from composed prompt"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-codex-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-codex-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
