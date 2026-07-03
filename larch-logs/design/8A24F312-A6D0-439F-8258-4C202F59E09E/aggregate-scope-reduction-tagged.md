### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/tokens.py:52-85
- **Concern**: [SCOPE-REDUCTION] The plan adds scaffold_tokens and payload_tokens beyond the byte split the issue requires. Scenario: The committed TSV and measure-panel-cost schemas grow extra derived columns even though acceptance only needs scaffold and payload byte columns plus scaffold-byte ranking
- **Proposed resolution**: Limit panel-prompt-sizes.tsv additions to scaffold_bytes and payload_bytes; keep existing prompt and agent token columns unchanged and omit per-section token columns unless a separate requirement needs them
