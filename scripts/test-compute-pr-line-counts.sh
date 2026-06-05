#!/usr/bin/env bash
# test-compute-pr-line-counts.sh — offline harness for compute-pr-line-counts.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/compute-pr-line-counts.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-compute-pr-line-counts.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    FAIL=$((FAIL + 1))
}

pass() {
    printf 'PASS: %s\n' "$1"
    PASS=$((PASS + 1))
}

read_kv() {
    local key=$1 text=$2
    printf '%s\n' "$text" | awk -F= -v k="$key" '$1==k{print $2; exit}'
}

[ -x "$HELPER" ] || fail 'compute-pr-line-counts.sh is executable'

mkdir -p "$TMP/bin"
GH_LOG="$TMP/gh.log"
: >"$GH_LOG"
export GH_SHIM_LOG="$GH_LOG"

cat > "$TMP/bin/gh" <<'SHIM'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"${GH_SHIM_LOG:?}"
if [ "${GH_SHIM_FAIL:-false}" = true ]; then
    exit 1
fi
case "$*" in
    *pulls/*/files*)
        printf '%s\t%s\t%s\n' 'scripts/foo.sh' 10 2
        printf '%s\t%s\t%s\n' 'larch-logs/implement/run-x/summary.md' 5 1
        printf '%s\t%s\t%s\n' 'assets/binary.png' 0 0
        printf '%s\t%s\t%s\n' 'scripts/renamed.sh' 4 0
        printf '%s\t%s\t%s\n' 'docs/user guide.md' 3 1
        ;;
esac
exit 0
SHIM
chmod +x "$TMP/bin/gh"
export PATH="$TMP/bin:$PATH"

out=$("$HELPER" --repo 'owner/repo' --pr-number 42)
[ "$(read_kv LINES_STATUS "$out")" = ok ] || fail "bucketing LINES_STATUS (got: $out)"
[ "$(read_kv CODE_ADDED "$out")" = 17 ] || fail "CODE_ADDED sum (expected 17, got $(read_kv CODE_ADDED "$out"))"
[ "$(read_kv CODE_DELETED "$out")" = 3 ] || fail "CODE_DELETED sum (expected 3)"
[ "$(read_kv LOGS_ADDED "$out")" = 5 ] || fail "LOGS_ADDED sum (expected 5)"
[ "$(read_kv LOGS_DELETED "$out")" = 1 ] || fail "LOGS_DELETED sum (expected 1)"
pass 'bucketing and sums including space filename'

out_skip=$("$HELPER" --repo 'owner/repo' --pr-number 0)
[ "$(read_kv LINES_STATUS "$out_skip")" = skipped ] || fail 'no-pr skip status'
[ "$(read_kv REASON "$out_skip")" = no-pr ] || fail 'no-pr skip reason'
pass 'no-pr skip path'

out_empty=$("$HELPER" --repo 'owner/repo' --pr-number '')
[ "$(read_kv LINES_STATUS "$out_empty")" = skipped ] || fail 'empty pr skip status'
pass 'empty pr-number skip path'

GH_SHIM_FAIL=true
export GH_SHIM_FAIL
out_fail=$("$HELPER" --repo 'owner/repo' --pr-number 9)
GH_SHIM_FAIL=false
export GH_SHIM_FAIL
[ "$(read_kv LINES_STATUS "$out_fail")" = unavailable ] || fail 'gh-failed status'
[ "$(read_kv REASON "$out_fail")" = gh-failed ] || fail 'gh-failed reason'
pass 'gh-failed unavailable path'

GH_SHIM_FAIL=false
: >"$GH_LOG"
"$HELPER" --repo '' --pr-number 7 >/dev/null
if command grep -Fq 'repos/{owner}/{repo}/pulls/7/files' "$GH_LOG" 2>/dev/null; then
    pass 'empty --repo uses placeholder endpoint'
else
    fail "empty --repo endpoint shape (log: $(cat "$GH_LOG"))"
fi

# Inline-triage rule 2: validate --paginate is passed in the gh api call (FINDING_18)
: >"$GH_LOG"
"$HELPER" --repo 'owner/repo' --pr-number 55 >/dev/null
if command grep -Fq -- '--paginate' "$GH_LOG" 2>/dev/null; then
    pass 'gh api --paginate flag used'
else
    fail "gh api --paginate flag missing (log: $(cat "$GH_LOG"))"
fi

# Inline-triage rule 2: non-numeric PR number is treated as no-pr (FINDING_7)
out_nonnumeric=$("$HELPER" --repo 'owner/repo' --pr-number 'abc')
[ "$(read_kv LINES_STATUS "$out_nonnumeric")" = skipped ] || fail 'non-numeric pr-number skip status'
[ "$(read_kv REASON "$out_nonnumeric")" = no-pr ] || fail 'non-numeric pr-number skip reason'
pass 'non-numeric pr-number skip path'

# Inline-triage rule 2: invalid REPO format (extra slash) is rejected (FINDING_7)
out_badrepo=$("$HELPER" --repo 'owner/repo/extra' --pr-number 1)
[ "$(read_kv LINES_STATUS "$out_badrepo")" = skipped ] || fail 'extra-slash repo skip status'
pass 'extra-slash repo skip path'

[ "$FAIL" -eq 0 ] || exit 1
printf 'PASS=%s\n' "$PASS"
