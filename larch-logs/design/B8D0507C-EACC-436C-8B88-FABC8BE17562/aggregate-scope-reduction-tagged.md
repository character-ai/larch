### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/render-review-phase-detail.sh; python/progress_report.py:365-379
- **Concern**: [SCOPE-REDUCTION] Unconditional Gantt rendering in the shared renderer leaks Mermaid blocks into progress-report callers despite the plan excluding progress-report behavior. Scenario: python/progress_report.py shells out to scripts/render-review-phase-detail.sh without any suppression flag and only strips simple Markdown; after the proposed renderer change, live /design or /implement progress output can include Gantt headings, code fences, and task lines even though charts are supposed to live only in final summary notes and the plan says not to change progress-report behavior
- **Proposed resolution**: Add an explicit suppression path, for example a --no-gantt flag passed by python/progress_report.py, or otherwise filter the new Gantt sections before terminal output; keep final-summary callers rendering charts and add one focused regression for progress output
