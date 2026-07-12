### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/review_tally.py:288-297
- **Concern**: Static focus mapping has no architectural-compliance entry.. Scenario: The new specialist is recorded as code-quality in scout-archetype-yield.tsv instead of architecture.
- **Proposed resolution**: Add architectural-compliance: architecture and cover the mapping.



### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/review/review_tally.py:288-297
- **Concern**: Static attribution does not recognize architectural-compliance. Scenario: Compliance findings default to code-quality in yield.tsv and downstream reviewer metrics
- **Proposed resolution**: Add architectural-compliance: architecture to _static_focus_area and test the mapping



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/review_test_support.py:123-170,211-249
- **Concern**: Shared review-core stubs remain three-slot. Scenario: Updated pipeline tests cannot exercise the new compliance slot and may report false coverage failures
- **Proposed resolution**: Add the compliance slug to fixture outputs, manifests, and collector records



