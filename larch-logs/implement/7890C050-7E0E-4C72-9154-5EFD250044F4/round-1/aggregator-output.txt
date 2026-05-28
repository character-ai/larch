### FINDING_1: Untested dedup-python-failed rollback path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The new fail-closed handling for Python failure or non-numeric dedup output is not covered by a targeted regression test, so a future heredoc/Python regression could silently restore the old `dedup_removed=0` corruption path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Missing comment for fence range invariant
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The `in_fence_lines` loop lacks an explicit off-by-one comment documenting why `range(top_i + 1, i)` excludes the fence boundary lines, making future edits to the bounds riskier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Dedup semantics changed for fence-like lines inside Constraints
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Consecutive duplicate fence-marker lines inside `## Constraints` may now be protected from deduplication where the previous toggle-based behavior would have collapsed them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Duplicated rollback handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The rollback handling for Python exit failure and non-numeric `dedup_removed` is duplicated, which risks inconsistent future edits between the two failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Duplicated post-apply dedup test harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The post-apply dedup tests duplicate the same `bash -c`/`awk` extraction harness, so adding another case would likely copy the block again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Plan acceptance red check is not CI-enforced
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The pre-patch red verification for the plan acceptance bug is not enforced by CI, so a fixture that never fails on main could merge without proving it exercises the reported regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Unclosed-fence test depends on prior stubs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The unclosed-fence test case relies on stubs created by an earlier block, so reordering tests or running the case in isolation can fail due to a missing `dedup-emit-driver.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Broader dedup semantics after unclosed fence in Constraints
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: With `## Constraints` before an unclosed fence, duplicate bullets that old behavior collapsed may now be preserved; that changed ordering/semantic behavior is untested or undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: dedup-python-failed leaves backup file
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The dedup failure rollback restores `plan.txt` but leaves the `.plan-before-revise.*` backup under `DESIGN_TMPDIR`, unlike the normal failure cleanup path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Redundant dedup_removed fallback after numeric guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `${dedup_removed:-0}` is still used after the numeric guard has established success, which suggests an empty value remains possible on the success path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Inline Python heredoc remains brittle
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The large inline Python heredoc is tightly coupled to awk-extracted tests, so accidental column-zero shell syntax in the function body could break all dedup tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Parser and dedup fence models differ
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The AWK parser and Python dedup logic appear to use different fence-boundary semantics, which could cause future divergence when either path changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Section-aware dedup test has weak stdout assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The section-aware dedup test uses a weaker `grep -q` stdout check, so extra stderr/stdout lines could pass there while the unclosed-fence case would catch them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Missing full run_loop coverage for dedup-python-failed
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no full `run_loop` integration test proving the caller wiring handles the new `LOOP_REASON=dedup-python-failed` correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Dedup runs before size guard
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `_run_post_apply_pipeline` runs dedup before `check-plan-size.sh`; with `readlines()`, pathological single-line plans may slightly increase peak memory, though the ordering and trust boundary predate this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Test harness uses eval for extracted function
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The new test reuses the existing `eval "$(awk ...)"` extraction pattern. Production does not use this pattern and `PLR` is repo-controlled, so this is only future test-harness hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] dedup-python-failed is undocumented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `dedup-python-failed` is absent from the `plan-review-loop.md` `LOOP_REASON` tables, making operator debugging harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Validator failure leaves deduped plan in place
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On validator failure after successful dedup, the backup is removed without restoring the original plan, leaving the deduped `plan.txt` in place. This is noted as pre-existing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
