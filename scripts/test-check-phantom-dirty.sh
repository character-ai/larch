#!/usr/bin/env bash
# Offline regression harness for scripts/check-phantom-dirty.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SUT="$REPO_ROOT/scripts/check-phantom-dirty.sh"
SNAPSHOT="$REPO_ROOT/scripts/snapshot-untracked.sh"
REAL_GIT="$(command -v git)"
TMPROOT="$(mktemp -d /tmp/larch-test-phantom-dirty-XXXXXX)"
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

repo_clean=$(new_repo clean)
baseline_clean="$TMPROOT/clean.baseline"
write_baseline "$repo_clean" "$baseline_clean"
run_sut "$repo_clean" "$TMPROOT/clean.out" --baseline "$baseline_clean" --step clean --phantom-paths-dir "$TMPROOT/phantoms"
assert_contains "clean status" "STATUS=clean" "$TMPROOT/clean.out"

repo_phantom=$(new_repo phantom)
baseline_phantom="$TMPROOT/phantom.baseline"
write_baseline "$repo_phantom" "$baseline_phantom"
printf 'new\n' > "$repo_phantom/new.txt"
run_sut "$repo_phantom" "$TMPROOT/phantom.out" --baseline "$baseline_phantom" --step 2-post-dispatch --phantom-paths-dir "$TMPROOT/phantoms"
assert_contains "phantom status" "STATUS=phantom" "$TMPROOT/phantom.out"
assert_contains "phantom count" "PHANTOM_COUNT=1" "$TMPROOT/phantom.out"
PHANTOM_FILE=$(awk -F= '$1=="PHANTOM_PATHS_FILE"{print $2}' "$TMPROOT/phantom.out")
assert_file_has_nul_path "phantom path copied" "$PHANTOM_FILE" "new.txt"

repo_unknown=$(new_repo unknown)
printf 'new\n' > "$repo_unknown/new.txt"
run_sut "$repo_unknown" "$TMPROOT/unknown.out" --baseline "$TMPROOT/missing.baseline" --step missing-baseline --phantom-paths-dir "$TMPROOT/phantoms"
assert_contains "missing baseline unknown" "STATUS=unknown" "$TMPROOT/unknown.out"
assert_contains "missing baseline reason" "REASON=baseline-missing-untracked-ambiguous" "$TMPROOT/unknown.out"
assert_not_contains "missing baseline not phantom" "STATUS=phantom" "$TMPROOT/unknown.out"

repo_tracked=$(new_repo tracked)
baseline_tracked="$TMPROOT/tracked.baseline"
write_baseline "$repo_tracked" "$baseline_tracked"
printf 'change\n' >> "$repo_tracked/tracked.txt"
run_sut "$repo_tracked" "$TMPROOT/tracked.out" --baseline "$baseline_tracked" --step tracked --phantom-paths-dir "$TMPROOT/phantoms"
assert_contains "tracked-only status" "STATUS=tracked-only" "$TMPROOT/tracked.out"
assert_not_contains "tracked-only no phantom file" "PHANTOM_PATHS_FILE=" "$TMPROOT/tracked.out"

repo_empty=$(new_repo empty)
baseline_empty="$TMPROOT/empty.baseline"
: > "$baseline_empty"
printf 'new\n' > "$repo_empty/after-empty.txt"
run_sut "$repo_empty" "$TMPROOT/empty.out" --baseline "$baseline_empty" --step empty --phantom-paths-dir "$TMPROOT/phantoms"
assert_contains "empty baseline phantom" "STATUS=phantom" "$TMPROOT/empty.out"
assert_contains "empty baseline count" "PHANTOM_COUNT=1" "$TMPROOT/empty.out"

repo_space=$(new_repo space)
baseline_space="$TMPROOT/space.baseline"
write_baseline "$repo_space" "$baseline_space"
mkdir -p "$repo_space/dir"
printf 'new\n' > "$repo_space/dir/name - dash.txt"
run_sut "$repo_space" "$TMPROOT/space.out" --baseline "$baseline_space" --step space.dash --phantom-paths-dir "$TMPROOT/phantoms"
SPACE_FILE=$(awk -F= '$1=="PHANTOM_PATHS_FILE"{print $2}' "$TMPROOT/space.out")
assert_contains "space path phantom" "STATUS=phantom" "$TMPROOT/space.out"
assert_file_has_nul_path "space path preserved" "$SPACE_FILE" "dir/name - dash.txt"

stub_dir="$TMPROOT/stub-bin"
mkdir -p "$stub_dir"
cat > "$stub_dir/git" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "ls-files" ]]; then
    exit 42
fi
exec "${REAL_GIT:?REAL_GIT required}" "$@"
STUB
chmod +x "$stub_dir/git"

repo_capture=$(new_repo capture)
baseline_capture="$TMPROOT/capture.baseline"
(cd "$repo_capture" && PATH="$stub_dir:$PATH" REAL_GIT="$REAL_GIT" "$SNAPSHOT" --output "$baseline_capture" --nul)
printf 'new\n' > "$repo_capture/capture-new.txt"
run_sut "$repo_capture" "$TMPROOT/capture.out" --baseline "$baseline_capture" --step capture --phantom-paths-dir "$TMPROOT/phantoms"
assert_contains "failed capture unknown" "STATUS=unknown" "$TMPROOT/capture.out"
assert_not_contains "failed capture not phantom" "STATUS=phantom" "$TMPROOT/capture.out"

repo_bad_step=$(new_repo bad-step)
baseline_bad="$TMPROOT/bad-step.baseline"
write_baseline "$repo_bad_step" "$baseline_bad"
for bad_step in "../x" "/" $'line\nbreak' "a=1"; do
    out="$TMPROOT/bad-step-${PASS}.out"
    run_sut "$repo_bad_step" "$out" --baseline "$baseline_bad" --step "$bad_step" --phantom-paths-dir "$TMPROOT/phantoms"
    assert_contains "bad step status $bad_step" "STATUS=unknown" "$out"
    assert_contains "bad step reason $bad_step" "REASON=bad-step" "$out"
done

if (( FAIL > 0 )); then
    printf 'FAIL: test-check-phantom-dirty.sh - %s failed, %s passed\n' "$FAIL" "$PASS" >&2
    printf '  %s\n' "${FAILURES[@]}" >&2
    exit 1
fi

printf 'PASS: test-check-phantom-dirty.sh - %s assertions passed\n' "$PASS"
