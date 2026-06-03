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
    LARCH_QUIET_DISABLE || true

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

# 1b. Production-style command substitution captures only FD3 contract output.
helper="$SCRATCH/cmdsubst.sh"
log="$SCRATCH/cmdsubst.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; printf "RAW_HELPER_KV=hidden\n"; emit "> banner"; emit "WORSE: display"; emit_kv TRUSTED trailer'
out=$("$helper" "$log")
assert_eq "$out" $'> banner\nWORSE: display\nTRUSTED=trailer' "command substitution visible output"
grep -q '^RAW_HELPER_KV=hidden$' "$log" || fail "command substitution raw stdout not logged"
if grep -Fq 'RAW_HELPER_KV=hidden' <<<"$out"; then
    fail "command substitution leaked raw stdout"
fi
if grep -Fq '> banner' "$log" || grep -Fq 'WORSE: display' "$log" || grep -Fq 'TRUSTED=trailer' "$log"; then
    fail "command substitution logged FD3 display output"
fi

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

# 4. Empty values are emitted as KEY=.
helper="$SCRATCH/empty.sh"
write_helper "$helper" 'larch_quiet_init; emit_kv EMPTY ""'
out=$("$helper")
assert_eq "$out" "EMPTY=" "empty kv"

# 5. Default log path is exported and receives ordinary output.
helper="$SCRATCH/default-log.sh"
write_helper "$helper" 'IMPLEMENT_TMPDIR=$1; export IMPLEMENT_TMPDIR; larch_quiet_init; echo hidden; emit_kv LOG "$LARCH_QUIET_LOG_FILE"'
out=$("$helper" "$SCRATCH")
case "$out" in LOG="$SCRATCH"/larch-quiet-*) ;; *) fail "default log path unexpected: $out" ;; esac
default_log=${out#LOG=}
grep -q '^hidden$' "$default_log" || fail "default log did not receive output"

# 6. Pre-existing LARCH_QUIET_ACTIVE leaves output unchanged in child context.
helper="$SCRATCH/active.sh"
write_helper "$helper" 'LARCH_QUIET_ACTIVE=1; export LARCH_QUIET_ACTIVE; larch_quiet_init; echo still-visible'
out=$("$helper")
assert_eq "$out" "still-visible" "pre-active no redirect"

# 7. Unwritable log directory falls back to no redirect instead of failing.
helper="$SCRATCH/bad-log.sh"
touch "$SCRATCH/not-a-dir"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; echo visible'
out=$("$helper" "$SCRATCH/not-a-dir/log")
assert_eq "$out" "visible" "bad log fallback"

# 8. Pure filters can force disable and preserve stdin-to-stdout behavior.
helper="$SCRATCH/filter.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; larch_quiet_init; tr a-z A-Z'
out=$(printf 'abc\n' | "$helper")
assert_eq "$out" "ABC" "filter disable"

# 9. emit handles multi-word text as one line.
helper="$SCRATCH/emit-text.sh"
write_helper "$helper" 'larch_quiet_init; emit "two words"'
out=$("$helper")
assert_eq "$out" "two words" "emit text"

# 10. larch_err reaches the process stderr while ordinary stderr is logged.
helper="$SCRATCH/larch_err.sh"
log="$SCRATCH/larch_err.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; echo noisy; larch_err "user-visible"; emit_kv STATUS ok'
"$helper" "$log" >"$SCRATCH/larch_err.out" 2>"$SCRATCH/larch_err.err"
assert_eq "$(cat "$SCRATCH/larch_err.out")" "STATUS=ok" "larch_err contract stdout"
grep -q '^user-visible$' "$SCRATCH/larch_err.err" || fail "larch_err not on stderr"
grep -q '^noisy$' "$log" || fail "larch_err noisy not logged"
grep -q '^user-visible$' "$log" || fail "larch_err not mirrored to quiet log"

# 10b. larch_errf preserves formatting/newlines on stderr and in the quiet log.
helper="$SCRATCH/larch_errf.sh"
log="$SCRATCH/larch_errf.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; larch_errf "prefix:%s\\nsecond line\\n" "value"; emit_kv STATUS ok'
"$helper" "$log" >"$SCRATCH/larch_errf.out" 2>"$SCRATCH/larch_errf.err"
assert_eq "$(cat "$SCRATCH/larch_errf.out")" "STATUS=ok" "larch_errf contract stdout"
assert_eq "$(cat "$SCRATCH/larch_errf.err")" $'prefix:value\nsecond line' "larch_errf stderr formatting"
assert_file_contains "$log" "prefix:value" "larch_errf mirrored first line"
assert_file_contains "$log" "second line" "larch_errf mirrored second line"

# 10c. larch_err redacts token families via redact-secrets.sh --streaming.
helper="$SCRATCH/larch_err_redact.sh"
log="$SCRATCH/larch_err_redact.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; larch_quiet_init; larch_err "token ghp_abcdefghijklmnopqrstuvwxyz123456 secret"; emit_kv STATUS ok'
"$helper" "$log" >"$SCRATCH/larch_err_redact.out" 2>"$SCRATCH/larch_err_redact.err"
assert_eq "$(cat "$SCRATCH/larch_err_redact.out")" "STATUS=ok" "larch_err redaction stdout"
grep -Fq '<REDACTED-TOKEN>' "$SCRATCH/larch_err_redact.err" || fail "larch_err redaction stderr missing placeholder"
grep -Fq '<REDACTED-TOKEN>' "$log" || fail "larch_err redaction log missing placeholder"
if grep -Fq 'ghp_abcdefghijklmnopqrstuvwxyz123456' "$SCRATCH/larch_err_redact.err" || grep -Fq 'ghp_abcdefghijklmnopqrstuvwxyz123456' "$log"; then
    fail "larch_err redaction leaked token"
fi

# 10d. Missing redactor emits a warning and preserves the original message.
helper="$SCRATCH/larch_err_redact_missing.sh"
log="$SCRATCH/larch_err_redact_missing.log"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; LARCH_LIB_QUIET_DIR=$2; export LARCH_LIB_QUIET_DIR; larch_quiet_init; larch_err "plain diagnostic"; emit_kv STATUS ok'
"$helper" "$log" "$SCRATCH/missing-helper-dir" >"$SCRATCH/larch_err_redact_missing.out" 2>"$SCRATCH/larch_err_redact_missing.err"
assert_eq "$(cat "$SCRATCH/larch_err_redact_missing.out")" "STATUS=ok" "larch_err missing redactor stdout"
assert_eq "$(cat "$SCRATCH/larch_err_redact_missing.err")" $'WARN larch_err-redaction-unavailable\nplain diagnostic' "larch_err missing redactor stderr"
assert_file_contains "$log" "WARN larch_err-redaction-unavailable" "missing redactor warning logged"
assert_file_contains "$log" "plain diagnostic" "missing redactor original message logged"

# 10e. Redactor failure emits a warning and preserves the original message.
helper="$SCRATCH/larch_err_redact_fail.sh"
log="$SCRATCH/larch_err_redact_fail.log"
redactor_dir="$SCRATCH/redactor-fail"
mkdir -p "$redactor_dir"
{
    printf '#!/usr/bin/env bash\n'
    printf 'exit 9\n'
} > "$redactor_dir/redact-secrets.sh"
chmod +x "$redactor_dir/redact-secrets.sh"
write_helper "$helper" 'LARCH_QUIET_LOG_FILE=$1; export LARCH_QUIET_LOG_FILE; LARCH_LIB_QUIET_DIR=$2; export LARCH_LIB_QUIET_DIR; larch_quiet_init; larch_err "plain diagnostic"; emit_kv STATUS ok'
"$helper" "$log" "$redactor_dir" >"$SCRATCH/larch_err_redact_fail.out" 2>"$SCRATCH/larch_err_redact_fail.err"
assert_eq "$(cat "$SCRATCH/larch_err_redact_fail.out")" "STATUS=ok" "larch_err failed redactor stdout"
assert_eq "$(cat "$SCRATCH/larch_err_redact_fail.err")" $'WARN larch_err-redaction-failed\nplain diagnostic' "larch_err failed redactor stderr"
assert_file_contains "$log" "WARN larch_err-redaction-failed" "failed redactor warning logged"
assert_file_contains "$log" "plain diagnostic" "failed redactor original message logged"

# 11. sanitize_diagnostic_line strips C0 control bytes from one line.
helper="$SCRATCH/sanitize.sh"
write_helper "$helper" 'printf "before\x01\x02\x03after\x07.end\n" | sanitize_diagnostic_line'
out=$("$helper" 2>/dev/null)
[ "$out" = "beforeafter.end" ] || fail "sanitize_diagnostic_line did not strip controls: '$out'"

# 12. emit_kv rejects embedded LF.
helper="$SCRATCH/emit-kv-lf.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv BAD $'"'"'line1\nline2'"'"' || printf "rc=%s\n" "$?"'
"$helper" >"$SCRATCH/emit-kv-lf.out" 2>"$SCRATCH/emit-kv-lf.err"
assert_eq "$(cat "$SCRATCH/emit-kv-lf.out")" "rc=2" "emit_kv lf reject rc"
grep -Fq 'emit_kv: value for key BAD must not contain newline or carriage return' "$SCRATCH/emit-kv-lf.err" \
    || fail "emit_kv lf reject message"

# 13. emit_kv rejects embedded CR.
helper="$SCRATCH/emit-kv-cr.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv BAD $'"'"'line1\rline2'"'"' || printf "rc=%s\n" "$?"'
"$helper" >"$SCRATCH/emit-kv-cr.out" 2>"$SCRATCH/emit-kv-cr.err"
assert_eq "$(cat "$SCRATCH/emit-kv-cr.out")" "rc=2" "emit_kv cr reject rc"

# 14. emit_kv rejects both LF and CR.
helper="$SCRATCH/emit-kv-both.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv BAD $'"'"'a\n\rb'"'"' || printf "rc=%s\n" "$?"'
"$helper" >"$SCRATCH/emit-kv-both.out" 2>"$SCRATCH/emit-kv-both.err"
assert_eq "$(cat "$SCRATCH/emit-kv-both.out")" "rc=2" "emit_kv both reject rc"

# 15. emit_kv allows literal backslash-n (not a newline byte).
helper="$SCRATCH/emit-kv-literal.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv OK "literal\\n text"'
out=$("$helper")
assert_eq "$out" 'OK=literal\n text' "emit_kv literal backslash-n"

# 16. emit_kv allows long single-line values.
helper="$SCRATCH/emit-kv-long.sh"
write_helper "$helper" 'LARCH_QUIET_DISABLE=1; export LARCH_QUIET_DISABLE; emit_kv LONG "$(printf "%2000s" "" | tr " " "A")"'
out=$("$helper")
case "$out" in LONG=AAAA*) ;; *) fail "emit_kv long single-line value" ;; esac

printf 'PASS: test-lib-quiet.sh\n'
