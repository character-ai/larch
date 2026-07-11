### [Plan Review] FINDING_1

### FINDING_1: Preserve literal bracket escaping for canonical `[BUG]` headings
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The Tier B raw-heading grep plan does not require bracket escaping for the new canonical token. Scenario: An implementer may extend the existing `grep -Eq` alternation with an unescaped `[BUG]` token; in ERE that is a character class matching one of B/U/G, not the literal prefix, so `### [BUG] /implement …` raw slices can stop matching and Tier B dedup comments may accept leaked full report bodies
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit contract line under `### UPDATED: scripts/file-failure-report-cross-repo.sh` to keep literal bracket escaping (for example `^### \[(BUG|Bug)\] /(implement|design)` or separate `\ [BUG\]` and `\ [Bug\]` branches) and extend `scripts/test-file-failure-report-cross-repo.sh` with a canonical `[BUG]` raw-heading rejection case for `/implement` alongside the existing legacy `/design` case


