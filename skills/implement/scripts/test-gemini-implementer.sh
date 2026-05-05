#!/usr/bin/env bash
# test-gemini-implementer.sh — Offline harness for scripts/launch-gemini-implement.sh.
#
# PATH-stubs `gemini` and verifies launcher flag validation, KV-only stdout,
# argv shape, model forwarding, sidecar redirection, and resume prompt
# composition.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/scripts/launch-gemini-implement.sh"
AGENT_PROMPT="$REPO_ROOT/agents/gemini-implementer.md"

[[ -x "$LAUNCHER" ]] || { echo "FAIL: launcher not executable: $LAUNCHER" >&2; exit 1; }
[[ -f "$AGENT_PROMPT" ]] || { echo "FAIL: agent prompt missing: $AGENT_PROMPT" >&2; exit 1; }

PASS_COUNT=0
FAIL_COUNT=0
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }

SCRATCH=$(mktemp -d -t gemini-implementer-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

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
STUB_GEMINI="$STUB_BIN/gemini"
cat > "$STUB_GEMINI" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_ARGV_FILE:?}"
: "${STUB_PROMPT_FILE:?}"
: "${STUB_MANIFEST_PATH:?}"
prompt_next=false
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$STUB_ARGV_FILE"
    if [[ "$prompt_next" == "true" ]]; then
        printf '%s' "$arg" > "$STUB_PROMPT_FILE"
        prompt_next=false
    elif [[ "$arg" == "--prompt" ]]; then
        prompt_next=true
    fi
done
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf 'stub gemini stdout\n'
EOF
chmod +x "$STUB_GEMINI"

TRANSCRIPT="$SCRATCH/transcript.txt"
SIDECAR="$SCRATCH/sidecar.log"
MANIFEST="$SCRATCH/manifest.json"
QA_PENDING="$SCRATCH/qa-pending.json"
ARGV_FILE="$SCRATCH/gemini-argv.txt"
PROMPT_FILE="$SCRATCH/gemini-prompt.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$ARGV_FILE" \
    STUB_PROMPT_FILE="$PROMPT_FILE" \
    STUB_MANIFEST_PATH="$MANIFEST" \
    LARCH_GEMINI_MODEL="stub-gemini-model" \
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

if [[ -s "$TRANSCRIPT" ]] && grep -Fq 'stub gemini stdout' "$TRANSCRIPT"; then
    pass
else
    fail 5 "stub Gemini stdout was not captured to transcript"
fi

if grep -Fxq -- '--prompt' "$ARGV_FILE" \
   && grep -Fxq -- '--approval-mode' "$ARGV_FILE" \
   && grep -Fxq -- 'yolo' "$ARGV_FILE" \
   && grep -Fxq -- '--skip-trust' "$ARGV_FILE" \
   && grep -Fxq -- '--model' "$ARGV_FILE" \
   && grep -Fxq -- 'stub-gemini-model' "$ARGV_FILE"; then
    pass
else
    fail 6 "Gemini argv missing required headless/model flags: $(tr '\n' ' ' < "$ARGV_FILE")"
fi

if grep -Fxq -- '--output-format' "$ARGV_FILE" || grep -Fxq -- 'json' "$ARGV_FILE"; then
    fail 7 "Gemini implementer argv must not request stdout JSON"
else
    pass
fi

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
    LARCH_GEMINI_MODEL="stub-gemini-model" \
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
    echo "PASS: test-gemini-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-gemini-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
