### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:7-8
- **Concern**: Plan rejects the required protected-path warning/path disclosure. Scenario: The issue asks for an operator warning that Codex hit a protected path and Main Claude will implement, plus first-detection text that clarifies the protected path name; the plan only exposes the class and explicitly says not to display the path
- **Proposed resolution**: Add the minimal operator-facing warning to the existing Step 2/Step 18a warning surface for this bail token, naming the protected path when available or the known protected surface for this case, while keeping FAILURE_CLASS=protected-path and RESUME_HINT=step2-impl


