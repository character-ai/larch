### [Plan Review] FINDING_51

### FINDING_51:
- **Reviewer(s)**: Cursor-Requirements, Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:102 scripts/ship-pr.sh:827-867
- **Concern**: HEAD re-check between helper iterations is described as an existing ship-pr pattern.. Scenario: run_checks_with_lint_fix_loop has no git rev-parse between attempts; only lint-fix-loop checks after dispatch.
- **Proposed resolution**: Concurrent pushes could slip between command reruns without the claimed guard. Implement an explicit HEAD compare at the start of each helper iteration or drop the existing wording.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan:L101-103 scripts/ship-pr.sh:795-871
- **Concern**: HEAD guard described as existing ship-pr pattern between iterations. Scenario: run_checks_with_lint_fix_loop has no HEAD compare across attempts; only lint-fix-loop.sh post-dispatch does
- **Proposed resolution**: Attribute to lint-fix-loop.sh:272-275 or specify new explicit rev-parse checks in run_captured_cmd_then_fix_loop


### [Plan Review] FINDING_66

### FINDING_66:
- **Reviewer(s)**: Cursor-dyn-fd3-capture
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:21
- **Concern**: Phrases default stdout via FD-3 emit. Scenario: Readers may think post-init POSIX stdout carries KV lib-quiet contract is caller-visible stream duped to FD3 before FD1 moves to the log scripts/lib-quiet.md:14-19 scripts/lib-quiet.sh:70-75
- **Proposed resolution**: In ci-failed-jobs.md say contract lines are emitted on the preserved caller-visible FD after larch_quiet_init not on the quiet log FD1


### [Plan Review] FINDING_69

### FINDING_69:
- **Reviewer(s)**: Cursor-dyn-eval-injection
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/ci-failed-jobs.sh (planned; plan.txt job-name/TSV section)
- **Concern**: Tab-separated `--output-tsv` rows include raw `JOB_NAME` without delimiter escaping. Scenario: A job `.name` containing a literal tab (or other workflow-controlled oddity) splits into extra columns when `run_per_job_local_fix_loop` parses the TSV, so a `fixable` row can pick up the wrong `LOCAL_CMD` field and later drive `eval`
- **Proposed resolution**: Reject or normalize fields (strip/replace `\t` `\n` `\r`; or emit ASCII RS/FS; or JSON-lines instead of TSV); add a harness case with embedded tab in `.name`


### [Plan Review] FINDING_75

### FINDING_75:
- **Reviewer(s)**: Codex-dyn-make-probe-reliability
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: Makefile:40-79; docs/linting.md:40-44,135-142; <TMPDIR>/plan.txt:80,101-103
- **Concern**: Full-matrix fallback can repeat per failed shard because the per-job loop does not deduplicate identical LOCAL_CMD values. Scenario: Current Makefile has explicit test-harnesses-1 through test-harnesses-20 rules and make -n missing targets returns 2, so fallback is not used for today's shards; under shard-count drift or a false probe, many failed matrix rows could each run make test-harnesses up to 3 times within one outer attempt and again across three outer attempts
- **Proposed resolution**: Deduplicate per-job commands before execution, coalesce all test-harnesses fallback rows into one run, and cap full-matrix fallback to once per outer attempt or bail on shard drift after one diagnostic


