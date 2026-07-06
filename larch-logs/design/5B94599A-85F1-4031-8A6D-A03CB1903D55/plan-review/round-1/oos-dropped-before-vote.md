### OOS_2: No bash 3.2 end-to-end test that jq-less Step 4b tail survives a no-match grep probe
- **Description**: No bash 3.2 end-to-end test that jq-less Step 4b tail survives a no-match grep probe. Scenario: The latent bug only appears on macOS bash 3.2 without jq; lint plus unit fixtures may still miss an integration regression if the subshell redirect is misplaced
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step3b-tail.sh
- **Phase**: design

