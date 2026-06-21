### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-no-raw-stderr-after-quiet-init.sh:7-63
- **Concern**: Harness repoint uses undefined $CLI after LINT removal. Scenario: The plan removes LINT and repoints run_lint to python3 "$CLI" lint no-raw-stderr-after-quiet-init but never adds CLI="$REPO_ROOT/python/cli.py" or a cli.py presence preflight (unlike scripts/test-lint-literal-counts.sh and scripts/test-check-topology-rule-paths.sh). make test-lint-no-raw-stderr-after-quiet-init fails immediately with an empty CLI expansion.
- **Proposed resolution**: Add the same CLI bind and python3/cli.py preflight bullets used for the literal-counts and topology harnesses before repointing run_lint.
