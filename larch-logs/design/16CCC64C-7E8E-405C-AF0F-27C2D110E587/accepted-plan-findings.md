### FINDING_3: Plan gap — fence-harness file omitted from design-reachable surfaces for external coders
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Issue mitigation #1 requires `/design` plans that add `skills/implement/SKILL.md` Bash fences to list `scripts/test-implement-fence-shape.sh` in Files to modify/create. The plan only adds an implement-biased note to `.claude/rules/skill-editing-trace.md`. External implementers do not receive `.claude/rules` injections, so `EXPECTED_NEW` was never incremented and `test-implement-fence-shape` failed at ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend the `skill-editing-trace.md` update to explicitly require `/design` Step 2b plans that add/remove/convert implement `SKILL.md` Bash fences to include `### UPDATED: scripts/test-implement-fence-shape.sh` with `EXPECTED_OLD`/`EXPECTED_NEW` increment guidance (or add the same one-line requirement to a design-reachable surface such as `skills/design/references/readability-style.md` plan-drafting section).


