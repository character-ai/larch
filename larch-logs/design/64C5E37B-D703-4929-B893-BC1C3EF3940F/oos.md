### OOS_1: [SCOPE-REDUCTION] Approach still scopes `step8_oos_checkpoint_main` stderr replay changes
- **Description**: [SCOPE-REDUCTION] Approach still scopes `step8_oos_checkpoint_main` stderr replay changes. Scenario: Approach line 22 instructs mirroring stderr-only replay in `step8_oos_checkpoint_main`, a separate post-driver `python/cli.py implement step-8-oos-checkpoint` surface. Collapsing the three pre-driver fences into `ship pre-driver` does not require changing that helper; doing so alters unrelated CLI stdout behavior outside the acceptance surface.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:22
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

