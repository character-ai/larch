### OOS_1: Fate policy does not dock issues closed as DUPLICATE without combine marker
- **Description**: Fate policy does not dock issues closed as DUPLICATE without combine marker. Scenario: [OOS] issues deduped or closed as duplicate may keep retroactive +1 even though backlog value is gone like wontfix/combined-away
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:22-24
- **Phase**: design



### OOS_2: _fetch_filed_oos_issue_details requests full comments without a cap or close-comment-first strategy
- **Description**: _fetch_filed_oos_issue_details requests full comments without a cap or close-comment-first strategy. Scenario: issue_create.fetch-issue-details caps comments; a long-closed OOS source issue may omit an early Combined into #N close comment from the view payload, leaving combined-away as unknown instead of docked
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:180-201
- **Phase**: design



