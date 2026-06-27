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
  agents/_implementer-base.md
  agents/codex-implementer.md
  agents/cursor-implementer.md
  python/combine_issues.py
  python/ci_agentic_fix.py
  python/larch/implement/ci_agentic_fix.py
  python/larch/implement/preflight.py
  python/test_combine_issues.py
  python/test_deps_audit.py
  SECURITY.md
  docs/linting.md
  docs/skills.md
  python/larch/state/admission.py
  python/preflight.py
  python/issue_wire.py
  python/larch/issue/tracking_issue.py
  python/test_admission.py
  python/test_ci_agentic_fix.py
  scripts/test-legacy-title-prefix-literals-scope.sh
  python/test_issue_wire.py
  python/test_tracking_issue.py
  skills/deps/SKILL.md
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
done < <(git grep -l -E '\[(IN PROGRESS|PLANNED)\]' -- ':!larch-logs/' ':!larch-logs/' 2>/dev/null || true)

echo "PASS: legacy title-prefix literal scope"
exit 0
