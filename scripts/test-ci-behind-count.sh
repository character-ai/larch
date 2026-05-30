#!/usr/bin/env bash
# Regression tests for scripts/ci-behind-count.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SUBJECT="$REPO_ROOT/scripts/ci-behind-count.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-ci-behind-count.XXXXXX")"
PASS=0
FAIL=0
trap 'rm -rf "$TMPROOT"' EXIT

ok() { printf '  PASS: %s\n' "$1"; PASS=$((PASS + 1)); }
fail() { printf '  FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }

assert_kv() {
    local label=$1 out=$2 key=$3 expected=$4
    local actual
    actual=$(printf '%s\n' "$out" | awk -F= -v k="$key" '$1 == k { print substr($0, index($0,"=")+1); exit }')
    if [ "$actual" = "$expected" ]; then
        ok "$label"
    else
        fail "$label (expected ${key}=${expected} got ${actual:-<empty>})"
        printf '%s\n' "$out" | sed 's/^/    /' >&2 || true
    fi
}

assert_rc() {
    local label=$1 actual=$2 expected=$3
    if [ "$actual" = "$expected" ]; then ok "$label"; else fail "$label (expected rc $expected got $actual)"; fi
}

init_repo() {
    local root=$1
    git -C "$root" init -q
    git -C "$root" config user.email test@example.com
    git -C "$root" config user.name test
    git -C "$root" checkout -q -b main
    printf 'base\n' > "$root/README.md"
    git -C "$root" add README.md
    git -C "$root" commit -q -m base
    git -C "$root" checkout -q -b feature
    printf 'feature\n' > "$root/README.md"
    git -C "$root" add README.md
    git -C "$root" commit -q -m feature
}

run_behind() {
    local root=$1 out=$2 err=$3 rc=0
    shift 3
    (cd "$root" && LARCH_QUIET_DISABLE=1 "$SUBJECT" "$@") >"$out" 2>"$err" || rc=$?
    printf '%s\n' "$rc"
}

# Equal: feature HEAD matches main tip.
T1="$TMPROOT/equal"
mkdir -p "$T1"
init_repo "$T1"
out="$T1/out"; err="$T1/err"
rc=$(run_behind "$T1" "$out" "$err" --no-fetch)
assert_rc "equal branch exits 0" "$rc" 0
assert_kv "equal behind count" "$(cat "$out")" BEHIND_COUNT 0

# Behind: advance origin/main after feature branched.
T2="$TMPROOT/behind"
mkdir -p "$T2"
init_repo "$T2"
git -C "$T2" checkout -q main
printf 'main2\n' > "$T2/README.md"
git -C "$T2" add README.md
git -C "$T2" commit -q -m main2
git -C "$T2" remote add origin "$T2/.git" 2>/dev/null || true
git -C "$T2" fetch -q origin main
git -C "$T2" checkout -q feature
out="$T2/out"; err="$T2/err"
rc=$(run_behind "$T2" "$out" "$err" --no-fetch)
assert_rc "behind branch exits 0" "$rc" 0
assert_kv "behind count is 1" "$(cat "$out")" BEHIND_COUNT 1

# Ahead: feature has commits not on main (behind count stays 0).
T3="$TMPROOT/ahead"
mkdir -p "$T3"
init_repo "$T3"
out="$T3/out"; err="$T3/err"
rc=$(run_behind "$T3" "$out" "$err" --no-fetch)
assert_rc "ahead-only exits 0" "$rc" 0
assert_kv "ahead-only behind count" "$(cat "$out")" BEHIND_COUNT 0

# Fork-style upstream remote.
T4="$TMPROOT/fork"
mkdir -p "$T4"
init_repo "$T4"
git -C "$T4" checkout -q main
printf 'upstream\n' > "$T4/README.md"
git -C "$T4" add README.md
git -C "$T4" commit -q -m upstream
git -C "$T4" remote add upstream "$T4/.git" 2>/dev/null || true
git -C "$T4" fetch -q upstream main
git -C "$T4" checkout -q feature
out="$T4/out"; err="$T4/err"
rc=$(run_behind "$T4" "$out" "$err" --base-remote upstream --base-ref main --no-fetch)
assert_rc "upstream base exits 0" "$rc" 0
assert_kv "upstream behind count" "$(cat "$out")" BEHIND_COUNT 1

# Fail-open on fetch failure (network blip).
T6="$TMPROOT/fetchfail"
mkdir -p "$T6/bin" "$T6/repo"
REAL_GIT=$(command -v git)
init_repo "$T6/repo"
git -C "$T6/repo" remote add origin "$T6/repo/.git" 2>/dev/null || true
git -C "$T6/repo" checkout -q feature
cat > "$T6/bin/git" <<STUB
#!/usr/bin/env bash
case "\$1" in
  fetch) echo "fatal: unable to access remote" >&2; exit 128 ;;
esac
exec "$REAL_GIT" "\$@"
STUB
chmod +x "$T6/bin/git"
out="$T6/out"; err="$T6/err"
rc=0
( cd "$T6/repo" && LARCH_QUIET_DISABLE=1 PATH="$T6/bin:$PATH" \
    "$SUBJECT" --base-remote origin --base-ref main ) >"$out" 2>"$err" || rc=$?
assert_rc "fetch failure exits 0" "$rc" 0
assert_kv "fetch failure fail-open count" "$(cat "$out")" BEHIND_COUNT 0
if grep -Fq 'fetch' "$err"; then
    ok "fetch failure emits diagnostic"
else
    fail "fetch failure should emit stderr diagnostic"
fi

# Fail-open on bad ref.
T5="$TMPROOT/badref"
mkdir -p "$T5"
git -C "$T5" init -q
git -C "$T5" config user.email test@example.com
git -C "$T5" config user.name test
git -C "$T5" checkout -q -b feature
printf 'x\n' > "$T5/README.md"
git -C "$T5" add README.md
git -C "$T5" commit -q -m only
out="$T5/out"; err="$T5/err"
rc=$(run_behind "$T5" "$out" "$err" --base-remote origin --base-ref main --no-fetch)
assert_rc "bad ref exits 0" "$rc" 0
assert_kv "bad ref fail-open" "$(cat "$out")" BEHIND_COUNT 0
if grep -Fq 'rev-list' "$err" || grep -Fq 'BEHIND_COUNT=0' "$err"; then
    ok "bad ref emits diagnostic"
else
    fail "bad ref should emit stderr diagnostic"
fi

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
