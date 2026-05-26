#!/usr/bin/env bash
# test-lib-quiet.sh — unit tests for scripts/lib-quiet.sh.
# shellcheck disable=SC2016

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIB="$ROOT/scripts/lib-quiet.sh"
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/test-lib-quiet.XXXXXX")
trap 'rm -rf "$SCRATCH"' EXIT
# Isolate from a parent larch session (implement exports IMPLEMENT_TMPDIR / quiet
# state); leaked LARCH_QUIET_LOG_FILE breaks default-log path assertions.
unset IMPLEMENT_TMPDIR REVIEW_TMPDIR DESIGN_TMPDIR \
    LARCH_QUIET_ACTIVE LARCH_QUIET_PID LARCH_QUIET_LOG_FILE LARCH_QUIET_LOG \
    LARCH_QUIET_BREADCRUMBS LARCH_QUIET_DISABLE LARCH_BREADCRUMB_STREAM \
    LARCH_DONE_SENTINEL LARCH_STATUS_FILE LARCH_BREADCRUMBS_SURFACED_FILE \
    LARCH_QUIET_BREADCRUMB_FD || true

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

assert_eq() {
    local got=$1 want=$2 label=$3
    [ "$got" = "$want" ] || fail "$label: got [$got], want [$want]"
}

assert_file_contains() {
    local file=$1 needle=$2 label=$3
    grep -Fq "$needle" "$file" || fail "$label: missing [$needle]"
}

write_helper() {
    local path=$1 body=$2
    {
        printf '#!/usr/bin/env bash\n'
        printf 'set -euo pipefail\n'
        printf 'LIB=%q\n' "$LIB"
        printf '# shellcheck source=scripts/lib-quiet.sh\n'
        printf 'source "$LIB"\n'
        printf '%s\n' "$body"
    } > "$path"
    chmod +x "$path"
}

# 1. emit and emit_kv remain visible while ordinary stdout/stderr go to log.
helper="$SCRATCH/basic.sh"
log="$SCRATCH/basic.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; echo noisy; echo err >&2; emit_kv STATUS ok; emit done'
out=$("$helper" "$log")
assert_eq "$out" $'STATUS=ok\ndone' "basic visible output"
grep -q '^noisy$' "$log" || fail "basic stdout not logged"
grep -q '^err$' "$log" || fail "basic stderr not logged"

# 2. LARCH_QUIET_DISABLE preserves legacy stdout/stderr.
helper="$SCRATCH/disabled.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; larch_quiet_init; echo legacy; emit_kv STATUS ok'
out=$("$helper" 2>/dev/null)
assert_eq "$out" $'legacy\nSTATUS=ok' "disable mode"

# 3. Nested init does not change the active log or lose fd3.
helper="$SCRATCH/nested.sh"
log="$SCRATCH/nested.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; first=$LARCH_QUIET_LOG_FILE; larch_quiet_init; second=$LARCH_QUIET_LOG_FILE; echo hidden; emit_kv FIRST "$first"; emit_kv SECOND "$second"'
out=$("$helper" "$log")
assert_eq "$out" "FIRST=$log
SECOND=$log" "nested init"
grep -q '^hidden$' "$log" || fail "nested log missing stdout"

# 4. Breadcrumbs are quiet by default.
helper="$SCRATCH/breadcrumb-quiet.sh"
log="$SCRATCH/breadcrumb.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; emit_breadcrumb --category=progress "step done"; emit_kv STATUS ok'
out=$("$helper" "$log")
assert_eq "$out" "STATUS=ok" "breadcrumb quiet stdout"
grep -q '^step done$' "$log" || fail "breadcrumb not logged"

# 5. Breadcrumbs can be surfaced explicitly.
helper="$SCRATCH/breadcrumb-visible.sh"
log="$SCRATCH/breadcrumb-visible.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; LARCH_QUIET_BREADCRUMBS=1; export LARCH_QUIET_LOG_FILE LARCH_QUIET_BREADCRUMBS; larch_quiet_init; emit_breadcrumb --category=progress "step done"; emit_kv STATUS ok'
out=$("$helper" "$log")
assert_eq "$out" $'step done\nSTATUS=ok' "breadcrumb visible stdout"

# 5b. Breadcrumbs can use an inherited alternate fd when stdout is captured.
helper="$SCRATCH/breadcrumb-fd.sh"
log="$SCRATCH/breadcrumb-fd.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; LARCH_QUIET_BREADCRUMBS=1; export LARCH_QUIET_LOG_FILE LARCH_QUIET_BREADCRUMBS; larch_quiet_init; exec 5>&3; export LARCH_QUIET_BREADCRUMB_FD=5; emit_breadcrumb --category=progress "step done"; emit_kv STATUS ok'
"$helper" "$log" >"$SCRATCH/breadcrumb-fd.out"
assert_eq "$(cat "$SCRATCH/breadcrumb-fd.out")" $'step done\nSTATUS=ok' "breadcrumb visible alternate fd"

# 6. Empty values are emitted as KEY=.
helper="$SCRATCH/empty.sh"
write_helper "$helper" 'larch_quiet_init; emit_kv EMPTY ""'
out=$("$helper")
assert_eq "$out" "EMPTY=" "empty kv"

