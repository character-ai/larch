### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/exec_issue_detail.py:91-108
- **Concern**: [SCOPE-REDUCTION] Haiku `subprocess.run(["claude", "--print", ...])` assessment adds a new LLM dependency, latency, token cost, and ~200 lines of prompt/parse/fallback code for every non-empty category. Scenario: The issue requires explicit listing of exec issues and warnings with descriptions; the example assessments are illustrative ("something like"). Listing redacted `display_text` rows alone satisfies the stated gap without blocking final-summary on Claude availability or adding per-run subprocess cost
- **Proposed resolution**: Ship v1 with `render_issue_detail_block(..., assess=False)` (numbered rows only). Add assessments later behind an env flag if operators still want them
