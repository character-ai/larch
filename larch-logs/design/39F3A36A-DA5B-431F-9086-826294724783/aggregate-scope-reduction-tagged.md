### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: README.md:291-298
- **Concern**: [SCOPE-REDUCTION] Firm README.md and docs/skills.md updates are outside binding issue surfaces. Scenario: Binding scope lists only `python/analyze_issues.py`, `.claude/skills/analyze-issues/SKILL.md`, and `docs/point-competition.md`. Duplicate verdict-flag synopsis in README and docs/skills.md adds maintenance without changing verdict correctness or the committed artifact path (prior FINDING_14 rejection still applies).
- **Proposed resolution**: Drop `### UPDATED: README.md` and `### UPDATED: docs/skills.md` from the firm plan; keep operator-facing verdict docs in the skill and `docs/point-competition.md` only.

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:197-199
- **Concern**: [SCOPE-REDUCTION] Keep the severity slice verdict-only; adding it to normal diagnostic reports is extra surface area the capstone feature does not need.. Scenario: Normal /analyze-issues output changes even when --ground-truth-verdict is off, so the plan adds churn and new test burden without restoring a broken path.
- **Proposed resolution**: Gate the severity slice behind verdict mode, and leave the existing diagnostic report unchanged.
