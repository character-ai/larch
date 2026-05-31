### FINDING_10: MAV apply head relocation lacks dedicated test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `run_implement_mav_apply` has no dedicated test proving it writes the relocated `pre-coder-head.txt`; a regression could write back to `round_dir` and keep `structural_loc=0` for MAV resume paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Missing Step 5 structural_loc coverage for relocated pre-coder head
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: No test asserts that `review-implement-step5-loop.sh` reads `pre-coder-head.txt` from the relocated snapshot directory when computing `structural_loc`. A regression could leave `structural_loc=0`, causing substantial-round or bulk-skip gates to misfire without current tests failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


