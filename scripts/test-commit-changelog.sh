#!/usr/bin/env bash
# test-commit-changelog.sh — Offline harness for commit-changelog.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/commit-changelog.sh"

PASS=0
FAIL=0
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

ok() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $*" >&2; FAIL=$((FAIL + 1)); }

setup_repo() {
    local repo=$1
    mkdir -p "$repo"
    cd "$repo"
    git init -q
    git config user.email test@test.com
    git config user.name Test
    cat > CHANGELOG.md <<'CHANGELOG'
# Changelog

## [Unreleased]

## [1.2.2] - 2026-01-01

### Fixed

- Old fix.
CHANGELOG
    echo "base" > README.md
    git add -A
    git commit -q -m "Initial commit"
}

run_subject() {
    bash "$SUBJECT" "$@"
}

# Test 1: happy path commits only CHANGELOG.md with exact subject.
repo="$TMPDIR_BASE/test1"
setup_repo "$repo"
printf '\n- New fix.\n' >> "$repo/CHANGELOG.md"
out=$(cd "$repo" && run_subject --version 1.2.3)
if printf '%s\n' "$out" | grep -q '^COMMITTED=true$' &&
    printf '%s\n' "$out" | grep -q '^COMMIT_SHA=[0-9a-f]\{7,40\}$' &&
    [ "$(git -C "$repo" log -1 --format=%s)" = "Update CHANGELOG for 1.2.3" ] &&
    [ "$(git -C "$repo" diff-tree --no-commit-id --name-only -r HEAD)" = "CHANGELOG.md" ]; then
    ok
else
    fail "happy path did not create expected CHANGELOG-only commit: $out"
fi

# Test 2: no CHANGELOG change is an expected no-op.
repo="$TMPDIR_BASE/test2"
setup_repo "$repo"
out=$(cd "$repo" && run_subject --version 1.2.3)
if printf '%s\n' "$out" | grep -q '^COMMITTED=false$' &&
    [ "$(git -C "$repo" log --oneline | wc -l | tr -d ' ')" = "1" ]; then
    ok
else
    fail "no-change path should be COMMITTED=false: $out"
fi

# Test 3: invalid version fails.
repo="$TMPDIR_BASE/test3"
setup_repo "$repo"
set +e
out=$(cd "$repo" && run_subject --version nope)
rc=$?
set -e
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -q '^COMMITTED=false$'; then ok; else fail "invalid version should fail"; fi

# Test 4: missing CHANGELOG.md fails.
repo="$TMPDIR_BASE/test4"
setup_repo "$repo"
rm "$repo/CHANGELOG.md"
set +e
out=$(cd "$repo" && run_subject --version 1.2.3)
rc=$?
set -e
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -q 'ERROR=CHANGELOG.md not found'; then ok; else fail "missing changelog should fail"; fi

# Test 5: dirty tracked non-CHANGELOG file fails.
repo="$TMPDIR_BASE/test5"
setup_repo "$repo"
printf 'dirty\n' >> "$repo/README.md"
set +e
out=$(cd "$repo" && run_subject --version 1.2.3)
rc=$?
set -e
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -q 'ERROR=tracked file dirty outside CHANGELOG.md'; then ok; else fail "dirty non-changelog should fail"; fi

# Test 6: untracked files do not block.
repo="$TMPDIR_BASE/test6"
setup_repo "$repo"
printf '\n- New fix.\n' >> "$repo/CHANGELOG.md"
echo pending > "$repo/untracked.txt"
out=$(cd "$repo" && run_subject --version 1.2.3)
if printf '%s\n' "$out" | grep -q '^COMMITTED=true$'; then ok; else fail "untracked file blocked commit: $out"; fi

# Test 7: --replaces-version retitles stale entry and removes the old heading.
repo="$TMPDIR_BASE/test7"
setup_repo "$repo"
out=$(cd "$repo" && run_subject --version 1.2.3 --replaces-version 1.2.2)
if printf '%s\n' "$out" | grep -q '^COMMITTED=true$' &&
    grep -q '^## \[1.2.3\] - ' "$repo/CHANGELOG.md" &&
    ! grep -q '^## \[1.2.2\] - ' "$repo/CHANGELOG.md" &&
    grep -q 'Old fix.' "$repo/CHANGELOG.md"; then
    ok
else
    fail "replaces-version did not retitle stale entry: $out"
fi

# Test 8: --replaces-version missing old heading inserts a fresh section.
repo="$TMPDIR_BASE/test8"
setup_repo "$repo"
cat > "$repo/CHANGELOG.md" <<'CHANGELOG'
# Changelog

## [Unreleased]

## [1.2.1] - 2025-12-31

### Fixed

- Older fix.
CHANGELOG
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m "Resolve changelog conflict"
out=$(cd "$repo" && run_subject --version 1.2.3 --replaces-version 9.9.9)
if printf '%s\n' "$out" | grep -q '^COMMITTED=true$' &&
    grep -q '^## \[1.2.3\] - ' "$repo/CHANGELOG.md" &&
    ! grep -q '^## \[9.9.9\] - ' "$repo/CHANGELOG.md"; then
    ok
else
    fail "missing replaces-version heading should insert a fresh section: $out"
fi

# Test 9: duplicate target headings fail closed.
repo="$TMPDIR_BASE/test9"
setup_repo "$repo"
cat >> "$repo/CHANGELOG.md" <<'CHANGELOG'

## [1.2.3] - 2026-01-02

### Added

- Duplicate heading.
CHANGELOG
git -C "$repo" add CHANGELOG.md
git -C "$repo" commit -q -m "Add duplicate changelog heading"
set +e
out=$(cd "$repo" && run_subject --version 1.2.3)
rc=$?
set -e
if [ "$rc" -eq 1 ] && printf '%s\n' "$out" | grep -q 'ERROR=multiple existing'; then
    ok
else
    fail "duplicate target headings should fail closed: $out"
fi

total=$((PASS + FAIL))
echo "test-commit-changelog: $PASS/$total passed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
