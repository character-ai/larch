#!/usr/bin/env bash
# Editorial invariant: plan-adequacy audit block in /implement SKILL (issue #2485).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL="$REPO_ROOT/skills/implement/SKILL.md"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$SKILL" ]] || fail "missing SKILL.md"

grep -Fq '<reviewer_issue_title>' "$SKILL" || fail "missing XML reviewer_issue_title wrap"
grep -Fq '<reviewer_issue_body>' "$SKILL" || fail "missing XML reviewer_issue_body wrap"
grep -Fq '<reviewer_plan>' "$SKILL" || fail "missing XML reviewer_plan wrap"
grep -Fq '**Fixed rubric**' "$SKILL" || fail "missing fixed rubric heading"
grep -Fq 'AUDIT=pass' "$SKILL" || fail "missing AUDIT=pass envelope"
grep -Fq 'AUDIT=refuse' "$SKILL" || fail "missing AUDIT=refuse envelope"
grep -Fq '## Concrete questions for /design' "$SKILL" || fail "missing concrete questions heading"
grep -Fq '**Few-shot A — pass**' "$SKILL" || fail "missing few-shot pass example"
grep -Fq '**Few-shot B — refuse**' "$SKILL" || fail "missing few-shot refuse example"
grep -Fq '**⚠ --emergency and --draft are mutually exclusive. Aborting.**' "$SKILL" || fail "missing emergency/draft mutex"
grep -Fq 'issue #<N> has no larch:plan block AND the issue body is empty' "$SKILL" || fail "missing empty-body emergency abort"
grep -Fq 'STATE=awaiting-response' "$SKILL" || fail "missing clarify awaiting-response guard"
grep -Fq 'BYPASS kind=<lowercase-token> issue=<number>' "$SKILL" || fail "missing structured emergency bypass log grammar"

echo "PASS: test-plan-adequacy-audit.sh"
