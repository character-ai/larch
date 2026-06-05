### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:43-75
- **Concern**: RecordingRunner is argv-keyed (dict/prefix/sequential), not a list queue; plan lists import swap only. Scenario: Shared test_support.py cannot drop in; ~1600 lines of ci_monitor tests break on lookup semantics and tuple-shaped runner.calls assertions
- **Proposed resolution**: Either exempt test_ci_monitor.py from consolidation (keep local stub) or extend the plan to port its keyed-runner API and update every calls assertion

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_support.py (new); python/test_ci_monitor.py:43-77; python/test_run_logs.py:28-52
- **Concern**: Shared RecordingRunner contract does not cover runners that the plan says are import-swap only. Scenario: test_ci_monitor depends on exact/prefix/sequential response maps and tuple-shaped calls; test_run_logs depends on git_commits. The proposed helper only promises a response queue/default fallback, so the import swaps would break or require hidden extra rewrites.
- **Proposed resolution**: Keep the shared import swap limited to simple queue runners, or explicitly add exact/prefix/sequential maps, tuple call recording, and git_commits support before migrating these files.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:67-69,108-110
- **Concern**: Shared RecordingRunner swap includes test_ci_monitor.py but that file uses a dict/prefix/sequential stub that raises AssertionError on misses, not the list-queue helper the plan defines. Scenario: Blind import swap breaks the entire ci_monitor suite (~1600 lines) or forces a bloated test_support that violates the minimum-change cluster
- **Proposed resolution**: Keep test_ci_monitor.py on its local RecordingRunner; limit test_support.py to the nine list-queue copies only

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:680-685
- **Concern**: Contract JSON emission still depends on journal append succeeding. Scenario: A deleted or unwritable tmpdir, or a race during result emission, can make JsonlJournal.append raise before the JSON reaches contract_stream, leaving Step 8+ with empty stdout despite the proposed error envelope
- **Proposed resolution**: Make journaling best-effort in emit_result and always write the redacted JSON to contract_stream; suppress or breadcrumb journal write failures without changing the result exit code

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_finalize_bash_parity.py:25-40
- **Concern**: Alias-field removal misses a RunContext constructor. Scenario: The plan removes branch_name as a dataclass field, but this parity test still constructs RunContext(branch_name="feat"), so make py-test fails with an unexpected keyword after the proposed change
- **Proposed resolution**: Include python/test_finalize_bash_parity.py in the migration and remove the branch_name kwarg or rely on branch plus the read-only alias property

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/test_ci_monitor.py:43-76; python/test_run_logs.py:27-49
- **Concern**: Shared RecordingRunner import swap collapses specialized test-runner semantics. Scenario: ci_monitor tests rely on keyed, prefix, sequential responses and fail-closed unexpected argv; run_logs tests rely on git_commits and default success after queued responses. A queue-only shared helper either breaks these tests or weakens their regression checks
- **Proposed resolution**: Keep specialized runners local for these files, or explicitly preserve and test their current semantics before swapping them to test_support.py

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ci_monitor.py:43-77
- **Concern**: RecordingRunner is argv-keyed not list-based. Scenario: Plan says import-swap only; replacing with list-queue test_support.RecordingRunner breaks every ci_monitor test
- **Proposed resolution**: Exclude test_ci_monitor.py from consolidation or add a separate keyed stub in test_support.py

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1009-1024,1040
- **Concern**: FINDING_1: Python ship invocation still drops --no-logs-commit. Scenario: The bash branch passes --no-logs-commit, but the Python branch does not; a LARCH_SHIP_PR_IMPL=python run can overwrite NO_LOGS_COMMIT=false in ship-pr-state.sh and create log commits despite the user flag
- **Proposed resolution**: Add --no-logs-commit "$no_logs_commit" to the Python invoke fence and pin it in scripts/test-implement-structure.sh

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1050-1062
- **Concern**: FINDING_2: Python exit-3 CI-fix path can re-enter bash. Scenario: The shared autonomous CI-fix sub-procedure ends with "Re-invoke ship-pr.sh"; after a Python driver exit-3, a successful main-agent CI fix would switch implementation paths mid-run
- **Proposed resolution**: Make the re-invoke text selector-aware, e.g. re-run the same Step 8+ Invoke branch, and add a structure pin for the Python path

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_ci_monitor.py:43-78, python/test_run_logs.py:28-48
- **Concern**: FINDING_3: Shared RecordingRunner plan omits specialized runner contracts. Scenario: test_ci_monitor needs keyed, prefix, sequential responses and tuple calls; test_run_logs needs git_commits. An import-only swap to the described queue/fallback helper will break tests or weaken assertions
- **Proposed resolution**: Keep these specialized runners local for minimum change, or make test_support preserve their exact APIs and update assertions deliberately

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-quiet-fd-parity
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ship.py:755-759
- **Concern**: Planned quiet_init before argparse conflicts with the plan's help and usage contracts. Scenario: quiet_init redirects fd1 and fd2 by default, so argparse --help and parse-error usage go to the quiet log instead of caller-visible stdout/stderr
- **Proposed resolution**: Delay quiet_init until after successful parse and ctx binding, or explicitly route argparse help/usage to contract_stream/FD4 before returning or emitting JSON

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/test_ci_monitor.py:43-75
- **Concern**: Shared RecordingRunner spec omits the ci_monitor runner API. Scenario: The plan says test_ci_monitor.py is an import swap only, but its runner needs exact response maps, prefix responses, sequential responses, tuple call logs, and strict unexpected-argv failures
- **Proposed resolution**: Either leave this local runner in place or make python/test_support.py preserve those exact/prefix/sequential and tuple-call semantics before migrating test_ci_monitor.py

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:67-69,104-106; python/test_ci_monitor.py:42-77
- **Concern**: RecordingRunner consolidation includes test_ci_monitor.py but only lists import swap. Scenario: That file uses dict/prefix/sequential argv-keyed stub with tuple calls and AssertionError on misses, not the list-queue helper the plan defines
- **Proposed resolution**: Exclude test_ci_monitor.py from cluster 4 (keep local stub) or extend the plan with a full port of its runner API before any import swap

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-json-state-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1045-1065
- **Concern**: A1/A2 omit the shared post-invoke exit matrix that still mandates ship-pr-state reads and ship-pr.sh re-invocation. Scenario: After A1 edits the Python selector (~955), the orchestrator still follows 1045-1065: unconditional read of ship-pr-state.sh, Exit 0/3/6 bullets re-invoke ship-pr.sh, Exit 4 reads STALL_* from ship-pr-state — breaking LARCH_SHIP_PR_IMPL=python loops (OOS resume, transient retry, CI-fix) despite the selector already naming python3 ship.py for oos-filing
- **Proposed resolution**: Extend A1 to branch 1045-1067 explicitly (parse instruction, Exit 0/3/4/6 bullets, OOS checkpoint fork-flag reads) for python vs bash; add A2 greps for python re-invoke targets on Exit 0 and Exit 6, not only exit-code mapping pins

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-json-state-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:454-455
- **Concern**: skills/implement/SKILL.md A1 (planned) routes Exit 4 STALL_TRACKING/STALL_STEP from finalize-state.sh, but invalid-tmpdir STALLED returns without write_finalize_state. Scenario: Orchestrator exit 4 reads stale/missing finalize-state (STALL_TRACKING still false from pre-invoke ship-pr-state seed); Step 18 stall rename/classification can treat a hard tmpdir rejection as non-stall
- **Proposed resolution**: Call write_finalize_state(ctx.with_(stall_tracking=True, stall_step="tmpdir-invalid"), ...) before returning invalid-tmpdir STALLED, or document a JSON-only fallback and keep A1 from naming finalize-state as the sole Exit 4 stall-metadata source

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-json-state-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:88-97, python/ship.py:352-389, python/ship.py:667-668, python/finalize.py:344-368, scripts/lib-finalize-state-keys.sh:37-60
- **Concern**: Planned Python exit-4 routing relies on finalize-state.sh for STALL_TRACKING/STALL_STEP, but handled ShipError/Stalled exceptions can still return STALLED without writing that file and ship-pr-state.sh lacks stall fallback keys. Scenario: If pr.ensure_pr or another phase raises ShipError after a PHASE write, run_ship returns outcome STALLED/exit 4; Step 8+ reads finalize-state for stall data, restore-finalize-state defaults missing STALL_TRACKING to false, and Step 18 can skip stall recovery or cleanup/rename as non-stalled
- **Proposed resolution**: Minimum change: in the run_ship handled-exception catch, derive the ShipResult first and, when it is STALLED and ctx.tmpdir is valid, call write_finalize_state(ctx.with_(stall_tracking=True, stall_step=<phase-or-detail>), tmpdir/finalize-state.sh); add one regression that injects a ShipError from pr.ensure_pr and asserts finalize-state has STALL_TRACKING=true

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-evidence-scope-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ci_monitor.py:42-77
- **Concern**: RecordingRunner is not a duplicate of the nine list/queue stubs. Scenario: Plan D treats test_ci_monitor.py as import-swap-only into test_support.py, but its runner uses dict/prefix/sequential argv matching and raises AssertionError on misses (lines 68-77), not the shared queue-plus-default fallback API. Swapping imports breaks ~1600 lines of CI monitor tests or forces a heavyweight superset helper.
- **Proposed resolution**: Exclude test_ci_monitor.py from consolidation (keep its local runner) or narrow D to the nine compatible files and drop the “10 duplicating” count.

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-evidence-scope-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_finalize_bash_parity.py:26-44; python/run_context.py:27-58
- **Concern**: Plan removes the RunContext branch_name field but omits this constructor call from the update list. Scenario: After branch_name becomes a read-only property, RunContext(..., branch_name="feat") raises TypeError during py-test
- **Proposed resolution**: Add ### UPDATED: python/test_finalize_bash_parity.py and migrate the fixture to canonical branch only, or explicitly keep constructor alias compatibility

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-evidence-scope-drift
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/test_ci_monitor.py:42-77,576-583; python/test_run_logs.py:27-52,91-105; python/test_gh.py:42-45; python/test_push.py:43-45
- **Concern**: Planned shared RecordingRunner is narrower than existing runner contracts. Scenario: A simple calls plus queue plus fallback helper breaks ci_monitor exact/prefix/sequential responses, drops run_logs git_commits assertions, or weakens gh/push no-response failures
- **Proposed resolution**: For minimum change, leave specialized runners local and only dedupe identical queue/fallback copies, or specify and test exact/prefix/sequential/git_commits/strict-exhaustion behavior before importing it there

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-evidence-scope-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/ship.py:680-685,755-768; scripts/lib-quiet.sh:73-78,158-163
- **Concern**: B1 help/usage stream contract conflicts with B4 quiet_init at the top of main. Scenario: After quiet_init redirects fd1/fd2, argparse --help and parse-error usage go to the quiet log; only emit_result is planned to route to fd3
- **Proposed resolution**: Initialize quiet after argparse handling, or add explicit contract/diagnostic stream routing for argparse help and usage before claiming those streams stay caller-visible

### OOS_1:
- **Description**: _write_ship_state always clears RESUME_PHASE and CALLER_KIND; no Python path emits ship_pr_pre_push conflict metadata. Scenario: Pre-push rebase conflicts cannot trigger the Exit 4 RESUME_PHASE=ship-pr-rrr-phase14 / CALLER_KIND=ship_pr_pre_push handoff in skills/implement/SKILL.md:1064 on the Python driver; conflict auto-recovery remains bash-only
- **Reviewer**: Cursor-dyn-json-state-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ship.py:387-388
- **Phase**: design
