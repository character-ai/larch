### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:24-32
- **Concern**: [SCOPE-REDUCTION] Plan adds `_capture_stdout_stderr` and in-process `design_oos.*_main` calls though Bash already isolates prepare/annotate via `python3 cli.py design file-oos-{prepare,annotate}` subprocess with stdout/stderr redirection. Scenario: New helper plus crash-path tests duplicate a boundary Bash already has; in-process calls need exception swallowing that subprocess gets for free
- **Proposed resolution**: Keep orchestration in `step5b_*_main` but invoke existing CLI verbs with `subprocess.run` (stdout to `oos-filing-*.env` / capture file, stderr to `oos-filing-*.stderr.log`) and delete `_capture_stdout_stderr` plus callable-crash tests


