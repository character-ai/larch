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

assert_subprocess_guard_present() {
    local test_id="$1"
    if grep -Fq "persistent interactive subprocess sessions" "$AGENT_PROMPT" \
       && grep -Fq 'interactive-subprocess-unsupported' "$AGENT_PROMPT"; then
        pass
    else
        fail "$test_id" "generated codex prompt missing Hard guard #9 (issue #2991 subprocess-tool prohibition)"
    fi
}

SCRATCH=$(mktemp -d -t codex-implementer-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT
unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR REVIEW_TMPDIR || true
export LARCH_EXECUTION_ISSUES_LOG="$SCRATCH/execution-issues.md"
export LARCH_TIMING_LEDGER="$SCRATCH/timing-ledger.tsv"

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

assert_manifest_template_present "manifest-template"
assert_subprocess_guard_present "subprocess-guard"

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
STUB_CODEX="$STUB_BIN/codex"
cat > "$STUB_CODEX" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_ARGV_FILE:?}"
: "${STUB_PROMPT_FILE:?}"
: "${STUB_LAST_ARG_FILE:?}"
: "${STUB_SEPARATOR_INDEX_FILE:?}"
: "${STUB_MANIFEST_PATH:?}"
if [[ -n "${STUB_TOKEN_SESSION_FILE:-}" ]]; then
    printf '%s\n' "${LARCH_TOKEN_SESSION_ID:-}" > "$STUB_TOKEN_SESSION_FILE"
fi
if [[ -n "${STUB_CODEX_HOME_FILE:-}" ]]; then
    printf '%s\n' "${CODEX_HOME:-}" > "$STUB_CODEX_HOME_FILE"
fi
if [[ -n "${STUB_CODEX_CONFIG_FILE:-}" && -n "${CODEX_HOME:-}" && -f "$CODEX_HOME/config.toml" ]]; then
    cp "$CODEX_HOME/config.toml" "$STUB_CODEX_CONFIG_FILE"
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
    printf 'auth-error: authentication required\n' >&2
    exit 1
fi
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
TOKEN_SESSION_FILE="$SCRATCH/codex-token-session.txt"
CODEX_HOME_FILE="$SCRATCH/codex-home.txt"
CODEX_CONFIG_FILE="$SCRATCH/codex-config.toml"
IMPLEMENT_TMPDIR_FIXTURE="$SCRATCH/implement-tmpdir"
mkdir -p "$IMPLEMENT_TMPDIR_FIXTURE"
printf 'mock-codex-session\n' > "$IMPLEMENT_TMPDIR_FIXTURE/session-id"
printf 'SOURCE_FILE=/tmp/mock.jsonl\n' > "$IMPLEMENT_TMPDIR_FIXTURE/claude-source.env"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$ARGV_FILE" \
    STUB_PROMPT_FILE="$PROMPT_FILE" \
    STUB_LAST_ARG_FILE="$LAST_ARG_FILE" \
    STUB_SEPARATOR_INDEX_FILE="$SEPARATOR_INDEX_FILE" \
    STUB_MANIFEST_PATH="$MANIFEST" \
    STUB_TOKEN_SESSION_FILE="$TOKEN_SESSION_FILE" \
    STUB_CODEX_HOME_FILE="$CODEX_HOME_FILE" \
    STUB_CODEX_CONFIG_FILE="$CODEX_CONFIG_FILE" \
    IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR_FIXTURE" \
    LARCH_TOKEN_SESSION_ID="stale-codex-session" \
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

if [[ "$(cat "$TOKEN_SESSION_FILE")" == "mock-codex-session" ]]; then
    pass
else
    fail 4a "launcher did not overwrite stale LARCH_TOKEN_SESSION_ID from IMPLEMENT_TMPDIR/session-id"
fi

if [[ -s "$CODEX_HOME_FILE" ]] && [[ "$(cat "$CODEX_HOME_FILE")" == /tmp/larch-codex-home-* ]]; then
    pass
else
    fail 4b "launcher did not set CODEX_HOME to a per-invocation /tmp directory"
fi

