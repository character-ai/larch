#!/usr/bin/env bash
# Regression tests for scripts/ci-failed-jobs.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/ci-failed-jobs.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-ci-failed-jobs.XXXXXX")"
PASS=0
FAIL=0
trap 'rm -rf "$TMPROOT"' EXIT

ok() { printf '  PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf '  FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

assert_file_contains() {
    local label=$1 file=$2 needle=$3
    if grep -Fq "$needle" "$file"; then ok "$label"; else fail "$label (missing $needle)"; sed 's/^/    /' "$file" >&2 || true; fi
}

assert_rc() {
    local label=$1 actual=$2 expected=$3
    if [ "$actual" = "$expected" ]; then ok "$label"; else fail "$label (expected $expected got $actual)"; fi
}

write_subject() {
    local root=$1
    mkdir -p "$root/scripts"
    cp "$SUBJECT" "$root/scripts/ci-failed-jobs.sh"
    cp "$REPO_ROOT/scripts/lib-quiet.sh" "$root/scripts/lib-quiet.sh"
    chmod +x "$root/scripts/ci-failed-jobs.sh"
}

write_gh_lines() {
    local root=$1
    cat > "$root/scripts/gh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
case "${GH_MODE:-lines}" in
  in-progress)
    printf '%s\n' 'run 123 is still in progress; logs will be available when it is complete' >&2
    exit 1
    ;;
  fail)
    if [ -n "${GH_FAIL_STDERR_FILE:-}" ] && [ -r "${GH_FAIL_STDERR_FILE}" ]; then
        cat "${GH_FAIL_STDERR_FILE}" >&2
    else
        printf '%s\n' 'HTTP 500' >&2
    fi
    exit 2
    ;;
  lines)
    cat "${GH_LINES_FILE:-/dev/null}"
    exit "${GH_RC:-0}"
    ;;
esac
SH
    chmod +x "$root/scripts/gh"
}

write_lines_file() {
    local file=$1
    shift
    : > "$file"
    while [ "$#" -gt 0 ]; do
        printf '%s\n' "$1" >> "$file"
        shift
    done
}

run_subject() {
    local root=$1 out=$2 err=$3 tsv=$4 rc=0
    PATH="$root/scripts:$PATH" LARCH_QUIET_DISABLE="${LARCH_QUIET_DISABLE:-1}" \
        GH_MODE="${GH_MODE:-lines}" GH_LINES_FILE="${GH_LINES_FILE:-}" \
        GH_FAIL_STDERR_FILE="${GH_FAIL_STDERR_FILE:-}" \
        "$root/scripts/ci-failed-jobs.sh" --run-id run123 --repo owner/repo --output-tsv "$tsv" \
        > "$out" 2> "$err" || rc=$?
    printf '%s\n' "$rc"
}

T1="$TMPROOT/t1"
mkdir -p "$T1"
write_subject "$T1"
write_gh_lines "$T1"
out="$T1/out"; err="$T1/err"; tsv="$T1/jobs.tsv"
write_lines_file "$T1/lines.txt" "lint" "test-harnesses (7)" "gitleaks"
GH_LINES_FILE="$T1/lines.txt"
rc=$(run_subject "$T1" "$out" "$err" "$tsv")
assert_rc "mixed failed jobs exits 0" "$rc" 0
assert_file_contains "count emitted" "$out" "FAILED_JOBS_COUNT=3"
assert_file_contains "fixable list emitted" "$out" "FAILED_JOBS_FIXABLE=lint,test-harnesses:7"
assert_file_contains "unfixable list emitted" "$out" "FAILED_JOBS_UNFIXABLE=gitleaks=history-scan"
assert_file_contains "tsv lint row" "$tsv" $'lint\t\tfixable'
assert_file_contains "tsv shard row" "$tsv" $'test-harnesses\t7\tfixable'

T2="$TMPROOT/t2"
mkdir -p "$T2"
write_subject "$T2"
write_gh_lines "$T2"
write_lines_file "$T2/lines.txt" "test-harnesses (abc)" "test-harnesses (7); echo pwn"
GH_LINES_FILE="$T2/lines.txt"
rc=$(run_subject "$T2" "$T2/out" "$T2/err" "$T2/jobs.tsv")
assert_rc "malformed/shard exits 0" "$rc" 0
assert_file_contains "non-digit shard falls back to unsharded fixable" "$T2/jobs.tsv" $'test-harnesses\t\tfixable'
assert_file_contains "injection job is malformed" "$T2/out" "FAILED_JOBS_UNFIXABLE=test-harnesses7echopwn=malformed-job-name"

T3="$TMPROOT/t3"
mkdir -p "$T3"
write_subject "$T3"
write_gh_lines "$T3"
: > "$T3/lines.txt"
GH_LINES_FILE="$T3/lines.txt"
rc=$(run_subject "$T3" "$T3/out" "$T3/err" "$T3/jobs.tsv")
assert_rc "zero failed jobs exits 0" "$rc" 0
assert_file_contains "zero count emitted" "$T3/out" "FAILED_JOBS_COUNT=0"

