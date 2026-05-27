### FINDING_1: [OUT_OF_SCOPE] Duplicate zero-findings success tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Duplicate zero-findings success harness cases exercise the same stub/assertion shape across multiple blocks, increasing maintenance drift risk. One source marks the duplication as optional/out-of-scope, but the same duplication was raised in-scope by other reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Missing nospace pseudo-heading plus attestation regression
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan edge case for `###FINDING_1:` plus empty-merge attestation is not covered by a dedicated harness case, so a regression could incorrectly accept the nospace pseudo-heading as `REASON=ok` instead of `validation-exhausted`. One source tagged this as out-of-scope/plan-fidelity, but the same coverage gap was raised in-scope by other reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] All-OOS attestation-only path lacks integration coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: All-OOS input with attestation-only aggregate success is not covered end to end. The behavior spans empty in-scope ballots, preserved OOS output, possible voter dispatch, and `oos_only_slots` handling, so future changes could break this shape silently. Some reviewers framed this as out-of-scope or optional integration coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Attestation-only aggregate success lacks review-core coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `review-core` lacks an integration test for `REASON=ok` with `MERGED_COUNT=0`, so wrapper-level regressions could still exit incorrectly or skip/mis-order voters even while aggregate unit tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Missing execution-issues assertion for nonconforming heading with attestation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `nonconforming_heading_with_attestation` case does not assert the expected `execution-issues.md` warning, so the new warning branch could break without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Ok-path attestation tests do not assert absence of warnings
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Successful attestation paths do not check that `execution-issues.md` remains free of false-positive warnings, leaving ok-path warning regressions uncaught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] review-and-fix wrapper lacks continue-after-ok coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `review-and-fix` tests cover exhaustion paths but not the new continue-after-aggregate-ok empty-ballot path, leaving Step 5 wrapper behavior under-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Attestation-only success can wipe a nonempty ballot
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A static empty-merge attestation token can cause validation to succeed and replace a nonempty pre-merge ballot with whitespace-only `findings.md`, allowing review to proceed with zero in-scope findings. The behavior is documented, but reviewers recommend operator-visible signaling or secondary checks for `INPUT_COUNT>0` and `MERGED_COUNT=0` if stronger integrity is needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Zero-block success must keep whitespace-only persistence guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Zero-block success intentionally persists whitespace-only `findings.md`, preventing accepted narrative text from leaking into voter prompts or ballot artifacts. Reviewer indicates no change is needed beyond retaining the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Cache mtime refresh behavior is bounded
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Cache mtime refresh only touches version-shaped basenames under `CLAUDE_PLUGIN_ROOT`; a mis-set root is effectively bounded to no-op or wrong-version mtime bump. Reviewer marks this as already bounded and documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Nonconforming marker precedence is undocumented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: When output contains both attestation and nonconforming pseudo-finding markers, validation still exhausts but reports `nonconforming_heading_with_attestation` rather than `preamble_finding_substring`. If intentional, the precedence should be documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Empty attested ballots still launch voters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `REASON=ok` with an empty ballot still dispatches voters, incurring token cost for zero findings. Reviewer frames this as non-functional and optional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Branch contains out-of-plan work
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch-vs-main diff includes substantial work outside the #2939 file list; reviewers should focus feature-scope review on the relevant commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