CODEX_HOME_VALUE=$(cat "$CODEX_HOME_FILE" 2>/dev/null || true)
case "$CODEX_HOME_VALUE" in
    "$IMPLEMENT_TMPDIR_FIXTURE"|"$IMPLEMENT_TMPDIR_FIXTURE"/*)
        fail 4c "CODEX_HOME must be outside IMPLEMENT_TMPDIR/session tmpdir; got $CODEX_HOME_VALUE"
        ;;
    *)
        pass
        ;;
esac

if [[ -s "$CODEX_CONFIG_FILE" ]] \
   && [[ "$(sed -n '1p' "$CODEX_CONFIG_FILE")" == "instructions = '''" ]] \
   && grep -Fq "You are the Codex implementer for \`/implement\` Step 2" "$CODEX_CONFIG_FILE"; then
    pass
else
    fail 4d "CODEX_HOME config.toml should carry top-level implementer instructions"
fi

if [[ -s "$TRANSCRIPT" ]] && grep -Fq 'stub codex stdout' "$TRANSCRIPT"; then
    pass
else
    fail 5 "stub Codex output-last-message payload was not captured to transcript"
fi

LOCK_USER="larch-test-codex-impl-$$"
LOCK_PATH="/tmp/larch-codex-serial-${LOCK_USER}.lock"
LOCK_SEEN="$SCRATCH/codex-lock-seen.txt"
rm -rf "$LOCK_PATH"
LOCK_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    USER="$LOCK_USER" \
    STUB_ARGV_FILE="$SCRATCH/codex-lock-argv.txt" \
    STUB_PROMPT_FILE="$SCRATCH/codex-lock-prompt.txt" \
    STUB_LAST_ARG_FILE="$SCRATCH/codex-lock-last.txt" \
    STUB_SEPARATOR_INDEX_FILE="$SCRATCH/codex-lock-sep.txt" \
    STUB_MANIFEST_PATH="$SCRATCH/codex-lock-manifest.json" \
    STUB_LOCK_PATH="$LOCK_PATH" \
    STUB_LOCK_SEEN_FILE="$LOCK_SEEN" \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_SESSION_ID="codex-lock-$LOCK_USER" \
    LARCH_EXTERNAL_SERIAL_LOCK_FORCE_UNAME=Darwin \
    LARCH_EXTERNAL_SERIAL_LOCK_DELAY=1 \
    LARCH_CODEX_MODEL="stub-codex-model" \
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/codex-lock-transcript.txt" \
        --sidecar-log "$SCRATCH/codex-lock-sidecar.log" \
        --manifest-path "$SCRATCH/codex-lock-manifest.json" \
        --qa-pending-path "$SCRATCH/codex-lock-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$LOCK_OUT" == *"LAUNCHER_EXIT=0"* && "$(cat "$LOCK_SEEN" 2>/dev/null)" == "present" ]]; then
    pass
else
    fail 5a "Codex implementer should hold /tmp serial lock while spawning codex; out=$LOCK_OUT"
fi
rm -rf "$LOCK_PATH"

RETRY_COUNT="$SCRATCH/codex-retry-count.txt"
RETRY_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$SCRATCH/codex-retry-argv.txt" \
    STUB_PROMPT_FILE="$SCRATCH/codex-retry-prompt.txt" \
    STUB_LAST_ARG_FILE="$SCRATCH/codex-retry-last.txt" \
    STUB_SEPARATOR_INDEX_FILE="$SCRATCH/codex-retry-sep.txt" \
    STUB_MANIFEST_PATH="$SCRATCH/codex-retry-manifest.json" \
    STUB_COUNT_FILE="$RETRY_COUNT" \
    STUB_AUTH_FAIL_UNTIL=1 \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_SESSION_ID="codex-retry-$$" \
    LARCH_EXTERNAL_AUTH_RETRIES=2 \
    LARCH_CODEX_MODEL="stub-codex-model" \
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/codex-retry-transcript.txt" \
        --sidecar-log "$SCRATCH/codex-retry-sidecar.log" \
        --manifest-path "$SCRATCH/codex-retry-manifest.json" \
        --qa-pending-path "$SCRATCH/codex-retry-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$RETRY_OUT" == *"LAUNCHER_EXIT=0"* && "$(cat "$RETRY_COUNT" 2>/dev/null)" == "2" ]]; then
    pass
else
    fail 5b "Codex implementer should retry one auth failure; count=$(cat "$RETRY_COUNT" 2>/dev/null) out=$RETRY_OUT"
fi

FAIL_WITH_USAGE_BIN="$SCRATCH/fail-with-usage-bin"
mkdir -p "$FAIL_WITH_USAGE_BIN"
cat > "$FAIL_WITH_USAGE_BIN/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then
        output_path="$arg"
    fi
    last="$arg"
done
[[ -n "$output_path" ]] || exit 9
printf 'failed codex transcript\n' > "$output_path"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{
  "schema_version": "1",
  "status": "bailed",
  "bail_reason": "stub-bailed"
}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf '{"type":"token_usage","input_tokens":7777,"cached_input_tokens":7000,"output_tokens":222}\n'
exit 1
EOF
chmod +x "$FAIL_WITH_USAGE_BIN/codex"

FAIL_WITH_USAGE_LEDGER="$SCRATCH/fail-with-usage-ledger.jsonl"
FAIL_WITH_USAGE_TRANSCRIPT="$SCRATCH/fail-with-usage-transcript.txt"
FAIL_WITH_USAGE_SIDECAR="$SCRATCH/fail-with-usage-sidecar.log"
FAIL_WITH_USAGE_MANIFEST="$SCRATCH/fail-with-usage-manifest.json"
FAIL_WITH_USAGE_QA="$SCRATCH/fail-with-usage-qa.json"
FAIL_WITH_USAGE_OUT=$(cd "$REPO_ROOT" && \
    PATH="$FAIL_WITH_USAGE_BIN:$PATH" \
    STUB_MANIFEST_PATH="$FAIL_WITH_USAGE_MANIFEST" \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_SESSION_ID="codex-fail-with-usage-$$" \
    LARCH_TOKEN_LEDGER="$FAIL_WITH_USAGE_LEDGER" \
    LARCH_CODEX_MODEL="stub-codex-model" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$LAUNCHER" \
        --transcript-path "$FAIL_WITH_USAGE_TRANSCRIPT" \
        --sidecar-log "$FAIL_WITH_USAGE_SIDECAR" \
        --manifest-path "$FAIL_WITH_USAGE_MANIFEST" \
        --qa-pending-path "$FAIL_WITH_USAGE_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$FAIL_WITH_USAGE_OUT" == *"LAUNCHER_EXIT=1"* ]] \
   && [[ -s "$FAIL_WITH_USAGE_LEDGER" ]] \
   && jq -e 'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_implement" and .input==777 and .cache_read==7000 and .output==222 and .total==7999)' \
       "$FAIL_WITH_USAGE_LEDGER" >/dev/null 2>&1; then
    pass
else
    fail 5c "failed implement run with parseable usage should still record codex vendor row; out=$FAIL_WITH_USAGE_OUT ledger=$(cat "$FAIL_WITH_USAGE_LEDGER" 2>/dev/null)"
fi

AUTH_STDERR_ONLY_BIN="$SCRATCH/auth-stderr-only-bin"
mkdir -p "$AUTH_STDERR_ONLY_BIN"
cat > "$AUTH_STDERR_ONLY_BIN/codex" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'Error: not logged in\n' >&2
exit 7
EOF
chmod +x "$AUTH_STDERR_ONLY_BIN/codex"

AUTH_STDERR_ONLY_LEDGER="$SCRATCH/auth-stderr-only-ledger.jsonl"
AUTH_STDERR_ONLY_TRANSCRIPT="$SCRATCH/auth-stderr-only-transcript.txt"
AUTH_STDERR_ONLY_SIDECAR="$SCRATCH/auth-stderr-only-sidecar.log"
AUTH_STDERR_ONLY_MANIFEST="$SCRATCH/auth-stderr-only-manifest.json"
AUTH_STDERR_ONLY_QA="$SCRATCH/auth-stderr-only-qa.json"
AUTH_STDERR_ONLY_OUT=$(cd "$REPO_ROOT" && \
    PATH="$AUTH_STDERR_ONLY_BIN:$PATH" \
    IMPLEMENT_TMPDIR='' \
    LARCH_EXTERNAL_AUTH_RETRIES=1 \
    LARCH_TOKEN_SESSION_ID="codex-auth-stderr-only-$$" \
    LARCH_TOKEN_LEDGER="$AUTH_STDERR_ONLY_LEDGER" \
    LARCH_CODEX_MODEL="stub-codex-model" \
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
    "$LAUNCHER" \
        --transcript-path "$AUTH_STDERR_ONLY_TRANSCRIPT" \
        --sidecar-log "$AUTH_STDERR_ONLY_SIDECAR" \
        --manifest-path "$AUTH_STDERR_ONLY_MANIFEST" \
        --qa-pending-path "$AUTH_STDERR_ONLY_QA" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
if [[ "$AUTH_STDERR_ONLY_OUT" == *"LAUNCHER_EXIT=7"* ]] \
   && grep -Fq 'Error: not logged in' "$AUTH_STDERR_ONLY_SIDECAR" \
   && grep -Fq 'parse-codex-usage.sh: no usage events' "$AUTH_STDERR_ONLY_SIDECAR" \
   && [[ "$(grep -c '"type":"token_usage"' "${AUTH_STDERR_ONLY_TRANSCRIPT}.events.jsonl" 2>/dev/null | tr -d ' ')" == "0" ]] \
   && ! jq -e 'select(.type=="vendor" and .vendor=="codex")' "$AUTH_STDERR_ONLY_LEDGER" >/dev/null 2>&1; then
    pass
else
    fail 5d "stderr-only auth failure should leave empty events/no vendor row and preserve auth text; out=$AUTH_STDERR_ONLY_OUT sidecar=$(cat "$AUTH_STDERR_ONLY_SIDECAR" 2>/dev/null) ledger=$(cat "$AUTH_STDERR_ONLY_LEDGER" 2>/dev/null)"
fi

if [[ "$(sed -n '1p' "$ARGV_FILE")" == "exec" ]] \
   && [[ "$(sed -n '2p' "$ARGV_FILE")" == "--full-auto" ]] \
   && [[ "$(sed -n '3p' "$ARGV_FILE")" == "-C" ]] \
   && [[ "$(sed -n '4p' "$ARGV_FILE")" == "$REPO_ROOT" ]] \
   && [[ "$(sed -n '5p' "$ARGV_FILE")" == "--add-dir" ]] \
   && [[ "$(sed -n '6p' "$ARGV_FILE")" == "$(cd "$(dirname "$MANIFEST")" && pwd -P)" ]] \
   && [[ "$(sed -n '7p' "$ARGV_FILE")" == "--add-dir" ]] \
   && [[ "$(sed -n '8p' "$ARGV_FILE")" == "$REPO_ROOT" ]] \
   && grep -Fxq -- '-m' "$ARGV_FILE" \
   && grep -Fxq -- 'stub-codex-model' "$ARGV_FILE" \
   && grep -Fxq -- '-c' "$ARGV_FILE" \
   && grep -Fxq -- 'model_reasoning_effort="high"' "$ARGV_FILE" \
   && grep -Fxq -- "projects.\"$REPO_ROOT\".trust_level=\"trusted\"" "$ARGV_FILE" \
   && grep -Fxq -- '--output-last-message' "$ARGV_FILE"; then
    pass
else
    fail 6 "Codex argv missing required exec/full-auto/add-dir(session)/add-dir(repo)/model/output flags: $(tr '\n' ' ' < "$ARGV_FILE")"
fi

SEPARATOR_INDEX=$(sed -n '1p' "$SEPARATOR_INDEX_FILE")
ARG_INDEX=$(sed -n '2p' "$SEPARATOR_INDEX_FILE")
if [[ "$SEPARATOR_INDEX" == "$((ARG_INDEX - 1))" ]] \
   && cmp -s "$LAST_ARG_FILE" "$PROMPT_FILE"; then
    pass
else
    fail 7 "Codex argv should end with -- then the composed prompt as the last positional arg"
fi

if grep -Fq "You are the Codex implementer for \`/implement\` Step 2" "$PROMPT_FILE"; then
    fail 7a "dynamic prompt must not contain the static implementer preamble"
else
    pass
fi
if grep -Fq '## This invocation' "${TRANSCRIPT}.prompt"; then
    pass
else
    fail 7b "dynamic prompt sidecar should contain invocation parameters"
fi
if cmp -s "$PROMPT_FILE" "${TRANSCRIPT}.prompt"; then
    pass
else
    fail 7c "dynamic prompt sidecar should match the prompt passed to Codex"
fi

RESUME_TRANSCRIPT="$SCRATCH/resume-transcript.txt"
RESUME_SIDECAR="$SCRATCH/resume-sidecar.log"
RESUME_MANIFEST="$SCRATCH/resume-manifest.json"
RESUME_QA="$SCRATCH/resume-qa.json"
RESUME_ARGV="$SCRATCH/resume-argv.txt"
RESUME_PROMPT="$SCRATCH/resume-prompt.txt"
RESUME_LAST_ARG="$SCRATCH/resume-last-arg.txt"
RESUME_SEPARATOR_INDEX="$SCRATCH/resume-separator-index.txt"
RESUME_TOKEN_SESSION_FILE="$SCRATCH/resume-token-session.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$RESUME_ARGV" \
    STUB_PROMPT_FILE="$RESUME_PROMPT" \
    STUB_LAST_ARG_FILE="$RESUME_LAST_ARG" \
    STUB_SEPARATOR_INDEX_FILE="$RESUME_SEPARATOR_INDEX" \
    STUB_MANIFEST_PATH="$RESUME_MANIFEST" \
    STUB_TOKEN_SESSION_FILE="$RESUME_TOKEN_SESSION_FILE" \
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
T9_LAST_ARG="$SCRATCH/t9-last-arg.txt"
T9_SEPARATOR_INDEX="$SCRATCH/t9-separator-index.txt"
T9_TOKEN_SESSION_FILE="$SCRATCH/t9-token-session.txt"

OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$T9_ARGV" \
    STUB_PROMPT_FILE="$T9_PROMPT" \
    STUB_LAST_ARG_FILE="$T9_LAST_ARG" \
    STUB_SEPARATOR_INDEX_FILE="$T9_SEPARATOR_INDEX" \
    STUB_MANIFEST_PATH="$T9_MANIFEST" \
    STUB_TOKEN_SESSION_FILE="$T9_TOKEN_SESSION_FILE" \
    LARCH_CODEX_MODEL="stub-codex-model" \
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
    LARCH_CODEX_MODEL=$'bad\nmodel' "$LAUNCHER" \
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
   && grep -Fq 'LARCH_CODEX_MODEL' "$MODEL_SIDECAR" \
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
TENV_LAST_ARG="$SCRATCH/tenv-last-arg.txt"
TENV_SEPARATOR_INDEX="$SCRATCH/tenv-separator-index.txt"
TENV_LEDGER="$SCRATCH/tenv-timing.tsv"
cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$TENV_ARGV" \
    STUB_PROMPT_FILE="$TENV_PROMPT" \
    STUB_LAST_ARG_FILE="$TENV_LAST_ARG" \
    STUB_SEPARATOR_INDEX_FILE="$TENV_SEPARATOR_INDEX" \
    STUB_MANIFEST_PATH="$TENV_MANIFEST" \
    LARCH_CODEX_MODEL="stub-codex-model" \
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
if [[ -f "$TENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" && $6 == "codex" && $7 == "codex-implement" { found=1 } END { exit(found ? 0 : 1) }' "$TENV_LEDGER"; then
    pass
else
    fail "timing-env" "env LARCH_TIMING_TASK_KIND=--prompt should fall back to codex-implement; ledger=$(cat "$TENV_LEDGER" 2>/dev/null)"
fi
if [[ -f "$TENV_LEDGER" ]] && awk -F'\t' '$2 == "vendor" { print $7 }' "$TENV_LEDGER" | grep -Fxq -- '--prompt'; then
    fail "timing-env-leak" "env LARCH_TIMING_TASK_KIND=--prompt leaked into codex implement timing ledger"
else
    pass
fi

DISPATCHER="$REPO_ROOT/skills/implement/scripts/step2-implement.sh"
STEP2_REPO="$SCRATCH/step2-codex-retry-repo"
mkdir -p "$STEP2_REPO"
git -C "$STEP2_REPO" init -q -b main
git -C "$STEP2_REPO" config user.email "test@example.invalid"
git -C "$STEP2_REPO" config user.name "larch test"
printf 'base\n' > "$STEP2_REPO/README.md"
git -C "$STEP2_REPO" add README.md
git -C "$STEP2_REPO" commit -q -m initial
STEP2_TMP="$SCRATCH/step2-codex-retry-tmp"
mkdir -p "$STEP2_TMP"
STEP2_LEDGER="$STEP2_TMP/timing.tsv"
STEP2_OUT=$(cd "$STEP2_REPO" && \
    RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05 \
    LARCH_TIMING_LEDGER="$STEP2_LEDGER" \
    LARCH_CODEX_MODEL=$'bad\nmodel' \
    "$DISPATCHER" --tmpdir "$STEP2_TMP" --plan-file "$PLAN" --feature-file "$FEATURE" \
        --coder codex 2>&1)
STEP2_ROWS=$(awk -F'\t' '$2 == "vendor" && $6 == "codex" && $7 == "codex-implement" && $12 != "0" { c++ } END { print c + 0 }' "$STEP2_LEDGER" 2>/dev/null || echo 0)
if [[ "$STEP2_OUT" == *"STATUS=bailed"* ]] \
   && [[ "$STEP2_OUT" == *"REASON=codex-runtime-failure"* ]] \
   && [[ "$STEP2_OUT" == *"TOOL=codex"* ]] \
   && [[ "$STEP2_OUT" == *"ORCHESTRATOR_EDIT_AUTHORITY=forbidden"* ]] \
   && [[ "$STEP2_ROWS" == "2" ]] \
   && [[ ! -e "$STEP2_TMP/manifest.json" ]]; then
    pass
else
    fail "step2-codex-retry" "dispatcher should retry codex preflight failure once then bail codex-runtime-failure with two non-zero timing rows; rows=$STEP2_ROWS out=$STEP2_OUT ledger=$(cat "$STEP2_LEDGER" 2>/dev/null)"
fi

# Test 10: record-vendor smoke (issue #1351 Gap 1). Stub Codex prints a
# Codex --json usage event to stdout; after the launcher returns, dump the
# per-session ledger and assert a vendor row with per-bucket Codex usage.
# Skip when jq is unavailable — the assertion uses jq even though the
# launcher now records per-bucket tokens via parse-codex-usage.sh.
if command -v jq >/dev/null 2>&1; then
    RV_STUB_BIN="$SCRATCH/rv-bin"
    mkdir -p "$RV_STUB_BIN"
    cat > "$RV_STUB_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ -n "${CODEX_STUB_ARGV_LOG:-}" ]]; then printf '%s\n' "$arg" >> "$CODEX_STUB_ARGV_LOG"; fi
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || { echo "stub codex missing --output-last-message" >&2; exit 9; }
printf 'stub codex transcript payload\n' > "$output_path"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf '{"msg":{"usage":{"input_tokens":7777,"cached_input_tokens":0,"output_tokens":0}}}\n'
STUB_EOF
    chmod +x "$RV_STUB_BIN/codex"

    RV_SESSION_ID="rv-codex-$$"
    RV_TRANSCRIPT="$SCRATCH/rv-transcript.txt"
    RV_SIDECAR="$SCRATCH/rv-sidecar.log"
    RV_MANIFEST="$SCRATCH/rv-manifest.json"
    RV_QA="$SCRATCH/rv-qa.json"
    RV_ARGV="$SCRATCH/rv-argv.txt"

    RV_LEDGER="$SCRATCH/rv-codex-token-ledger.jsonl"
    cd "$REPO_ROOT" && \
        PATH="$RV_STUB_BIN:$PATH" \
        STUB_MANIFEST_PATH="$RV_MANIFEST" \
        CODEX_STUB_ARGV_LOG="$RV_ARGV" \
        LARCH_CODEX_MODEL="stub-codex-model" \
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

    if grep -Fxq -- '--json' "$RV_ARGV"; then
        pass
    else
        fail 10 "--json missing from codex implementer argv; argv=$(cat "$RV_ARGV" 2>/dev/null)"
    fi
    if [[ -f "$RV_LEDGER" ]] && jq -e \
        'select(.type=="vendor" and .vendor=="codex" and .raw=="codex_implement" and .input==7777 and .cache_read==0 and .output==0 and .total==7777)' \
        "$RV_LEDGER" >/dev/null 2>&1; then
        pass
    else
        fail 10 "codex record-vendor JSONL missing or buckets wrong; ledger=$RV_LEDGER content=$(cat "$RV_LEDGER" 2>/dev/null) sidecar=$(cat "$RV_SIDECAR" 2>/dev/null)"
    fi
    rm -f "$RV_LEDGER"

    cat > "$RV_STUB_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || { echo "stub codex missing --output-last-message" >&2; exit 9; }
printf 'stub codex transcript payload\n' > "$output_path"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
STUB_EOF
    chmod +x "$RV_STUB_BIN/codex"
    RV_FAIL_LEDGER="$SCRATCH/rv-codex-fail-token-ledger.jsonl"
    RV_FAIL_MANIFEST="$SCRATCH/rv-fail-manifest.json"
    cd "$REPO_ROOT" && \
        PATH="$RV_STUB_BIN:$PATH" \
        STUB_MANIFEST_PATH="$RV_FAIL_MANIFEST" \
        LARCH_CODEX_MODEL="stub-codex-model" \
        LARCH_TOKEN_SESSION_ID="rv-codex-fail-$$" \
        LARCH_TOKEN_LEDGER="$RV_FAIL_LEDGER" \
        IMPLEMENT_TMPDIR='' \
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$LAUNCHER" \
            --transcript-path "$SCRATCH/rv-fail-transcript.txt" \
            --sidecar-log "$SCRATCH/rv-fail-sidecar.log" \
            --manifest-path "$RV_FAIL_MANIFEST" \
            --qa-pending-path "$SCRATCH/rv-fail-qa.json" \
            --plan-file "$PLAN" \
            --feature-file "$FEATURE" \
            --agent-prompt "$AGENT_PROMPT" \
            --timeout 30 >/dev/null
    if [[ ! -e "$RV_FAIL_LEDGER" ]] || ! jq -e 'select(.type=="vendor" and .vendor=="codex")' "$RV_FAIL_LEDGER" >/dev/null 2>&1; then
        pass
    else
        fail 10 "codex fail-closed no-usage case should not append vendor row; ledger=$(cat "$RV_FAIL_LEDGER" 2>/dev/null)"
    fi

    cat > "$RV_STUB_BIN/codex" <<'STUB_EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${STUB_MANIFEST_PATH:?}"
output_path=""
last=""
for arg in "$@"; do
    if [[ "$last" == "--output-last-message" ]]; then output_path="$arg"; fi
    last="$arg"
done
[[ -n "$output_path" ]] || { echo "stub codex missing --output-last-message" >&2; exit 9; }
printf 'stub codex transcript schema drift\n' > "$output_path"
cat > "$STUB_MANIFEST_PATH.tmp" <<JSON
{"schema_version":"1","status":"bailed","bail_reason":"stub-bailed"}
JSON
mv "$STUB_MANIFEST_PATH.tmp" "$STUB_MANIFEST_PATH"
printf '{"type":"token_usage","input_tokens":"abc","cached_input_tokens":0,"output_tokens":1}\n'
STUB_EOF
    chmod +x "$RV_STUB_BIN/codex"
    RV_DRIFT_LEDGER="$SCRATCH/rv-codex-drift-token-ledger.jsonl"
    RV_DRIFT_MANIFEST="$SCRATCH/rv-drift-manifest.json"
    RV_DRIFT_SIDECAR="$SCRATCH/rv-drift-sidecar.log"
    cd "$REPO_ROOT" && \
        PATH="$RV_STUB_BIN:$PATH" \
        STUB_MANIFEST_PATH="$RV_DRIFT_MANIFEST" \
        LARCH_CODEX_MODEL="stub-codex-model" \
        LARCH_TOKEN_SESSION_ID="rv-codex-drift-$$" \
        LARCH_TOKEN_LEDGER="$RV_DRIFT_LEDGER" \
        IMPLEMENT_TMPDIR='' \
        CLAUDE_PLUGIN_ROOT="$REPO_ROOT" \
        "$LAUNCHER" \
            --transcript-path "$SCRATCH/rv-drift-transcript.txt" \
            --sidecar-log "$RV_DRIFT_SIDECAR" \
            --manifest-path "$RV_DRIFT_MANIFEST" \
            --qa-pending-path "$SCRATCH/rv-drift-qa.json" \
            --plan-file "$PLAN" \
            --feature-file "$FEATURE" \
            --agent-prompt "$AGENT_PROMPT" \
            --timeout 30 >/dev/null
    if grep -Fq 'parse-codex-usage.sh: jq failed' "$RV_DRIFT_SIDECAR" 2>/dev/null; then
        pass
    else
        fail 10 "codex schema drift should append parse diagnostic to sidecar; sidecar=$(cat "$RV_DRIFT_SIDECAR" 2>/dev/null)"
    fi
    if [[ ! -e "$RV_DRIFT_LEDGER" ]] || ! jq -e 'select(.type=="vendor" and .vendor=="codex")' "$RV_DRIFT_LEDGER" >/dev/null 2>&1; then
        pass
    else
        fail 10 "codex schema drift should not append vendor row; ledger=$(cat "$RV_DRIFT_LEDGER" 2>/dev/null)"
    fi
else
    pass  # jq absent — skip per launcher runtime guard parallel
fi

# Test 11: --manifest-path and --qa-pending-path with different parents -> exit 2.
EXIT=0
T11_OUT="$SCRATCH/t11-output.txt"
mkdir -p "$SCRATCH/t11-other-parent"
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t11-transcript.txt" \
    --sidecar-log "$SCRATCH/t11-sidecar.log" \
    --manifest-path "$SCRATCH/t11-manifest.json" \
    --qa-pending-path "$SCRATCH/t11-other-parent/qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 30 >"$T11_OUT" 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq "must share the same parent directory" "$T11_OUT"; then
    pass
else
    fail 11 "mismatched manifest/qa-pending parents should exit 2 with the parent-mismatch message, got $EXIT: $(cat "$T11_OUT")"
fi

# Test 12: --manifest-path under a non-existent parent directory -> exit 2.
EXIT=0
T12_OUT="$SCRATCH/t12-output.txt"
"$LAUNCHER" \
    --transcript-path "$SCRATCH/t12-transcript.txt" \
    --sidecar-log "$SCRATCH/t12-sidecar.log" \
    --manifest-path "$SCRATCH/t12-missing-subdir/manifest.json" \
    --qa-pending-path "$SCRATCH/t12-missing-subdir/qa.json" \
    --plan-file "$PLAN" \
    --feature-file "$FEATURE" \
    --agent-prompt "$AGENT_PROMPT" \
    --timeout 30 >"$T12_OUT" 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq "session tmpdir does not exist" "$T12_OUT"; then
    pass
else
    fail 12 "missing session tmpdir should exit 2 with the does-not-exist message, got $EXIT: $(cat "$T12_OUT")"
fi

# Test 13 (issue #1480 Bug #2): defensive `--timing-task-kind` validation.
# Empty or flag-like values must be rejected with exit 2 and a clear message.
# Pass `--timing-task-kind` first so the new validation fires before any
# unrelated argv check; required flags below the validation are not reached.
T13_OUT="$SCRATCH/t13-empty.out"
EXIT=0
"$LAUNCHER" --timing-task-kind "" >"$T13_OUT" 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq "non-empty, non-flag-like value" "$T13_OUT"; then
    pass
else
    fail 13 "empty timing-task-kind should exit 2 with non-empty-non-flag-like message, got $EXIT: $(cat "$T13_OUT")"
fi

T13b_OUT="$SCRATCH/t13b-flaglike.out"
EXIT=0
"$LAUNCHER" --timing-task-kind --plan-file >"$T13b_OUT" 2>&1 || EXIT=$?
if [[ "$EXIT" == "2" ]] && grep -Fq "non-empty, non-flag-like value" "$T13b_OUT"; then
    pass
else
    fail 13b "flag-like timing-task-kind should exit 2 with non-empty-non-flag-like message, got $EXIT: $(cat "$T13b_OUT")"
fi

# Test cap-hit: when the per-step token budget cap is exceeded, the launcher
# exits immediately with LAUNCHER_EXIT=0 MANIFEST_WRITTEN=false STATUS=cap_hit
# without invoking the underlying Codex binary.
CH_SESSION="cap-hit-codex-$$-$RANDOM"
CH_LEDGER="$SCRATCH/cap-hit-codex-ledger.jsonl"
printf '{"type":"vendor","vendor":"codex","total":9999}\n' > "$CH_LEDGER"

CH_ARGV="$SCRATCH/cap-hit-codex-argv.txt"
CH_OUT=$(cd "$REPO_ROOT" && \
    PATH="$STUB_BIN:$PATH" \
    STUB_ARGV_FILE="$CH_ARGV" \
    STUB_PROMPT_FILE="$SCRATCH/cap-hit-codex-prompt.txt" \
    STUB_LAST_ARG_FILE="$SCRATCH/cap-hit-codex-last-arg.txt" \
    STUB_SEPARATOR_INDEX_FILE="$SCRATCH/cap-hit-codex-sep.txt" \
    STUB_MANIFEST_PATH="$SCRATCH/cap-hit-codex-manifest.json" \
    IMPLEMENT_TMPDIR='' \
    LARCH_TOKEN_LEDGER="$CH_LEDGER" \
    LARCH_TOKEN_SESSION_ID="$CH_SESSION" \
    LARCH_TOKEN_BUDGET_CAP_IMPLEMENT=1 \
    LARCH_CODEX_MODEL="stub-codex-model" \
    "$LAUNCHER" \
        --transcript-path "$SCRATCH/cap-hit-codex-transcript.txt" \
        --sidecar-log "$SCRATCH/cap-hit-codex-sidecar.log" \
        --manifest-path "$SCRATCH/cap-hit-codex-manifest.json" \
        --qa-pending-path "$SCRATCH/cap-hit-codex-qa.json" \
        --plan-file "$PLAN" \
        --feature-file "$FEATURE" \
        --agent-prompt "$AGENT_PROMPT" \
        --timeout 30)
rm -f "$CH_LEDGER"

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
    fail "cap-hit-no-invoke" "cap_hit path must not invoke the underlying Codex binary"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-codex-implementer.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-codex-implementer.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
