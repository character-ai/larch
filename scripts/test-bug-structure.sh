#!/bin/bash
# Structural regression test for skills/bug/SKILL.md.
# Pins the prompt-side /bug --urgent parsing contract and the forced
# /issue --title-prefix invocation for default and urgent bug reports.
#
# Asserts:
#  (A) Frontmatter argument-hint documents [--urgent].
#  (B) Contract documents --urgent as the only flag.
#  (C) The old no-flags prose is absent.
#  (D) The skill removes leading --urgent tokens before validation.
#  (E) Step 5 invokes /issue with --title-prefix.
#  (F) Both [BUG] and [BUG] (URGENT) prefixes are present.
#  (G) The skill still says not to pass --no-dedup.
#
# Exit 0 on pass, exit 1 on any assertion failure.
# shellcheck disable=SC2016
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/bug/SKILL.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/bug/SKILL.md missing: $SKILL_MD"

grep -Fq 'argument-hint: "[--urgent] <bug description>"' "$SKILL_MD" \
  || fail "(A) frontmatter argument-hint must include [--urgent]"

grep -Fq '`--urgent` is the only flag.' "$SKILL_MD" \
  || fail "(B) contract must document --urgent as the only flag"

if grep -Fq 'This skill has no flags' "$SKILL_MD"; then
  fail "(C) old no-flags contract prose is still present"
fi

grep -Fq 'Remove one or more leading `--urgent` tokens from the description before validation.' "$SKILL_MD" \
  || fail "(D) contract must strip leading --urgent before validation"

grep -Fq -- '--title-prefix' "$SKILL_MD" \
  || fail "(E) Step 5 invocation must pass --title-prefix"

grep -Fq '[BUG]' "$SKILL_MD" \
  || fail "(F.1) default [BUG] prefix literal missing"

grep -Fq '[BUG] (URGENT)' "$SKILL_MD" \
  || fail "(F.2) urgent [BUG] (URGENT) prefix literal missing"

grep -Fq 'Do not include `--no-dedup`.' "$SKILL_MD" \
  || fail "(G) skill must still say not to pass --no-dedup"

echo "test-bug-structure.sh: all assertions passed"
