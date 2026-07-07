### OOS_1: [OUT_OF_SCOPE] state tracking still uses `.bg-wait-active`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Stall recovery still keys off `.bg-wait-active` instead of the bgjob registry, so abandoned checks stay misclassified until state code is migrated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Migrate _tokens.py per plan in a follow-up change


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] launch sites still teach `run_in_background`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The current `SKILL.md` still instructs operators to use `run_in_background`, so the migration away from that workflow is incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Finish wrapper/skill migration per plan


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] deny hook does not verify registry liveness
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Stale registry rows can keep blocking `run_in_background` because the deny hook does not check liveness before denying.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Teach hook to call bgjob status/liveness or reap before deny
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

