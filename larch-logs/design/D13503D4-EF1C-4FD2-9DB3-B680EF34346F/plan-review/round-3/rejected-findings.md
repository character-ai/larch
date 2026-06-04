### [Plan Review] FINDING_4

### FINDING_4: Plan may not deliver the requested Step 3 turn reduction
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The feature request says the preview should become the first action inside `run-step3-review.sh` and remove the separate preview turn, but the plan keeps a separate live preview-only driver fence. That transfers sentinel ownership without necessarily reducing per-entry Step 3 turns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Revise the Phase 2 acceptance to say turn reduction is explicitly deferred, or implement a single driver invocation that streams the preview before review without a second Step 3 fence


