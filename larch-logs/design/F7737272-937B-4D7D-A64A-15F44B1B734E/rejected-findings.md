### [Plan Review] FINDING_2

### FINDING_2: Baseline refresh should require canonical regeneration
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan allows manual baseline edits even though CI checks the committed baseline against a byte-exact regenerated output. Partial JSON surgery can appear to satisfy one-way growth checks while still failing the freshness test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace Step 3 manual-update wording with a single required command: make regen-skill-closure-baseline or python3 python/cli.py lint skill-closure-growth --write; treat manual edits as out of scope.
  - From Cursor-Innovation: Replace step 3 with make regen-skill-closure-baseline (or python3 python/cli.py lint skill-closure-growth --write) and drop the manual-update option


