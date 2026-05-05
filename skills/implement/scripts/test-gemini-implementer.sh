#!/usr/bin/env bash
# test-gemini-implementer.sh — Offline harness for scripts/launch-gemini-implement.sh.
#
# Always-on slice: PATH-stubs `gemini` and verifies launcher flag validation,
# KV-only stdout, argv shape, and prompt composition.
# Optional local smoke: pass --real-smoke with GEMINI_HEALTHY=true to run a
# real Gemini CLI prompt. Not wired into Makefile.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/scripts/launch-gemini-implement.sh"
AGENT_PROMPT="$REPO_ROOT/agents/gemini-implementer.md"

[[ -x "$LAUNCHER" ]] || { echo "FAIL: launcher not executable: $LAUNCHER" >&2; exit 1; }
[[ -f "$AGENT_PROMPT" ]] || { echo "FAIL: agent prompt missing: $AGENT_PROMPT" >&2; exit 1; }

if [[ "${1-}" == "--real-smoke" ]]; then
    if [[ "${GEMINI_HEALTHY:-false}" != "true" ]]; then
        echo "SKIP: real Gemini smoke requires GEMINI_HEALTHY=true"
        exit 0
    fi
    SCRATCH=$(mktemp -d -t gemini-implementer-smoke.XXXXXX)
    trap 'rm -rf "$SCRATCH"' EXIT
    PLAN="$SCRATCH/plan.md"
    FEATURE="$SCRATCH/feature.txt"
    printf 'Write a bailed test manifest only.\n' > "$PLAN"
    printf 'Real Gemini smoke.\n' > "$FEATURE"
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

SCRATCH=$(mktemp -d -t gemini-implementer-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

PLAN="$SCRATCH/plan.md"
FEATURE="$SCRATCH/feature.txt"
printf 'fake plan\n' > "$PLAN"
printf 'fake feature\n' > "$FEATURE"

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
capture_prompt=false
for arg in "$@"; do
    printf '%s\n' "$arg" >> "$STUB_ARGV_FILE"
    if [[ "$capture_prompt" == "true" ]]; then
        printf '%s' "$arg" > "$STUB_PROMPT_FILE"
        capture_prompt=false
    elif [[ "$arg" == "--prompt" ]]; then
        capture_prompt=true
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
    LARCH_GEMINI_MODEL="stub-model" \
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

if [[ "$(sed -n '1p' "$ARGV_FILE")" == "--prompt" ]] \
   && grep -Fxq -- '--approval-mode' "$ARGV_FILE" \
   && grep -Fxq -- 'yolo' "$ARGV_FILE" \
   && grep -Fxq -- '--skip-trust' "$ARGV_FILE" \
   && grep -Fxq -- '--model' "$ARGV_FILE" \
   && grep -Fxq -- 'stub-model' "$ARGV_FILE"; then
    pass
else
    fail 6 "Gemini argv shape should include --prompt, --approval-mode yolo, --skip-trust, and model args"
fi

if grep -Fxq -- '--output-format' "$ARGV_FILE"; then
    fail 7 "Gemini implementer launcher must not depend on --output-format"
else
    pass
fi

if grep -Fq 'Work at your maximum reasoning effort level.' "$PROMPT_FILE" \
   && grep -Fq 'Plan to implement:' "$PROMPT_FILE" \
   && grep -Fq 'Write manifest.json (atomically) at:' "$PROMPT_FILE"; then
    pass
else
    fail 8 "Gemini prompt did not include max-reasoning prefix and invocation parameters"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-gemini-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-gemini-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
