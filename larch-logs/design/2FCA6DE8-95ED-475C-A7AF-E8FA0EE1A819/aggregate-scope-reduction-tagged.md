### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:113-114; scripts/lib-phantom-probe.sh:17-33,76-103
- **Concern**: [SCOPE-REDUCTION] Phantom plan permits porting append-execution-issue logic in B1. Scenario: The absorbed surface is phantom probing; current library delegates all execution-issue writes to append-execution-issue.sh. Porting that helper duplicates a security-sensitive markdown mutation path and expands B1 beyond the listed git/gh/ci primitives.
- **Proposed resolution**: Make probe_with_warn call existing scripts/append-execution-issue.sh via proc only; remove the "or ports it byte-identically" option and leave append-execution-issue.sh out of B1.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:85; scripts/gh-run-logs.sh:41-55; scripts/gh-run-logs.md:3-9
- **Concern**: [SCOPE-REDUCTION] gh run-logs adds redaction to a raw stdout contract. Scenario: Legacy gh-run-logs emits the pointer plus the raw last 100 lines and existing callers perform redaction where needed. Moving redaction into the migrated verb changes diagnostic output and can hide data before caller-owned processing.
- **Proposed resolution**: Keep gh run-logs parity to pointer header plus unredacted tail-100 and exits 0/1/3; keep redaction at existing downstream pipes/callers.

### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:113-114; scripts/append-execution-issue.sh:76-155
- **Concern**: [SCOPE-REDUCTION] The plan allows porting append-execution-issue.sh inside the phantom work even though B1 only absorbs lib-phantom-probe.sh and phantom-probe-with-warn.sh. Scenario: Porting the append helper expands the PR into an unrelated lock/atomic-write migration; a partial reimplementation can corrupt execution-issues.md or lose concurrent warning entries
- **Proposed resolution**: Remove the "or ports it byte-identically" option and require phantom.probe_with_warn to call the existing scripts/append-execution-issue.sh helper; defer that helper's Python migration to a separate issue

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/cli.py:14-18
- **Concern**: [SCOPE-REDUCTION] Plan mandates six new *_cli.py companions plus matching test_*_cli.py files. Scenario: docs/python-migration.md registers (domain, verb) → (module, main) directly; only report_tokens_cli.py is a multi-step CLI pipeline. Six thin argparse wrappers duplicate the dispatcher pattern and add ~12 files without changing runtime behavior
- **Proposed resolution**: Register one main(argv) per domain module (git, push, pr, gh, merge, ci_monitor) with internal subcommand dispatch; keep library logic in the typed modules and drop the six *_cli.py companions unless a domain truly needs a separate entry surface

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:98-114
- **Concern**: [SCOPE-REDUCTION] The plan creates `python/phantom.py` outside the scoped existing consolidation surfaces. Scenario: The issue scope asks consolidation into existing Python surfaces plus CLI verbs; adding a new runtime module expands architecture for two phantom/check scripts instead of using the existing `git`/checks surface the plan already exposes via `git phantom-probe`
- **Proposed resolution**: Do not add `python/phantom.py`; home the phantom parity functions in an existing in-scope module, preferably the module backing the `git` CLI verbs, unless the plan explicitly re-scopes this with justification

### FINDING_1:
- **Reviewer(s)**: Codex-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:161-167; scripts/implement-finalize.sh:398-400; scripts/timing-report.sh:42-54
- **Concern**: [SCOPE-REDUCTION] Deferred-to-E1 says it is the recursive ship-pr closure, but omits read-workflow-path even though implement-finalize calls timing-report and timing-report invokes $SCRIPT_DIR/read-workflow-path.sh. Scenario: If B1 deletes scripts/read-workflow-path.sh without repointing this ship-pr-closure edge, the legacy bash ship-pr path loses its workflow fallback; if migration_lint catches it, the plan stalls at deletion instead
- **Proposed resolution**: Add read-workflow-path to Deferred-to-E1, or explicitly require scripts/timing-report.sh to be cut over before scripts/read-workflow-path.sh is eligible for deletion
