#!/usr/bin/env bash
# test-hook-stop-fail-close.sh — Regression harness for
# skills/implement/scripts/hook-stop-fail-close.sh.
#
# Black-box tests for post-/review boundary Stop blocking, including
# jq-failure and jq/python3-absent static-literal fallback paths.
#
# Usage:
#   bash scripts/test-hook-stop-fail-close.sh
#
# Exit codes:
#   0 — all assertions passed
#   1 — at least one assertion failed

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
HOOK="$REPO_ROOT/skills/implement/scripts/hook-stop-fail-close.sh"
STATIC_BLOCK='{"decision":"block","reason":"You halted mid-Step-5 (post-/review boundary). Execute Cross-Skill Presence Propagation + Step 6 breadcrumb, then touch .review-boundary-passed inside the active /implement tmpdir."}'

if [[ ! -x "$HOOK" ]]; then
    echo "ERROR: hook script not found or not executable: $HOOK" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "FAIL: harness jq not on PATH; cannot validate JSON output" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "FAIL: harness python3 not on PATH; cannot set up implement tmpdir" >&2
    exit 1
fi

PASS=0
FAIL=0
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-hook-stop-fail-close.XXXXXX")
STUB_BIN=$(mktemp -d "${TMPDIR:-/tmp}/test-hook-stop-fail-close-stub.XXXXXX")
trap 'rm -rf "$TMP" "$STUB_BIN"' EXIT

fail() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1" >&2
}

pass() {
    PASS=$((PASS + 1))
}

setup_implement_tmpdir() {
    local cache_root="$TMP/cache"
    local sessions_root="$cache_root/larch/sessions"
    local implement_dir="$sessions_root/claude-implement-test-$$"
    local cwd="$TMP/repo"
    mkdir -p "$cwd" "$implement_dir"
    printf '# larch session identity (hook routing)\nCLONE_PATH=%s\nSESSION_ID=sid-test\n' "$cwd" \
        >"$implement_dir/.larch-keepalive"
    : >"$implement_dir/review-round-summary.md"
    printf '%s' "$cache_root"
}

invoke_hook() {
    local cwd="$1"
    local path_prefix="${2:-}"
    local payload
    payload=$(jq -cn --arg cwd "$cwd" '{stop_hook_active:false,cwd:$cwd,session_id:"sid-test"}')
    # shellcheck disable=SC2030 # subshell-local env scoping is intentional
    (
        export XDG_CACHE_HOME="$cache_root"
        export LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=0
        export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
        export PATH="${path_prefix}${PATH}"
        printf '%s' "$payload" | "$HOOK"
    )
}

assert_block_json() {
    local label="$1"
    local out="$2"
    if ! printf '%s' "$out" | jq empty >/dev/null 2>&1; then
        fail "$label: stdout is not valid JSON: $out"
        return
    fi
    local decision
    decision=$(printf '%s' "$out" | jq -r '.decision // empty')
    if [[ "$decision" != "block" ]]; then
        fail "$label: expected decision=block, got: $out"
        return
    fi
    pass "$label"
}

assert_empty() {
    local label="$1"
    local out="$2"
    if [[ -z "$out" ]]; then
        pass "$label"
    else
        fail "$label: expected empty stdout, got: $out"
    fi
}

assert_exact() {
    local label="$1"
    local out="$2"
    local expected="$3"
    if [[ "$out" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label: expected '$expected', got '$out'"
    fi
}

cache_root=$(setup_implement_tmpdir)
cwd="$TMP/repo"

# T1 — jq-present path blocks with dynamic reason containing tmpdir basename.
out=$(invoke_hook "$cwd")
assert_block_json "T1 jq-present post-/review boundary blocks" "$out"
if printf '%s' "$out" | jq -e '.reason | contains("claude-implement-test")' >/dev/null 2>&1; then
    pass "T1 reason includes implement tmpdir basename"
else
    fail "T1 reason missing implement tmpdir basename: $out"
fi

# T2 — jq -cn failure falls back to python3 JSON encoding.
REAL_JQ=$(command -v jq)
cat >"$STUB_BIN/jq" <<EOF
#!/usr/bin/env bash
if [[ "\$*" == *"-cn"* ]]; then
  exit 1
fi
exec "$REAL_JQ" "\$@"
EOF
chmod +x "$STUB_BIN/jq"
out=$(invoke_hook "$cwd" "$STUB_BIN:")
assert_block_json "T2 jq-failure still blocks via python3 fallback" "$out"
if printf '%s' "$out" | jq -e '.reason | contains("claude-implement-test")' >/dev/null 2>&1; then
    pass "T2 python3 fallback preserves dynamic reason"
else
    fail "T2 python3 fallback reason missing tmpdir basename: $out"
fi

# T3 — jq failure plus python3 json.dumps failure uses static literal.
REAL_PY=$(command -v python3)
cat >"$STUB_BIN/python3" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == "-c" && "\${2:-}" == *json.dumps* ]]; then
  exit 1
fi
exec "$REAL_PY" "\$@"
EOF
chmod +x "$STUB_BIN/python3"
out=$(invoke_hook "$cwd" "$STUB_BIN:")
assert_exact "T3 jq/python3 JSON failure uses static fallback" "$out" "$STATIC_BLOCK"

# T4 — jq-absent/failure static fallback when python3 JSON encoding is also stubbed.
# Uses a failing jq stub (not PATH removal) because cwd parsing requires jq on PATH.
out=$(invoke_hook "$cwd" "$STUB_BIN:")
assert_exact "T4 static fallback when jq and python3 JSON encoding fail" "$out" "$STATIC_BLOCK"

# T5 — stop_hook_active=true is silent.
payload=$(jq -cn --arg cwd "$cwd" '{stop_hook_active:true,cwd:$cwd}')
# shellcheck disable=SC2031 # subshell-local env scoping is intentional
out=$(
    export XDG_CACHE_HOME="$cache_root"
    export LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=0
    export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
    printf '%s' "$payload" | "$HOOK"
)
assert_empty "T5 stop_hook_active=true is silent" "$out"

# T6 — .review-boundary-passed releases the guard.
touch "$cache_root/larch/sessions/claude-implement-test-$$/.review-boundary-passed"
out=$(invoke_hook "$cwd")
assert_empty "T6 review-boundary-passed releases guard" "$out"

TOTAL=$((PASS + FAIL))
echo "hook-stop-fail-close.sh: $PASS/$TOTAL passed"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
