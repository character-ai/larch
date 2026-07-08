### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: plan.txt:67-70
- **Concern**: [SCOPE-REDUCTION] Follow-up issue filing path does not require the existing issue surface. Scenario: The scope_disposition module is assigned to file the follow-up issue, but the spec requires filing via /issue and repo conventions route issue creation through the existing issue helper. A custom direct gh path can bypass existing redaction, dedup, and dependency semantics while adding new issue-filing logic.
- **Proposed resolution**: Require proceed-partial to call the existing issue creation CLI or module with a body file, then use the existing dependency helper for the block relation. Do not add a second direct issue-create implementation in scope_disposition.py.
