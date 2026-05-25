### OOS_1:
- **Description**: SKIP_REASON awk uses FS== so the first REASON_TOKEN line yields $2 including trailing fence metadata (e.g. pipe-in-node-label fence).. Scenario: step-7a substring logic is even less reliable if future heuristics parse SKIP_REASON sloppily; root fix belongs in the generator, not step-7a.
- **Reviewer**: Cursor-dyn-sanitizer-token-contract
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:104
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2794
