### OOS_1: [OUT_OF_SCOPE] risk-integration: branch-1-resume lacks dirty-tree checkpoint
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Branch-1-resume still calls `_perform_tracking_side_effects` without the new dirty-tree checkpoint. On resume with a dirty working tree, tracking side effects (rename, run-log init) can run before `_phase_plan`'s later dirty bail. Share the dirty-tree probe across branch-1-resume and branch-2-adopt, or document resume dirty-tree expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


