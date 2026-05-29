Normalizing reviewer input into a merged finding list: grouping by behavioral risk and first-seen order.
### FINDING_1: PLAN_LINES subtracts distinct optional keys, not every strict trailer line
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `metadata_trailer_lines` in `lib-plan-optional-trailers.awk` uses `has_added + has_deleted + has_mech` (0–3 distinct keys), not the count of every strict optional trailer line in the final contiguous metadata block. Plans at the body-line boundary with duplicate `diff_added:` (or multiple strict trailer lines) can under-subtract metadata lines, inflate `PLAN_LINES`, and fire a spurious `plan-body-lines` hard trigger while `diff_added` stays soft (last-match-wins). `check-plan-size.md` calls for subtracting all recognized optional metadata trailer lines in the block; use `block_len` or an equivalent physical line count, and add boundary harness cases (e.g. 800 body + duplicate `diff_added`, or 799 body + three `diff_added` lines).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Missing script-md sibling / shebang inconsistency for shared trailer library
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `lib-plan-optional-trailers.sh` is sourced-only but carries a shebang while peer libs (e.g. `lib-findings-classification.sh`) do not, and there is no `lib-plan-optional-trailers.md` co-located stub per the repo `script-md-siblings` contract. Contributors editing trailer grammar may miss documented invariants and downstream callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Dead code `snapshot_optional_trailer_values`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `snapshot_optional_trailer_values` in `lib-plan-optional-trailers.sh` is unused. Future edits may assume trailer values are snapshotted for validation when only keys are checked today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Redundant subshell churn parsing awk four-line output
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check-plan-size.sh` uses four `sed` calls to parse one awk multi-line result on every Step 2b.5 invocation instead of a single `read`/`mapfile` pass over the four-line block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Keys-only trailer preservation lacks deliberate-documentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `validate_optional_trailer_preservation` checks keys only, not trailer values—intentional for the recompute path but easy to misread when extending validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Gate B optional-trailer preservation enforced in prompts, not bash dedup path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Gate B trailer preservation is documented and prompt-driven while review-loop and waterfall paths enforce related rules in bash. Gate B dedup can drop `mechanical_churn` while keeping high `diff_lines`, and Step 2b.5 legacy hard triggers apply if a verify step is skipped. Reuse snapshot/validate helpers for Gate B dedup or add a small script wrapper shared with `plan-review-loop`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Leading-zero trailer digits break threshold comparisons (awk + bash)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Trailer digit parsing allows leading zeros. In bash, `[[ -gt ]]` on values like `002001` or `003000` can be interpreted as octal, so `diff_added`/`diff_lines` hard gates in `check-plan-size.sh` may not fire when decimal values exceed thresholds; invalid forms like `08`/`09` can error or evaluate false and skip the gate. Awk regex has the same class of issue for parsed trailer values. Coerce with `10#` before comparisons, optionally reject leading-zero trailers in awk, and add harness cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Cases 14–29 omit `assert_always_emitted_keys` on success paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: New harness cases in `test-check-plan-size.sh` (14–29) do not call `assert_always_emitted_keys` on `run_ok` exit 0, though the plan mandates always-emitted `DIFF_ADDED`, `DIFF_DELETED`, `MECHANICAL_CHURN`, and `SOFT_ADVISORY`. A partial regression could stop emitting one key on some paths while other assertions still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: `test-design-structure.sh` does not grep `diff_deleted` in SKILL.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structural test greps `diff_added` and `mechanical_churn` in `SKILL.md` but not `diff_deleted`, despite the Gate preservation contract listing all three. `diff_deleted` preservation prose could be dropped without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] No focused unit harness for awk trailer parser modes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `lib-plan-optional-trailers.awk` behavior is only covered via integration tests. Subtle last-match-wins or `has_key` bugs may require debugging through full `plan-review-loop` or waterfall fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Self-declared trailers downgrade diff gating without repo verification
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `mechanical_churn` and `diff_added` trailers can downgrade or replace diff hard gating without verification against actual repo churn. A plan or issue body can end with `mechanical_churn: true` and low `diff_added` while `diff_lines` stays above legacy thresholds; Step 2b.5 and `plan-review-loop` may proceed without Split/Cancel for very large stated churn. Trailers should be documented as unverified assertions; do not rely on this gate alone for safety limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Case 25 encodes under-subtraction for duplicate `diff_added` lines
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-check-plan-size.sh` case 25 locks in under-subtraction for duplicate `diff_added` lines instead of the plan’s full-line-count rule for optional metadata. The suite can stay green while the parser bug remains, blocking detection of false `plan-body-lines` hard triggers from duplicate metadata. Recompute expected `PLAN_LINES`/`HARD_TRIGGER` after fixing awk and document duplicate-line subtraction in `test-check-plan-size.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Gate B trailer preservation not surfaced in SKILL.md Step 2b/2b.5
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Gate B optional-trailer preservation lives in `approval-gates.md` but is not duplicated in `SKILL.md` as the plan file list requested. Operators reading only Step 2b/2b.5 may miss rewrite snapshot/validate rules unless they follow the Gate B mandatory read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):** Input findings 1/6/15 → FINDING_1; 2/9 → FINDING_2; 8/14 → FINDING_7. FINDING_12 (test case 25) is kept separate from FINDING_1 because it targets a different artifact (harness expectations) even though it tracks the same root parser behavior. All source slots used generic “Address the concern above” revisions; no additional verbatim fix text was available to quote.
