### OOS_1: [OUT_OF_SCOPE] Planned operator docs updates are still missing
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-statusline-security
- **Severity**: minor
- **Concern**: The planned docs work for installation, configuration, and workflow surfaces is still absent; this is documentation debt rather than a behavioral issue in the new statusline path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update installation, configuration, and workflow docs per the plan.
  - From dyn-dyn-statusline-security: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Legacy current-implement-env pointer writing remains
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The current-implement-env pointer writer still exists even though live-discovery retirement was the stated consumer; stale pointers may accumulate without affecting the new file-based statusline path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Complete the MAY_UPDATE consumer audit and remove the pointer writer if unused.
  - From cursor-specialist-correctness: Complete the MAY_UPDATE consumer audit and retire the pointer when safe.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Statusline registry scans are still too broad
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Statusline staleness detection still scans the full bgjob registry on each refresh, which can make large clones slower than the target budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Cache or scope registry lookups per clone if profiling shows regressions.
  - From cursor-specialist-correctness: Cache liveness per clone or scope the registry scan.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Statusline reader still lacks a symlink ancestor guard
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The progress-log reader still follows symlinked ancestors, which is a containment gap but not part of the active statusline design path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Apply assert_no_symlink_path_or_ancestors and nofollow open before tailing.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_5: [OUT_OF_SCOPE] Tier-2 breadcrumbs remain coarse in some plan surfaces
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-statusline-security
- **Severity**: minor
- **Concern**: Some tier-2 breadcrumbs still stay at a coarse round-start or generic phase level relative to the plan’s reviewer and CI granularity; this is a visibility gap, not a security defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add curated notes at CI-fix dispatch with round number and job names.
  - From dyn-dyn-statusline-security: Address the concern above.


Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

### OOS_6: [OUT_OF_SCOPE] Live-discovery retirement residue remains
- **Reviewer(s)**: dyn-dyn-statusline-security
- **Severity**: minor
- **Concern**: The old live-discovery and mid-run _report machinery still ship even though the progress-report CLI entry point is gone; this is retirement residue, not an active exploit path in the new statusline design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-statusline-security: Address the concern above.
Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

