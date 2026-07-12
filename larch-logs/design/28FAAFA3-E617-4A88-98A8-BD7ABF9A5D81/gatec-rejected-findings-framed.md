---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_5

### FINDING_5: Bootstrap retains an independent `diff_lines` parser
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The bootstrap migration only replaces its optional-size regex while leaving a local whole-line `diff_lines` regex and fence-index scan. This creates a second trailer owner and can let bootstrap handle malformed or non-terminal candidates differently from the shared terminal parser.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Route `diff_lines` location and fenced handling through `plan_grammar` while preserving bootstrap’s provenance-stripping policy, then add a bootstrap regression for conflicting/non-terminal `diff_lines` lines.


---LARCH-REJECTED-END---
