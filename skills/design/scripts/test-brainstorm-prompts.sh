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

# shellcheck disable=SC2016 # literal prompt token line, not shell expansion.
style_line='Style requirements: `<READABILITY_STYLE>`.'
style_count=$(grep -Fxc -- "$style_line" "$BP" || true)
[[ "$style_count" == 3 ]] || fail "brainstorm-prompts.md must contain three exact readability style lines, got $style_count"

for section in '<BRAINSTORM_FRAMING_PROMPT>' '<BRAINSTORM_SCOPE_PROMPT>' '<BRAINSTORM_PRAGMATIC_PROMPT>'; do
    awk -v section="$section" -v style_line="$style_line" '
        $0 ~ "^## `" section "`" { in_section=1; next }
        in_section && /^---$/ { exit }
        in_section && $0 == style_line { found=1 }
        END { exit found ? 0 : 1 }
    ' "$BP" || fail "brainstorm-prompts.md missing readability line in $section"
done

grep -Fq 'MANDATORY: READ ENTIRE FILE' "$BM" || fail "brainstorm.md missing MANDATORY directive"
# shellcheck disable=SC2016 # literal plugin-root token in skill prose, not shell expansion.
grep -Fq '${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md' "$BM" \
    || fail "brainstorm.md missing shared readability path literal"

grep -Fq 'skills/design/references/brainstorm-prompts.md' "$BM" \
    || fail "brainstorm.md missing path literal skills/design/references/brainstorm-prompts.md"

echo "test-brainstorm-prompts: ok"
