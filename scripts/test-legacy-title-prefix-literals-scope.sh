#!/usr/bin/env bash
# Regression: legacy bracket tokens [IN PROGRESS] / [PLANNED] must not sprawl
# beyond deliberate migration/admission/fixture surfaces. A naive repo-wide
# "zero git grep hits" check false-fails on the correct implementation; this
# harness scopes the audit to an explicit allow-list of paths.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$REPO_ROOT"

ALLOW=(
  agents/_implementer-base.md
  skills/implement/prompts/codex-implementer.md
  skills/implement/prompts/cursor-implementer.md
  python/test_deps_audit.py
  SECURITY.md
  docs/linting.md
  docs/skills.md
  crates/larch-core/src/admission.rs
  crates/larch-core/src/issue/deps_audit.rs
  crates/larch-core/src/issue/title.rs
  crates/larch-core/tests/issue_wire.rs
  crates/larch-cli/src/admission_commands.rs
  crates/larch-cli/src/combine_issues_commands.rs
  python/preflight.py
  python/issue_wire.py
  python/larch/issue/title_match.py
  python/larch/issue/tracking_issue.py
  scripts/test-legacy-title-prefix-literals-scope.sh
  python/test_issue_wire.py
  python/tests/issue/test_tracking_issue.py
  python/tests/issue/test_title_match.py
  skills/combine-issues/SKILL.md
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
done < <(git grep -l -E '\[(IN PROGRESS|PLANNED)\]' -- ':!larch-logs/' ':!plugin/' 2>/dev/null || true)

echo "PASS: legacy title-prefix literal scope"
exit 0
