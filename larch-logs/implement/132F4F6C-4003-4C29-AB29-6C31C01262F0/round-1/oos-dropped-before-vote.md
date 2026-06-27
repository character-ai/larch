### OOS_1: [OUT_OF_SCOPE] no-stall breadcrumb prints before escalation-filing breakout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Composite prints the no-stall breadcrumb before NEXT_ACTION=escalation-filing. Operators see "no stall detected" on a branch that immediately requires escalation filing work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Print the breadcrumb only on the internal-finalize path, not on escalation-filing breakout.

### OOS_2: [OUT_OF_SCOPE] ship-pr-exit-matrix execution-issues refresh doc drift
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-closeout-oos-output.txt
- **Severity**: nit
- **Concern**: Exit matrix still documents standalone execution-issues refresh orchestrator fence removed from SKILL.md. This branch deleted that fence and folded refresh into the checkpoint, but did not update the exit matrix. Future edits may reintroduce a duplicate fence or confuse when refresh runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Update ship-pr-exit-matrix.md to point at step-8-oos-checkpoint plus any restored terminal refresh site
  - From dyn-dyn-closeout-oos-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] normalize-outcome failure produces no operator-visible signal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: normalize-outcome non-zero returns empty KV map with no failure log. Escalation-success filing is skipped without operator-visible signal when normalize-outcome fails transiently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log normalize-outcome failure to execution-issues.md or emit a diagnostic KV before falling through to finalize

### OOS_4: [OUT_OF_SCOPE] Step 18 tests miss mixed-layer stall and escalation-success branches
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New Step 18 tests miss a mixed-layer active-stall case and the escalation-success sentinel branch. CI will not exercise two new composite branches introduced by the change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add one case that activates a non-memory stall layer while memory is inactive, and one case that sets the escalation-success sentinel with evidence present, so the composite OR gate and filing skip are both exercised

### OOS_5: [OUT_OF_SCOPE] step-18.md documents retired two-call gate/finalize flow
- **Reviewer(s)**: dyn-dyn-step18-routing-output.txt
- **Severity**: nit
- **Concern**: Still documents the retired dominant no-stall flow as `--phase gate` plus `--phase finalize` (two Bash calls). The contract moved to `implement step-18-gate-finalize` plus breakout-only finalize; the file's own "Edit in sync" section was not updated. Doc drift that can mislead harness and wrapper edits, not a runtime regression in the folded Python path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step18-routing-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] refresh_execution_issues seeds incomplete summary metadata
- **Reviewer(s)**: dyn-dyn-closeout-oos-output.txt
- **Severity**: latent
- **Concern**: `refresh_execution_issues()` still seeds `summary-metadata.md` without Agent/Coder/Larch-version when the file is empty (bash `refresh-execution-issues.sh` lines 82-91 include those fields). Not introduced here; still relevant if the folded checkpoint path is the first refresh on a run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-closeout-oos-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] summary-comment-template.md references retired refresh fence
- **Reviewer(s)**: dyn-dyn-closeout-oos-output.txt
- **Severity**: nit
- **Concern**: Still references the retired Step 8+ `execution-issues refresh` fence as a publication surface. Not updated in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-closeout-oos-output.txt: Address the concern above.

