### FINDING_1: Structural pin contradicts Step 3 review-counter behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still expects empty or unrecognized `LOOP_STATUS` to roll back the review counter, but the current SKILL prose and Step 3 behavior only roll back on `tally-error` and otherwise consume the slot. This makes `make lint` fail and leaves docs/tests/runtime inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_11: Linting docs still mention removed Quick/sketch vocabulary
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md` still describes `test-write-run-params` in terms of zero-sketch and full-and-quick budget examples, conflicting with the v2 SIMPLE/HARD model and acceptance requirement to remove `sketch_budget`, `review_budget`, and quick-mode vocabulary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: Already-planned ad-hoc path forces HARD classification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 0b creates a minimal v2 `run-params.json` with `design_classification=HARD` when an already-planned issue re-enters ad-hoc Q&A without an existing params file. That can bypass the tier choice and route the session through HARD caps and reviewer emphasis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: SIMPLE reviewer emphasis diverges from locked plan prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/render-plan-review-prompt.sh` uses SIMPLE tier emphasis text that no longer matches the plan-locked reviewer prose, including the security carve-out and missing Accept YES line. This can bias SIMPLE reviews differently from the intended minimum-change contract while tests only check partial substrings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_5: Token analysis still uses obsolete Quick-mode fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/report-tokens/scripts/run-analysis.sh` still falls back to legacy Quick-mode tally heuristics or unknown workflow-path handling after Quick review removal. Runs with missing or incomplete timing JSON can be mislabeled instead of resolving from `run-params.json` / `design_classification`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


