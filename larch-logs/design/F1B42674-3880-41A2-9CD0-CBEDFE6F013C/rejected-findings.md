### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-no-raw-stderr-after-quiet-init.sh:7-63
- **Concern**: Harness repoint uses undefined $CLI after LINT removal. Scenario: The plan removes LINT and repoints run_lint to python3 "$CLI" lint no-raw-stderr-after-quiet-init but never adds CLI="$REPO_ROOT/python/cli.py" or a cli.py presence preflight (unlike scripts/test-lint-literal-counts.sh and scripts/test-check-topology-rule-paths.sh). make test-lint-no-raw-stderr-after-quiet-init fails immediately with an empty CLI expansion.
- **Proposed resolution**: Add the same CLI bind and python3/cli.py preflight bullets used for the literal-counts and topology harnesses before repointing run_lint.




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:2427-2456
- **Concern**: [SCOPE-REDUCTION] Subprocess render call omits cwd=_REPO_ROOT. Scenario: Subprocess inherits capture-transcript caller cwd; if cwd is outside the repo, child cli.py or future relative-path reads can fail or resolve wrong paths even with absolute cli.py path
- **Proposed resolution**: Add cwd=str(_REPO_ROOT) to subprocess.run in capture_transcript_main alongside absolute python/cli.py and absolute --input/--output paths

