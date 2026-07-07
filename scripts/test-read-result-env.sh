#!/usr/bin/env bash
# Offline harness for read-result-env.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SUBJECT="$ROOT/scripts/read-result-env.sh"
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/test-read-result-env.XXXXXX")
trap 'rm -rf "$SCRATCH"' EXIT

PASS=0
FAIL=0
RC=0
OUT=""

fail() {
    FAIL=$((FAIL + 1))
    printf '  FAIL: %s\n' "$*" >&2
}

pass() {
    PASS=$((PASS + 1))
    printf '  PASS: %s\n' "$*"
}

run_subject() {
    set +e
    OUT=$("$SUBJECT" "$@" 2>"$SCRATCH/stderr")
    RC=$?
    set -e
}

assert_rc() {
    local label="$1" want="$2"
    if [ "$RC" = "$want" ]; then
        pass "$label rc"
    else
        fail "$label rc — expected $want, got $RC; stdout=<$OUT>; stderr=<$(cat "$SCRATCH/stderr" 2>/dev/null || true)>"
    fi
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

assert_stdout_contains() {
    local label="$1" needle="$2"
    if printf '%s\n' "$OUT" | grep -Fq -- "$needle"; then
        pass "$label"
    else
        fail "$label — missing stdout <$needle>; got <$OUT>"
    fi
}

write_input() {
    local path="$1"
    shift
    printf '%s\n' "$@" >"$path"
}

primary="$SCRATCH/primary.env"
out="$SCRATCH/out.env"
write_input "$primary" 'INIT_STATUS=ok' 'SECRET=drop' 'RUN_PARAMS_PATH=/tmp/run.json' '' 'DESIGN_CLASSIFICATION='
run_subject --input "$primary" --allow INIT_STATUS --allow RUN_PARAMS_PATH --output "$out"
assert_rc 'allowlisted primary' 0
assert_file_contains 'allowlisted key written' "$out" "INIT_STATUS='ok'"
assert_file_contains 'multiple allow written' "$out" "RUN_PARAMS_PATH='/tmp/run.json'"
assert_file_not_contains 'non-allowlisted key dropped' "$out" 'SECRET='
assert_file_not_contains 'unallowed key dropped' "$out" 'DESIGN_CLASSIFICATION='

write_input "$primary" '' ''
run_subject --input "$primary" --output "$out"
assert_rc 'no allow flags' 0
if [ -f "$out" ] && [ ! -s "$out" ]; then
    pass 'no allow flags writes empty output'
else
    fail 'no allow flags should write empty sourceable output'
fi

write_input "$primary" 'RUN_PARAMS_PATH=/tmp/a=b=c'
run_subject --input "$primary" --allow RUN_PARAMS_PATH --output "$out"
assert_rc 'embedded equals primary' 0
assert_file_contains 'embedded equals preserved primary' "$out" "RUN_PARAMS_PATH='/tmp/a=b=c'"

fallback="$SCRATCH/fallback.env"
write_input "$fallback" 'RUN_PARAMS_PATH=/tmp/fallback=a=b'
run_subject --input "$SCRATCH/missing.env" --fallback-input "$fallback" --allow RUN_PARAMS_PATH --output "$out"
assert_rc 'embedded equals fallback' 0
assert_file_contains 'embedded equals preserved fallback' "$out" "RUN_PARAMS_PATH='/tmp/fallback=a=b'"

write_input "$primary" 'WARN=look=here' 'ERROR=bad=thing' 'INIT_STATUS=ok'
run_subject --input "$primary" --allow INIT_STATUS --output "$out"
assert_rc 'warn error replay' 0
assert_stdout_contains 'WARN replay first equals' 'WARN=look=here'
assert_stdout_contains 'ERROR replay first equals' 'ERROR=bad=thing'
assert_file_not_contains 'WARN not written to output' "$out" 'WARN='
assert_file_not_contains 'ERROR not written to output' "$out" 'ERROR='

write_input "$primary" 'INIT_STATUS=ok' 'malformed-line'
run_subject --input "$primary" --allow INIT_STATUS --output "$out"
assert_rc 'nonblank no equals skipped' 0
assert_file_contains 'nonblank no equals still reads valid keys' "$out" "INIT_STATUS='ok'"

ln -s "$primary" "$SCRATCH/primary-link.env"
run_subject --input "$SCRATCH/primary-link.env" --allow INIT_STATUS --output "$out"
assert_rc 'symlink input without fallback' 1

run_subject --input "$SCRATCH/no-such.env" --allow INIT_STATUS --output "$out"
assert_rc 'missing input without fallback' 1

mkdir "$SCRATCH/primary-dir.env"
run_subject --input "$SCRATCH/primary-dir.env" --allow INIT_STATUS --output "$out"
assert_rc 'nonregular primary without fallback' 1

write_input "$fallback" 'INIT_STATUS=ok'
run_subject --input "$SCRATCH/no-such.env" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'missing input with fallback' 0
assert_file_contains 'missing fallback parsed' "$out" "INIT_STATUS='ok'"

run_subject --input "$SCRATCH/primary-link.env" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'symlink input with fallback' 0
assert_file_contains 'symlink fallback parsed' "$out" "INIT_STATUS='ok'"
assert_stdout_contains 'symlink fallback breadcrumb' 'refusing primary path'

run_subject --input "$SCRATCH/primary-dir.env" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'nonregular primary with fallback' 0
assert_file_contains 'nonregular fallback parsed' "$out" "INIT_STATUS='ok'"

write_input "$primary" 'INIT_STATUS=primary'
write_input "$fallback" 'INIT_STATUS=fallback'
run_subject --input "$primary" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'regular input ignores fallback' 0
assert_file_contains 'regular primary wins' "$out" "INIT_STATUS='primary'"
assert_file_not_contains 'fallback ignored for regular' "$out" "INIT_STATUS='fallback'"

write_input "$primary" ''
write_input "$fallback" 'INIT_STATUS=fallback'
run_subject --input "$primary" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'empty regular primary ignores fallback' 0
assert_file_not_contains 'empty primary must not revive fallback' "$out" 'INIT_STATUS='

write_input "$primary" 'INIT_STATUS=ok' 'malformed-line'
write_input "$fallback" 'INIT_STATUS=fallback'
rm -f "$out"
run_subject --input "$primary" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'malformed regular primary with fallback' 0
assert_file_contains 'malformed primary uses primary valid keys' "$out" "INIT_STATUS='ok'"
assert_file_not_contains 'malformed primary must not fall back' "$out" "INIT_STATUS='fallback'"

ln -s "$fallback" "$SCRATCH/fallback-link.env"
run_subject --input "$SCRATCH/no-such.env" --fallback-input "$SCRATCH/fallback-link.env" --allow INIT_STATUS --output "$out"
assert_rc 'symlink fallback input' 1

mkdir "$SCRATCH/fallback-dir.env"
run_subject --input "$SCRATCH/no-such.env" --fallback-input "$SCRATCH/fallback-dir.env" --allow INIT_STATUS --output "$out"
assert_rc 'nonregular fallback input' 1

printf 'INIT_STATUS=bad\rvalue\n' >"$primary"
run_subject --input "$primary" --allow INIT_STATUS --output "$out"
assert_rc 'carriage return value skipped' 0
assert_file_not_contains 'carriage return key not written' "$out" 'INIT_STATUS='

write_input "$primary" "RUN_PARAMS_PATH=Bob's run"
run_subject --input "$primary" --allow RUN_PARAMS_PATH --output "$out"
assert_rc 'single quote encoded' 0
assert_file_contains 'single quote source encoding' "$out" "RUN_PARAMS_PATH='Bob'\"'\"'s run'"
# shellcheck source=/dev/null
. "$out"
if [ "${RUN_PARAMS_PATH:-}" = "Bob's run" ]; then
    pass 'output sourceable quote value'
else
    fail "output sourceable quote value — got <${RUN_PARAMS_PATH:-}>"
fi

write_input "$primary" 'INIT_STATUS=ok' 'RENAMED=true'
run_subject --input "$primary" --allow INIT_STATUS --allow RENAMED --output "$out"
assert_rc 'sourceable expected vars' 0
unset INIT_STATUS RENAMED
# shellcheck source=/dev/null
. "$out"
if [ "${INIT_STATUS:-}" = ok ] && [ "${RENAMED:-}" = true ]; then
    pass 'output binds expected variables'
else
    fail 'output should bind expected variables'
fi

init_primary="$SCRATCH/.design-init-runparams-result.env"
ln -s "$primary" "$init_primary"
write_input "$fallback" 'INIT_STATUS=ok'
run_subject --input "$init_primary" --fallback-input "$fallback" --allow INIT_STATUS --output "$out"
assert_rc 'design init symlink fallback' 0
assert_stdout_contains 'design init symlink breadcrumb preserved' '**⚠ Step 0b: design-init-runparams result env is a symlink; refusing to source**'

if [ "$FAIL" -ne 0 ]; then
    printf '\nread-result-env tests: %s passed, %s failed\n' "$PASS" "$FAIL" >&2
    exit 1
fi
printf '\nread-result-env tests: %s passed, 0 failed\n' "$PASS"
