# Review Round 2

- Mode: `diff`
- 4 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_15: Backtick-wrapped security tokens can fail open into public OOS filing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `is_security_block` strips backticks before matching and can miss backtick-wrapped security focus-area/header tokens, allowing security-routed accepted OOS prose to be normalized, preserved, and filed publicly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_4: emit-tally contract docs do not match preserve/rebuild/fail runtime behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: Docs say `OOS_ACCEPTED_COUNT>0` preserves `oos-accepted-review.md`, but implementation also checks sink count and may rebuild from `oos.md` or exit 1. Maintainers reading the contract could reintroduce overwrite/truncation or misunderstand desync handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.


### FINDING_5: oos-serialize contract and harness do not pin Result=accepted filtering or canonical OOS header output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: latent
- **Concern**: Serializer behavior changed to filter `Result=accepted` and rewrite legacy headers to `### OOS_<seq>:`, but tests/docs still under-cover or misdescribe those behaviors, including rejected-block exclusion and scope-drift non-recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.


### FINDING_8: Header-level bare “security” matching falsely withholds non-security accepted OOS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-pipeline-output.txt, dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: New header heuristics treat ordinary titles containing “security” as security-routed, causing legitimate non-security accepted OOS to be withheld from `oos-accepted-review.md` and possibly never filed. The AWK implementation also raises portability inconsistency on macOS/BSD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.
  - From dyn-shell-portability-output.txt: Address the concern above.


