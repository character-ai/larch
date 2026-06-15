### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/rules/python-test-monkeypatch-lambdas.md (planned)
- **Concern**: Planned rule tells implementers to run make py-lint after editing tests. Scenario: agents/codex-implementer.md and agents/cursor-implementer.md forbid external implementers from running scripts/relevant-checks.sh or any larch skill; orchestrator-owned validation runs later. A path-triggered rule that says run make py-lint conflicts with that contract and may cause wasted work, policy confusion, or ignored guidance.
- **Proposed resolution**: Rephrase the rule to state that pyright strict mode is enforced by orchestrator/CI (make py-lint) and require the suppression at write time; do not instruct external coders to run make py-lint themselves.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/rules/skill-editing-trace.md (planned)
- **Concern**: Planned fence-harness note tells implementers to run make test-implement-fence-shape. Scenario: Same external-implementer contract: validation is orchestrator-owned. Naming make test-implement-fence-shape as an implementer action duplicates the py-lint conflict and may be skipped or fought.
- **Proposed resolution**: Say CI/orchestrator runs make test-implement-fence-shape; implementers must update EXPECTED_OLD and EXPECTED_NEW in scripts/test-implement-fence-shape.sh when fence count changes, without directing them to run the target.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/skill-editing-trace.md:2
- **Concern**: [SCOPE-REDUCTION] Implement fence-harness note is planned inside skill-editing-trace, whose paths glob all skills/**/SKILL.md. Scenario: The new EXPECTED_OLD/EXPECTED_NEW reminder will inject on design/review/research SKILL edits where it does not apply, diluting a cross-skill trace rule and missing the tighter implement-only trigger the bug needs
- **Proposed resolution**: Create a dedicated rule (for example implement-fence-shape-harness.md) with paths scoped to skills/implement/SKILL.md and scripts/test-implement-fence-shape.sh instead of extending skill-editing-trace.md

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:9-15
- **Concern**: Issue mitigation #1 requires /design plans that add implement SKILL.md Bash fences to list scripts/test-implement-fence-shape.sh in Files to modify/create; the plan only adds an implement-biased note to .claude/rules/skill-editing-trace.md. Scenario: The documented failure was Codex implementing from a design plan that listed only skills/implement/SKILL.md; external implementers do not receive .claude/rules injections, so EXPECTED_NEW was never incremented and test-implement-fence-shape failed at ship
- **Proposed resolution**: Extend the skill-editing-trace.md update to explicitly require /design Step 2b plans that add/remove/convert implement SKILL.md Bash fences to include ### UPDATED: scripts/test-implement-fence-shape.sh with EXPECTED_OLD/EXPECTED_NEW increment guidance (or add the same one-line requirement to a design-reachable surface such as skills/design/references/readability-style.md plan-drafting section)
