### FINDING_1: PLAN_LINES subtracts distinct optional keys, not every strict trailer line
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `metadata_trailer_lines` in `lib-plan-optional-trailers.awk` uses `has_added + has_deleted + has_mech` (0–3 distinct keys), not the count of every strict optional trailer line in the final contiguous metadata block. Plans at the body-line boundary with duplicate `diff_added:` (or multiple strict trailer lines) can under-subtract metadata lines, inflate `PLAN_LINES`, and fire a spurious `plan-body-lines` hard trigger while `diff_added` stays soft (last-match-wins). `check-plan-size.md` calls for subtracting all recognized optional metadata trailer lines in the block; use `block_len` or an equivalent physical line count, and add boundary harness cases (e.g. 800 body + duplicate `diff_added`, or 799 body + three `diff_added` lines).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Case 25 encodes under-subtraction for duplicate `diff_added` lines
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test-check-plan-size.sh` case 25 locks in under-subtraction for duplicate `diff_added` lines instead of the plan’s full-line-count rule for optional metadata. The suite can stay green while the parser bug remains, blocking detection of false `plan-body-lines` hard triggers from duplicate metadata. Recompute expected `PLAN_LINES`/`HARD_TRIGGER` after fixing awk and document duplicate-line subtraction in `test-check-plan-size.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


