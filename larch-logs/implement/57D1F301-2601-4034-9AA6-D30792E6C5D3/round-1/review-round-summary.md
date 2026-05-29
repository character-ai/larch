# Review Round 1

- Mode: `diff`
- 13 accepted, 6 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Triplicated optional-trailer metadata awk parsers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Optional-trailer snapshot/validate awk is duplicated verbatim across `revise-plan-with-waterfall.sh`, `plan-review-loop.sh`, and `check-plan-size.sh` (three copies). Regex or last-match semantics can drift so one script accepts a metadata block another rejects, causing inconsistent gating vs revision acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Extract shared parser or add cross-script fixture test


### FINDING_10: test-design-structure 3175 pins incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structural pins in `test-design-structure.sh` do not grep-pin `diff_deleted` preservation, validate-before-`EMIT_PLAN`, or related prose across all three reference docs; doc drift could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Preservation fixtures omit diff_deleted assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Preservation tests in `test-revise-plan-with-waterfall.sh` and `test-plan-review-loop.sh` omit `diff_deleted` assertions. A regression that drops only the `diff_deleted` trailer could pass unified-diff and mechanical-churn loop tests while restoring legacy total-churn gating for deletion-heavy plans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Add grep -q '^diff_deleted: 100$' "$DMECH/plan.txt" (matching the stub) alongside diff_added and mechanical_churn checks.


### FINDING_12: Legacy check-plan-size cases omit new key assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Legacy cases 1–13 in `test-check-plan-size.sh` do not assert always-emitted `DIFF_ADDED` / `DIFF_DELETED` / `MECHANICAL_CHURN` / `SOFT_ADVISORY` keys on exit 0; removal could slip through if only cases 14+ run in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: Case 22b assertions weaker than 22a
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Case 22b assertions are weaker than 22a; a malformed double-space trailer could regress legacy fallback without failing 22b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Missing harness for 801 body lines with metadata subtraction
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: No test covers an 801-line plan body with optional metadata subtracted and low `diff_added`; metadata subtraction could regress and falsely clear the plan-body hard trigger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Trailer preservation validates key presence only, not values
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Preservation validation checks only that optional trailer keys remain present, not that `diff_added`, `diff_deleted`, or `mechanical_churn` values are unchanged. A waterfall or plan-review revision can lower `diff_added`, flip `mechanical_churn`, or otherwise change gate-driving values while validation passes; Step 2b.5 / plan-size-trigger behavior can change silently despite operator belief estimates were preserved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Snapshot and compare parsed trailer values or document and test key-only enforcement explicitly.
  - From cursor-specialist-security-output.txt: Snapshot and compare full strict trailer lines or values; reject value drift unless explicitly recomputed.
  - From cursor-specialist-edge-cases-output.txt: Snapshot strict trailer values or metadata-block hash and reject candidates that change diff_added/diff_deleted/mechanical_churn without matching diff_lines recompute


### FINDING_20: Missing test for mechanical_churn under already-soft diff
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: No test asserts that `mechanical_churn: true` under an already-soft `diff_added` emits `SOFT_ADVISORY=false`; advisory print logic could regress to always setting `SOFT_ADVISORY` when `mechanical_churn` is true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

**Merge notes (for voters, not part of machine output):**
- Input FINDING_2/8/16/18 → FINDING_2; FINDING_1/20 → FINDING_1; FINDING_3/26 → FINDING_3; FINDING_12/22 → FINDING_11.
- FINDING_6 vs FINDING_8 vs FINDING_17: same code area, different fixes (restore logic vs test vs reason string) — kept separate.
- FINDING_9 vs FINDING_16: related deletion-heavy behavior but test vs operator footgun — kept separate.
- FINDING_5 (`[OUT_OF_SCOPE]`) not merged with FINDING_18 (in-scope SKILL.md gap).

### FINDING_3: EMIT_PLAN fixture uses non-contiguous optional trailers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-emit-plan.sh` optional-trailer fixture uses blank-separated trailers instead of a contiguous metadata block immediately above `diff_lines`. Maintainers may copy the layout into real plans; `check-plan-size` would ignore non-contiguous `diff_added` / `diff_deleted`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_6: Dedup trailer-loss path restores wrong plan snapshot
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: On optional-trailer dedup validation failure, `plan-review-loop.sh` restores `pre_dedup` then overwrites with the pre-revise `plan_backup`. Revision may apply optional trailers; dedup corrupts metadata; validation fails; `plan.txt` ends up pre-revision while downstream logic still assumes a revised plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Unified-diff tier aborts after first candidate trailer failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The unified-diff tier does not try later candidates after post-apply trailer validation fails. The first apply-able patch in one response may strip trailers while a second patch in the same response would preserve them; the tier fails without exhausting candidates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: No regression test for optional-trailer-dedup-loss path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The optional-trailer-dedup-loss failure path in `plan-review-loop.sh` has no regression coverage. Dedup could strip required optional trailers after waterfall revision; the loop could emit wrong `LOOP_STATUS`/`REASON` or revert to legacy total-churn hard gating without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: diff_deleted-only legacy fallback edge case untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: A plan with `diff_deleted: 9999` and `diff_lines: 5000` but no `diff_added` could incorrectly hard-trigger on additions logic if the parser regresses; no harness asserts the expected legacy fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


