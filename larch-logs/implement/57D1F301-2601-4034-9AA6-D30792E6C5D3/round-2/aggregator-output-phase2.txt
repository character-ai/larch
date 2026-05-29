Normalized aggregator output from the supplied reviewer slots (read-only; no codebase verification).

### FINDING_1: Strict optional-trailer value equality blocks legitimate recompute
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `validate_optional_trailers_preserved` requires exact numeric equality against a pre-revision snapshot when `values_file` is passed, which conflicts with documented preserve-or-recompute semantics. Scope-shrinking revisions that keep strict trailer keys and grammar but legitimately change `diff_added` / `diff_deleted` / `mechanical_churn` fail validation; waterfall or post-dedup paths may mark `invalid-patch` and fail the round despite an otherwise valid plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Magic `substr` offsets for trailer values in awk
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `diff_added` and `diff_deleted` extraction in `lib-plan-optional-trailers.awk` uses fixed `substr` offsets tied to token spelling; renaming trailers or changing single-space grammar can break extraction without a clear regex failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: `check-plan-size.md` sync list omits trailer libs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The “Edit in sync” list does not mention `lib-plan-optional-trailers.sh` or `.awk`, so future trailer-parser edits may update `check-plan-size.md` while leaving the shared awk module undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Missing script-md stubs for design `lib-*.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Skill-local `lib-*.sh` files lack script-md sibling stubs required elsewhere in the repo, making argv, callers, and edit-in-sync rules harder to discover (pre-existing gap also noted for `lib-findings-classification.sh`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Redundant optional-trailer validation on file-replacement path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `revise-plan-with-waterfall.sh` validates optional trailers on the candidate and again on `plan.txt` after apply, adding extra full-file awk passes on every tier-4 success; post-apply validation alone may suffice unless early reject is needed for clearer errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Legacy `diff_lines` hard trigger when `diff_added` is absent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Deletion-heavy relief depends on designers emitting `diff_added`, but the script still hard-triggers on legacy `diff_lines` when `diff_added` is absent. A plan with large `diff_lines` and no optional trailers still gets `HARD_TRIGGER_FIRED=true` and Split/Cancel only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_9: Structural tests omit `SKILL.md` Gate A/B trailer guardrails
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Structural pins omit `SKILL.md` requirements for snapshot / `diff_deleted` / validate-before-`EMIT_PLAN` that plan acceptance expects. Gate B and discussion direct-rewrite preservation prose may live only in references; an operator following `SKILL.md` for manual rewrites could omit trailer preservation while `test-design-structure.sh` still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

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

### FINDING_13: Honor-system optional trailers can bypass hard size gate
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Optional plan-size trailers are self-asserted without independent verification. A designer or compromised agent can set `mechanical_churn: true` and low `diff_added` to bypass diff hard Split/Cancel while the plan remains large and complex; `mechanical_churn: true` is trusted without verifying mechanicality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: No cross-check between optional trailers and `diff_lines`
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: No consistency check between `diff_added` / `diff_deleted` and final `diff_lines` while emit still publishes `diff_lines`. Gates may pass on low `diff_added` while `diff-lines.txt` / `DIFF_LINES` show a very large total, or high `diff_deleted` with low totals can bypass hard triggers while misrepresenting churn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_17: Gate A/B direct `plan.txt` rewrites lack script trailer guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate A/B direct `plan.txt` rewrites enforce optional trailers via prompt only, with no script guard. A Gate B dedup rewrite that drops `mechanical_churn: true` can revert to legacy `diff_lines` hard gating and force Split/Cancel on a deletion-heavy plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Case 29 omits legacy hard trigger with `diff_deleted` only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Case 29 does not assert legacy hard trigger when `diff_deleted` is present but `diff_lines` exceeds 1500 without `diff_added` (harness gap; implementation may already be correct).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
