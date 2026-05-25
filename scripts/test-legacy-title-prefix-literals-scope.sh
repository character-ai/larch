#!/usr/bin/env bash
# Regression: legacy bracket tokens [IN PROGRESS] / [PLANNED] must not sprawl
# beyond deliberate migration/admission/fixture surfaces. A naive repo-wide
# "zero git grep hits" check false-fails on the correct implementation; this
# harness scopes the audit to an explicit allow-list of paths.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$REPO_ROOT"

ALLOW=(
  .claude/skills/combine-issues/SKILL.md
  .claude/skills/combine-issues/scripts/combinable-issues-title-filter.jq
  .claude/skills/combine-issues/scripts/fetch-combinable-issues.sh
  SECURITY.md
  docs/linting.md
  scripts/implement-admission.md
  scripts/implement-admission.sh
  scripts/lib-title-markers.sh
  scripts/test-fetch-combinable-issues-filter.sh
  scripts/test-implement-admission.sh
  scripts/test-legacy-title-prefix-literals-scope.sh
  scripts/test-lib-title-eligibility.sh
  scripts/test-tracking-issue-write.sh
  scripts/tracking-issue-write.md
  scripts/tracking-issue-write.sh
)

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  ok=false
  for a in "${ALLOW[@]}"; do
    if [[ "$file" == "$a" ]]; then
      ok=true
      break
    fi
  done
  if [[ "$ok" != true ]]; then
    git grep -n -E '\[(IN PROGRESS|PLANNED)\]' -- "$file" >&2 || true
    fail "legacy prefix literal in unexpected path: $file (extend ALLOW= only when deliberate)"
  fi
done < <(git grep -l -E '\[(IN PROGRESS|PLANNED)\]' -- ':!CHANGELOG.md' ':!larch-logs/' 2>/dev/null || true)

echo "PASS: legacy title-prefix literal scope"
exit 0
