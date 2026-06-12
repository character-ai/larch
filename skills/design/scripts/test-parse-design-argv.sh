#!/usr/bin/env bash
# Offline harness for parse-design-argv.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
SUBJECT="$SCRIPT_DIR/parse-design-argv.sh"

PASS=0
FAIL=0
OUT=""
RC=0
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/test-parse-design-argv.XXXXXX")
trap 'rm -rf "$SCRATCH"' EXIT
ARGV_ENV=""
partition_requested=""
brainstorm_requested=""
approve_requested=""
skip_approve_requested=""
no_dedup_requested=""
run_id=""
POSITIONAL_KIND=""
POSITIONAL_VALUE=""
VALIDATION_ERROR=""

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

run_case_with_output() {
    ARGV_ENV="$SCRATCH/argv.env"
    rm -f "$ARGV_ENV"
    set +e
    OUT=$("$SUBJECT" --output "$ARGV_ENV" "$@")
    RC=$?
    set -e
}

source_argv_env() {
    unset  partition_requested brainstorm_requested approve_requested skip_approve_requested no_dedup_requested run_id POSITIONAL_KIND POSITIONAL_VALUE VALIDATION_ERROR
    # shellcheck source=/dev/null
    . "$ARGV_ENV"
}

assert_file_contains() {
    local label="$1" file="$2" needle="$3"
    if grep -Fq -- "$needle" "$file"; then
        pass "$label"
    else
        fail "$label — missing <$needle> in $file"
    fi
}

assert_file_not_contains() {
    local label="$1" file="$2" needle="$3"
    if grep -Fq -- "$needle" "$file"; then
        fail "$label — unexpected <$needle> in $file"
    else
        pass "$label"
    fi
}

assert_eq() {
    local label="$1" got="$2" want="$3"
    if [ "$got" = "$want" ]; then
        pass "$label"
    else
        fail "$label — expected <$want>, got <$got>"
    fi
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
    if printf '%s\n' "$OUT" | grep -Eq '^(PARTITION_REQUESTED|BRAINSTORM_REQUESTED|APPROVE_REQUESTED|SKIP_APPROVE_REQUESTED|NO_DEDUP_REQUESTED|RUN_ID|POSITIONAL_KIND|POSITIONAL_VALUE)='; then
        fail "$label emitted success KVs on validation failure"
    else
        pass "$label emitted no success KVs"
    fi
}

assert_success_kv_count() {
    local label="$1" want="$2" got
    got=$(printf '%s\n' "$OUT" | awk -F= '/^(PARTITION_REQUESTED|BRAINSTORM_REQUESTED|APPROVE_REQUESTED|SKIP_APPROVE_REQUESTED|NO_DEDUP_REQUESTED|RUN_ID|POSITIONAL_KIND|POSITIONAL_VALUE)=/ {count++} END {print count + 0}')
    if [ "$got" = "$want" ]; then
        pass "$label success KV count"
    else
        fail "$label success KV count — expected $want, got $got"
    fi
}

assert_common_false() {
    local label="$1"
    assert_kv "$label" PARTITION_REQUESTED false
    assert_kv "$label" BRAINSTORM_REQUESTED false
    assert_kv "$label" APPROVE_REQUESTED false
    assert_kv "$label" SKIP_APPROVE_REQUESTED false
    assert_kv "$label" NO_DEDUP_REQUESTED false
    assert_kv "$label" RUN_ID ""
}

# bare numeric tail
run_case 3249
assert_rc 'numeric tail' 0
assert_success_kv_count 'numeric tail' 8
assert_common_false 'numeric tail'
assert_kv 'numeric tail' POSITIONAL_KIND issue
assert_kv 'numeric tail' POSITIONAL_VALUE 3249

# numeric issue ignores trailing tokens
run_case 3249 extra words
assert_rc 'numeric issue extra tokens' 0
assert_kv 'numeric issue extra tokens' POSITIONAL_KIND issue
assert_kv 'numeric issue extra tokens' POSITIONAL_VALUE 3249
assert_kv 'numeric issue extra tokens' SKIP_APPROVE_REQUESTED false

