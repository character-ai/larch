### FINDING_5: Documentation still exposes retired public --approve spelling
- **Reviewer(s)**: Cursor-dyn-token-sweep
- **Severity**: important
- **Concern**: The plan covers skip-approve forwarding but misses the design-init-runparams documentation row that still names public `--approve`, leaving a stale public flag reference after the intended hard rename to `--per-round-approval`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-token-sweep: In the design-init-runparams.md UPDATED block add an explicit bullet: rename the argv-table note on line 18 from Public `--approve` to Public `--per-round-approval` (keep `--approve-requested` internal CLI name unchanged)