T4="$TMPROOT/t4"
mkdir -p "$T4"
write_subject "$T4"
write_gh_lines "$T4"
GH_MODE=in-progress
rc=$(run_subject "$T4" "$T4/out" "$T4/err" "$T4/jobs.tsv")
assert_rc "in-progress exits 3" "$rc" 3

T5="$TMPROOT/t5"
mkdir -p "$T5"
write_subject "$T5"
write_gh_lines "$T5"
GH_MODE=fail
rc=$(run_subject "$T5" "$T5/out" "$T5/err" "$T5/jobs.tsv")
assert_rc "gh failure exits 1" "$rc" 1

T6="$TMPROOT/t6"
mkdir -p "$T6"
write_subject "$T6"
write_gh_lines "$T6"
write_lines_file "$T6/lines.txt" "lint"
GH_MODE=lines
GH_LINES_FILE="$T6/lines.txt" LARCH_QUIET_DISABLE="" PATH="$T6/scripts:$PATH" \
    "$T6/scripts/ci-failed-jobs.sh" --run-id run123 --repo owner/repo --output-tsv "$T6/jobs.tsv" \
    > "$T6/fd3.out" 2> "$T6/fd3.err"
assert_file_contains "quiet fd3 carries kv output" "$T6/fd3.out" "FAILED_JOBS_COUNT=1"
if grep -Fq $'lint\t\tfixable' "$T6/fd3.out"; then
    fail "quiet fd3 suppresses TSV rows from stdout"
else
    ok "quiet fd3 suppresses TSV rows from stdout"
fi

T7="$TMPROOT/t7"
mkdir -p "$T7"
write_subject "$T7"
write_gh_lines "$T7"
write_lines_file "$T7/lines.txt" \
    "lint" "lint-mermaid" "shellcheck" "test-harnesses (4)" "agent-lint" "agnix" "smoke-dialectic" "agent-sync" \
    "gitleaks" "trufflehog"
GH_LINES_FILE="$T7/lines.txt"
rc=$(run_subject "$T7" "$T7/out" "$T7/err" "$T7/jobs.tsv")
assert_rc "table-driven mapping exits 0" "$rc" 0
for row in \
    $'lint\t\tfixable' \
    $'lint-mermaid\t\tfixable' \
    $'shellcheck\t\tfixable' \
    $'test-harnesses\t4\tfixable' \
    $'agent-lint\t\tfixable' \
    $'agnix\t\tfixable' \
    $'smoke-dialectic\t\tfixable' \
    $'agent-sync\t\tfixable' \
    $'gitleaks\t\tno-local-equivalent' \
    $'trufflehog\t\tno-local-equivalent'
do
    assert_file_contains "table-driven row $row" "$T7/jobs.tsv" "$row"
done

T8="$TMPROOT/t8"
mkdir -p "$T8"
write_subject "$T8"
write_gh_lines "$T8"
printf '%b\n' 'HTTP 500\x07Bad Gateway\x1b[31mred\x1b[0m' > "$T8/stderr.txt"
GH_MODE=fail
GH_FAIL_STDERR_FILE="$T8/stderr.txt"
rc=$(run_subject "$T8" "$T8/out" "$T8/err" "$T8/jobs.tsv")
assert_rc "control-byte gh failure exits 1" "$rc" 1
assert_file_contains "control-byte stderr preserves prefix" "$T8/err" "HTTP 500"
assert_file_contains "control-byte stderr preserves prose" "$T8/err" "Bad Gateway"
if grep -aF $'\x07' "$T8/err" >/dev/null; then
    fail "control-byte stderr strips BEL"
else
    ok "control-byte stderr strips BEL"
fi
if grep -aF $'\x1b' "$T8/err" >/dev/null; then
    fail "control-byte stderr strips ESC"
else
    ok "control-byte stderr strips ESC"
fi
unset GH_FAIL_STDERR_FILE

workflow_jobs=$(awk '
    /^jobs:$/ { in_jobs=1; next }
    in_jobs && /^[a-zA-Z_][a-zA-Z0-9_-]*:/ { exit }
    in_jobs && /^  [a-z][a-z0-9_-]+:$/ { sub(/^  /, ""); sub(/:$/, ""); print }
' "$REPO_ROOT/.github/workflows/ci.yaml")
for job in $workflow_jobs; do
    case "$job" in
        lint|lint-mermaid|shellcheck|test-harnesses|agent-lint|agnix|gitleaks|trufflehog|agent-sync|smoke-dialectic)
            ok "workflow job mapped: $job"
            ;;
        *)
            fail "workflow job missing from ci-failed-jobs mapping: $job"
            ;;
    esac
done

if [ "$FAIL" -ne 0 ]; then
    printf 'test-ci-failed-jobs: %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'test-ci-failed-jobs: %s passed\n' "$PASS"
