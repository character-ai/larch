### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/step2-dispatch.md:32
- **Concern**: External-launcher token-mark contract stays inverted. Scenario: The shipped Step 2 contract still tells readers that external launchers must not emit token mark "Step 2 — implementation", but the plan moves that mark into the Codex and Cursor launchers. That stale contract contradicts the new runtime path and invites a revert or a bad follow-on change.
- **Proposed resolution**: Update the contract text and ownership bullets so binary-present Codex/Cursor launches own the Step 2 token mark, while dispatcher token marks remain on Claude fallback and binary-missing routes.



### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/report/test_tokens.py:867-885
- **Concern**: Cursor branch of the new Step 2 report fallback is untested. Scenario: The planned regression only covers codex_implement. A bug in the new cursor_implement remap would still leave Cursor implement runs folded into Step 0 and the cost split wrong.
- **Proposed resolution**: Add the same ledger fixture for cursor_implement, or parametrize the new report regression over both raw labels.



