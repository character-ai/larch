### OOS_1: [OUT_OF_SCOPE] Broader validator default repo-root ambiguity
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-agent-dispatch-output.txt
- **Severity**: nit
- **Concern**: `validate-plan.sh`’s default `REPO_ROOT` behavior is broader than the auto-fix change and may affect all plan-command validation, not only the new revalidation path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-agent-dispatch-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Assessor/Revert handoff coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: Revert is covered at helper level, but the Step 3.6 WORSE → Revert orchestration handoff is not tested end-to-end for plan rollback and cursor/count state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-design-flow-output.txt, dyn-state-persistence-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Auto-fix offline coverage excludes live launcher/root/cycle behavior
- **Reviewer(s)**: dyn-agent-dispatch-output.txt
- **Severity**: latent
- **Concern**: Offline auto-fix tests do not cover live Codex/Cursor launcher exit parsing, repo-root parity with caller sites, or orchestrator cycle limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-agent-dispatch-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Run-params re-init can overwrite stored router flags
- **Reviewer(s)**: dyn-state-persistence-output.txt
- **Severity**: latent
- **Concern**: The broader run-params merge behavior can overwrite stored true router flags on re-init when argv flags are false; this predates `--approve` but now also affects it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-persistence-output.txt: Address the concern above.


