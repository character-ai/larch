### OOS_1: [OUT_OF_SCOPE] stale route-state REPO can leak into fresh Step 0b
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-resume-env
- **Severity**: minor
- **Concern**: Route-state gap-fill can seed REPO on non-resume Step 0b entries, so a reused tmpdir can pair a new issue with an old repo and send later `gh issue view` / `design route` calls to the wrong remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Limit route-state REPO gap-fill to paused-resume recovery, or always invoke resolve_repo() when env still lacks REPO after gap-fill unless route is resume@.
  - From cursor-specialist-edge-cases: Restrict gap-fill to resume@ intent or clear stale route-state on fresh Step 0a setup.
  - From dyn-dyn-resume-env: Address the concern above.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=true
