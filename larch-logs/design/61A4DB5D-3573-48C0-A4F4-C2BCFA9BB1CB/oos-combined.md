### OOS_1: Aggregated rollup of 3 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 3 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_1:**: - **Description**: Library rename() still lacks shell redacted idempotency. Scenario: Plan adds CLI rename_main canonical-title comparison but keeps tracking_issue.rename() unchanged; Python ship fina… [Files: python/finalize.py:435-441]
  - **OOS_1:**: - **Description**: Sibling `*.md` contract files are not listed for cutover. Scenario: `implement-bootstrap.md`, `design-publish.md`, `implement-finalize.md`, and similar files still name retired help… [Files: design-publish.md implement-bootstrap.md implement-finalize.md skills/implement/scripts/test-implement-bootstrap.md]
  - **OOS_4:**: - **Description**: skills/implement/SKILL.md invariant #2 still names tracking-issue-summary.sh but the plan only lists an emergency-preflight edit for that file. Scenario: The stale helper name is do… [Files: skills/implement/SKILL.md skills/implement/SKILL.md:26 tracking-issue-summary.sh]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 3 entries
- **Phase**: implement

