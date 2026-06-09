### OOS_7: [OUT_OF_SCOPE] Non-ship-pr call-site cutover to Python CLI is incomplete
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-regression-risk-output.txt
- **Severity**: important
- **Concern**: Live implement/release/bootstrap surfaces still invoke bash helper wrappers while new Python CLI verbs exist. Most reviewers treat this as an unmet migration/cutover requirement; one reviewer marked the interim dual-path state as out of scope rather than a new regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-regression-risk-output.txt: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] Execution-issue warning appends lack outbound redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Warning entries appended by the pre-existing execution-issue path can reach committed execution issues without outbound redaction; the source reviewer marked this as not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] Migration lint live-reference detection misses basename/nonstandard invocations
- **Reviewer(s)**: cursor-specialist-security-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `migration_lint.py` may miss live script references that are invoked by bare basename or non-`SCRIPT_DIR` forms, so deletion gates can incorrectly allow retiring scripts that are still called.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.


