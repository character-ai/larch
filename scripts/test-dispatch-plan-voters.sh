#!/usr/bin/env bash
# Regression harness for scripts/dispatch-plan-voters.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/dispatch-plan-voters.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-dispatch-plan-voters.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PLUGIN="$TMP/plugin"
mkdir -p "$PLUGIN/scripts"

cat > "$PLUGIN/scripts/agent-model-args.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tool=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="$2"; shift 2 ;;
        --with-effort) shift ;;
        *) shift ;;
    esac
done
case "$tool" in
    codex) printf '%s\n' -m stub-codex -c 'model_reasoning_effort="high"' ;;
    cursor) printf '%s\n' --model stub-cursor ;;
    *) exit 1 ;;
esac
STUB
chmod +x "$PLUGIN/scripts/agent-model-args.sh"

cat > "$PLUGIN/scripts/cursor-auth-flags.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' --api-key stub-key
STUB
chmod +x "$PLUGIN/scripts/cursor-auth-flags.sh"

cat > "$PLUGIN/scripts/cursor-wrap-prompt.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf ' /max-mode on. Prompt: %s' "$1"
STUB
chmod +x "$PLUGIN/scripts/cursor-wrap-prompt.sh"

cat > "$PLUGIN/scripts/append-tool-failure.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${APPEND_LOG:?}"
STUB
chmod +x "$PLUGIN/scripts/append-tool-failure.sh"

cat > "$PLUGIN/scripts/wait-for-reviewers.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--timeout" ]]; then shift 2; fi
idx=0
for sentinel in "$@"; do
    idx=$((idx + 1))
    for _ in 1 2 3 4 5; do
        [[ -f "$sentinel" ]] && break
        sleep 0.05
    done
    if [[ -f "$sentinel" ]]; then
        code=$(tr -d '[:space:]' < "$sentinel")
        printf 'DONE %s %s: exit=%s\n' "$idx" "$(basename "$sentinel" .done)" "$code"
    else
        printf 'TIMEOUT %s %s\n' "$idx" "$(basename "$sentinel" .done)"
    fi
done
STUB
chmod +x "$PLUGIN/scripts/wait-for-reviewers.sh"

cat > "$PLUGIN/scripts/run-external-agent.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
tool=""
output=""
capture="false"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) tool="$2"; shift 2 ;;
        --output) output="$2"; shift 2 ;;
        --timeout) shift 2 ;;
        --capture-stdout) capture="true"; shift ;;
        --) shift; break ;;
        *) shift ;;
    esac
done
{
    printf 'INVOCATION tool=%s output=%s capture=%s\n' "$tool" "$output" "$capture"
    for arg in "$@"; do printf 'ARG %s\n' "$arg"; done
    printf 'END\n'
} >> "${RUN_LOG:?}"
if [[ "${FAIL_TOOL:-}" == "$tool" ]]; then
    printf 'failed %s\n' "$tool" > "$output"
    printf '23\n' > "$output.done"
    exit 23
fi
printf '%s vote ok\n' "$tool" > "$output"
printf '0\n' > "$output.done"
STUB
chmod +x "$PLUGIN/scripts/run-external-agent.sh"

BALLOT="$TMP/ballot.txt"
printf 'FINDING_1: example\n' > "$BALLOT"

RUN_LOG="$TMP/run.log"
APPEND_LOG="$TMP/append.log"
export RUN_LOG APPEND_LOG

assert_contains() {
    local label="$1" needle="$2" file="$3"
    if ! grep -Fq -- "$needle" "$file"; then
        echo "FAIL: $label: missing '$needle' in $file" >&2
        exit 1
    fi
}

assert_not_contains() {
    local label="$1" needle="$2" file="$3"
    if grep -Fq -- "$needle" "$file"; then
        echo "FAIL: $label: unexpected '$needle' in $file" >&2
        exit 1
    fi
}

out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --design-tmpdir "$TMP/happy" \
    --codex-available true \
    --cursor-available true \
    --session-env-path "$TMP/session.env")
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out"
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out"
grep -Fq 'DISPATCH_OK=true' <<< "$out"
assert_contains "codex launched through wrapper" "INVOCATION tool=codex" "$RUN_LOG"
assert_contains "cursor launched through wrapper" "INVOCATION tool=cursor" "$RUN_LOG"
assert_contains "codex read-only sandbox" "ARG --sandbox" "$RUN_LOG"
assert_contains "cursor plan mode" "ARG --mode" "$RUN_LOG"
assert_contains "codex output arg" "ARG --output-last-message" "$RUN_LOG"
assert_contains "cursor wrapped prompt" "ARG  /max-mode on. Prompt:" "$RUN_LOG"
if find "$TMP/happy" -name '*plan-voter-prompt*' -print | grep -q .; then
    echo "FAIL: prompt temp files were not cleaned up" >&2
    exit 1
fi

: > "$RUN_LOG"
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --design-tmpdir "$TMP/codex-fallback" \
    --codex-available false \
    --cursor-available true)
grep -Fq 'VOTER_2_STATUS=fallback' <<< "$out"
grep -Fq 'VOTER_3_STATUS=launched' <<< "$out"
assert_not_contains "codex not launched when unavailable" "INVOCATION tool=codex" "$RUN_LOG"
assert_contains "cursor still launched" "INVOCATION tool=cursor" "$RUN_LOG"

: > "$RUN_LOG"
out=$(CLAUDE_PLUGIN_ROOT="$PLUGIN" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --design-tmpdir "$TMP/cursor-fallback" \
    --codex-available true \
    --cursor-available false)
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out"
grep -Fq 'VOTER_3_STATUS=fallback' <<< "$out"
assert_contains "codex still launched" "INVOCATION tool=codex" "$RUN_LOG"
assert_not_contains "cursor not launched when unavailable" "INVOCATION tool=cursor" "$RUN_LOG"

: > "$RUN_LOG"
: > "$APPEND_LOG"
out=$(FAIL_TOOL=codex CLAUDE_PLUGIN_ROOT="$PLUGIN" "$SCRIPT" \
    --ballot-file "$BALLOT" \
    --design-tmpdir "$TMP/launch-failure" \
    --codex-available true \
    --cursor-available false \
    --session-env-path "$TMP/session.env")
grep -Fq 'VOTER_2_STATUS=launched' <<< "$out"
grep -Fq 'DISPATCH_OK=false' <<< "$out"
assert_contains "launch failure appended" "run-external-agent.sh codex plan voter" "$APPEND_LOG"

assert_contains "wrapper reference present" "run-external-agent.sh" "$SCRIPT"
awk '
    /codex exec|cursor agent/ {
        if (prev !~ /RUN_EXTERNAL_AGENT/) {
            printf "FAIL: direct external-agent command found outside wrapper argv: %s\n", $0 > "/dev/stderr"
            exit 1
        }
    }
    { prev = $0 }
' "$SCRIPT"

echo "All assertions passed."
