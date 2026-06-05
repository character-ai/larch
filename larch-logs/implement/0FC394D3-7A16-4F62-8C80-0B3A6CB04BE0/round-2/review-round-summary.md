# Review Round 2

- Mode: `diff`
- 3 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: CHANGELOG conflicts are bump-classified in Python but not bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-parity-output.txt, dyn-bump-classifier-output.txt, cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `_is_bump_path` treats `CHANGELOG.md`, `CHANGELOG.rst`, and bare `CHANGELOG` as bump/version paths, suppressing pre-push conflict handoff for CHANGELOG-only conflicts. Bash `ship_pr_vendor_conflict_csv_is_non_bump_only` does not classify CHANGELOG files this way, so bash can hand off while Python stalls without the handoff flag. This creates bash-fidelity and Phase 7 routing risk; if intentional, it needs explicit documentation and parity coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-bash-parity-output.txt: Address the concern above.
  - From dyn-bump-classifier-output.txt: Address the concern above.
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_2: Bump and mixed conflict tests do not exercise the enabled handoff gate
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bump-classifier-output.txt
- **Severity**: important
- **Concern**: Existing bump-only and mixed-conflict exhaustion tests omit `enable_pre_push_handoff=True`, so they only prove plain `Stalled` when handoff is disabled. The production path from `ship.py` enables handoff, leaving a regression hole where bump or mixed conflicts could incorrectly raise `PrePushConflictHandoff` or write the flag without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bump-classifier-output.txt: Address the concern above.


### FINDING_3: Site-2 resolved-conflict path lacks enabled-handoff regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The site-2 test does not enable handoff, so a future change could emit `PrePushConflictHandoff` after a winning recovery tier without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


