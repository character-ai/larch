### OOS_1: [OUT_OF_SCOPE] OOS heading detection is brittle to leading BOM/whitespace
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_is_oos_issue_body` only matches `## Out-of-Scope Observation` at byte zero, so a leading UTF-8 BOM, blank line, or leading spaces in a hand-assembled `oos-body-*.txt` can skip auto-prefixing and leave the original bug reachable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: If this resurfaces in production, normalize by stripping BOM and leading whitespace, then match the first non-empty line against the heading.
  - From cursor-specialist-edge-cases: Strip optional BOM and leading whitespace, then match the first non-empty line against the OOS heading; add a dry-run regression for a leading newline.

### OOS_2: [OUT_OF_SCOPE] OOS heading literal is duplicated across writers and detectors
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The OOS heading literal is duplicated across `issue_create`, `oos_filer`, and `SKILL.md`, so a template edit in one place can desync auto-prefix detection from bodies that still look like OOS issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Centralize the heading in one shared constant or helper imported by all writers and detectors.
