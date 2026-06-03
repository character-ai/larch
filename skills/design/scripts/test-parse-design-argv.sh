#!/usr/bin/env bash
# Offline harness for parse-design-argv.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SUBJECT="$SCRIPT_DIR/parse-design-argv.sh"

PASS=0
FAIL=0
OUT=""
RC=0

fail() {
    FAIL=$((FAIL + 1))
    printf '  FAIL: %s\n' "$*" >&2
}

pass() {
    PASS=$((PASS + 1))
    printf '  PASS: %s\n' "$*"
}

run_case() {
    set +e
    OUT=$("$SUBJECT" "$@")
    RC=$?
    set -e
}

assert_rc() {
    local label="$1" want="$2"
    if [ "$RC" = "$want" ]; then
        pass "$label rc"
    else
        fail "$label rc — expected $want, got $RC"
    fi
}

kv_value() {
    local key="$1"
    printf '%s\n' "$OUT" | awk -F= -v k="$key" '$1 == k {print substr($0, length(k)+2); found=1; exit} END {if (!found) print ""}'
}

assert_kv() {
    local label="$1" key="$2" want="$3" got
    got=$(kv_value "$key")
    if [ "$got" = "$want" ]; then
        pass "$label $key"
    else
        fail "$label $key — expected <$want>, got <${got}>"
    fi
}

assert_no_flag_kvs() {
    local label="$1"
    if printf '%s\n' "$OUT" | grep -Eq '^(HARD_REQUESTED|PARTITION_REQUESTED|BRAINSTORM_REQUESTED|MANUAL_REQUESTED|NO_DEDUP_REQUESTED|RUN_ID|POSITIONAL_KIND|POSITIONAL_VALUE)='; then
        fail "$label emitted success KVs on validation failure"
    else
        pass "$label emitted no success KVs"
    fi
}

assert_common_false() {
    local label="$1"
    assert_kv "$label" HARD_REQUESTED false
    assert_kv "$label" PARTITION_REQUESTED false
    assert_kv "$label" BRAINSTORM_REQUESTED false
    assert_kv "$label" MANUAL_REQUESTED false
    assert_kv "$label" NO_DEDUP_REQUESTED false
    assert_kv "$label" RUN_ID ""
}

# bare numeric tail
run_case 3249
assert_rc 'numeric tail' 0
assert_common_false 'numeric tail'
assert_kv 'numeric tail' POSITIONAL_KIND issue
assert_kv 'numeric tail' POSITIONAL_VALUE 3249

# numeric issue ignores trailing tokens
run_case 3249 extra words
assert_rc 'numeric issue extra tokens' 0
assert_kv 'numeric issue extra tokens' POSITIONAL_KIND issue
assert_kv 'numeric issue extra tokens' POSITIONAL_VALUE 3249

# bare verbal tail
run_case add a foo flag
assert_rc 'verbal tail' 0
assert_kv 'verbal tail' POSITIONAL_KIND verbal
assert_kv 'verbal tail' POSITIONAL_VALUE 'add a foo flag'

# each boolean flag alone
run_case --hard
assert_rc '--hard' 0
assert_kv '--hard' HARD_REQUESTED true
assert_kv '--hard' POSITIONAL_KIND none

run_case -p
assert_rc '-p' 0
assert_kv '-p' PARTITION_REQUESTED true

run_case --partition
assert_rc '--partition' 0
assert_kv '--partition' PARTITION_REQUESTED true

run_case --brainstorm
assert_rc '--brainstorm' 0
assert_kv '--brainstorm' BRAINSTORM_REQUESTED true

run_case --manual
assert_rc '--manual' 0
assert_kv '--manual' MANUAL_REQUESTED true

run_case -m
assert_rc '-m' 0
assert_kv '-m' MANUAL_REQUESTED true

run_case --no-dedup
assert_rc '--no-dedup' 0
assert_kv '--no-dedup' NO_DEDUP_REQUESTED true

