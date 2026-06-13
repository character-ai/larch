### OOS_1: [OUT_OF_SCOPE] Cursor same-path scout normalization untested in Step 2 harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Scout normalization harness coverage is Codex-only (`LAUNCH_SCOUT_MANIFEST_PATH` differs from `SCOUT_CODER_MANIFEST`). The Cursor same-path case (`input == output`) is documented in the plan but not covered at the dispatcher level. Test 13a exercises only the Codex path; a wrapper regression on input==output paths would not be caught while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a cursor-stub variant that writes the sidecar to `$TMPDIR/scout-coder-manifest.json` and asserts normalized filtering plus `no_wrapper_stdout_lines`.
  - From cursor-specialist-testing-output.txt: Add a Cursor stub test that writes the sidecar to $TMPDIR/scout-coder-manifest.json and asserts filtered output at the same path.


