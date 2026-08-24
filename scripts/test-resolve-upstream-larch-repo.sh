#!/usr/bin/env bash
# test-resolve-upstream-larch-repo.sh — delegation harness for the upstream resolver.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_SCRIPT="$SCRIPT_DIR/resolve-upstream-larch-repo.sh"
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-resolve-upstream.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$*" | sed 's/^/    /'; }

PLUGIN_ROOT="$TMPROOT/plugin"
mkdir -p "$PLUGIN_ROOT/.claude-plugin" "$PLUGIN_ROOT/scripts"
PLUGIN_ROOT="$(cd "$PLUGIN_ROOT" && pwd -P)"
printf '{"repository":"character-ai/larch"}\n' >"$PLUGIN_ROOT/.claude-plugin/plugin.json"
cp "$SOURCE_SCRIPT" "$PLUGIN_ROOT/scripts/resolve-upstream-larch-repo.sh"
cat >"$PLUGIN_ROOT/scripts/larch.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf 'CLAUDE_PLUGIN_ROOT=%s\n' "${CLAUDE_PLUGIN_ROOT:-}" >"${LARCH_STUB_LOG:?}"
printf 'ARGV=%s\n' "$*" >>"$LARCH_STUB_LOG"
if [ "${LARCH_STUB_FAIL:-}" = true ]; then
    printf '%s\n' 'resolve-upstream-larch-repo: repository metadata missing' >&2
    exit 1
fi
printf '%s\n' 'character-ai/larch'
STUB
chmod +x "$PLUGIN_ROOT/scripts/larch.sh" "$PLUGIN_ROOT/scripts/resolve-upstream-larch-repo.sh"

set +e
out=$(LARCH_STUB_LOG="$TMPROOT/delegation.log" "$PLUGIN_ROOT/scripts/resolve-upstream-larch-repo.sh" 2>"$TMPROOT/delegation.err")
rc=$?
set -e
if [ "$rc" -eq 0 ] && [ "$out" = character-ai/larch ] && [ ! -s "$TMPROOT/delegation.err" ]; then
    pass "resolver delegates successfully"
else
    fail "resolver delegates successfully" "rc=$rc out=$out err=$(cat "$TMPROOT/delegation.err")"
fi
if grep -qxF "CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT" "$TMPROOT/delegation.log" && \
   grep -qxF 'ARGV=plugin resolve-repository' "$TMPROOT/delegation.log"; then
    pass "resolver binds the adjacent plugin root and Rust verb"
else
    fail "resolver binds the adjacent plugin root and Rust verb" "$(cat "$TMPROOT/delegation.log")"
fi

set +e
out=$(LARCH_STUB_LOG="$TMPROOT/failure.log" LARCH_STUB_FAIL=true "$PLUGIN_ROOT/scripts/resolve-upstream-larch-repo.sh" 2>"$TMPROOT/failure.err")
rc=$?
set -e
if [ "$rc" -eq 1 ] && [ -z "$out" ] && grep -q 'repository metadata missing' "$TMPROOT/failure.err"; then
    pass "resolver propagates Rust metadata refusal"
else
    fail "resolver propagates Rust metadata refusal" "rc=$rc out=$out err=$(cat "$TMPROOT/failure.err")"
fi

if grep -q 'python3' "$SOURCE_SCRIPT"; then
    fail "resolver runtime is Python-free"
else
    pass "resolver runtime is Python-free"
fi

if [ "$FAIL" -ne 0 ]; then
    echo "FAILURES: $FAIL"
    exit 1
fi
echo "PASS: $PASS"
