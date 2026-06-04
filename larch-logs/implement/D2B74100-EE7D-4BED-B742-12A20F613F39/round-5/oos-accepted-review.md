### FINDING_11: [OUT_OF_SCOPE] Plan wording vs postplan invalid-repo short-circuit before pause-save delegation
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: PLAN_FINDING_2 describes delegating repo handling to `design-pause-save.sh` on internal pause, but invalid resolved repo fails inside postplan with `PAUSE_OK=false` and never execs pause-save. Debugging shows postplan invalid-repo output rather than pause-save invalid-repo. Behavior may match intent but diverges from plan delegation wording; document the short-circuit in `design-postplan-emit.md` or exec pause-save for one canonical invalid-repo path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


