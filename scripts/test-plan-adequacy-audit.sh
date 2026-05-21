#!/usr/bin/env bash
# Editorial invariant: plan-adequacy audit block in /implement SKILL (issue #2485).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL="$REPO_ROOT/skills/implement/SKILL.md"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$SKILL" ]] || fail "missing SKILL.md"

grep -Fq '<reviewer_issue_title>' "$SKILL" || fail "missing XML reviewer_issue_title wrap"
grep -Fq '<reviewer_plan>' "$SKILL" || fail "missing XML reviewer_plan wrap"
grep -Fq '**Fixed rubric**' "$SKILL" || fail "missing fixed rubric heading"
grep -Fq 'AUDIT=pass' "$SKILL" || fail "missing AUDIT=pass envelope"
grep -Fq 'AUDIT=refuse' "$SKILL" || fail "missing AUDIT=refuse envelope"
grep -Fq '## Concrete questions for /design' "$SKILL" || fail "missing concrete questions heading"
grep -Fq '**Few-shot A — pass**' "$SKILL" || fail "missing few-shot pass example"
grep -Fq '**Few-shot B — refuse**' "$SKILL" || fail "missing few-shot refuse example"

echo "PASS: test-plan-adequacy-audit.sh"
