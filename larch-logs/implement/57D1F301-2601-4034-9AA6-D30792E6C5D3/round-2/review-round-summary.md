# Review Round 2

- Mode: `diff`
- 9 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Strict optional-trailer value equality blocks legitimate recompute
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `validate_optional_trailers_preserved` requires exact numeric equality against a pre-revision snapshot when `values_file` is passed, which conflicts with documented preserve-or-recompute semantics. Scope-shrinking revisions that keep strict trailer keys and grammar but legitimately change `diff_added` / `diff_deleted` / `mechanical_churn` fail validation; waterfall or post-dedup paths may mark `invalid-patch` and fail the round despite an otherwise valid plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: No negative file-replacement test for stripped optional trailers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness case covers file-replacement dropping optional trailers; regression in early `validate_optional_trailers_preserved` for file-replacement could allow trailer-stripped plans to win a tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: `test-check-plan-size.md` lags cases 27–29
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness documentation stops at case 26 while the script implements cases 27–29, so contributors may miss new edge cases when updating thresholds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: No test for value-mismatch preservation rejection
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No harness asserts that `validate_optional_trailers_preserved` fails when trailer values differ but keys remain; waterfall could accept value-changing patches unless behavior is intentionally relaxed (see FINDING_1).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: `PLAN_LINES` over-subtracts metadata block with duplicate keys
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `PLAN_LINES` subtracts every strict metadata line in the block (`block_len`) while duplicate keys use last-match-wins for gating only. Multiple `diff_added` lines plus other optional trailers can undercount body lines so plan-body-lines gating does not fire despite >800 real body lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Gate B pipeline snapshots trailers after dedup rewrite
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Gate B’s shared post-apply pipeline places optional-trailer snapshot step 4a after dedup rewrite steps 1–3, contradicting “before dedup rewrite” wording and the snapshot-then-validate contract. LLM dedup can strip `diff_added` or `mechanical_churn` before step 4a; Step 2b.5 may then hard-trigger on legacy `diff_lines` despite pre-revision relief.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: `check-plan-size.md` sync list omits trailer libs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The “Edit in sync” list does not mention `lib-plan-optional-trailers.sh` or `.awk`, so future trailer-parser edits may update `check-plan-size.md` while leaving the shared awk module undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_7: Misleading `LOOP_STATUS=emit-plan-failed` for trailer dedup loss
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Optional-trailer loss after dedup is reported as `LOOP_STATUS=emit-plan-failed` even when emit did not fail, obscuring the real failure mode (optional-trailer dedup loss).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Weak dedup-preservation test fixture
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The dedup preservation fixture does not match a plan body-decoy scenario and does not assert that dedup removed lines. If `dedup-plan-lines.py` stops deduplicating trailer-shaped lines or only dedups outside the metadata block, the test can pass without exercising failure mode #10.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