# bare verbal tail
run_case add a foo flag
assert_rc 'verbal tail' 0
assert_kv 'verbal tail' POSITIONAL_KIND verbal
assert_kv 'verbal tail' POSITIONAL_VALUE 'add a foo flag'

# each boolean flag alone

run_case -p
assert_rc '-p' 0
assert_kv '-p' PARTITION_REQUESTED true

run_case --partition
assert_rc '--partition' 0
assert_kv '--partition' PARTITION_REQUESTED true

run_case --brainstorm
assert_rc '--brainstorm' 0
assert_kv '--brainstorm' BRAINSTORM_REQUESTED true

run_case --per-round-approval
assert_rc '--per-round-approval' 0
assert_kv '--per-round-approval' APPROVE_REQUESTED true
assert_kv '--per-round-approval' SKIP_APPROVE_REQUESTED false
assert_kv '--per-round-approval' POSITIONAL_KIND none

# --per-round-approval composes with an issue tail and leaves other booleans false
run_case --per-round-approval 3249
assert_rc '--per-round-approval issue' 0
assert_kv '--per-round-approval issue' APPROVE_REQUESTED true
assert_kv '--per-round-approval issue' SKIP_APPROVE_REQUESTED false
assert_kv '--per-round-approval issue' POSITIONAL_KIND issue
assert_kv '--per-round-approval issue' POSITIONAL_VALUE 3249

run_case --skip-approve
assert_rc '--skip-approve' 0
assert_kv '--skip-approve' SKIP_APPROVE_REQUESTED true
assert_kv '--skip-approve' APPROVE_REQUESTED false
assert_kv '--skip-approve' POSITIONAL_KIND none

run_case -s
assert_rc '-s' 0
assert_kv '-s' SKIP_APPROVE_REQUESTED true
assert_kv '-s' APPROVE_REQUESTED false
assert_kv '-s' POSITIONAL_KIND none

# --skip-approve composes with an issue tail
run_case --skip-approve 3249
assert_rc '--skip-approve issue' 0
assert_kv '--skip-approve issue' SKIP_APPROVE_REQUESTED true
assert_kv '--skip-approve issue' APPROVE_REQUESTED false
assert_kv '--skip-approve issue' POSITIONAL_KIND issue
assert_kv '--skip-approve issue' POSITIONAL_VALUE 3249

# --per-round-approval and --skip-approve are orthogonal; both can appear together
run_case --per-round-approval --skip-approve 3249
assert_rc '--per-round-approval --skip-approve compose' 0
assert_kv '--per-round-approval --skip-approve compose' APPROVE_REQUESTED true
assert_kv '--per-round-approval --skip-approve compose' SKIP_APPROVE_REQUESTED true
assert_kv '--per-round-approval --skip-approve compose' POSITIONAL_KIND issue
assert_kv '--per-round-approval --skip-approve compose' POSITIONAL_VALUE 3249

# retired --approve is rejected
run_case --approve
assert_rc 'retired --approve' 3
assert_kv 'retired --approve' VALIDATION_ERROR --approve
assert_no_flag_kvs 'retired --approve'

run_case --manual
assert_rc '--manual' 3
assert_kv '--manual' VALIDATION_ERROR --manual
assert_no_flag_kvs '--manual'

run_case -m
assert_rc '-m' 3
assert_kv '-m' VALIDATION_ERROR -m
assert_no_flag_kvs '-m'

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

run_case --run-id $'bad\nid' 3249
assert_rc '--run-id newline smuggling' 3
assert_kv '--run-id newline smuggling' VALIDATION_ERROR newline-in-value
assert_no_flag_kvs '--run-id newline smuggling'

# flags then positional
run_case -p --brainstorm --no-dedup 3249
assert_rc 'flags then positional' 0
assert_kv 'flags then positional' POSITIONAL_KIND issue
assert_kv 'flags then positional' POSITIONAL_VALUE 3249

# positional then flaglike: trailing token is not re-parsed
run_case 3249 --bogus
assert_rc 'positional then flaglike' 0
assert_kv 'positional then flaglike' POSITIONAL_KIND issue
assert_kv 'positional then flaglike' POSITIONAL_VALUE 3249

