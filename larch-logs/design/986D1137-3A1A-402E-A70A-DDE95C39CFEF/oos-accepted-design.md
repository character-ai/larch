### OOS_1: Gap 1 names the step-5 bash wrapper; the plan only exercises review-and-fix step5 --difficulty
- **Description**: Gap 1 names the step-5 bash wrapper; the plan only exercises review-and-fix step5 --difficulty. Scenario: A regression that drops DIFFICULTY_OVERRIDE forwarding in step-5-review.sh would not be caught. The mapping under test is still covered at the CLI boundary.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-5-review.sh:57-87
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/6188
