#!/usr/bin/env bash
# Offline regression harness for scripts/check-mid-run-dirty-tree.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUT="$REPO_ROOT/scripts/check-mid-run-dirty-tree.sh"
TMPROOT="$(mktemp -d /tmp/larch-test-mid-run-dirty-tree-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
FAILURES=()
pass() { PASS=$((PASS + 1)); }
fail() { FAIL=$((FAIL + 1)); FAILURES+=("$1"); }

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if grep -Fq -- "$needle" "$haystack"; then pass; else fail "$label: missing $needle in $haystack"; fi
}

assert_not_contains() {
    local label="$1" needle="$2" haystack="$3"
    if grep -Fq -- "$needle" "$haystack"; then fail "$label: unexpected $needle in $haystack"; else pass; fi
}

assert_file_has_nul_path() {
    local label="$1" file="$2" expected="$3"
    if EXPECTED_PATH="$expected" LC_ALL=C perl -0ne 'chomp; if ($_ eq $ENV{EXPECTED_PATH}) { $found = 1 } END { exit($found ? 0 : 1) }' "$file"; then
        pass
    else
        fail "$label: missing NUL path $expected in $file"
    fi
}

new_repo() {
    local dir="$TMPROOT/$1"
    mkdir -p "$dir"
    git -C "$dir" init -q
    git -C "$dir" config user.email test@example.com
    git -C "$dir" config user.name Test
    printf 'base\n' > "$dir/tracked.txt"
    git -C "$dir" add tracked.txt
    git -C "$dir" commit -q -m init
    printf '%s\n' "$dir"
}

write_baseline() {
    local repo="$1" baseline="$2"
    git -C "$repo" ls-files --others --exclude-standard -z | LC_ALL=C sort -z > "$baseline"
}

run_sut() {
    local repo="$1" output="$2"
    shift 2
    (cd "$repo" && "$SUT" "$@") > "$output"
}

repo_a=$(new_repo a)
run_sut "$repo_a" "$TMPROOT/a.out" --mode checkpoint
assert_contains "checkpoint clean status" "STATUS=clean" "$TMPROOT/a.out"
assert_contains "checkpoint clean mode" "MODE=checkpoint" "$TMPROOT/a.out"

repo_b=$(new_repo b)
baseline_b="$TMPROOT/b.baseline"
write_baseline "$repo_b" "$baseline_b"
printf 'change\n' >> "$repo_b/tracked.txt"
run_sut "$repo_b" "$TMPROOT/b.out" --mode baseline --baseline "$baseline_b" --sidecar "$TMPROOT/b.sidecar"
assert_contains "tracked dirty status" "STATUS=dirty" "$TMPROOT/b.out"
TRACKED_B=$(awk -F= '$1=="TRACKED_PATHS_FILE"{print $2}' "$TMPROOT/b.out")
assert_file_has_nul_path "tracked dirty path" "$TRACKED_B" "tracked.txt"

repo_c=$(new_repo c)
baseline_c="$TMPROOT/c.baseline"
write_baseline "$repo_c" "$baseline_c"
printf 'staged\n' >> "$repo_c/tracked.txt"
git -C "$repo_c" add tracked.txt
run_sut "$repo_c" "$TMPROOT/c.out" --mode baseline --baseline "$baseline_c" --sidecar "$TMPROOT/c.sidecar"
TRACKED_C=$(awk -F= '$1=="TRACKED_PATHS_FILE"{print $2}' "$TMPROOT/c.out")
assert_contains "staged dirty status" "STATUS=dirty" "$TMPROOT/c.out"
assert_file_has_nul_path "staged dirty path" "$TRACKED_C" "tracked.txt"

repo_d=$(new_repo d)
baseline_d="$TMPROOT/d.baseline"
write_baseline "$repo_d" "$baseline_d"
printf 'new\n' > "$repo_d/new.txt"
run_sut "$repo_d" "$TMPROOT/d.out" --mode baseline --baseline "$baseline_d" --sidecar "$TMPROOT/d.sidecar"
NEW_D=$(awk -F= '$1=="NEW_UNTRACKED_PATHS_FILE"{print $2}' "$TMPROOT/d.out")
assert_contains "new untracked status" "STATUS=dirty" "$TMPROOT/d.out"
assert_file_has_nul_path "new untracked path" "$NEW_D" "new.txt"

repo_e=$(new_repo e)
printf 'new\n' > "$repo_e/new.txt"
run_sut "$repo_e" "$TMPROOT/e.out" --mode baseline --baseline "$TMPROOT/e.missing" --sidecar "$TMPROOT/e.sidecar"
assert_contains "missing baseline unknown" "STATUS=unknown" "$TMPROOT/e.out"
assert_contains "missing baseline reason" "REASON=baseline-missing-untracked-ambiguous" "$TMPROOT/e.out"
assert_not_contains "missing baseline no new path file" "NEW_UNTRACKED_PATHS_FILE=" "$TMPROOT/e.out"