run_case 3249 --hard
assert_rc 'numeric issue trailing retired --hard' 3
assert_kv 'numeric issue trailing retired --hard' VALIDATION_ERROR --hard
assert_no_flag_kvs 'numeric issue trailing retired --hard'

# validation errors
run_case --hard
assert_rc 'retired --hard' 3
assert_kv 'retired --hard' VALIDATION_ERROR --hard
assert_no_flag_kvs 'retired --hard'

run_case --per-round-approval --per-round-approval
assert_rc 'duplicate per-round-approval' 3
assert_kv 'duplicate per-round-approval' VALIDATION_ERROR --per-round-approval
assert_no_flag_kvs 'duplicate per-round-approval'

run_case --skip-approve --skip-approve
assert_rc 'duplicate skip-approve' 3
assert_kv 'duplicate skip-approve' VALIDATION_ERROR --skip-approve
assert_no_flag_kvs 'duplicate skip-approve'

run_case -s -s
assert_rc 'duplicate -s' 3
assert_kv 'duplicate -s' VALIDATION_ERROR --skip-approve
assert_no_flag_kvs 'duplicate -s'

run_case --simple 3249
assert_rc 'retired simple' 3
assert_kv 'retired simple' VALIDATION_ERROR --simple
assert_no_flag_kvs 'retired simple'

run_case --medium 3249
assert_rc 'retired medium' 3
assert_kv 'retired medium' VALIDATION_ERROR --medium
assert_no_flag_kvs 'retired medium'

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
run_case --
assert_rc 'terminator only' 0
assert_kv 'terminator only' POSITIONAL_KIND none
assert_kv 'terminator only' POSITIONAL_VALUE ""

run_case -- 3249
assert_rc 'terminator issue' 0
assert_kv 'terminator issue' POSITIONAL_KIND issue
assert_kv 'terminator issue' POSITIONAL_VALUE 3249

run_case -- --hard
assert_rc 'terminator flaglike verbal' 0
assert_common_false 'terminator flaglike verbal'
assert_kv 'terminator flaglike verbal' POSITIONAL_KIND verbal

# verbal metacharacters passed as one arg
run_case "Strunk & White \$x"
assert_rc 'metachar verbal' 0
assert_kv 'metachar verbal' POSITIONAL_KIND verbal
assert_kv 'metachar verbal' POSITIONAL_VALUE "Strunk & White \$x"

# embedded newline in verbal token is rejected
run_case $'foo\n=true'
assert_rc 'newline smuggling' 3
assert_kv 'newline smuggling' VALIDATION_ERROR newline-in-value
assert_no_flag_kvs 'newline smuggling'


# hidden --output writes sourceable success output and preserves stdout compatibility
run_case_with_output -p --brainstorm --per-round-approval --skip-approve --no-dedup --run-id RID42 3249
assert_rc 'hidden output full flags' 0
assert_success_kv_count 'hidden output full flags' 8
assert_file_contains 'hidden output partition binding' "$ARGV_ENV" "partition_requested='true'"
assert_file_contains 'hidden output brainstorm binding' "$ARGV_ENV" "brainstorm_requested='true'"
assert_file_contains 'hidden output approve binding' "$ARGV_ENV" "approve_requested='true'"
assert_file_contains 'hidden output skip binding' "$ARGV_ENV" "skip_approve_requested='true'"
assert_file_contains 'hidden output no-dedup binding' "$ARGV_ENV" "no_dedup_requested='true'"
assert_file_contains 'hidden output run-id binding' "$ARGV_ENV" "run_id='RID42'"
assert_file_contains 'hidden output positional kind binding' "$ARGV_ENV" "POSITIONAL_KIND='issue'"
assert_file_contains 'hidden output positional value binding' "$ARGV_ENV" "POSITIONAL_VALUE='3249'"
source_argv_env
if [ "$partition_requested" = true ] \
  && [ "$brainstorm_requested" = true ] \
  && [ "$approve_requested" = true ] \
  && [ "$skip_approve_requested" = true ] \
  && [ "$no_dedup_requested" = true ] \
  && [ "$run_id" = RID42 ] \
  && [ "$POSITIONAL_KIND" = issue ] \
  && [ "$POSITIONAL_VALUE" = 3249 ]; then
    pass 'hidden output sourceable success bindings'
