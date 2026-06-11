### OOS_1: [OUT_OF_SCOPE] Design-route pause integration tests were removed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Removed design-route pause integration coverage raises the risk that pause/resume routing regressions go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Step 3b sanitize pause-save omits repo forwarding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `design-step3b-sanitize.sh` pause-save does not forward `REPO`, so forked-repo pause saves may omit `--repo`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


