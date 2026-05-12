#!/usr/bin/env bash
# Structural regression test for /implement SKILL.md + larch-log migration.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
REFS_DIR="$REPO_ROOT/skills/implement/references"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -d "$REFS_DIR" ]] || fail "skills/implement/references missing"

for heading in "## Load-Bearing Invariants" "## NEVER List" "## Rebase Checkpoint Macro"; do
  count="$(grep -c "^$heading$" "$SKILL_MD" || true)"
  [[ "$count" == "1" ]] || fail "expected exactly one $heading heading, found $count"
done

for ref in summary-comment-template.md bump-verification.md codex-manifest-schema.md conflict-resolution.md pr-body-template.md rebase-rebump-subprocedure.md; do
  [[ -f "$REFS_DIR/$ref" ]] || fail "missing reference: $ref"
done

grep -Fq 'scripts/larch-log.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/larch-log.sh"
grep -Fq 'scripts/tracking-issue-summary.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/tracking-issue-summary.sh"
grep -Fq 'summary-comment-template.md' "$SKILL_MD" \
  || fail "SKILL.md must reference summary-comment-template.md"

old_surfaces=(anchor-section-markers.sh assemble-anchor.sh hydrate-anchor.sh refresh-anchor.sh upsert-anchor find-anchor ANCHOR_COMMENT_ID "\$IMPLEMENT_TMPDIR/anchor-sections")
for old in "${old_surfaces[@]}"; do
  if grep -Fq "$old" "$SKILL_MD"; then
    fail "SKILL.md still references removed anchor surface: $old"
  fi
done

grep -Fq 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" \
  || fail "focus-area enum missing"
grep 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" | grep -q 'security' \
  || fail "focus-area enum line must include security"

grep -Fq '### Larch-log batches' "$SKILL_MD" \
  || fail "SKILL.md must contain the Larch-log batches section heading"
grep -q 'Skip.*Normal mode.*post.*design.*sections' "$SKILL_MD" \
  || fail "quick mode must explicitly skip Normal mode before the Larch-log batches tail"

echo "All assertions passed."
