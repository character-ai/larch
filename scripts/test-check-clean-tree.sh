#!/usr/bin/env bash
# test-check-clean-tree.sh — regression harness for check-clean-tree.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCRIPT="$REPO_ROOT/scripts/check-clean-tree.sh"
REAL_GIT=$(command -v git)

[ -x "$SCRIPT" ] || { echo "FAIL: $SCRIPT not executable"; exit 1; }

PASS=0
FAIL=0
SANDBOX=$(mktemp -d "${TMPDIR:-/tmp}/larch-check-clean-tree-test.XXXXXX")
trap 'rm -rf "$SANDBOX"' EXIT

assert_rc() {
    local actual=$1 expected=$2 label=$3
    if [ "$actual" -eq "$expected" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label (expected rc=$expected got rc=$actual)"
    fi
}

assert_contains() {
    local needle=$1 haystack=$2 label=$3
    if printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

assert_not_contains() {
    local needle=$1 haystack=$2 label=$3
    if ! printf '%s' "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        echo "PASS: $label"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $label"
        echo "  expected not to contain: $needle"
        printf '%s\n' "$haystack" | sed 's/^/    /'
    fi
}

make_repo() {
    local name=$1 repo
    repo="$SANDBOX/$name"
    mkdir -p "$repo"
    git -C "$repo" init -q
    printf '%s\n' "$repo"
}

run_check() {
    local repo=$1
    shift
    set +e
    OUT=$(cd "$repo" && "$SCRIPT" "$@" 2>"$SANDBOX/stderr.txt")
    RC=$?
    ERR=$(cat "$SANDBOX/stderr.txt")
    set -e
}

make_git_status_failure_shim() {
    local dir=$1
    mkdir -p "$dir"
    cat > "$dir/git" <<SHIM_EOF
#!/usr/bin/env bash
if [ "\${1:-}" = "status" ] && [ "\${2:-}" = "--porcelain" ]; then
    printf 'fatal: shim status failed\\nsecond line\\twith tab\\n' >&2
    exit 1
fi
exec "$REAL_GIT" "\$@"
SHIM_EOF
    chmod +x "$dir/git"
}

repo=$(make_repo clean)
run_check "$repo"
assert_rc "$RC" 0 "clean: exit 0"
assert_contains "CLEAN=true" "$OUT" "clean: emits CLEAN=true"
assert_not_contains "DIRTY_OUT=" "$OUT" "clean: no DIRTY_OUT"

repo=$(make_repo dirty-default)
printf 'dirty\n' > "$repo/untracked.txt"
run_check "$repo"
assert_rc "$RC" 0 "dirty default: exit 0"
assert_contains "CLEAN=false" "$OUT" "dirty default: emits CLEAN=false"
assert_contains "DIRTY_OUT=" "$OUT" "dirty default: emits DIRTY_OUT"

repo=$(make_repo dirty-fail-closed)
printf 'dirty\n' > "$repo/untracked.txt"
run_check "$repo" --fail-closed
assert_rc "$RC" 0 "dirty fail-closed: exit 0"
assert_contains "CLEAN=false" "$OUT" "dirty fail-closed: emits CLEAN=false"
assert_contains "DIRTY_OUT=" "$OUT" "dirty fail-closed: emits DIRTY_OUT"

shim_dir="$SANDBOX/git-shim"
make_git_status_failure_shim "$shim_dir"

repo=$(make_repo probe-fail-default)
PATH="$shim_dir:$PATH" run_check "$repo"
assert_rc "$RC" 0 "probe failure default: exit 0"
assert_contains "CLEAN=true" "$OUT" "probe failure default: fail-open CLEAN=true"
assert_contains "git status --porcelain failed" "$ERR" "probe failure default: stderr carries raw diagnostic"

repo=$(make_repo probe-fail-closed)
PATH="$shim_dir:$PATH" run_check "$repo" --fail-closed
assert_rc "$RC" 1 "probe failure fail-closed: exit 1"
assert_contains "CLEAN=unknown" "$OUT" "probe failure fail-closed: emits CLEAN=unknown"
assert_contains "PROBE_ERROR=git exited 1" "$OUT" "probe failure fail-closed: emits PROBE_ERROR"
assert_contains "git status --porcelain failed" "$ERR" "probe failure fail-closed: stderr carries raw diagnostic"
assert_not_contains "$(printf '\t')" "$OUT" "probe failure fail-closed: stdout summary has no tabs"

repo=$(make_repo bad-arg)
run_check "$repo" --unknown-flag
assert_rc "$RC" 2 "bad arg: exit 2"
assert_contains "unknown flag" "$ERR" "bad arg: stderr diagnostic"

echo
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
