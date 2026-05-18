#!/usr/bin/env bash
# test-write-rejected-findings.sh — offline harness for write-rejected-findings.sh.

set -euo pipefail
export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/write-rejected-findings.sh"
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-write-rejected-findings.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT
PASS=0; FAIL=0
pass(){ PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail(){ FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains(){ case "$2" in *"$1"*) pass "$3" ;; *) fail "$3 (missing $1)" ;; esac; }
finish(){ [ "$FAIL" -eq 0 ] || exit 1; printf 'PASS=%s\n' "$PASS"; }

empty="$TMP_ROOT/empty"; mkdir -p "$empty"
out=$("$HELPER" --implement-tmpdir "$empty")
assert_contains 'STATUS=empty' "$out" 'empty status emitted'
assert_contains 'REJECTED_COUNT=0' "$out" 'empty count emitted'

case_dir="$TMP_ROOT/nonempty"; mkdir -p "$case_dir"
printf '[Code Review] one\n\n- two\n' > "$case_dir/rejected-findings.md"
out=$("$HELPER" --implement-tmpdir "$case_dir" --run-id run-3 --log-root "$case_dir/logs")
assert_contains 'STATUS=ok' "$out" 'nonempty status emitted'
assert_contains 'REJECTED_COUNT=2' "$out" 'nonempty count emitted'
assert_contains 'details=rejected-findings.md' "$out" 'summary detail label emitted'
if [ -s "$case_dir/logs/implement/run-3/rejected-findings.md" ]; then pass 'optional copy written'; else fail 'optional copy written'; fi

# full-file preference: when rejected-findings-full.md exists it should be copied
full_dir="$TMP_ROOT/full"; mkdir -p "$full_dir"
printf 'bare\n' > "$full_dir/rejected-findings.md"
printf '### [rejected] FINDING_1\n\nFull detail body in /Users/example/project/file.txt with token sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD.\n\nVote tally: YES=0 NO=2 EXON=0 NEUTRAL=0\n' \
    > "$full_dir/rejected-findings-full.md"
out=$("$HELPER" --implement-tmpdir "$full_dir" --run-id run-4 --log-root "$full_dir/logs")
assert_contains 'STATUS=ok' "$out" 'full-file status ok'
assert_contains 'REJECTED_COUNT=1' "$out" 'full-file count uses detailed file'
assert_contains 'details=rejected-findings-full.md' "$out" 'full detail label emitted'
if grep -q 'Full detail body' "$full_dir/logs/implement/run-4/rejected-findings.md" 2>/dev/null; then
    pass 'full file used when present'
else
    fail 'full file used when present'
fi
if grep -q '^bare$' "$full_dir/logs/implement/run-4/rejected-findings.md" 2>/dev/null; then
    fail 'bare file must not be used when full exists'
else
    pass 'bare file not used when full exists'
fi
if grep -q '<REDACTED-TOKEN>' "$full_dir/logs/implement/run-4/rejected-findings.md" 2>/dev/null; then
    pass 'full file copy redacts secrets'
else
    fail 'full file copy redacts secrets'
fi
if grep -q 'sk-ant-' "$full_dir/logs/implement/run-4/rejected-findings.md" 2>/dev/null; then
    fail 'raw secret should not persist in copied full file'
else
    pass 'raw secret removed from copied full file'
fi
if grep -q '<OPERATOR_REPO_PATH>' "$full_dir/logs/implement/run-4/rejected-findings.md" 2>/dev/null; then
    pass 'full file copy redacts repo paths'
else
    fail 'full file copy redacts repo paths'
fi

# full-file fallback: empty summary should still report and persist detailed content
fallback_dir="$TMP_ROOT/fallback"; mkdir -p "$fallback_dir"
: > "$fallback_dir/rejected-findings.md"
printf '### [Code Review] Reviewer\n\nDetailed body only.\n' > "$fallback_dir/rejected-findings-full.md"
out=$("$HELPER" --implement-tmpdir "$fallback_dir" --run-id run-5 --log-root "$fallback_dir/logs")
assert_contains 'STATUS=ok' "$out" 'full fallback status ok'
assert_contains 'REJECTED_COUNT=1' "$out" 'full fallback count emitted'
assert_contains 'details=rejected-findings-full.md' "$out" 'fallback detail label emitted'
if grep -q 'Detailed body only' "$fallback_dir/logs/implement/run-5/rejected-findings.md" 2>/dev/null; then
    pass 'full fallback copy written'
else
    fail 'full fallback copy written'
fi

copy_fail_dir="$TMP_ROOT/copy-fail"; mkdir -p "$copy_fail_dir"
printf '[Code Review] one\n' > "$copy_fail_dir/rejected-findings.md"
printf 'not-a-directory\n' > "$copy_fail_dir/log-root-file"
set +e
out=$("$HELPER" --implement-tmpdir "$copy_fail_dir" --run-id run-6 --log-root "$copy_fail_dir/log-root-file")
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'copy failure exits non-zero'; else fail 'copy failure exits non-zero'; fi
assert_contains 'STATUS=failed' "$out" 'copy failure emits failed status'
assert_contains 'ERROR=failed to persist rejected findings log copy' "$out" 'copy failure emits error'

set +e
bad=$("$HELPER" 2>/dev/null)
rc=$?
set -e
if [ "$rc" -ne 0 ]; then pass 'missing tmpdir exits non-zero'; else fail 'missing tmpdir exits non-zero'; fi
assert_contains 'STATUS=failed' "$bad" 'missing args emits envelope'

finish
