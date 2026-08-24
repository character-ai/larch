#!/usr/bin/env bash
# test-hook-stop-fail-close.sh — Regression harness for
# skills/implement/scripts/hook-stop-fail-close.sh.
#
# Black-box tests for post-/review boundary Stop blocking, including
# jq-failure static-literal direct-stdout fallback path.
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

PASS=0
FAIL=0
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-hook-stop-fail-close.XXXXXX")
# The bootstrap refuses a LARCH_BINARY with a symlinked ancestor, and macOS
# resolves $TMPDIR through /var -> /private/var.
TMP=$(cd "$TMP" && pwd -P)
STUB_BIN=$(mktemp -d "${TMPDIR:-/tmp}/test-hook-stop-fail-close-stub.XXXXXX")
trap 'rm -rf "$TMP" "$STUB_BIN"' EXIT

# The hook reaches the Rust `session resolve-implement-tmpdir` owner through the
# verified bootstrap, which refuses to install inside a source checkout. Supply a
# version-matched fake so the harness stays offline; resolver behavior itself is
# pinned by the Rust unit tests and the session-lifecycle parity goldens.
BASH_BIN=$(command -v bash)
PLUGIN_VERSION=$(awk -F '"' '$2 == "version" { print $4 }' "$REPO_ROOT/.claude-plugin/plugin.json")
case "$(uname -s):$(uname -m)" in
    Darwin:arm64|Darwin:aarch64) LARCH_TARGET=aarch64-apple-darwin ;;
    Darwin:x86_64|Darwin:amd64) LARCH_TARGET=x86_64-apple-darwin ;;
    Linux:arm64|Linux:aarch64) LARCH_TARGET=aarch64-unknown-linux-gnu ;;
    Linux:x86_64|Linux:amd64) LARCH_TARGET=x86_64-unknown-linux-gnu ;;
    *) echo "FAIL: unsupported harness target" >&2; exit 1 ;;
esac
export LARCH_BINARY="$TMP/larch-fixture"
cat >"$LARCH_BINARY" <<STUB
#!$BASH_BIN
set -u
if [[ "\${1:-}" == "--version" ]]; then
    printf '%s\n' 'larch $PLUGIN_VERSION'
    exit 0
fi
if [[ "\${1:-}" == "bootstrap" && "\${2:-}" == "self-check" ]]; then
    printf '%s\n' '{"schema_version":1,"version":"$PLUGIN_VERSION","target":"$LARCH_TARGET"}'
    exit 0
fi
if [[ "\${1:-}" == "session" && "\${2:-}" == "resolve-implement-tmpdir" ]]; then
    shift 2
    cwd=""
    while [[ \$# -gt 0 ]]; do
        case "\$1" in
            --cwd) cwd="\$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    for candidate in "\${XDG_CACHE_HOME:-}/larch/sessions"/claude-implement-*; do
        [[ -d "\$candidate" ]] || continue
        [[ -f "\$candidate/.larch-keepalive" ]] || continue
        grep -qxF "CLONE_PATH=\$cwd" "\$candidate/.larch-keepalive" || continue
        [[ -f "\$candidate/review-round-summary.md" ]] || continue
        printf '%s' "\$candidate"
        exit 0
    done
    exit 0
fi
exit 2
STUB
chmod +x "$LARCH_BINARY"

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
        export LARCH_BINARY="$LARCH_BINARY"
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

# T2 — jq -cn failure uses the static direct-stdout fallback.
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
assert_exact "T2 jq failure uses static fallback" "$out" "$STATIC_BLOCK"

# T3 — stop_hook_active=true is silent.
payload=$(jq -cn --arg cwd "$cwd" '{stop_hook_active:true,cwd:$cwd}')
# shellcheck disable=SC2031 # subshell-local env scoping is intentional
out=$(
    export XDG_CACHE_HOME="$cache_root"
    export LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS=0
    export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
    printf '%s' "$payload" | "$HOOK"
)
assert_empty "T3 stop_hook_active=true is silent" "$out"

# T4 — .review-boundary-passed releases the guard.
touch "$cache_root/larch/sessions/claude-implement-test-$$/.review-boundary-passed"
out=$(invoke_hook "$cwd")
assert_empty "T4 review-boundary-passed releases guard" "$out"

if grep -q 'python3' "$HOOK"; then
    fail "T5 hook runtime is Python-free"
else
    pass "T5 hook runtime is Python-free"
fi

TOTAL=$((PASS + FAIL))
echo "hook-stop-fail-close.sh: $PASS/$TOTAL passed"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
