### [Plan Review] FINDING_5

### FINDING_5: Plan expands sentinel churn beyond the stated pure-LLM folding scope
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The proposed plan changes sentinel boundaries for later non-feature steps in addition to the named pure-LLM fold targets. That broadens pause/resume state-machine risk beyond what is needed for the stated acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Limit this PR to the named discussion/2a.4 folds plus required pause-load and Step 5c pause-check fixes; leave later sentinel hosts unchanged or split them into a separate follow-up.


