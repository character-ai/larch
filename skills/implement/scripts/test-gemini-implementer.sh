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

# Tighten run-external-agent.sh's poll cadence so the wrapper does not pay a
# 10s sleep per stub invocation. Production callers (real Gemini) inherit the
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

assert_model_rejection() {
    local label="$1"
    local value="$2"
    local transcript="$SCRATCH/model-$label-transcript.txt"
    local sidecar="$SCRATCH/model-$label-sidecar.log"
    local manifest="$SCRATCH/model-$label-manifest.json"
    local qa="$SCRATCH/model-$label-qa.json"
    local stdout="$SCRATCH/model-$label-stdout.txt"
    local code=0
    (
        cd "$REPO_ROOT"
        LARCH_GEMINI_MODEL="$value" "$LAUNCHER" \
            --transcript-path "$transcript" \
            --sidecar-log "$sidecar" \
            --manifest-path "$manifest" \
            --qa-pending-path "$qa" \
            --plan-file "$PLAN" \
            --feature-file "$FEATURE" \
            --agent-prompt "$AGENT_PROMPT" \
            --timeout 30
    ) >"$stdout" 2>&1 || code=$?
    if [[ "$code" == "0" ]] \
       && grep -Fxq 'LAUNCHER_EXIT=1' "$stdout" \
       && grep -Fxq 'MANIFEST_WRITTEN=false' "$stdout" \
       && grep -Fxq 'QA_PENDING_WRITTEN=false' "$stdout" \
       && grep -Fq 'ERROR: gemini model from LARCH_GEMINI_MODEL' "$sidecar"; then
        pass
    else
        fail "model-$label" "model rejection should exit 0 with LAUNCHER_EXIT=1 and sidecar diagnostic; code=$code stdout=$(cat "$stdout") sidecar=$(cat "$sidecar" 2>/dev/null)"
    fi
}

assert_model_rejection "empty" ""
assert_model_rejection "space" " "
assert_model_rejection "newline" $'foo\n'
assert_model_rejection "tab" $'\t'
assert_model_rejection "control-byte" $'foo\x01'

# Model rejection must not promote stale artifacts from prior attempts.
PRESEEDED_TRANSCRIPT="$SCRATCH/model-preseed-transcript.txt"
PRESEEDED_SIDECAR="$SCRATCH/model-preseed-sidecar.log"
PRESEEDED_MANIFEST="$SCRATCH/model-preseed-manifest.json"
PRESEEDED_QA="$SCRATCH/model-preseed-qa.json"
PRESEEDED_STDOUT="$SCRATCH/model-preseed-stdout.txt"
printf '{"status":"complete"}\n' > "$PRESEEDED_MANIFEST"
printf '{"qa":"pending"}\n' > "$PRESEEDED_QA"
EXIT=0
(
    cd "$REPO_ROOT"
    LARCH_GEMINI_MODEL=$'bad\x01model' "$LAUNCHER" \
        --transcript-path "$PRESEEDED_TRANSCRIPT" \
        --sidecar-log "$PRESEEDED_SIDECAR" \
        --manifest-path "$PRESEEDED_MANIFEST" \
        --qa-pending-path "$PRESEEDED_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30
) >"$PRESEEDED_STDOUT" 2>&1 || EXIT=$?
if [[ "$EXIT" == "0" ]] \
   && grep -Fxq 'LAUNCHER_EXIT=1' "$PRESEEDED_STDOUT" \
   && grep -Fxq 'MANIFEST_WRITTEN=false' "$PRESEEDED_STDOUT" \
   && grep -Fxq 'QA_PENDING_WRITTEN=false' "$PRESEEDED_STDOUT" \
   && ! grep -Fxq 'MANIFEST_WRITTEN=true' "$PRESEEDED_STDOUT" \
   && ! grep -Fxq 'QA_PENDING_WRITTEN=true' "$PRESEEDED_STDOUT"; then
    pass
