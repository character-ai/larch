### OOS_1:
- **Description**: Plan rewrites brainstorm/tally cases but does not mention updating expected_legacy_layout for post-#3548 anchor artifacts. Scenario: After #3548 materializes plan-review-scope-anchor.txt (and related context files) the legacy golden layout case may fail unless #3548 already updated the pin
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1304-1305
- **Phase**: design

