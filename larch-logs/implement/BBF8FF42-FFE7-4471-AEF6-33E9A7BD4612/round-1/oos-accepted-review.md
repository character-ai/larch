### OOS_1: [OUT_OF_SCOPE] Resume path skips implement pointer refresh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-portability-output.txt, dyn-pointer-lifecycle-output.txt, dyn-ci-inprogress-block-output.txt
- **Severity**: latent
- **Concern**: `resume_existing_tmpdir` reuses an existing `IMPLEMENT_TMPDIR` without writing or refreshing `current-implement-env-$LARCH_CLAUDE_PID.sh`, so resumed runs in a new Claude process may have no discoverable progress pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-bash-portability-output.txt, dyn-pointer-lifecycle-output.txt, dyn-ci-inprogress-block-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Progress hook timeout can silence long reports
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-ci-inprogress-block-output.txt
- **Severity**: important
- **Concern**: The UserPromptSubmit hook has a 10s timeout while progress rendering can spend up to 8s in the Step 5 detail subprocess plus filesystem walks and shim overhead; on large runs the hook can be killed and fail open with no progress output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-ci-inprogress-block-output.txt: Address the concern above.