else
    fail 'hidden output sourceable success bindings'
fi
assert_eq 'stdout partition matches source' "$(kv_value PARTITION_REQUESTED)" "$partition_requested"
assert_eq 'stdout brainstorm matches source' "$(kv_value BRAINSTORM_REQUESTED)" "$brainstorm_requested"
assert_eq 'stdout approve matches source' "$(kv_value APPROVE_REQUESTED)" "$approve_requested"
assert_eq 'stdout skip matches source' "$(kv_value SKIP_APPROVE_REQUESTED)" "$skip_approve_requested"
assert_eq 'stdout no-dedup matches source' "$(kv_value NO_DEDUP_REQUESTED)" "$no_dedup_requested"
assert_eq 'stdout run-id matches source' "$(kv_value RUN_ID)" "$run_id"
assert_eq 'stdout positional kind matches source' "$(kv_value POSITIONAL_KIND)" "$POSITIONAL_KIND"
assert_eq 'stdout positional value matches source' "$(kv_value POSITIONAL_VALUE)" "$POSITIONAL_VALUE"

run_case_with_output 777
assert_rc 'hidden output numeric tail' 0
source_argv_env
if [ "$POSITIONAL_KIND" = issue ] && [ "$POSITIONAL_VALUE" = 777 ]; then
    pass 'hidden output numeric tail source'
else
    fail 'hidden output numeric tail source'
fi

run_case_with_output add a foo flag
assert_rc 'hidden output verbal tail' 0
source_argv_env
if [ "$POSITIONAL_KIND" = verbal ] && [ "$POSITIONAL_VALUE" = 'add a foo flag' ]; then
    pass 'hidden output verbal tail source'
else
    fail 'hidden output verbal tail source'
fi

run_case_with_output "Strunk & White \$x"
assert_rc 'hidden output metachar verbal' 0
source_argv_env
assert_eq 'hidden output metachar source' "$POSITIONAL_VALUE" "Strunk & White \$x"

run_case_with_output "Bob's feature"
assert_rc 'hidden output quote verbal' 0
source_argv_env
assert_eq 'hidden output quote source' "$POSITIONAL_VALUE" "Bob's feature"
assert_file_contains 'hidden output quote encoded' "$ARGV_ENV" "POSITIONAL_VALUE='Bob'\"'\"'s feature'"

run_case_with_output --output public-path
assert_rc 'public output rejected' 3
assert_kv 'public output rejected' VALIDATION_ERROR --output
source_argv_env
assert_eq 'public output validation sources' "${VALIDATION_ERROR:-}" --output
assert_file_not_contains 'validation output has no partition binding' "$ARGV_ENV" 'partition_requested='

assert_rc 'public output interleaved rejected' 3
assert_kv 'public output interleaved rejected' VALIDATION_ERROR --output
source_argv_env
assert_eq 'public output interleaved validation sources' "${VALIDATION_ERROR:-}" --output

run_case_with_output "--bad'flag"
assert_rc 'quote-bearing validation token' 3
assert_kv 'quote-bearing validation token' VALIDATION_ERROR "--bad'flag"
source_argv_env
assert_eq 'quote-bearing validation token sources' "${VALIDATION_ERROR:-}" "--bad'flag"

run_case_with_output $'bad\nvalue'
assert_rc 'hidden output newline smuggling' 3
assert_kv 'hidden output newline smuggling' VALIDATION_ERROR newline-in-value
source_argv_env
assert_eq 'hidden output newline validation sources' "${VALIDATION_ERROR:-}" newline-in-value

if [ "$FAIL" -ne 0 ]; then
    printf '\nparse-design-argv tests: %s passed, %s failed\n' "$PASS" "$FAIL" >&2
    exit 1
fi
printf '\nparse-design-argv tests: %s passed, 0 failed\n' "$PASS"
