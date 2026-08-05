#!/usr/bin/env bash
# test-cleanup.sh — offline harness for cleanup.sh.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/cleanup.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-cleanup.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

# cleanup.sh reaches the Rust owner through the verified bootstrap script, so the
# harness stubs that entrypoint instead of the retired Python dispatcher.
plugin="$TMP_ROOT/plugin"; mkdir -p "$plugin/scripts"
cat > "$plugin/scripts/larch.sh" <<'STUB'
#!/usr/bin/env bash
[ "${1:-}" = session ] && [ "${2:-}" = cleanup-tmpdir ] || { printf '%s\n' "unexpected larch command: $*" >&2; exit 64; }
shift 2
dir=""
while [ $# -gt 0 ]; do case "$1" in --dir) dir=$2; shift 2 ;; *) shift ;; esac; done
printf '%s\n' "$dir" > "${CLEANUP_DIR_LOG:?}"
if [ "${CLEANUP_FAIL:-false}" = "true" ]; then
  exit "${CLEANUP_RC:-5}"
fi
rm -rf "$dir"
STUB
chmod +x "$plugin/scripts/larch.sh"

target="$TMP_ROOT/session"; mkdir -p "$target"
out=$(CLAUDE_PLUGIN_ROOT="$plugin" CLEANUP_DIR_LOG="$TMP_ROOT/dir.log" "$HELPER" --implement-tmpdir "$target")
assert_contains 'CLEANED=true' "$out" 'happy path cleaned'
if [ ! -e "$target" ]; then pass 'target removed'; else fail 'target removed'; fi
assert_contains "$target" "$(cat "$TMP_ROOT/dir.log")" 'passes target dir'

target_fail="$TMP_ROOT/session-fail"; mkdir -p "$target_fail"
set +e
failed=$(CLAUDE_PLUGIN_ROOT="$plugin" CLEANUP_DIR_LOG="$TMP_ROOT/dir-fail.log" CLEANUP_FAIL=true CLEANUP_RC=6 "$HELPER" --implement-tmpdir "$target_fail" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -eq 6 ]; then pass 'cleanup failure preserves exit code'; else fail 'cleanup failure preserves exit code'; fi
assert_contains 'CLEANED=false' "$failed" 'cleanup failure emits cleaned false'
assert_contains 'ERROR=cleanup-tmpdir failed' "$failed" 'cleanup failure emits error'

set +e
bad=$(CLAUDE_PLUGIN_ROOT="$plugin" "$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing args exits non-zero'; else fail 'missing args exits non-zero'; fi
assert_contains 'CLEANED=false' "$bad" 'missing args emits envelope'

finish
