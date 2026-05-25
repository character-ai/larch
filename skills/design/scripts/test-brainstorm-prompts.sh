#!/usr/bin/env bash
# Offline harness: brainstorm prompt tokens stay byte-stable (mirrors test-plan-review-prompt.sh scope).

set -euo pipefail

export LARCH_QUIET_DISABLE=1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

BP="$ROOT/skills/design/references/brainstorm-prompts.md"
BM="$ROOT/skills/design/references/brainstorm.md"

[[ -f "$BP" ]] || fail "missing $BP"
[[ -f "$BM" ]] || fail "missing $BM"

for needle in '<BRAINSTORM_FRAMING_PROMPT>' '<BRAINSTORM_SCOPE_PROMPT>' '<BRAINSTORM_PRAGMATIC_PROMPT>'; do
    grep -Fq -- "$needle" "$BP" || fail "brainstorm-prompts.md missing token $needle"
    grep -Fq -- "$needle" "$BM" || fail "brainstorm.md must reference token $needle"
done

grep -Fq 'MANDATORY — READ ENTIRE FILE' "$BM" || fail "brainstorm.md missing MANDATORY directive"
grep -Fq 'skills/design/references/brainstorm-prompts.md' "$BM" \
    || fail "brainstorm.md missing path literal skills/design/references/brainstorm-prompts.md"

echo "test-brainstorm-prompts: ok"