# run id
run_case --run-id RID42 3249
assert_rc '--run-id issue' 0
assert_kv '--run-id issue' RUN_ID RID42
assert_kv '--run-id issue' POSITIONAL_KIND issue
assert_kv '--run-id issue' POSITIONAL_VALUE 3249

run_case --run-id r1 add a thing
assert_rc '--run-id verbal tail' 0
assert_kv '--run-id verbal tail' RUN_ID r1
assert_kv '--run-id verbal tail' POSITIONAL_KIND verbal
assert_kv '--run-id verbal tail' POSITIONAL_VALUE 'add a thing'

run_case --run-id
assert_rc '--run-id missing' 3
assert_kv '--run-id missing' VALIDATION_ERROR --run-id
assert_no_flag_kvs '--run-id missing'

# flags then positional
run_case --hard 3249
assert_rc 'flags then positional' 0
assert_kv 'flags then positional' HARD_REQUESTED true
assert_kv 'flags then positional' POSITIONAL_KIND issue
assert_kv 'flags then positional' POSITIONAL_VALUE 3249

# positional then flaglike: trailing token is not re-parsed
run_case 3249 --hard
assert_rc 'positional then flaglike' 0
assert_kv 'positional then flaglike' HARD_REQUESTED false
assert_kv 'positional then flaglike' POSITIONAL_KIND issue
assert_kv 'positional then flaglike' POSITIONAL_VALUE 3249

# validation errors
run_case --hard --hard
assert_rc 'duplicate hard' 3
assert_kv 'duplicate hard' VALIDATION_ERROR --hard
assert_no_flag_kvs 'duplicate hard'

run_case --simple 3249
assert_rc 'retired simple' 3
assert_kv 'retired simple' VALIDATION_ERROR --simple
assert_no_flag_kvs 'retired simple'

run_case --bogus
assert_rc 'bogus long' 3
assert_kv 'bogus long' VALIDATION_ERROR --bogus
assert_no_flag_kvs 'bogus long'

run_case -z
assert_rc 'bogus short' 3
assert_kv 'bogus short' VALIDATION_ERROR -z
assert_no_flag_kvs 'bogus short'

# empty argv
run_case
assert_rc 'empty argv' 0
assert_kv 'empty argv' POSITIONAL_KIND none
assert_kv 'empty argv' POSITIONAL_VALUE ""

# end of options
run_case --hard --
assert_rc 'terminator only' 0
assert_kv 'terminator only' HARD_REQUESTED true
assert_kv 'terminator only' POSITIONAL_KIND none
assert_kv 'terminator only' POSITIONAL_VALUE ""

run_case --hard -- 3249
assert_rc 'terminator issue' 0
assert_kv 'terminator issue' HARD_REQUESTED true
assert_kv 'terminator issue' POSITIONAL_KIND issue
assert_kv 'terminator issue' POSITIONAL_VALUE 3249

run_case -- --hard
assert_rc 'terminator flaglike verbal' 0
assert_common_false 'terminator flaglike verbal'
assert_kv 'terminator flaglike verbal' POSITIONAL_KIND verbal
assert_kv 'terminator flaglike verbal' POSITIONAL_VALUE --hard

# verbal metacharacters passed as one arg
run_case "Strunk & White \$x"
assert_rc 'metachar verbal' 0
assert_kv 'metachar verbal' POSITIONAL_KIND verbal
assert_kv 'metachar verbal' POSITIONAL_VALUE "Strunk & White \$x"

# embedded newline in verbal token is rejected
run_case $'foo\nHARD_REQUESTED=true'
assert_rc 'newline smuggling' 3
assert_kv 'newline smuggling' VALIDATION_ERROR newline-in-value
assert_no_flag_kvs 'newline smuggling'

if [ "$FAIL" -ne 0 ]; then
    printf '\nparse-design-argv tests: %s passed, %s failed\n' "$PASS" "$FAIL" >&2
    exit 1
fi
printf '\nparse-design-argv tests: %s passed, 0 failed\n' "$PASS"
