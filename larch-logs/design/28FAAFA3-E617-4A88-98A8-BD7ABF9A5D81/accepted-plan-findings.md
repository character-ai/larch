### FINDING_3: Scope extraction can terminate before valid headings and fenced examples
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The planned scope extraction may apply a generic level-two section terminator before the shared fence-aware firm-heading iterator recognizes valid `## NEW: path` headings. Heading-like text inside fences may also terminate the section prematurely, causing dispatch and dirty-tree scope checks to miss valid paths accepted by the shared grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Define section-bound precedence around the shared fence-aware iterator: recognize valid firm headings before generic section termination, and ignore all headings while inside fences. Add fixtures combining level-two headings, fenced heading-like text, and later scope entries.


