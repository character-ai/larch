### FINDING_1: Step 2 token-mark contract is inverted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The shipped Step 2 contract still says external launchers must not emit the `Step 2 — implementation` token mark, but the plan moves that mark into the Codex and Cursor launchers. That stale contract conflicts with the intended runtime path and could cause a revert or follow-on regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: "Update the contract text and ownership bullets so binary-present Codex/Cursor launches own the Step 2 token mark, while dispatcher token marks remain on Claude fallback and binary-missing routes."

### FINDING_2: Cursor fallback path lacks regression coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The new Step 2 report fallback is only covered for `codex_implement`; the `cursor_implement` remap is untested, so a bug there could still fold Cursor implement runs into Step 0 and misstate the cost split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: "Add the same ledger fixture for cursor_implement, or parametrize the new report regression over both raw labels."
