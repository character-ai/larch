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

# 16. Missing category with a stream warns and writes no record.
helper="$SCRATCH/breadcrumb-missing-category.sh"
write_helper "$helper" 'LARCH_BREADCRUMB_STREAM=$1; export LARCH_BREADCRUMB_STREAM; larch_quiet_init; emit_breadcrumb "missing category"'
"$helper" "$SCRATCH/breadcrumb-missing-category.ndjson" >"$SCRATCH/breadcrumb-missing-category.out" 2>"$SCRATCH/breadcrumb-missing-category.err"
assert_eq "$(cat "$SCRATCH/breadcrumb-missing-category.out")" "" "missing category stdout"
assert_file_contains "$SCRATCH/breadcrumb-missing-category.err" "WARN unknown-category=<missing>" "missing category warning"
if [[ -s "$SCRATCH/breadcrumb-missing-category.ndjson" ]]; then
    fail "missing category should not write a stream record"
fi

# 17. Invalid category with a stream warns and writes no record.
helper="$SCRATCH/breadcrumb-invalid-category.sh"
write_helper "$helper" 'LARCH_BREADCRUMB_STREAM=$1; export LARCH_BREADCRUMB_STREAM; larch_quiet_init; emit_breadcrumb --category=bogus "invalid category"'
"$helper" "$SCRATCH/breadcrumb-invalid-category.ndjson" >"$SCRATCH/breadcrumb-invalid-category.out" 2>"$SCRATCH/breadcrumb-invalid-category.err"
assert_eq "$(cat "$SCRATCH/breadcrumb-invalid-category.out")" "" "invalid category stdout"
assert_file_contains "$SCRATCH/breadcrumb-invalid-category.err" "WARN unknown-category=bogus" "invalid category warning"
if [[ -s "$SCRATCH/breadcrumb-invalid-category.ndjson" ]]; then
    fail "invalid category should not write a stream record"
fi

# 18. Overlong breadcrumb payloads are replaced instead of leaking a prefix.
helper="$SCRATCH/breadcrumb-truncated.sh"
write_helper "$helper" 'LARCH_BREADCRUMB_STREAM=$1; export LARCH_BREADCRUMB_STREAM; larch_quiet_init; emit_breadcrumb --category=progress "$(printf "%1100s" "" | tr " " "A")"'
"$helper" "$SCRATCH/breadcrumb-truncated.ndjson" >"$SCRATCH/breadcrumb-truncated.out" 2>"$SCRATCH/breadcrumb-truncated.err"
assert_eq "$(cat "$SCRATCH/breadcrumb-truncated.out")" "" "truncated breadcrumb stdout"
assert_file_contains "$SCRATCH/breadcrumb-truncated.err" "WARN truncated breadcrumb record" "truncated breadcrumb warning"
assert_file_contains "$SCRATCH/breadcrumb-truncated.ndjson" "text=[truncated]" "truncated breadcrumb sentinel"
if grep -Eq 'text=A{20,}' "$SCRATCH/breadcrumb-truncated.ndjson"; then
    fail "truncated breadcrumb should not keep a secret prefix"
fi

# 19. Paired PID writer is a no-op when env var is unset.
helper="$SCRATCH/paired-pid-unset.sh"
write_helper "$helper" 'unset LARCH_PAIRED_PID_FILE; larch_quiet_write_paired_pid_file; printf "ok\n"'
out=$("$helper")
assert_eq "$out" "ok" "paired pid unset no-op"