# 7. Default log path is exported and receives ordinary output.
helper="$SCRATCH/default-log.sh"
write_helper "$helper" 'IMPLEMENT_TMPDIR=$1; export IMPLEMENT_TMPDIR; larch_quiet_init; echo hidden; emit_kv LOG "$LARCH_QUIET_LOG_FILE"'
out=$("$helper" "$SCRATCH")
case "$out" in LOG="$SCRATCH"/larch-quiet-*) ;; *) fail "default log path unexpected: $out" ;; esac
default_log=${out#LOG=}
grep -q '^hidden$' "$default_log" || fail "default log did not receive output"

# 8. Pre-existing LARCH_QUIET_ACTIVE leaves output unchanged in child context.
helper="$SCRATCH/active.sh"
write_helper "$helper" 'LARCH_QUIET_ACTIVE=1; export LARCH_QUIET_ACTIVE; larch_quiet_init; echo still-visible'
out=$("$helper")
assert_eq "$out" "still-visible" "pre-active no redirect"

# 9. Unwritable log directory falls back to no redirect instead of failing.
helper="$SCRATCH/bad-log.sh"
touch "$SCRATCH/not-a-dir"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; echo visible'
out=$("$helper" "$SCRATCH/not-a-dir/log")
assert_eq "$out" "visible" "bad log fallback"

# 10. Pure filters can force disable and preserve stdin-to-stdout behavior.
helper="$SCRATCH/filter.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; larch_quiet_init; tr a-z A-Z'
out=$(printf 'abc\n' | "$helper")
assert_eq "$out" "ABC" "filter disable"

# 11. emit handles multi-word text as one line.
helper="$SCRATCH/emit-text.sh"
write_helper "$helper" 'larch_quiet_init; emit "two words"'
out=$("$helper")
assert_eq "$out" "two words" "emit text"

# 12. larch_err reaches the process stderr while ordinary stderr is logged.
helper="$SCRATCH/larch_err.sh"
log="$SCRATCH/larch_err.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; echo noisy; larch_err "user-visible"; emit_kv STATUS ok'
"$helper" "$log" >"$SCRATCH/larch_err.out" 2>"$SCRATCH/larch_err.err"
assert_eq "$(cat "$SCRATCH/larch_err.out")" "STATUS=ok" "larch_err contract stdout"
grep -q '^user-visible$' "$SCRATCH/larch_err.err" || fail "larch_err not on stderr"
grep -q '^noisy$' "$log" || fail "larch_err noisy not logged"

# 13. emit_breadcrumb_stderr preserves stderr semantics without a stream.
helper="$SCRATCH/breadcrumb-stderr-unset.sh"
write_helper "$helper" 'larch_quiet_init; emit_breadcrumb_stderr --category=wait-ci "wait:%s" "done"'
"$helper" >"$SCRATCH/breadcrumb-stderr-unset.out" 2>"$SCRATCH/breadcrumb-stderr-unset.err"
assert_eq "$(cat "$SCRATCH/breadcrumb-stderr-unset.out")" "" "emit_breadcrumb_stderr unset stdout"
assert_eq "$(cat "$SCRATCH/breadcrumb-stderr-unset.err")" "wait:done" "emit_breadcrumb_stderr unset stderr bytes"

# 14. emit_breadcrumb_stderr writes only to the breadcrumb stream when set.
helper="$SCRATCH/breadcrumb-stderr-stream.sh"
write_helper "$helper" 'LARCH_BREADCRUMB_STREAM=$1; export LARCH_BREADCRUMB_STREAM; larch_quiet_init; emit_breadcrumb_stderr --category=wait-ci "wait:%s" "done"'
"$helper" "$SCRATCH/breadcrumb-stream.ndjson" >"$SCRATCH/breadcrumb-stderr-stream.out" 2>"$SCRATCH/breadcrumb-stderr-stream.err"
assert_eq "$(cat "$SCRATCH/breadcrumb-stderr-stream.out")" "" "emit_breadcrumb_stderr stream stdout"
assert_eq "$(cat "$SCRATCH/breadcrumb-stderr-stream.err")" "" "emit_breadcrumb_stderr stream stderr"
assert_file_contains "$SCRATCH/breadcrumb-stream.ndjson" "c=wait-ci" "emit_breadcrumb_stderr stream category"
assert_file_contains "$SCRATCH/breadcrumb-stream.ndjson" "text=wait:done" "emit_breadcrumb_stderr stream payload"

# 15. emit_breadcrumb does not mirror raw text when the breadcrumb stream is set.
helper="$SCRATCH/breadcrumb-stream-only.sh"
write_helper "$helper" 'LARCH_BREADCRUMB_STREAM=$1; LARCH_QUIET_BREADCRUMBS=1; export LARCH_BREADCRUMB_STREAM LARCH_QUIET_BREADCRUMBS; larch_quiet_init; emit_breadcrumb --category=progress "secret token"; emit_kv STATUS ok'
"$helper" "$SCRATCH/breadcrumb-only.ndjson" >"$SCRATCH/breadcrumb-stream-only.out" 2>"$SCRATCH/breadcrumb-stream-only.err"
assert_eq "$(cat "$SCRATCH/breadcrumb-stream-only.out")" "STATUS=ok" "emit_breadcrumb stream suppresses mirrored stdout"
assert_eq "$(cat "$SCRATCH/breadcrumb-stream-only.err")" "" "emit_breadcrumb stream suppresses mirrored stderr"
assert_file_contains "$SCRATCH/breadcrumb-only.ndjson" "c=progress" "emit_breadcrumb stream-only category"
assert_file_contains "$SCRATCH/breadcrumb-only.ndjson" "text=secret token" "emit_breadcrumb stream-only payload"

printf 'PASS: test-lib-quiet.sh\n'
