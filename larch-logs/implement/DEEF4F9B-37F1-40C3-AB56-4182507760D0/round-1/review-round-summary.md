# Review Round 1

- Mode: `diff`
- 8 accepted, 10 rejected (8 exonerated)

## Accepted Findings

### FINDING_19: Collaborative sketch docs do not identify the Step 2a entry fence as the SIMPLE write site
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `docs/collaborative-sketches.md` still describes SIMPLE sentinel writes without naming the Step 2a entry fence as the sole write site, conflicting with updated normative surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_20: run-step3-review contract doc omits cap-reached boundary-qualified routing
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/run-step3-review.md` does not document the updated cap-reached stdout breadcrumb or its Step 3b completion boundary → Step 4 → Gate C routing chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_21: Pause/resume harness contract markdown omits new legacy fixtures
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-design-pause-resume.md` was not updated to document the new legacy compatibility fixture expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_22: SIMPLE anti-pattern text does not locate sentinel writes in the entry fence
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` anti-pattern guidance still says to write the SIMPLE sentinel without clarifying that sentinel and marker writes occur only in the Step 2a entry fence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-sync-output.txt: Address the concern above.


### FINDING_24: AWK `IGNORECASE` use is not portable to BSD awk
- **Reviewer(s)**: dyn-bash-fences-output.txt
- **Severity**: latent
- **Concern**: `assert_no_direct_step3b_step4_routes` relies on `IGNORECASE`, a gawk extension ignored by BSD awk, making the routing-verb catch case-sensitive on macOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-fences-output.txt: Address the concern above.


### FINDING_4: Pause/resume fixtures do not execute compatibility guards
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-resume-legacy-output.txt
- **Severity**: important
- **Concern**: Legacy pause/resume tests verify STEP routing but not execution of the Step 4 FINALIZE guard or Step 2a.5 marker/artifact repair, so guard removal or broken runtime recovery could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-resume-legacy-output.txt: Address the concern above.


### FINDING_5: FINALIZE failure warning text is not pinned
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structure tests assert non-zero FINALIZE failure but not the operator-visible repair warning, so the breadcrumb required by FM6 could disappear while CI remains green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Step 2a.5 SIMPLE skip can bypass the compatibility fence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 2a.5 SIMPLE skip prose appears before the resume-compatibility fence, allowing an orchestrator to proceed directly to Step 2b without writing `.completed/step-2a.5` for legacy SIMPLE resumes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


