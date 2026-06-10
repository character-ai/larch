### OOS_3: [OUT_OF_SCOPE] Progress hook can exceed timeout and fail open
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt, dyn-schema-compat-output.txt
- **Severity**: important
- **Concern**: The `UserPromptSubmit` progress hook timeout is 10s while the matched report path can spend up to 8s in Step 5 detail rendering, plus Python/jq overhead, and can also walk the entire implement tmpdir. Large runs may cause the hook to be killed or fail open, so typing `p` passes through or shows no progress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-risk-integration-output.txt: Address the concern above.
  - From dyn-schema-compat-output.txt: Address the concern above.


