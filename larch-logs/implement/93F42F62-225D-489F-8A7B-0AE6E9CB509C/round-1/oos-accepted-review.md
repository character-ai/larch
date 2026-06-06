### FINDING_11: [OUT_OF_SCOPE] Unrecoverable pause markers can force repeated resume attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Invalid or unrecoverable pause markers are retained on failure, so later `/design` runs may repeatedly attempt the same doomed resume with no fresh-start escape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add route-level bypass or explicit operator gate for unrecoverable marker errors (not in this PR).


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] `done` resume returns OK without terminal artifact verification
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: latent
- **Concern**: `resume.start == "done"` exits successfully without rerunning post-merge or verifying terminal artifacts, so corrupt persisted done state could mask incomplete finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] Python merge-loop cap is one iteration looser than CI/bash cap
- **Reviewer(s)**: dyn-resume-state-output.txt, dyn-ci-loop-output.txt
- **Severity**: latent
- **Concern**: Python ship uses `iteration > MAX` while CI decision logic and Bash semantics use `>= MAX`, allowing one extra outer-loop pass in some resume/wait cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.
  - From dyn-ci-loop-output.txt: Align the merge-loop cap with `decide()` / bash by using `iteration >= config.SHIP_MERGE_LOOP_MAX_ITERATIONS`, or document and test that the outer cap is intentionally one step looser than the inner cap.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_18: [OUT_OF_SCOPE] Boolean state parsing is duplicated
- **Reviewer(s)**: dyn-resume-state-output.txt
- **Severity**: nit
- **Concern**: Boolean parsing logic is duplicated between run-log and ship state paths, creating drift risk over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-resume-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


