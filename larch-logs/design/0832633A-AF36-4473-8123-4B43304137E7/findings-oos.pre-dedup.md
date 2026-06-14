### OOS_1:
- **Description**: flags.md still implies --skip-validate skips all Step 5c composed-plan validation. Scenario: After the change, proceed-anyway skips only ordinary command validation; the missing-or-empty composed-plan precondition still exits 4. Stale reference text may mislead future edits but does not block the fix.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/flags.md:73
- **Phase**: design

