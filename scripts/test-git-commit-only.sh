#!/usr/bin/env bash
# test-git-commit-only.sh — Harness for --only pathspec commits.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GIT_COMMIT="$REPO_ROOT/scripts/git-commit.sh"

PASS_COUNT=0
FAIL_COUNT=0
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }

SCRATCH=$(mktemp -d -t git-commit-only-test.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

TEST_REPO="$SCRATCH/repo"
mkdir -p "$TEST_REPO"
git -C "$TEST_REPO" init -q -b main
git -C "$TEST_REPO" config user.email "test@example.com"
git -C "$TEST_REPO" config user.name "Test"
printf 'base\n' > "$TEST_REPO/staged.txt"
printf 'base\n' > "$TEST_REPO/recovered.txt"
git -C "$TEST_REPO" add staged.txt recovered.txt
git -C "$TEST_REPO" commit -q -m "init"

printf 'pre-existing staged\n' > "$TEST_REPO/staged.txt"
git -C "$TEST_REPO" add staged.txt
printf 'recovered change\n' > "$TEST_REPO/recovered.txt"
mkdir -p "$TEST_REPO/dir with space"
printf 'new recovered\n' > "$TEST_REPO/dir with space/new file.txt"

PATHSPEC="$SCRATCH/paths.nul"
printf 'recovered.txt\0dir with space/new file.txt\0' > "$PATHSPEC"

OUT="$SCRATCH/out.txt"
ERR="$SCRATCH/err.txt"
if (cd "$TEST_REPO" && "$GIT_COMMIT" -m "recover exact paths" --only --pathspec-from-file "$PATHSPEC" --pathspec-file-nul >"$OUT" 2>"$ERR"); then
    pass
else
    fail commit "git-commit --only pathspec failed: $(cat "$ERR")"
fi

if git -C "$TEST_REPO" show --name-only --format= HEAD | grep -Fq "dir with space/new file.txt" \
   && git -C "$TEST_REPO" show --name-only --format= HEAD | grep -Fxq "recovered.txt" \
   && ! git -C "$TEST_REPO" show --name-only --format= HEAD | grep -Fxq "staged.txt"; then
    pass
else
    fail paths "commit should include only recovered paths; got: $(git -C "$TEST_REPO" show --name-only --format= HEAD)"
fi

if ! git -C "$TEST_REPO" diff --cached --quiet -- staged.txt; then
    pass
else
    fail staged "pre-existing staged content should remain staged after --only commit"
fi

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-git-commit-only.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
fi
echo "FAIL: test-git-commit-only.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
exit 1
