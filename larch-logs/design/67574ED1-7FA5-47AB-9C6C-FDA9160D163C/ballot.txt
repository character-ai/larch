### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:24-32
- **Concern**: [SCOPE-REDUCTION] Plan adds `_capture_stdout_stderr` and in-process `design_oos.*_main` calls though Bash already isolates prepare/annotate via `python3 cli.py design file-oos-{prepare,annotate}` subprocess with stdout/stderr redirection. Scenario: New helper plus crash-path tests duplicate a boundary Bash already has; in-process calls need exception swallowing that subprocess gets for free
- **Proposed resolution**: Keep orchestration in `step5b_*_main` but invoke existing CLI verbs with `subprocess.run` (stdout to `oos-filing-*.env` / capture file, stderr to `oos-filing-*.stderr.log`) and delete `_capture_stdout_stderr` plus callable-crash tests

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step5b_annotate_main
- **Concern**: Annotate plan references oos_issue_stdout without defining it. Scenario: In step5b_annotate_main the --issue-stdout-file argument is built from oos_issue_stdout but the plan never binds it to design_tmpdir / "oos-issue.stdout.txt" (skills/design/scripts/design-step5b-annotate.sh:91). An implementer can NameError or pass the wrong path so ISSUES_FAILED detection and annotate I/O diverge from Bash.
- **Proposed resolution**: Add oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt" immediately after the tmpdir guard and pass str(oos_issue_stdout) to file_oos_annotate_main and to the ISSUES_FAILED grep on failure.
