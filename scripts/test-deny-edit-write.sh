#!/usr/bin/env bash
# test-deny-edit-write.sh — Regression harness for scripts/deny-edit-write.sh.
#
# Black-box tests cover the token-scoped activation gate and the active
# canonical-/tmp path policy. The harness isolates XDG_CACHE_HOME so local
# sentinels cannot affect results.
#
# Usage:
#   bash scripts/test-deny-edit-write.sh

set -euo pipefail
export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HOOK="$REPO_ROOT/scripts/deny-edit-write.sh"
CACHE_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/test-deny-edit-write-cache-XXXXXX")
ACTIVATION_DIR="$CACHE_ROOT/larch/deny-edit-write-active"
TEST_HOME="$CACHE_ROOT/home"
mkdir -p "$TEST_HOME"
trap 'rm -rf "$CACHE_ROOT" "${STUB_DIR:-}"' EXIT

if [[ ! -x "$HOOK" ]]; then
    echo "ERROR: hook script not found or not executable: $HOOK" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "FAIL: harness jq not on PATH; cannot validate JSON output" >&2
    exit 1
fi

PASS=0
FAIL=0

fail() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1" >&2
}

pass() {
    PASS=$((PASS + 1))
}

reset_activation() {
    rm -rf "$ACTIVATION_DIR"
    mkdir -p "$ACTIVATION_DIR"
}

activate() {
    local token="$1"
    local pid="${2:-$$}"
    mkdir -p "$ACTIVATION_DIR"
    : > "$ACTIVATION_DIR/$token-$pid"
}

stale_activation() {
    local token="$1"
    local path="$ACTIVATION_DIR/$token-stale"
    mkdir -p "$ACTIVATION_DIR"
    : > "$path"
    python3 - "$path" <<'PY'
import os
import sys
import time

path = sys.argv[1]
stale = time.time() - (7 * 60 * 60)
os.utime(path, (stale, stale))
PY
}

invoke() {
    # Run the hook with the given JSON payload on stdin; echo stdout.
    local token="$1"
    local payload="$2"
    if [[ -n "$token" ]]; then
        printf '%s' "$payload" | env XDG_CACHE_HOME="$CACHE_ROOT" HOME="$TEST_HOME" "$HOOK" "$token"
    else
        printf '%s' "$payload" | env XDG_CACHE_HOME="$CACHE_ROOT" HOME="$TEST_HOME" "$HOOK"
    fi
}

invoke_no_home() {
    local token="$1"
    local payload="$2"
    printf '%s' "$payload" | env -u XDG_CACHE_HOME -u HOME "$HOOK" "$token"
}

assert_deny() {
    local label="$1"
    local token="$2"
    local payload="$3"
    local out
    out=$(invoke "$token" "$payload")
    if ! printf '%s' "$out" | jq empty >/dev/null 2>&1; then
        fail "$label: stdout is not valid JSON: $out"
        return
    fi
    local decision
    decision=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // empty')
    local event
    event=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.hookEventName // empty')
    local reason
    reason=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason // empty')
    if [[ "$event" == "PreToolUse" && "$decision" == "deny" && -n "$reason" ]]; then
        pass
    else
        fail "$label: expected deny shape, got event='$event' decision='$decision' reason='$reason'"
    fi
}

assert_allow() {
    local label="$1"
    local token="$2"
    local payload="$3"
    local out
    out=$(invoke "$token" "$payload")
    if [[ -z "$out" ]]; then
        pass
    else
        fail "$label: expected empty stdout on allow, got: $out"
    fi
}

assert_allow_no_home() {
    local label="$1"
    local token="$2"
    local payload="$3"
    local out
    out=$(invoke_no_home "$token" "$payload")
    if [[ -z "$out" ]]; then
        pass
    else
        fail "$label: expected empty stdout on allow, got: $out"
    fi
}

# T0 — inactive gate allows without parsing.
reset_activation
assert_allow "T0 inactive repo path" research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"
assert_allow "T0b inactive malformed JSON" research 'not json at all'

# T1 — repo-path Write denies while research is active.
reset_activation
activate research
assert_deny "T1 Write repo path" research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"

# T2 — /tmp Write allows while active (not-yet-existing file — ancestor-walk path).
TMP_FILE="/tmp/test-deny-edit-write-$$-$RANDOM.txt"
assert_allow "T2 Write /tmp file (new)" research "{\"tool_input\":{\"file_path\":\"$TMP_FILE\"}}"

# T2b — /tmp Write allows for an existing file (direct-exist path, skips
# the dirname walk).
TMP_EXISTING=$(mktemp "/tmp/test-deny-edit-write-existing-XXXXXX")
assert_allow "T2b Write /tmp file (existing)" research "{\"tool_input\":{\"file_path\":\"$TMP_EXISTING\"}}"
rm -f "$TMP_EXISTING"

