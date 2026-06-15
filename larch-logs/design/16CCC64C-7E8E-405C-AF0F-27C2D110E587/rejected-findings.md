### [Plan Review] FINDING_1

### FINDING_1: Planned py-lint rule conflicts with external-implementer validation contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `.claude/rules/python-test-monkeypatch-lambdas.md` rule would tell implementers to run `make py-lint` after editing tests. External implementers (`agents/codex-implementer.md`, `agents/cursor-implementer.md`) are forbidden from running `scripts/relevant-checks.sh` or any larch skill; orchestrator-owned validation runs later. A path-triggered rule instructing them to run `make py-lint` conflicts with that contract and may cause wasted work, policy confusion, or ignored guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rephrase the rule to state that pyright strict mode is enforced by orchestrator/CI (`make py-lint`) and require the suppression at write time; do not instruct external coders to run `make py-lint` themselves.


### [Plan Review] FINDING_2

### FINDING_2: Planned fence-harness note directs implementers to run orchestrator-owned validation
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned fence-harness note in `.claude/rules/skill-editing-trace.md` would tell implementers to run `make test-implement-fence-shape`. Under the same external-implementer contract, validation is orchestrator-owned. Naming `make test-implement-fence-shape` as an implementer action duplicates the py-lint conflict pattern and may be skipped or fought.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Say CI/orchestrator runs `make test-implement-fence-shape`; implementers must update `EXPECTED_OLD` and `EXPECTED_NEW` in `scripts/test-implement-fence-shape.sh` when fence count changes, without directing them to run the target.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/skill-editing-trace.md:2
- **Concern**: [SCOPE-REDUCTION] Implement fence-harness note is planned inside skill-editing-trace, whose paths glob all skills/**/SKILL.md. Scenario: The new EXPECTED_OLD/EXPECTED_NEW reminder will inject on design/review/research SKILL edits where it does not apply, diluting a cross-skill trace rule and missing the tighter implement-only trigger the bug needs
- **Proposed resolution**: Create a dedicated rule (for example implement-fence-shape-harness.md) with paths scoped to skills/implement/SKILL.md and scripts/test-implement-fence-shape.sh instead of extending skill-editing-trace.md

