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
STUB_CURSOR="$STUB_BIN/cursor"
cat > "$STUB_CURSOR" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
last=""
: "${STUB_ARGV_FILE:?}"
: "${STUB_PROMPT_FILE:?}"
: "${STUB_MANIFEST_PATH:?}"
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

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$ARGV_FILE" \
    STUB_PROMPT_FILE="$PROMPT_FILE" \
    STUB_MANIFEST_PATH="$MANIFEST" \
    LARCH_CURSOR_MODEL="stub-model" \
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

if [[ -s "$TRANSCRIPT" ]] && grep -Fq 'stub cursor stdout' "$TRANSCRIPT"; then
    pass
else
    fail 5 "stub Cursor stdout was not captured to transcript"
fi

if [[ "$(sed -n '5p' "$ARGV_FILE")" == "--model" ]] \
   && [[ "$(sed -n '6p' "$ARGV_FILE")" == "stub-model" ]] \
   && [[ "$(sed -n '7p' "$ARGV_FILE")" == "--workspace" ]] \
   && [[ "$(sed -n '8p' "$ARGV_FILE")" == "$REPO_ROOT" ]]; then
    pass
else
    fail 6 "Cursor argv shape should place --workspace after model args and before prompt"
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

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-cursor-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-cursor-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
