Verifying the cited locations so we can normalize the three distinct findings accurately.
Three independent correctness findings on different surfaces; no merge candidates. Aggregated output:

### FINDING_1: Route handoff file-first loop drops WARN/ERROR from result env
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The Step 0b route-handoff file-first `while` loop over `.design-route-result.env` allowlists ROUTE/RESUME keys but not WARN/ERROR. When pause-load fallthrough writes failures only into the result env (stdout capture empty), file-only paths never surface pause-load WARN/ERROR because the pre-branch re-emit path also skips them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Mirror Step 3 WARN handling: in the file-first while-loop, add WARN|ERROR) branches that print breadcrumbs (and set vars if re-emit needs them); keep stdout merge filling only missing ROUTE keys

### FINDING_2: Structure Check 20 still pins obsolete Step 0b sub-step 2.5 anchors
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` Check 20 still requires SKILL.md sub-step `2.5. **Title-eligibility filter**` and enforces fetch→2.5→3 line order via awk. After the Step 0b rewrite (title eligibility in `design-route.sh`, renumbered sub-steps), the test can fail even when routing and extraction behavior are correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace Check 20 with greps on design-route.sh plus orchestrator cancel-title-filter-before-clarify ordering (drop or rewrite the 2.5 / filter_line awk)

### FINDING_3: design-route verdict treats end-before-start markers as already-planned
- **Reviewer(s)**: Cursor-dyn-bash32-portability
- **Severity**: important
- **Concern**: The verdict step in `skills/design/scripts/design-route.sh` uses `grep -c -E` for start/end markers and requires exactly one of each, but does not verify `end_line >= start_line`. If the end marker appears above the start marker, both counts are 1 and the driver can emit `ROUTE=already-planned` for a malformed body; `plan-block-read.sh` correctly treats that as absent via `grep -n` and integer line comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-bash32-portability: After count guards for exactly one start and one end, add grep -n -E plus start_line/end_line integer compare matching plan-block-read.sh; treat end before start as absent

---

**Merge notes**: No findings were combined (three distinct code paths and fixes). `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is omitted because structured `### FINDING_N:` blocks are present.

**Scope note**: `design-route.sh` and the route-handoff prose at `skills/design/SKILL.md:276-285` cited by reviewers are not on `main` in this workspace; aggregation is from the supplied reviewer slots only.
