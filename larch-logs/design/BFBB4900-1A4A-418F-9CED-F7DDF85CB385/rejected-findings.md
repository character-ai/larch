### [Plan Review] FINDING_4

### FINDING_4: G-Sec-3 still points at the deleted gh-body-file rule
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The G-Sec-3 deviate note still names the deleted `gh-body-file` rule, so the guideline-level pointer for inline `gh --body` usage disappears when the rule is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "Replace the deviate bullet with lint gh-body-inline as the mechanical backstop and BASH_AUTHORING.md for authoring guidance; do not leave G-Sec-3 silent on inline gh bodies."


### [Plan Review] FINDING_5

### FINDING_5: markdownlint MD038 guidance is dropped without a replacement note
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The `markdown-no-space-in-code-span` migration is planned as delete-only, but the retired rule's content is supposed to be rerouted to the mechanism doc. Without a replacement note, MD038-specific author guidance goes missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: "Add a concise MD038/no-inner-whitespace note to the markdownlint row or nearby docs/linting.md text, without copying the whole old rule"