make_git_stub() {
    local dir="$1" fail_word="$2"
    mkdir -p "$dir"
    cat > "$dir/git" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
case "${LARCH_FAIL_GIT_WORD:-}" in
    status) [[ "${1:-}" == "status" ]] && exit 42 ;;
    diff) [[ "${1:-}" == "diff" && "$*" != *"--cached"* ]] && exit 42 ;;
    diff-cached) [[ "${1:-}" == "diff" && "$*" == *"--cached"* ]] && exit 42 ;;
    ls-files) [[ "${1:-}" == "ls-files" ]] && exit 42 ;;
esac
exec /usr/bin/git "$@"
STUB
    chmod +x "$dir/git"
    printf '%s' "$fail_word" > "$dir/fail-word"
}

STUBDIR="$TMPROOT/stub-bin"
make_git_stub "$STUBDIR" unused

repo_f=$(new_repo f)
set +e
(cd "$repo_f" && PATH="$STUBDIR:$PATH" LARCH_FAIL_GIT_WORD=status "$SUT" --mode checkpoint) > "$TMPROOT/f.out"
set -e
assert_contains "git status failure unknown" "STATUS=unknown" "$TMPROOT/f.out"
assert_contains "git status failure reason" "REASON=git-status-failed" "$TMPROOT/f.out"

repo_g=$(new_repo g)
baseline_g="$TMPROOT/g.baseline"
write_baseline "$repo_g" "$baseline_g"
(cd "$repo_g" && PATH="$STUBDIR:$PATH" LARCH_FAIL_GIT_WORD=diff "$SUT" --mode baseline --baseline "$baseline_g") > "$TMPROOT/g.out"
assert_contains "git diff failure unknown" "STATUS=unknown" "$TMPROOT/g.out"
assert_contains "git diff failure reason" "REASON=git-diff-failed" "$TMPROOT/g.out"

repo_h=$(new_repo h)
baseline_h="$TMPROOT/h.baseline"
write_baseline "$repo_h" "$baseline_h"
(cd "$repo_h" && PATH="$STUBDIR:$PATH" LARCH_FAIL_GIT_WORD=ls-files "$SUT" --mode baseline --baseline "$baseline_h") > "$TMPROOT/h.out"
assert_contains "git ls-files failure unknown" "STATUS=unknown" "$TMPROOT/h.out"
assert_contains "git ls-files failure reason" "REASON=git-ls-files-failed" "$TMPROOT/h.out"

repo_i=$(new_repo i)
printf 'old\n' > "$repo_i/old.txt"
baseline_i="$TMPROOT/i.baseline"
write_baseline "$repo_i" "$baseline_i"
run_sut "$repo_i" "$TMPROOT/i.out" --mode baseline --baseline "$baseline_i"
assert_contains "preexisting untracked clean" "STATUS=clean" "$TMPROOT/i.out"

repo_j=$(new_repo j)
run_sut "$repo_j" "$TMPROOT/j.out" --unknown-flag
assert_contains "bad cli unknown" "STATUS=unknown" "$TMPROOT/j.out"

repo_k=$(new_repo k)
baseline_k="$TMPROOT/k.baseline"
write_baseline "$repo_k" "$baseline_k"
printf 'new\n' > "$repo_k/new.txt"
run_sut "$repo_k" "$TMPROOT/k1.out" --mode baseline --baseline "$baseline_k" --sidecar "$TMPROOT/k.sidecar"
run_sut "$repo_k" "$TMPROOT/k2.out" --mode baseline --baseline "$baseline_k" --sidecar "$TMPROOT/k.sidecar"
if cmp -s "$TMPROOT/k1.out" "$TMPROOT/k2.out"; then pass; else fail "sidecar stdout should be idempotent"; fi

repo_l=$(new_repo l)
baseline_l="$TMPROOT/l.baseline"
write_baseline "$repo_l" "$baseline_l"
newline_name=$'line\nbreak.txt'
printf 'new\n' > "$repo_l/$newline_name"
run_sut "$repo_l" "$TMPROOT/l.out" --mode baseline --baseline "$baseline_l" --sidecar "$TMPROOT/l.sidecar"
NEW_L=$(awk -F= '$1=="NEW_UNTRACKED_PATHS_FILE"{print $2}' "$TMPROOT/l.out")
assert_file_has_nul_path "newline path preserved" "$NEW_L" "$newline_name"

repo_m=$(new_repo m)
baseline_m="$TMPROOT/m.baseline"
write_baseline "$repo_m" "$baseline_m"
printf 'new\n' > "$repo_m/new.txt"
run_sut "$repo_m" "$TMPROOT/m.out" --mode baseline --baseline "$baseline_m" --sidecar "$TMPROOT/m.sidecar"
if [[ -f "$TMPROOT/m.sidecar" && ! -e "$TMPROOT/m.sidecar.tmp.$$" ]]; then pass; else fail "sidecar should be atomically published without leftover current-pid tmp"; fi

if (( FAIL > 0 )); then
    printf 'FAIL: test-check-mid-run-dirty-tree.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-check-mid-run-dirty-tree.sh - %s assertions passed\n' "$PASS"
