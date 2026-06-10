### OOS_1:
- **Description**: Option B adds a second Cursor probe branch that copies the setup trio instead of reusing one helper.. Scenario: Future edits to the normal preflight-0 path (auth export, private config, cleanup ordering) can miss the preflight-2 one-shot branch despite t-optb-setup-chain parity tests.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/check-reviewers.sh:280-314
- **Phase**: design