# 20. Paired PID writer atomically writes the caller PID and leaves no tmp files.
helper="$SCRATCH/paired-pid-write.sh"
session_tmp="$SCRATCH/session"
mkdir -p "$session_tmp/breadcrumbs"
write_helper "$helper" 'IMPLEMENT_TMPDIR=$1; LARCH_PAIRED_PID_FILE=$2; export IMPLEMENT_TMPDIR LARCH_PAIRED_PID_FILE; printf "PID=%s\n" "$$"; larch_quiet_write_paired_pid_file'
pid_path="$session_tmp/breadcrumbs/paired.pid"
out=$("$helper" "$session_tmp" "$pid_path")
written_pid=${out#PID=}
printf '%s\n' "$written_pid" >"$SCRATCH/paired-pid-expected"
cmp -s "$SCRATCH/paired-pid-expected" "$pid_path" || fail "paired pid file content"
assert_eq "$(wc -c <"$pid_path" | tr -d ' ')" "$(( ${#written_pid} + 1 ))" "paired pid file byte count"
if find "$session_tmp/breadcrumbs" -name 'paired.pid.tmp.*' -print -quit | grep -q .; then
    fail "paired pid writer left tmp files"
fi

# 21. Invalid or unwritable paths fail open with warnings.
helper="$SCRATCH/paired-pid-invalid.sh"
write_helper "$helper" 'IMPLEMENT_TMPDIR=$1; LARCH_PAIRED_PID_FILE=$2; export IMPLEMENT_TMPDIR LARCH_PAIRED_PID_FILE; larch_quiet_write_paired_pid_file; printf "after\n"'
bad_parent="$session_tmp/unwritable"
mkdir -p "$bad_parent"
chmod 500 "$bad_parent"
"$helper" "$session_tmp" "$bad_parent/paired.pid" >"$SCRATCH/paired-unwritable.out" 2>"$SCRATCH/paired-unwritable.err"
chmod 700 "$bad_parent"
assert_eq "$(cat "$SCRATCH/paired-unwritable.out")" "after" "paired pid unwritable fail-open stdout"
assert_file_contains "$SCRATCH/paired-unwritable.err" "WARN paired-pid-file-invalid" "paired pid unwritable warning"

outside_path="$SCRATCH/outside.pid"
"$helper" "$session_tmp" "$outside_path" >"$SCRATCH/paired-outside.out" 2>"$SCRATCH/paired-outside.err"
assert_eq "$(cat "$SCRATCH/paired-outside.out")" "after" "paired pid outside fail-open stdout"
assert_file_contains "$SCRATCH/paired-outside.err" "WARN paired-pid-file-invalid" "paired pid outside warning"
if [[ -e "$outside_path" ]]; then
    fail "paired pid outside path should not be written"
fi

symlink_path="$session_tmp/breadcrumbs/symlink.pid"
ln -s "$session_tmp/breadcrumbs/target.pid" "$symlink_path"
"$helper" "$session_tmp" "$symlink_path" >"$SCRATCH/paired-symlink.out" 2>"$SCRATCH/paired-symlink.err"
assert_file_contains "$SCRATCH/paired-symlink.err" "WARN paired-pid-file-invalid" "paired pid symlink warning"

dotdot_path="$session_tmp/breadcrumbs/../paired.pid"
"$helper" "$session_tmp" "$dotdot_path" >"$SCRATCH/paired-dotdot.out" 2>"$SCRATCH/paired-dotdot.err"
assert_file_contains "$SCRATCH/paired-dotdot.err" "WARN paired-pid-file-invalid" "paired pid dotdot warning"

relative_path="relative.pid"
"$helper" "$session_tmp" "$relative_path" >"$SCRATCH/paired-relative.out" 2>"$SCRATCH/paired-relative.err"
assert_file_contains "$SCRATCH/paired-relative.err" "WARN paired-pid-file-invalid" "paired pid relative warning"

# 22. Concurrent writers publish one complete PID line and clean tmp files.
helper="$SCRATCH/paired-pid-race.sh"
write_helper "$helper" 'IMPLEMENT_TMPDIR=$1; LARCH_PAIRED_PID_FILE=$2; export IMPLEMENT_TMPDIR LARCH_PAIRED_PID_FILE; printf "PID=%s\n" "$$"; larch_quiet_write_paired_pid_file'
race_path="$session_tmp/breadcrumbs/race.pid"
out1="$SCRATCH/race1.out"
out2="$SCRATCH/race2.out"
"$helper" "$session_tmp" "$race_path" >"$out1" 2>"$SCRATCH/race1.err" &
race_pid1=$!
"$helper" "$session_tmp" "$race_path" >"$out2" 2>"$SCRATCH/race2.err" &
race_pid2=$!
wait "$race_pid1"
wait "$race_pid2"
race_written="$(cat "$race_path")"
race_expected_1="$(cat "$out1")"
race_expected_1="${race_expected_1#PID=}"
race_expected_2="$(cat "$out2")"
race_expected_2="${race_expected_2#PID=}"
if [[ "$race_written" != "$race_expected_1" && "$race_written" != "$race_expected_2" ]]; then
    fail "paired pid race wrote unexpected content: $race_written"
fi
if find "$session_tmp/breadcrumbs" -name 'race.pid.tmp.*' -print -quit | grep -q .; then
    fail "paired pid race left tmp files"
fi

# 23. sanitize_diagnostic_line strips C0 control bytes from one line.
helper="$SCRATCH/sanitize.sh"
write_helper "$helper" 'printf "before\x01\x02\x03after\x07.end\n" | sanitize_diagnostic_line'
out=$("$helper" 2>/dev/null)
[ "$out" = "beforeafter.end" ] || fail "sanitize_diagnostic_line did not strip controls: '$out'"

# 24. emit_kv rejects embedded LF.
helper="$SCRATCH/emit-kv-lf.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv BAD $'"'"'line1\nline2'"'"' || printf "rc=%s\n" "$?"'
"$helper" >"$SCRATCH/emit-kv-lf.out" 2>"$SCRATCH/emit-kv-lf.err"
assert_eq "$(cat "$SCRATCH/emit-kv-lf.out")" "rc=2" "emit_kv lf reject rc"
grep -Fq 'emit_kv: value for key BAD must not contain newline or carriage return' "$SCRATCH/emit-kv-lf.err" \
    || fail "emit_kv lf reject message"

# 25. emit_kv rejects embedded CR.
helper="$SCRATCH/emit-kv-cr.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv BAD $'"'"'line1\rline2'"'"' || printf "rc=%s\n" "$?"'
"$helper" >"$SCRATCH/emit-kv-cr.out" 2>"$SCRATCH/emit-kv-cr.err"
assert_eq "$(cat "$SCRATCH/emit-kv-cr.out")" "rc=2" "emit_kv cr reject rc"

# 26. emit_kv rejects both LF and CR.
helper="$SCRATCH/emit-kv-both.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv BAD $'"'"'a\n\rb'"'"' || printf "rc=%s\n" "$?"'
"$helper" >"$SCRATCH/emit-kv-both.out" 2>"$SCRATCH/emit-kv-both.err"
assert_eq "$(cat "$SCRATCH/emit-kv-both.out")" "rc=2" "emit_kv both reject rc"

# 27. emit_kv allows literal backslash-n (not a newline byte).
helper="$SCRATCH/emit-kv-literal.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv OK "literal\\n text"'
out=$("$helper")
assert_eq "$out" 'OK=literal\n text' "emit_kv literal backslash-n"

# 28. emit_kv allows long single-line values.
helper="$SCRATCH/emit-kv-long.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv LONG "$(printf "%2000s" "" | tr " " "A")"'
out=$("$helper")
case "$out" in LONG=AAAA*) ;; *) fail "emit_kv long single-line value" ;; esac

printf 'PASS: test-lib-quiet.sh\n'
