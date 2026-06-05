### [Plan Review] FINDING_3

### FINDING_3: Step 5c publish fence can bypass pause handling
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The Step 5c publish fence still sources environment without an immediate canonical pause check, and the pause audit may miss its indented fence form. A pause after Step 5b could be ignored before publish-side effects occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Insert the design-pause-save.sh pause-check immediately after the source-env line in the indented Step 5c publish fence, before set +e; extend the new optional-whitespace fence extractor or pause audit to assert this fence is pause-bearing


