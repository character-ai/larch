### OOS_1: tracking-issue lifecycle writes sit outside create-one and the reporter helper
- **Description**: tracking-issue lifecycle writes sit outside create-one and the reporter helper. Scenario: /implement and tooling can still gh issue create or comment via tracking-issue create-issue and append-comment without the new authorization marker
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/issue/tracking_issue.py:266-318
- **Phase**: design



### OOS_2: /design clarify still mutates labels and comments directly
- **Description**: /design clarify still mutates labels and comments directly. Scenario: Clarify publish and label add/remove call gh issue comment and gh label APIs without any planned authorization input; clarify tests or replays can edit production issues outside the gated filing surfaces
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/design/clarify.py:399-449
- **Phase**: design



### OOS_3: audit-runs still has comment mutations beyond close-priors
- **Description**: audit-runs still has comment mutations beyond close-priors. Scenario: Plan gates close-priors only; augmentation and session-summary steps still use gh issue comment on real audit issues without operator authorization
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: security
- **Location**: python/larch/issue/audit_runs.py:1295-1296,.claude/skills/audit-runs/SKILL.md:167-198
- **Phase**: design



### OOS_4: Partition approval still closes the original issue via direct `gh issue comment` and `gh issue close` outside the planned gates
- **Description**: Partition approval still closes the original issue via direct `gh issue comment` and `gh issue close` outside the planned gates. Scenario: Approved decomposition can comment on and close the source issue from tests or unauthorized replays even when `issue create-one`, reporters, and salvage reconciliation refuse
- **Reviewer**: Cursor-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/design/decompose.py:462-480
- **Phase**: design



### OOS_5: `tracking-issue` create/comment/rename/upsert-summary mutations are not in the firm file list despite `/implement` bootstrap and scope-disposition callers
- **Description**: `tracking-issue` create/comment/rename/upsert-summary mutations are not in the firm file list despite `/implement` bootstrap and scope-disposition callers. Scenario: `bootstrap.py` and other live paths invoke `tracking-issue rename`, `append-comment`, and `upsert-summary` without any planned authorization contract, leaving title/comment mutations reachable outside the new boundary
- **Reviewer**: Cursor-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/issue/tracking_issue.py:266-348,839-924
- **Phase**: design



### OOS_6: `/design` clarify publish still posts comments and edits labels without a planned authorization check
- **Description**: `/design` clarify publish still posts comments and edits labels without a planned authorization check. Scenario: Clarify fetch/publish paths can comment on or relabel live issues from development replays even when filing choke points refuse
- **Reviewer**: Cursor-Requirements
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/design/clarify.py:391-449
- **Phase**: design



