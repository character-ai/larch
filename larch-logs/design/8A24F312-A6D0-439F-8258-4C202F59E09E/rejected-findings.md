### [Plan Review] FINDING_3

### FINDING_3: Implementer payload counting overstates path-referenced findings content
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The implementer prompt counts scrubbed findings-file bytes even though the prompt only path-references that file rather than inlining it. That can overstate payload, drive scaffold to zero, and erase the implementer scaffold signal needed for ranking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Set implementer `payload_bytes` to zero (or count only bytes actually written into `coder-prompt.md`), and drop the edge-case allowance for payload larger than prompt bytes on this path
  - From Cursor-Pragmatic: Set implementer `payload_bytes=0` (or pass explicit zero through `append_panel_prompt_size` / `build_panel_dispatch_env`). Drop the `coder_runner.py` bullet that counts scrubbed accepted-findings file bytes, and update `test_review_and_fix.py` to assert zero payload with non-zero scaffold for the path-referenced coder prompt.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/tokens.py:52-85
- **Concern**: [SCOPE-REDUCTION] The plan adds scaffold_tokens and payload_tokens beyond the byte split the issue requires. Scenario: The committed TSV and measure-panel-cost schemas grow extra derived columns even though acceptance only needs scaffold and payload byte columns plus scaffold-byte ranking
- **Proposed resolution**: Limit panel-prompt-sizes.tsv additions to scaffold_bytes and payload_bytes; keep existing prompt and agent token columns unchanged and omit per-section token columns unless a separate requirement needs them


