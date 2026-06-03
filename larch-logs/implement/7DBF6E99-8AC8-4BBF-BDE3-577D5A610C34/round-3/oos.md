### OOS_1: Assessor harness contract wording around symlink tests is confusing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The harness contract says symlink handoff tests are obsolete, but a symlink-refusal test still runs; the intended distinction is obsolete orchestrator parsing versus still-valid driver refusal coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: `assess-plan-round.sh` classification stream handling duplicates an in-scope risk
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The out-of-scope note also flags merged stdout/stderr plus `tail -n 1` in `resolve_design_classification`, matching the in-scope classification-capture concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_3: Minor assessor doc naming drift
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The doc references `_write_result_and_emit`, but the script uses `_write_result_env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_4: Assessor docs still mention workflow-path and fat-fence behavior
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: important
- **Concern**: Out-of-scope dynamic review noted stale `design-plan-quality-assessor.md` language about invoking on non-HARD `workflow_path` and result-env parsing, duplicating the in-scope stale-contract concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_5: Structure harness lacks planned `assert_thin_fence`
- **Reviewer(s)**: dyn-classification-gate-output.txt, dyn-pause-resume-output.txt
- **Severity**: important
- **Concern**: Out-of-scope dynamic notes also flag that `scripts/test-design-structure.sh` lacks the planned reusable `assert_thin_fence` helper and bypass triple-sentinel pin.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.
  - From dyn-pause-resume-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: Cheap classification gate hides stderr warnings
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: latent
- **Concern**: The Step 3.6 cheap gate redirects `read-design-classification.sh` stderr to `/dev/null`, hiding missing/invalid-classification warnings on the SIMPLE skip path, though fail-closed HARD behavior remains correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_7: Classification fail-closed paths look consistent
- **Reviewer(s)**: dyn-classification-gate-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that implemented classification fail-closed paths align across tests, orchestrator, assessor driver, and child override behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classification-gate-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: Pause-before-gate and rc=11 handoff behavior look aligned
- **Reviewer(s)**: dyn-pause-resume-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed that pause-before-gate, rc=11 handoff, Step 3.6 registry row, and mid-assessor resume behavior align with the thin-fence design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-pause-resume-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

