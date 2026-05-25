### FINDING_1: Capture lifecycle title prefix token before branching
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b documents a bare `if title_has_lifecycle_reject_prefix "$ISSUE_TITLE"` even though the predicate writes the matched token to stdout. That can leak raw stdout and leaves the stderr template without the actual token substitution. The prose should capture the token first, branch on whether it is non-empty, and use the captured value in the rejection banner.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Structure test does not pin title eligibility library sourcing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh` check (20) does not assert that `skills/design/SKILL.md` sources `lib-title-eligibility.sh`. The source line could be removed while other anchors still satisfy the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Export contract for title eligibility constants is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The contract and acceptance text imply four exported constants, but only `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER` is exported. Either the three bash regex constants should be exported too, or the documentation and acceptance language should be narrowed to sourced-only visibility plus the exported jq fragment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_4: Run Logs Audit Report fixture disagrees with plan intent
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The plan lists `[Run Logs Audit Report …]` as a report hit, while the harness and jq/bash grammar currently treat it as a miss because `Report` must abut `]`. This mismatch can confuse future maintainers and may either preserve an unintended miss or cause someone to “fix” the test in a way that breaks jq parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: Step 6 loses title-prefix brainstorm auto-enable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 0b sub-step 2.5 can auto-enable brainstorm from a `Brainstorm:` issue title, but Step 6 reinitializes `brainstorm_requested` from argv/upgrade paths only. `/design --simple N` on a brainstorm-prefixed issue can print the auto-enable banner, persist `brainstorm_requested=false`, and skip Step 1d.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Brainstorm reference omits title-prefix trigger
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/brainstorm.md` does not mention Step 0b sub-step 2.5 title-prefix auto-enable as a Step 1d.5 trigger. Operators may see the auto-enable banner but then read documentation that only explains argv or other triggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Already-planned ad-hoc Q&A gate ignores title-prefix brainstorm
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The already-planned ad-hoc Q&A branch only checks argv `--brainstorm`, not `brainstorm_requested` from the Step 0b 2.5 title-prefix path. A brainstorm-prefixed issue with an existing `larch:plan` can therefore skip mandatory Step 1d.5 in branch (b).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


