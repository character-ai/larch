### OOS_1: [OUT_OF_SCOPE] `issue-input-file` trusts upstream body redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `cmd_issue_input_file` composes the issue input from a caller-provided body file without a second redaction pass, so secrecy depends on callers always passing the `bug-body` output. This was described as pre-existing/out of scope but also raised as a residual security concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional defense-in-depth: run the composed file through `redact-secrets.sh` before write, or fail closed if `body-file` is not under the expected `stall-recovery-bug-body.md` path.


### OOS_2: [OUT_OF_SCOPE] Generic `/issue --input-file` body splitting footgun
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Generic batch parsing treats in-body `### <title>` lines as new item boundaries. Stall-recovery first-detection bodies avoid that shape today, but untrusted body content remains a general `/issue --input-file` risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Out of scope for #3568; tracked separately (#3550 / #3547 family).


### OOS_3: [OUT_OF_SCOPE] Unsafe-step regression test does not catch alnum-only prefix acceptance
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-issue-flow-output.txt
- **Severity**: important
- **Concern**: The `STALL_STEP=8a<script>` fixture would not catch a regression back to the old loose prefix glob, because the old and new logic both reject that non-alnum suffix. An alnum-only invalid suffix such as `8aevil` is needed to prove suffix rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add an 8aevil assert expecting unknown in the issue title line.
  - From cursor-specialist-edge-cases-output.txt: Add an alnum-only fixture such as STALL_STEP=8aevil that old glob accepts and new regex rejects; assert title uses unknown and excludes the suffix
  - From dyn-issue-flow-output.txt: an alnum-only invalid suffix such as `8aevil` would be a stronger regression pin.


