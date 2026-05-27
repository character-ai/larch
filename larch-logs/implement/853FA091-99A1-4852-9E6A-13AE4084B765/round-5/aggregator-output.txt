### FINDING_1: Structural pin contradicts Step 3 review-counter behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still expects empty or unrecognized `LOOP_STATUS` to roll back the review counter, but the current SKILL prose and Step 3 behavior only roll back on `tally-error` and otherwise consume the slot. This makes `make lint` fail and leaves docs/tests/runtime inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_4: [OUT_OF_SCOPE] Plan review can read wrong feature file after implement
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The plan-review-loop feature-file resolution prefers `IMPLEMENT_TMPDIR` over `DESIGN_TMPDIR` when both are set, so `/design` Step 3 after `/implement` in the same session can review against the wrong `feature-description.txt`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_5: Token analysis still uses obsolete Quick-mode fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/report-tokens/scripts/run-analysis.sh` still falls back to legacy Quick-mode tally heuristics or unknown workflow-path handling after Quick review removal. Runs with missing or incomplete timing JSON can be mislabeled instead of resolving from `run-params.json` / `design_classification`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Classification reader grep fallback can be spoofed
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/read-design-classification.sh` falls back to grep when both `python3` and `jq` are unavailable. A crafted `run-params.json` could expose a misleading `SIMPLE` substring before the actual field.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Step 3 cap env file is sourced directly
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` sources `.step3-review-cap.env` from `$DESIGN_TMPDIR`, which is consistent with the current same-UID trust model but would allow shell injection if that trust model is later tightened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Classification reader hides parse/read failures behind exit 0
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `scripts/read-design-classification.sh` always exits 0 and prints `HARD` on read or parse failure, with only a stderr warning. Automation checking `$?` can treat failures as success and silently apply HARD caps/emphasis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Gate C still offers re-run at review cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate C’s cap-aware option list is prose-only while Step 3 is the only mechanical guard. Operators can still be shown a Re-run option at cap, then lose a turn when Step 3 immediately short-circuits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Review-round slots are consumed before panel success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 3 persists the review-round count before launching the panel. Crashes or kills can consume cap slots without producing fresh panel findings, eventually forcing approval from stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: Linting docs still mention removed Quick/sketch vocabulary
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `docs/linting.md` still describes `test-write-run-params` in terms of zero-sketch and full-and-quick budget examples, conflicting with the v2 SIMPLE/HARD model and acceptance requirement to remove `sketch_budget`, `review_budget`, and quick-mode vocabulary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: timing-ledger fallback acceptance is not implemented literally
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The plan/acceptance text requires a `timing-ledger.sh` fallback chain, but `scripts/timing-ledger.sh` itself does not read `run-params`. The behavior may work through sibling timing-report readers, but the literal acceptance bullet remains unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
