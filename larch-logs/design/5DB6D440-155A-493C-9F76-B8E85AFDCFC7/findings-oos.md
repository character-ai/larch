### OOS_1: [OUT_OF_SCOPE] `design_oos.py` keeps a third local `_is_security_block_text` duplicate outside Item 3 consolidation
- **Description**: [OUT_OF_SCOPE] `design_oos.py` keeps a third local `_is_security_block_text` duplicate outside Item 3 consolidation. Scenario: Aggregate promotion in Step 5b still classifies security via a hand-rolled regex helper while plan/review tally move to `voting.is_security_block_text`, so design filing can drift from plan-review routing without a failing test in this change set.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_oos.py:120-128
- **Phase**: design



