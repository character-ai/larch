### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py:94-107
- **Concern**: LoopResult field addition is missing from the firm file list. Scenario: `LoopResult` is defined in `checks_run_relevant.py`, but the plan only lists `checks_lint_fix.py`. An implementer may add exhausted-log state only in the loop helper and miss the dataclass, breaking the stated contract to carry the final redacted log on `LoopResult`.
- **Proposed resolution**: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` with a new optional field (for example `last_failed_checks_redacted_log`) set only when post-check redaction succeeds.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1693-1700
- **Concern**: Exhausted ledger log provenance is underspecified for early exhausted exits. Scenario: When post-fix checks fail but `_redacted_log_for_dispatch` returns `None`, the loop exits with `LOOP_STATUS=exhausted` while `redacted_log_for_dispatch` still holds the pre-fix input log. Path validation alone would accept that stale file and emit `main-agent-edit`, handing the main agent failure details from before the last helper edit.
- **Proposed resolution**: Require ledger population only from a post-check log captured after the last failed checks iteration. On early exhausted exits with no such log, keep `NEXT_ACTION=stall` and omit `LINT_FIX_LEDGER_READY`. Add a `checks_repair_loop_main` test mirroring `test_run_check_fix_loop_dispatch_first_exhausted_missing_post_fix_raw_log`.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_run_relevant.py:94-110
- **Concern**: The plan requires `LoopResult` to carry a new validated final redacted-log path, but omits the dataclass owner from `Files to modify/create`. Scenario: Implementing the required state cleanly requires changing the shared `LoopResult` definition. If the implementer edits only the listed files, the final path cannot be carried through `run_check_fix_loop`; reusing `ledger_failure_detail_log` would conflict with the requirement to preserve existing `no-changes-stale` ledger behavior and to populate ledger fields only after validation.
- **Proposed resolution**: Add `python/larch/implement/checks_run_relevant.py` as an updated file and define the dedicated final-log field and its initialization/propagation contract.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: code-quality
- **Location**: python/larch/implement/checks_run_relevant.py:94-107
- **Concern**: LoopResult carrier for the final in-loop redacted log is missing from the plan file list. Scenario: The plan requires run_check_fix_loop to expose the last validated redacted failure log after helper iterations, but LoopResult is defined only in checks_run_relevant.py and has no field for that path today. Implementing solely in checks_lint_fix.py leaves no typed place to persist redacted_log_for_dispatch across exhausted returns, so _repair_loop_action cannot reliably distinguish the final log from argv --checks-log.
- **Proposed resolution**: Add ### UPDATED: python/larch/implement/checks_run_relevant.py with a new LoopResult field (for example final_redacted_checks_log) set on every exhausted terminal return in run_check_fix_loop before _repair_loop_action runs; have the exhausted ledger helper read and validate that field instead of argv --checks-log.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/checks-repair-loop.md:56-67
- **Concern**: Exhausted main-agent-edit does not bind diagnosis to the ledger failure log. Scenario: Section 1 tells the orchestrator to prefer composite DIGEST_FILE/REDACTED_LOG_FILE before repair-loop runs. Section 56 only records escalation and says "Repair via main-agent Edit/Write" without rebinding diagnosis. After LOOP_STATUS=exhausted, LINT_FIX_LEDGER_FAILURE_DETAIL_LOG can point at a newer in-loop redacted log while the orchestrator still holds the pre-loop digest/input, so inline repairs can target stale failures even when routing is fixed.
- **Proposed resolution**: In the planned checks-repair-loop.md update, add a normative rule under NEXT_ACTION=main-agent-edit: when LOOP_STATUS=exhausted and LINT_FIX_LEDGER_READY=true, read LINT_FIX_LEDGER_FAILURE_DETAIL_LOG (and optional STDERR_TAIL_PATH/CODER_LOG_FILE) for repair diagnosis, superseding the section 1 composite digest binding for that branch only.



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_run_relevant.py:94-106
- **Concern**: The planned exhausted-log handoff requires new state on `LoopResult`, but the plan omits this owner file from `Files to modify/create`. Scenario: `run_check_fix_loop` cannot expose the final validated redacted log to `_repair_loop_action` through the current `LoopResult` fields. An implementation must either modify this dataclass, use an undocumented dynamic attribute, or misuse existing ledger state, leaving the required handoff contract incomplete or fragile
- **Proposed resolution**: Add `python/larch/implement/checks_run_relevant.py` to the updated files and define the final exhausted-log field there, or specify a concrete alternative that preserves typed state without repurposing existing ledger fields



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_run_relevant.py:94-107
- **Concern**: Plan omits LoopResult home when adding final exhausted redacted-log state. Scenario: The plan requires run_check_fix_loop to expose the terminating iteration's validated redacted log for exhausted ledger population, but LoopResult is defined only in checks_run_relevant.py and the Files list updates checks_lint_fix.py alone. An implementer can miss the dataclass change or add ad hoc state that tests and type checks do not cover.
- **Proposed resolution**: Add ### UPDATED: python/larch/implement/checks_run_relevant.py with a LoopResult field (for example final_redacted_log_path) set in run_check_fix_loop before return; have exhausted ledger population read that field instead of argv --checks-log.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:1689-1700,1746-1748
- **Concern**: Exhausted ledger must not reuse prior-iteration or initial logs when the terminating check emits no redacted log. Scenario: The plan fixes initial --checks-log reuse (round-1 FINDING_4) but does not pin capture to the terminating iteration. On dispatch_first early return, loop.status can be exhausted while redacted_path is None; redacted_log_for_dispatch may still hold an older in-loop log that predates the last helper edit. Validating that stale path would hand the main agent pre-final-iteration failures.
- **Proposed resolution**: Set final_redacted_log_path only after the last failed check produces a validated redacted path (normal cap exit at 1746). On 1693-1700 exhausted exits with no new redacted log, leave the field empty so _repair_loop_action keeps NEXT_ACTION=stall with no ready ledger even if an older tmpdir log exists.



