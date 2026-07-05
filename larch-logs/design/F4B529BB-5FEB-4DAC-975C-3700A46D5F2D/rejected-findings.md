### [Plan Review] FINDING_4

### FINDING_4: Free-prose rescue needs explicit matching keys
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Free-prose rescue can mis-target items unless the merit list shows stable display keys and oos-4 defines a clear matching order; otherwise ambiguous requests can keep or reject the wrong items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In oos-4, require rescue matching against the displayed stable key and issue number, default to keep on ambiguity, and never treat an unmatched rescue as batch approval
  - From Cursor-Innovation: In oos-4, define rescue matching: accept issue number plus item title, the staged stable display key, or an unambiguous title substring; on ambiguous or no match, keep the item and ask once for clarification. Require the Rejected items (merit) list to show the same key on every line.
  - From Cursor-Requirements: Add to the Files section: each `Rejected items (merit):` line must prefix the stable display key and issue number (for example `A (#123)`), and oos-4 prose must define rescue matching priority (display key, then `#N`, then unique title substring) before any grouping or close steps run.