else
    fail "model-preseed" "model rejection with pre-existing manifest/qa should force false flags; exit=$EXIT stdout=$(cat "$PRESEEDED_STDOUT")"
fi

STUB_BIN="$SCRATCH/bin"
mkdir -p "$STUB_BIN"
STUB_GEMINI="$STUB_BIN/gemini"
cat > "$STUB_GEMINI" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_ARGV_FILE:?}"
: "${STUB_PROMPT_FILE:?}"
: "${STUB_MANIFEST_PATH:?}"
if [[ -n "${STUB_TOKEN_SESSION_FILE:-}" ]]; then
    printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$STUB_TOKEN_SESSION_FILE"
fi
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
TOKEN_SESSION_FILE="$SCRATCH/gemini-token-session.txt"
IMPLEMENT_TMPDIR_FIXTURE="$SCRATCH/implement-tmpdir"
mkdir -p "$IMPLEMENT_TMPDIR_FIXTURE"
printf 'mock-gemini-session\n' > "$IMPLEMENT_TMPDIR_FIXTURE/session-id"
printf 'SOURCE_FILE=/tmp/mock.jsonl\n' > "$IMPLEMENT_TMPDIR_FIXTURE/claude-source.env"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$ARGV_FILE" \
    STUB_PROMPT_FILE="$PROMPT_FILE" \
    STUB_MANIFEST_PATH="$MANIFEST" \
    STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_FILE" \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_FIXTURE" \
    LARCH_TOKEN_SESSION_ID="stale-gemini-session" \
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

if [[ "$(cat "$TOKEN_SESSION_FILE")" == "mock-gemini-session" ]]; then
    pass
else
    fail 4a "launcher did not overwrite stale LARCH_TOKEN_SESSION_ID from IMPLEMENT_TMPDIR/session-id"
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
    LARCH_GEMINI_MODEL="stub-gemini-model" \
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
    LARCH_GEMINI_MODEL="stub-gemini-model" \
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
if [[ -f "$TENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" && $6 == "gemini" && $7 == "gemini-implement" { found=1 } END { exit(found ? 0 : 1) }' "$TENV_LEDGER"; then
    pass
else
    fail "timing-env" "env LARCH_TIMING_TASK_KIND=--prompt should fall back to gemini-implement; ledger=$(cat "$TENV_LEDGER" 2>/dev/null)"
fi
if [[ -f "$TENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" { print $7 }' "$TENV_LEDGER" | grep -Fxq -- '--prompt'; then
    fail "timing-env-leak" "env LARCH_TIMING_TASK_KIND=--prompt leaked into gemini implement timing ledger"
else
    pass
fi

# Test 10 (issue #1480 Bug #2): defensive `--timing-task-kind` validation.
# Empty or flag-like values must be rejected with exit 2 and a clear message.
# Pass `--timing-task-kind` first so the new validation fires before any
# unrelated argv check; required flags below the validation are not reached.
T10_RC=0
T10_OUT=$("$LAUNCHER" --timing-task-kind "" 2>&1) || T10_RC=$?
if [[ "$T10_RC" == "2" ]] && grep -Fq "non-empty, non-flag-like value" <<<"$T10_OUT"; then
    pass
else
    fail 10 "empty timing-task-kind should exit 2 with non-empty-non-flag-like message, got rc=$T10_RC: $T10_OUT"
fi

T10b_RC=0
T10b_OUT=$("$LAUNCHER" --timing-task-kind --plan-file 2>&1) || T10b_RC=$?
if [[ "$T10b_RC" == "2" ]] && grep -Fq "non-empty, non-flag-like value" <<<"$T10b_OUT"; then
    pass
else
    fail 10b "flag-like timing-task-kind should exit 2 with non-empty-non-flag-like message, got rc=$T10b_RC: $T10b_OUT"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-gemini-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-gemini-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
