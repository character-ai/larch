### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-load.sh:253-259
- **Concern**: Step-4 resume compatibility is missing after FINALIZE moves to Step 3b. Scenario: A design paused before this PR after .completed/step-3b but before old Step 4 ACTION=FINALIZE resumes at Step 4; the new Step 4 assumes rejected-findings.md and sibling artifacts already exist, so legacy paused runs can fail or proceed with missing finalize artifacts
- **Proposed resolution**: Add a minimal compatibility path, e.g. when restored STEP=4 and .completed/finalize is absent, route back through Step 3b completion boundary or run an idempotent finalize fallback in the Step 4 entry fence; cover this in test-design-pause-resume.sh


