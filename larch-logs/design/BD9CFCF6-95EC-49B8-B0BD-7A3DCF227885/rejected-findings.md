### [Plan Review] FINDING_4

### FINDING_4: Ready-to-commit stall wiring lacks explicit stdout capture contract
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The Step 5 resume handoff in `SKILL.md` does not require the orchestrator to capture `step-5-resume.sh` stdout before continuing. Background fence output may not be bound before Step 6, so `resume-handoff-commit-failed` routing can be skipped silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require orchestrator to capture step-5-resume.sh stdout and parse COMMITTED ERROR SHA STEP5_REVIEW_STATUS from that capture before continuing


