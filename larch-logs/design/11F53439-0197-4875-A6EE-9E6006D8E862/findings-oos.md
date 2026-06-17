### OOS_1:
- **Description**: _render_rejected_findings_for_tally copies non-finding lines after the first ### FINDING_* header including disallowed section headers. Scenario: Non-fatal validation fixes tally JSON but bodies still carry stray headers from aggregate bleed; diagnostics remain noisy and validation warnings may fire every round.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:831-838
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] rc 4 warn-and-continue is more complex than deleting code-review body validation entirely. Scenario: Body is never stored in code-review-tally.json; keeping a scan that only warns adds code and tests for a discarded artifact.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/voting.py:816-821
- **Phase**: design

### OOS_3:
- **Description**: Post-fix ignored-header warnings stay on `write-tally` stderr only and are not relayed on the `flush_review_batches` success path. Scenario: Operators debugging multi-round runs lose even the prior `failed to flush code-review-tally batch` breadcrumb for header-validation issues; warnings are visible only in direct `write-tally` unit tests
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:916-919
- **Phase**: design

