### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:144-145
- **Concern**: public remote_branch_state must not regress finalize postbump semantics. Scenario: Plan replaces finalize._remote_branch_state with public git.remote_branch_state while adding full KV/redacted ERROR parity for check-remote-branch.sh. Prior reviews flagged ls-remote vs stale local-ref and ERROR redaction gaps
- **Proposed resolution**: A single typed helper with two surfaces: trichotomy for finalize.postbump; emit_kv STATE/RC/ERROR (redacted) for git check-remote-branch CLI; port test-implement-finalize.sh / finalize parity tests for both


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/cli.py:14-18
- **Concern**: [SCOPE-REDUCTION] Plan mandates six new *_cli.py companions plus matching test_*_cli.py files. Scenario: docs/python-migration.md registers (domain, verb) → (module, main) directly; only report_tokens_cli.py is a multi-step CLI pipeline. Six thin argparse wrappers duplicate the dispatcher pattern and add ~12 files without changing runtime behavior
- **Proposed resolution**: Register one main(argv) per domain module (git, push, pr, gh, merge, ci_monitor) with internal subcommand dispatch; keep library logic in the typed modules and drop the six *_cli.py companions unless a domain truly needs a separate entry surface


### [Plan Review] FINDING_16

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:81-82
- **Concern**: The `git-rebase-abort` row is **gap**, yet `_abort_rebase` already exists and propagates `git rebase --abort` failures.. Scenario: `scripts/git-rebase-abort.sh` always exits 0 (`|| true`); reusing `_abort_rebase` for the CLI would regress conflict-resolution callers expecting idempotency.
- **Proposed resolution**: Call out in the gap row that `_abort_rebase` is ship-only; add a new idempotent `rebase_abort` that swallows all failures before `git_cli` wraps it.


### [Plan Review] FINDING_18

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-parity-map
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/rebase.py:45-69
- **Concern**: The `git-sync-local-main` **gap** row omits that `_sync_local_main` already exists with a ship contract.. Scenario: It raises `Stalled` on `main` and emits no `RESULT=updated|absent|already_current`; porting the bash script by calling `_sync_local_main` would break KV/exit parity.
- **Proposed resolution**: Note in the gap row that `_sync_local_main` is not the backing; implement new `sync_local_main` returning `RESULT` and exit 0/1 per `scripts/git-sync-local-main.sh`.


### [Plan Review] FINDING_22

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-parity-map
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:98-114
- **Concern**: [SCOPE-REDUCTION] The plan creates `python/phantom.py` outside the scoped existing consolidation surfaces. Scenario: The issue scope asks consolidation into existing Python surfaces plus CLI verbs; adding a new runtime module expands architecture for two phantom/check scripts instead of using the existing `git`/checks surface the plan already exposes via `git phantom-probe`
- **Proposed resolution**: Do not add `python/phantom.py`; home the phantom parity functions in an existing in-scope module, preferably the module backing the `git` CLI verbs, unless the plan explicitly re-scopes this with justification


### [Plan Review] FINDING_25

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-deletion-gate
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:161-167; scripts/implement-finalize.sh:398-400; scripts/timing-report.sh:42-54
- **Concern**: [SCOPE-REDUCTION] Deferred-to-E1 says it is the recursive ship-pr closure, but omits read-workflow-path even though implement-finalize calls timing-report and timing-report invokes $SCRIPT_DIR/read-workflow-path.sh. Scenario: If B1 deletes scripts/read-workflow-path.sh without repointing this ship-pr-closure edge, the legacy bash ship-pr path loses its workflow fallback; if migration_lint catches it, the plan stalls at deletion instead
- **Proposed resolution**: Add read-workflow-path to Deferred-to-E1, or explicitly require scripts/timing-report.sh to be cut over before scripts/read-workflow-path.sh is eligible for deletion


