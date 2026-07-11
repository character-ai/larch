### FINDING_1: Preserve literal bracket escaping for canonical `[BUG]` headings
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The Tier B raw-heading grep plan does not require bracket escaping for the new canonical token. Scenario: An implementer may extend the existing `grep -Eq` alternation with an unescaped `[BUG]` token; in ERE that is a character class matching one of B/U/G, not the literal prefix, so `### [BUG] /implement …` raw slices can stop matching and Tier B dedup comments may accept leaked full report bodies
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit contract line under `### UPDATED: scripts/file-failure-report-cross-repo.sh` to keep literal bracket escaping (for example `^### \[(BUG|Bug)\] /(implement|design)` or separate `\ [BUG\]` and `\ [Bug\]` branches) and extend `scripts/test-file-failure-report-cross-repo.sh` with a canonical `[BUG]` raw-heading rejection case for `/implement` alongside the existing legacy `/design` case

### FINDING_2: Align the stall-report title contract with the canonical `[BUG]` prefix
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: minor
- **Concern**: The plan leaves the canonical stall-report title contract using mixed-case `[Bug]`. Generated reports use `[BUG]` while the shipped contract still documents `[Bug]`, leaving the runtime surface and its documented format inconsistent and allowing future implementations to reintroduce the wrong prefix. Users and maintainers following the canonical stall-recovery report contract can therefore continue producing or validating `[Bug]` titles, contradicting the requirement that generated bug titles use the one canonical `[BUG]` prefix
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the terminal and escalation title examples to `[BUG]` and include this contract file in the focused verification or production-prefix check
  - From Codex-Requirements: Update both terminal and escalation title examples to use [BUG]; document [Bug] only as legacy input if that compatibility note is needed
