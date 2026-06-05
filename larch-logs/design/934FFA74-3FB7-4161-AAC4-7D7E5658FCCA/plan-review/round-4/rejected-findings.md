### [Plan Review] FINDING_5

### FINDING_5: Conditional style-block loading is fragile
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A conditional load gate for a short style block forces each `/design` composition site to branch by step type, risking missed loads for user-facing prose or accidental loads for byte-stable work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Always inject the block at the user-facing composition steps named in skills/design/SKILL.md; drop the separate When-to-load rule


