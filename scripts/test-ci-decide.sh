#!/usr/bin/env bash
set -euo pipefail

export LARCH_QUIET_DISABLE=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT="$SCRIPT_DIR/ci-decide.sh"
REPORT=(python3 "$SCRIPT_DIR/../python/cli.py" stall-recovery)
pass=0
fail=0

tmp=$(mktemp -d "${TMPDIR:-/tmp}/ci-decide-test.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

run_case() {
    local name=$1
    shift
    "$SCRIPT" "$@" >"$tmp/$name.out"
}
kv() { awk -F= -v k="$1" '$1==k{print $2; exit}' "$2"; }
assert_eq() {
    local expected=$1 actual=$2 label=$3
    if [ "$expected" = "$actual" ]; then
        pass=$((pass + 1)); printf 'PASS: %s\n' "$label"
    else
        fail=$((fail + 1)); printf 'FAIL: %s expected=%s actual=%s\n' "$label" "$expected" "$actual"
    fi
}

run_case timeout --status pending --behind 0 --iteration 50 --rebase-count 0 --fix-attempts 0
assert_eq bail "$(kv ACTION "$tmp/timeout.out")" "timeout action bails"
assert_eq ci-timeout "$(kv BAIL_REASON "$tmp/timeout.out")" "timeout emits report-safe token"

run_case rebase --status pending --behind 1 --iteration 0 --rebase-count 20 --fix-attempts 0
assert_eq ci-too-many-rebases "$(kv BAIL_REASON "$tmp/rebase.out")" "rebase cap emits report-safe token"

run_case fixes --status fail --behind 0 --iteration 0 --rebase-count 0 --fix-attempts 10
assert_eq fix-attempts-exhausted "$(kv BAIL_REASON "$tmp/fixes.out")" "fix cap token stays aligned"

run_case error --status error --behind 0 --iteration 0 --rebase-count 0 --fix-attempts 0
assert_eq ci-status-error "$(kv BAIL_REASON "$tmp/error.out")" "ci-status error emits report-safe token"

for token in ci-timeout ci-too-many-rebases fix-attempts-exhausted ci-status-error; do
    dir="$tmp/report-$token"
    mkdir -p "$dir"
    cat >"$dir/ship-pr-state.sh" <<EOF
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=10
BAIL_REASON=$token
EXIT_CODE=3
EOF
    "${REPORT[@]}" classify --implement-tmpdir "$dir" >"$dir/classify.out"
    assert_eq "$token" "$(kv BAIL_REASON "$dir/classify.out")" "stall report accepts $token"
done

dir="$tmp/report-ci-local"
mkdir -p "$dir"
cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=10
BAIL_REASON=ci-local-unfixable:lint_1,test-2
EXIT_CODE=3
EOF
"${REPORT[@]}" classify --implement-tmpdir "$dir" >"$dir/classify.out"
assert_eq "ci-local-unfixable:lint_1,test-2" "$(kv BAIL_REASON "$dir/classify.out")" "stall report accepts ci-local compound suffix"

cat >"$dir/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=10
BAIL_REASON=ci-local-unfixable
EXIT_CODE=3
EOF
"${REPORT[@]}" classify --implement-tmpdir "$dir" >"$dir/bare.out"
assert_eq redacted "$(kv BAIL_REASON "$dir/bare.out")" "stall report rejects bare ci-local token"

printf '\nResults: %s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
