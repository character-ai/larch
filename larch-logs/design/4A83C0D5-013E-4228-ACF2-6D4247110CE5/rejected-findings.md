### [Plan Review] FINDING_3

### FINDING_3: design-route verdict treats end-before-start markers as already-planned
- **Reviewer(s)**: Cursor-dyn-bash32-portability
- **Severity**: important
- **Concern**: The verdict step in `skills/design/scripts/design-route.sh` uses `grep -c -E` for start/end markers and requires exactly one of each, but does not verify `end_line >= start_line`. If the end marker appears above the start marker, both counts are 1 and the driver can emit `ROUTE=already-planned` for a malformed body; `plan-block-read.sh` correctly treats that as absent via `grep -n` and integer line comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash32-portability: After count guards for exactly one start and one end, add grep -n -E plus start_line/end_line integer compare matching plan-block-read.sh; treat end before start as absent

---

**Merge notes**: No findings were combined (three distinct code paths and fixes). `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is omitted because structured `### FINDING_N:` blocks are present.

**Scope note**: `design-route.sh` and the route-handoff prose at `skills/design/SKILL.md:276-285` cited by reviewers are not on `main` in this workspace; aggregation is from the supplied reviewer slots only.

