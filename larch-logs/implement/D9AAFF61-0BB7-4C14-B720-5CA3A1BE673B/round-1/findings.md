### FINDING_1: [OUT_OF_SCOPE] Grep substring count pins do not verify bootstrap argument propagation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-assertion-logic-output.txt, dyn-doc-accuracy-output.txt
- **Severity**: important
- **Concern**: The new `scripts/test-implement-structure.sh` count checks use `grep -oF` on `_ib_*[@]` substrings with a threshold of 2. Because the `${arr[@]+"${arr[@]}"}` idiom contains each token twice on one wrapper line, these checks can pass without proving that both initial and resume bootstrap paths thread arguments correctly. The assertions also diverge from the plan’s `grep -cF` full-literal intent and make the failure messages misleading.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-test-assertion-logic-output.txt: Address the concern above.
  - From dyn-doc-accuracy-output.txt: Address the concern above.

### FINDING_2: Structure pins do not verify dirty-tree checkpoint ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The current prose-only pins can still pass if `run_dirty_tree_checkpoint` moves below branch creation in `phase_plan_materialize`, which would reintroduce duplicate branch or metadata behavior before runtime tests catch it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Dirty-tree prompt-side sentinel and re-probe orchestration remain untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-test-assertion-logic-output.txt
- **Severity**: latent
- **Concern**: The branch does not add coverage for the full prompt-side dirty-tree orchestration path, including sentinel handling, AskUserQuestion gating, or re-probe routing. These gaps predate the change or were out of scope, but regressions there would not be caught by the new structure pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-test-assertion-logic-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Resume-tail does not assert duplicate tracking metadata is skipped
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no assertion that resume-tail skips duplicate tracking metadata operations. A regression removing the `phase_tracking` `RESUME_PLAN_TAIL` short-circuit might not be caught by the new pins or B7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Branch name derivation remains a pre-existing trust and hardening concern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `phase_plan_materialize` still derives `branch_name_derived` from the GitHub issue title and passes it to `create-branch.sh`. Slugification limits characters but is not a complete injection-hardening story. This is unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Resume-tail identity trusts session-local tmpdir state
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--resume-plan-tail` trusts `$IMPLEMENT_TMPDIR/parent-issue.md` plus `--issue-number` matching. A party able to write that tmpdir could influence resume identity. This trust model predates the change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Append-tool-failure path is documented as non-idempotent
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The audit notes that `append-tool-failure.sh` appends on failure paths and is not independently idempotent if re-entered. The reviewer treats this as accurate future-work documentation, not a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Documentation anchors may drift from live source lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-doc-accuracy-output.txt
- **Severity**: nit
- **Concern**: Some `scripts/implement-bootstrap.md` line anchors are stale or imprecise relative to `scripts/implement-bootstrap.sh`, which can send maintainers to the wrong code while auditing idempotency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-doc-accuracy-output.txt: Address the concern above.

### FINDING_9: Phase plan materialize resume-tail documentation mixes first-pass and resume ranges
- **Reviewer(s)**: dyn-doc-accuracy-output.txt
- **Severity**: important
- **Concern**: The `phase_plan_materialize` audit heading describes lines `~750–911` as resume-tail re-entry scope, but resume skips the earlier first-pass block and actually runs the post-checkpoint tail through the emitter. This makes the scope easy to misread as code executed on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-accuracy-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Resume-tail skips issue-state recheck
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The resume-tail sentinel fast path skips `get-issue-state` recheck. If the issue closes after the first pass but before resume, the resume path may proceed with stale OPEN assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Plan line references for structure-test thresholds are stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan references `_ib_preflight` count-at-least-2 lines, while the live harness uses a threshold of at least 1. Future implementers may copy the wrong threshold or line anchor from the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Prose pin is acceptable despite not being a standalone sentence
- **Reviewer(s)**: dyn-test-assertion-logic-output.txt
- **Severity**: nit
- **Concern**: The pinned substring `the first pass bails at this checkpoint` appears inside a longer sentence rather than as a standalone sentence. The reviewer notes the pin still matches and is acceptable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-assertion-logic-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Committed run-log artifacts add unrelated PR noise
- **Reviewer(s)**: dyn-test-assertion-logic-output.txt, dyn-doc-accuracy-output.txt
- **Severity**: nit
- **Concern**: The branch includes committed `larch-logs/implement/...` run artifacts unrelated to the idempotency documentation and structure pins under review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-assertion-logic-output.txt: Address the concern above.
  - From dyn-doc-accuracy-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Phase tracking cross-reference is accurate
- **Reviewer(s)**: dyn-doc-accuracy-output.txt
- **Severity**: nit
- **Concern**: The `phase_tracking` cross-reference matches the live source range and correctly states that resume-tail returns before rename, log init, or tracking issue posting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-accuracy-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Commit list observations are not review findings
- **Reviewer(s)**: dyn-doc-accuracy-output.txt
- **Severity**: nit
- **Concern**: The reviewer listed commits present since merge-base, including the idempotency documentation commit and the run-log flush commit. These are contextual observations rather than behavioral defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-accuracy-output.txt: Address the concern above.
