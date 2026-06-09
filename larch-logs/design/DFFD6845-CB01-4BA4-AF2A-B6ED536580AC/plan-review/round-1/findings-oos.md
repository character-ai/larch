### OOS_1:
- **Description**: C2 relies on dispatch voters passing --role voter without --model but plan verifies only test-launch-claude-review.sh not dispatch call sites. Scenario: A future edit could add --model to a dispatcher and silently bypass LARCH_VOTER_MODEL without a failing test
- **Reviewer**: Cursor-dyn-voter-caller-surface
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/dispatch-plan-voters.sh:97-105; scripts/dispatch-code-voters.sh:120-127; plan.txt:483-486
- **Phase**: design

