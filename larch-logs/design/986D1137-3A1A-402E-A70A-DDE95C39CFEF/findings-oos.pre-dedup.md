### OOS_1: Gap 1 still bypasses the Step 5 bash wrapper
- **Description**: Gap 1 still bypasses the Step 5 bash wrapper. Scenario: Issue scope asks for `--difficulty` on the step-5 wrapper surface (`run-flags.sh` forwarding). The plan only calls `review-and-fix step5 --difficulty` directly, so wrapper regressions would not be caught.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-5-review.sh
- **Phase**: design



