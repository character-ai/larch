### FINDING_2: [OUT_OF_SCOPE] stale route-state REPO can seed the wrong remote on init
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `step0_init_main` unconditionally merges route-state keys including `REPO` without the `ISSUE_NUMBER`-only gap-fill guard. A reused tmpdir with stale route-state `REPO` could still seed the wrong remote on the init-only Step 0 entry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Apply the same ISSUE_NUMBER-only gap-fill policy to step0_init_main or skip route-state REPO merge when ISSUE_NUMBER is already bound


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] resume path no longer backfills REPO from route state
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `ISSUE_NUMBER`-present sessions no longer gap-fill `REPO` from route state, so `resolve_repo()` becomes the sole `REPO` backfill. If pause/resume leaves `ISSUE_NUMBER` in session without `REPO` and the canonical repo exists only in route state, `gh issue view` may target `resolve_repo()` instead of the paused repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document the trade-off or gap-fill REPO from route state only on resume@ routes when ISSUE_NUMBER is already set
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

