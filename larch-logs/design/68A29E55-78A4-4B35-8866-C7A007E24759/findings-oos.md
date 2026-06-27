### OOS_1: Code-review voter dispatch still gates DISPATCH_OK on voter_1_status != failed
- **Description**: Code-review voter dispatch still gates DISPATCH_OK on voter_1_status != failed. Scenario: /review Step 5 can hit the same class of bug if Claude voter fails while other judges succeed; plan_review_panel fix does not touch this parallel path
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_voters.py:774
- **Phase**: design



### OOS_2: effective-judges subprocess failure forces effective=0
- **Description**: effective-judges subprocess failure forces effective=0. Scenario: If voting effective-judges exits non-zero, effective is coerced to 0 and dispatch fails closed even when voter files are substantive; unrelated to Claude-only gate but can reproduce dropped tallies
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_panel.py:1000
- **Phase**: design



