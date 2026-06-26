### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:17-22
- **Concern**: [SCOPE-REDUCTION] Firm diagnostics preservation branch exceeds issue acceptance criteria. Scenario: The issue requires dynamic slot accounting, threshold inclusion, dropped-slots ledger visibility, and Warnings via `execution-issues.md`. The firm plan still mandates `agent_waterfall` bounded stderr copies, `_finalize_dropped_reviewer_round`, `run_logs.py` allowlist expansion for `dropped-*-*.txt`, `SECURITY.md`, and extra harness surface without changing whether dynamic drops count as failures or whether warnings fire. That is ~150+ lines of artifact-policy work beyond the stated acceptance criteria.
- **Proposed resolution**: Drop the firm diagnostics/run-log/SECURITY branch; keep waterfall `*.dropped-slots`, threshold `DYNAMIC_*` KVs, `progress_report` labeling from committed TSV plus `panel-manifest.ndjson`, and `review_and_fix` post-retry warning surfacing only. Treat stderr preservation as a separate follow-up issue if still wanted.
