#!/usr/bin/env bash
# Regression harness for gather-branch-context.sh larch-logs pathspec exclusion.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/gather-branch-context.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-gather-branch-context.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

REPO="$TMP/fixture-repo"
mkdir -p "$REPO"
(
    cd "$REPO"
    git init -b main >/dev/null 2>&1
    git config user.email "test@example.com"
    git config user.name "Test User"
    mkdir -p src larch-logs/run
    printf 'v1\n' >src/feature.txt
    git add src/feature.txt
    git commit -m "base code" >/dev/null
    git checkout -b feature >/dev/null 2>&1
    printf 'run-log\n' >larch-logs/run/session.txt
    git add larch-logs/run/session.txt
    git commit -m "add run log" >/dev/null
    printf 'v2\n' >>src/feature.txt
    git add src/feature.txt
    git commit -m "feature change" >/dev/null
)

OUT="$TMP/out"
mkdir -p "$OUT"
(
    cd "$REPO"
    LARCH_QUIET_DISABLE=1 "$SCRIPT" --output-dir "$OUT"
) >"$TMP/stdout.env"

grep -Fq 'DIFF_FILE=' "$TMP/stdout.env" || fail "missing DIFF_FILE kv"
grep -Fq 'FILE_LIST_FILE=' "$TMP/stdout.env" || fail "missing FILE_LIST_FILE kv"
grep -Fq 'src/feature.txt' "$OUT/diff.txt" || fail "diff should include code change"
grep -Fq 'src/feature.txt' "$OUT/file-list.txt" || fail "file-list should include code change"
grep -Fq 'feature change' "$OUT/commit-log.txt" || fail "commit-log should include code commit"
grep -Fq 'add run log' "$OUT/commit-log.txt" && fail "commit-log must exclude larch-logs-only commits"
grep -Fq 'larch-logs/' "$OUT/diff.txt" && fail "diff must exclude larch-logs"
grep -Fq 'larch-logs/' "$OUT/file-list.txt" && fail "file-list must exclude larch-logs"

echo "All assertions passed."
