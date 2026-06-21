### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:2427-2456
- **Concern**: [SCOPE-REDUCTION] Subprocess render call omits cwd=_REPO_ROOT. Scenario: Subprocess inherits capture-transcript caller cwd; if cwd is outside the repo, child cli.py or future relative-path reads can fail or resolve wrong paths even with absolute cli.py path
- **Proposed resolution**: Add cwd=str(_REPO_ROOT) to subprocess.run in capture_transcript_main alongside absolute python/cli.py and absolute --input/--output paths
