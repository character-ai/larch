### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-schema-drift
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:34,40,49,94,102,210,263
- **Concern**: Canonical vN to tool map is re-stated in multiple proposed contracts instead of having one authority. Scenario: One section can later drift to v1=Claude v2=Cursor v3=Codex while harness or docs still say v2=Codex, producing silently mis-labeled TSV analytics
- **Proposed resolution**: Choose one authority, preferably skills/design/scripts/tally-plan-review.md plus one map in tally-plan-review.sh, and change parser md, plan-review.md, harness md, docs/run-logs.md, and acceptance text to cite that authority without re-stating the tuple