# T3 — /tmp traversal denies (canonicalizes to /etc/passwd).
assert_deny "T3 traversal /tmp/../etc/passwd" research '{"tool_input":{"file_path":"/tmp/../etc/passwd"}}'

# T4 — relative path denies.
assert_deny "T4 relative path" research '{"tool_input":{"file_path":"foo.txt"}}'

# T5 — empty / missing path denies (fail-closed while active).
assert_deny "T5 missing file_path" research '{"tool_input":{}}'
assert_deny "T5b empty object" research '{}'

# T6 — malformed JSON denies while active.
assert_deny "T6 malformed JSON" research 'not json at all'

# T7 — NotebookEdit with notebook_path under /tmp allows.
TMP_IPYNB="/tmp/test-deny-edit-write-$$-$RANDOM.ipynb"
assert_allow "T7 NotebookEdit notebook_path /tmp" research "{\"tool_input\":{\"notebook_path\":\"$TMP_IPYNB\"}}"

# T7b — Empty file_path with valid /tmp notebook_path allows. Guards
# against jq `//` treating "" as present (which would deny here).
assert_allow "T7b empty file_path with /tmp notebook_path" research "{\"tool_input\":{\"file_path\":\"\",\"notebook_path\":\"$TMP_IPYNB\"}}"

# T8 — NotebookEdit with notebook_path under repo denies.
assert_deny "T8 NotebookEdit notebook_path repo" research "{\"tool_input\":{\"notebook_path\":\"$REPO_ROOT/notebook.ipynb\"}}"

# T9 — idempotency: two deny invocations produce byte-identical stdout.
OUT_A=$(invoke research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}")
OUT_B=$(invoke research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}")
if [[ "$OUT_A" == "$OUT_B" ]]; then
    pass
else
    fail "T9: deny output not idempotent ('$OUT_A' vs '$OUT_B')"
fi

# T10 — jq-absent fallback byte-identical to jq-present deny while active.
BASH_BIN=$(command -v bash)
FIND_BIN=$(command -v find)
STUB_DIR=$(mktemp -d "${TMPDIR:-/tmp}/test-deny-edit-write-stub-XXXXXX")
ln -s "$BASH_BIN" "$STUB_DIR/bash"
ln -s "$FIND_BIN" "$STUB_DIR/find"
OUT_JQ_PRESENT=$(invoke research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}")
OUT_JQ_ABSENT=$(env -i PATH="$STUB_DIR" XDG_CACHE_HOME="$CACHE_ROOT" HOME="$TEST_HOME" "$BASH_BIN" "$HOOK" research <<<"{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}")
if [[ "$OUT_JQ_PRESENT" == "$OUT_JQ_ABSENT" ]]; then
    pass
else
    fail "T10: jq-absent deny output diverged from jq-present deny output: '$OUT_JQ_ABSENT' vs '$OUT_JQ_PRESENT'"
fi

# T10b — jq-absent but inactive allows with empty stdout.
reset_activation
OUT_JQ_ABSENT_INACTIVE=$(env -i PATH="$STUB_DIR" XDG_CACHE_HOME="$CACHE_ROOT" HOME="$TEST_HOME" "$BASH_BIN" "$HOOK" research <<<'not json at all')
if [[ -z "$OUT_JQ_ABSENT_INACTIVE" ]]; then
    pass
else
    fail "T10b: jq-absent inactive hook should allow with empty stdout, got: '$OUT_JQ_ABSENT_INACTIVE'"
fi

# T11 — stale sentinel does not activate the hook.
reset_activation
stale_activation research
assert_allow "T11 stale repo path" research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"
assert_allow "T11b stale /tmp path" research "{\"tool_input\":{\"file_path\":\"$TMP_FILE\"}}"

# T12 — token scoping keeps consumers independent.
reset_activation
activate research
assert_allow "T12 research sentinel does not activate bug token" bug "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"
reset_activation
activate bug
assert_allow "T12b bug sentinel does not activate research token" research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"
assert_allow "T12c tokenless invocation stays inactive" "" "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"
assert_allow "T12d unrecognized token stays inactive" unknown "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"
assert_deny "T12e bug token denies with bug sentinel" bug "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"

# T13 — activation is PID-agnostic; a foreign-PID sentinel activates.
reset_activation
activate research 999999
assert_deny "T13 foreign PID sentinel activates" research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"

# T14 — unset HOME and XDG_CACHE_HOME allow rather than tripping set -u.
assert_allow_no_home "T14 unset HOME/XDG allows" research "{\"tool_input\":{\"file_path\":\"$REPO_ROOT/foo.txt\"}}"

TOTAL=$((PASS + FAIL))
echo "deny-edit-write.sh: $PASS/$TOTAL passed"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
