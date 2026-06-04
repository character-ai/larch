### FINDING_10: Malformed repo tests are too narrow
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The malformed `--repo` test only covers `/abs`, so weaker validation could still accept other invalid shapes such as `bad..repo` or `a/b/c`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Internal pause checkpoint lacks invalid source-env repo coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no regression test proving an invalid `REPO` from `source-env` fails before internal pause-save execution during Step 2b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Clarify rename gate references a nonexistent sub-step
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The rename gate references sub-step 3.3, which does not exist, risking mis-ordering of rename versus publish normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: Step 0b fetches issue before resolving explicit repo
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: important
- **Concern**: Step 0b calls `gh issue view "$ISSUE_NUMBER"` before resolving and validating `REPO`, so it can read an issue from the hub default while later mutations target a different explicit repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.


### FINDING_3: Clarify publish fail-closed contract is prompt/grep-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-summary-contracts-output.txt
- **Severity**: important
- **Concern**: Clarify publish normalization, failed-publish branching, and ordering before rename are enforced mainly by SKILL.md prose and structural greps, not runnable behavior, so the orchestrator can regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_4: Run-log synthesis and outcome documentation are incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: The run-summary path has split guard authority and stale outcome documentation; direct `render-run-summary.sh` callers can still synthesize run-log paths for `publish-skipped`, while docs omit newer `publish-skipped` and `failed-publish` contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_7: Clarify failed-publish summary loses recovery metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-publish-flow-output.txt, dyn-summary-contracts-output.txt
- **Severity**: important
- **Concern**: Step 0b clarify parses `DESIGN_LOG_*` recovery metadata, but the final summary runs in a separate shell without exporting those variables, so failed-publish summaries can omit log flush PR and recovery branch bullets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-publish-flow-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.


### FINDING_9: Step 5c failed-publish sentinel behavior lacks behavioral coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Withholding `.completed/step-5c` on failed publish is only prompt/grep enforced, so an orchestrator regression could mark Step 5c complete after `PUBLISH_OK=false` and cause resume to skip publish retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


