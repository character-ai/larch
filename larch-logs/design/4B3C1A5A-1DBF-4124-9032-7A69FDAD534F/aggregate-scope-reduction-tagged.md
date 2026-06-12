### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/audit_runs.py:323-324
- **Concern**: [SCOPE-REDUCTION] Plan tells scan-run to duplicate terminal-outcome suffixes from scripts/run-log-terminal-outcomes.inc.bash while python/run_logs.py:41-43 already defines the same regex for verify-completeness bail gating. Scenario: Three copies (inc.bash, run_logs, audit_runs) can drift; audit required-file bail skips and run-log verify-completeness can disagree on the same run dir
- **Proposed resolution**: Import or re-export the existing constant from python/run_logs.py (or one shared module) instead of duplicating the inc.bash pattern in audit_runs.py

### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:41-43,397-428,615-620,847-849
- **Concern**: [SCOPE-REDUCTION] The plan adds, tests, documents, and retires `combine-issues search-implementing`, but the scoped combine migration names only `fetch-combinable-issues.sh` and `apply-combination.sh`.. Scenario: This expands a SIMPLE migration into the OOS actuality-check path and adds a new CLI contract not required for the specified combine fetch/apply cutover.
- **Proposed resolution**: Drop `combine-issues search-implementing` from this plan, keep `.claude/skills/combine-issues/scripts/search-implementing-issue.sh` and its SKILL.md call unchanged, and leave that helper for a separate scoped migration if needed.

### FINDING_2:
- **Reviewer(s)**: Codex-dyn-contract-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/audit-runs/scripts/audit-scan-run.sh:132-155; .claude/skills/audit-runs/scripts/audit-scan-run.md:45-49
- **Concern**: [SCOPE-REDUCTION] Planned oos_disposition git-log fallback expands audit scan inline-triage evidence. Scenario: audit-scan-run currently returns inline_triage_hits=0 when run-local codex-commit-message.txt or session-transcript.jsonl is absent; adding a git-log fallback can change oos-silent-drop NDJSON from fail to pass and alter inline_triage_hits
- **Proposed resolution**: Remove the git-log fallback from the audit scan port; keep git-log counting only in the retained runtime gate path unless a separate contract change is approved
