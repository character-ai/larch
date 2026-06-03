#!/usr/bin/env bash
# Regression harness for gather-context.sh.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)
SCRIPT="$REPO_ROOT/skills/review/scripts/gather-context.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/test-gather-context.XXXXXX")

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

# Build a minimal fixture git repo (~10 files) so git ls-files enumerates a
# tiny set instead of the real 67k-file repo. The production script runs git
# ls-files relative to the current directory; cd-ing into the fixture keeps
# the harness fast (<1s) while still exercising the real matching logic.
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/test-gather-context-fixture.XXXXXX")
trap 'rm -rf "$TMP" "$FIXTURE"' EXIT

mkdir -p "$FIXTURE/skills/review/scripts" "$FIXTURE/docs"
touch "$FIXTURE/skills/review/SKILL.md"
touch "$FIXTURE/skills/review/scripts/gather-context.sh"
touch "$FIXTURE/docs/review-agents.md"
touch "$FIXTURE/README.md"
touch "$FIXTURE/README.md"
git -C "$FIXTURE" init --quiet
git -C "$FIXTURE" -c user.name=test -c user.email=test@test.com add .
git -C "$FIXTURE" -c user.name=test -c user.email=test@test.com commit --quiet -m "fixture"

out=$(cd "$FIXTURE" && CLAUDE_PLUGIN_ROOT="$REPO_ROOT" "$SCRIPT" --mode description --description-text "review skill" --output-dir "$TMP")
assert_stdout_cap "$out"
grep -Fq 'MODE=description' <<< "$out"
scope=$(printf '%s\n' "$out" | awk -F= '$1=="FILE_LIST_FILE"{print $2}')
scope=$(printf '%b' "${scope//\\x/\\x}")
[[ -s "$scope" ]] || { echo "FAIL: description produced empty scope" >&2; exit 1; }
grep -Fq 'skills/review/SKILL.md' "$scope" || { echo "FAIL: expected review skill in scope" >&2; exit 1; }

echo "All assertions passed."
