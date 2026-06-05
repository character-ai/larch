### FINDING_1: Shared RecordingRunner consolidation misses specialized runner APIs
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-evidence-scope-drift, Codex-dyn-evidence-scope-drift
- **Severity**: important
- **Concern**: The planned shared `RecordingRunner`/import-swap consolidation only covers simple queue/fallback runners, but several target tests rely on specialized semantics such as exact argv maps, prefix matches, sequential responses, tuple-shaped call logs, `git_commits`, and strict unexpected-call failures. A blind swap would break tests or weaken their assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Either exempt test_ci_monitor.py from consolidation (keep local stub) or extend the plan to port its keyed-runner API and update every calls assertion
  - From Codex-Arch: Keep the shared import swap limited to simple queue runners, or explicitly add exact/prefix/sequential maps, tuple call recording, and git_commits support before migrating these files.
  - From Cursor-Edge: Keep test_ci_monitor.py on its local RecordingRunner; limit test_support.py to the nine list-queue copies only
  - From Codex-Edge: Keep specialized runners local for these files, or explicitly preserve and test their current semantics before swapping them to test_support.py
  - From Cursor-Innovation: Exclude test_ci_monitor.py from consolidation or add a separate keyed stub in test_support.py
  - From Codex-Innovation: Keep these specialized runners local for minimum change, or make test_support preserve their exact APIs and update assertions deliberately
  - From Codex-Pragmatic: Either leave this local runner in place or make python/test_support.py preserve those exact/prefix/sequential and tuple-call semantics before migrating test_ci_monitor.py
  - From Cursor-Requirements: Exclude test_ci_monitor.py from cluster 4 (keep local stub) or extend the plan with a full port of its runner API before any import swap
  - From Cursor-dyn-evidence-scope-drift: Exclude test_ci_monitor.py from consolidation (keep its local runner) or narrow D to the nine compatible files and drop the “10 duplicating” count.
  - From Codex-dyn-evidence-scope-drift: For minimum change, leave specialized runners local and only dedupe identical queue/fallback copies, or specify and test exact/prefix/sequential/git_commits/strict-exhaustion behavior before importing it there


### FINDING_2: Contract JSON emission can be blocked by journal append failure
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: `emit_result` still writes the journal before the contract JSON, so a journal append failure can prevent JSON from reaching `contract_stream`, leaving callers with empty stdout despite the error envelope plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Make journaling best-effort in emit_result and always write the redacted JSON to contract_stream; suppress or breadcrumb journal write failures without changing the result exit code


### FINDING_3: RunContext branch_name constructor usage is omitted
- **Reviewer(s)**: Codex-Edge, Codex-dyn-evidence-scope-drift
- **Severity**: important
- **Concern**: The plan removes `branch_name` as a `RunContext` dataclass field but misses a fixture that still passes `branch_name="feat"`, causing `py-test` to fail with an unexpected keyword argument.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Include python/test_finalize_bash_parity.py in the migration and remove the branch_name kwarg or rely on branch plus the read-only alias property
  - From Codex-dyn-evidence-scope-drift: Add ### UPDATED: python/test_finalize_bash_parity.py and migrate the fixture to canonical branch only, or explicitly keep constructor alias compatibility


### FINDING_4: Python ship invocation drops --no-logs-commit
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The bash ship path passes `--no-logs-commit`, but the Python branch does not, so `LARCH_SHIP_PR_IMPL=python` can ignore the user flag and create log commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add --no-logs-commit "$no_logs_commit" to the Python invoke fence and pin it in scripts/test-implement-structure.sh


### FINDING_6: quiet_init before argparse hides help and usage output
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-quiet-fd-parity, Codex-dyn-evidence-scope-drift
- **Severity**: important
- **Concern**: Initializing quiet mode before argparse redirects stdout/stderr, so `--help` and parse-error usage can go to the quiet log instead of remaining caller-visible as the plan’s stream contract requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic, Codex-dyn-quiet-fd-parity: Delay quiet_init until after successful parse and ctx binding, or explicitly route argparse help/usage to contract_stream/FD4 before returning or emitting JSON
  - From Codex-dyn-evidence-scope-drift: Initialize quiet after argparse handling, or add explicit contract/diagnostic stream routing for argparse help and usage before claiming those streams stay caller-visible


### FINDING_7: Python STALLED exits may lack finalize-state stall metadata
- **Reviewer(s)**: Cursor-dyn-json-state-contract, Codex-dyn-json-state-contract
- **Severity**: important
- **Concern**: Planned Python exit-4 handling relies on `finalize-state.sh` for `STALL_TRACKING`/`STALL_STEP`, but invalid tmpdir and handled exception paths can return `STALLED` without writing that file. Step 8+/Step 18 can then see stale or missing stall metadata and misclassify or skip stall recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-json-state-contract: Call write_finalize_state(ctx.with_(stall_tracking=True, stall_step="tmpdir-invalid"), ...) before returning invalid-tmpdir STALLED, or document a JSON-only fallback and keep A1 from naming finalize-state as the sole Exit 4 stall-metadata source
  - From Codex-dyn-json-state-contract: Minimum change: in the run_ship handled-exception catch, derive the ShipResult first and, when it is STALLED and ctx.tmpdir is valid, call write_finalize_state(ctx.with_(stall_tracking=True, stall_step=<phase-or-detail>), tmpdir/finalize-state.sh); add one regression that injects a ShipError from pr.ensure_pr and asserts finalize-state has STALL_TRACKING=true### OOS_1:
- **Description**: _write_ship_state always clears RESUME_PHASE and CALLER_KIND; no Python path emits ship_pr_pre_push conflict metadata. Scenario: Pre-push rebase conflicts cannot trigger the Exit 4 RESUME_PHASE=ship-pr-rrr-phase14 / CALLER_KIND=ship_pr_pre_push handoff in skills/implement/SKILL.md:1064 on the Python driver; conflict auto-recovery remains bash-only
- **Reviewer**: Cursor-dyn-json-state-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:387-388
- **Phase**: design


