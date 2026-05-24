### OOS_4: Add scout-archetype-yield.tsv to round_artifact_included allowlist (pre-existing gap)
- **Description**: `scripts/larch-log.sh round_artifact_included` (~lines 67-101) doesn't list `scout-archetype-yield.tsv` in its allowlist; the `*.tsv` exclusion suppresses it. This predates the L6 PR but is the same mechanism L6 relies on for `findings-classification.tsv`. Worth tracking as a separate issue if round dirs should also carry yield bytes.
- **Reviewer**: Codex-Pragmatic

