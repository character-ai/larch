### FINDING_1: Step 6 resume hint has no documented dispatch path
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Stall Routing Contract
- **Severity**: major
- **Concern**: The plan emits `checks-commit-route-retry` for Step 6 helper exhaustion, but the stall-recovery contract explicitly excludes automatic Step 6 retry and provides no corresponding consumer. This leaves the hint unhandled and contradicts the deliberate Step-3-only asymmetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep the Step-3-only asymmetry (classification-only for Step 6, RESUME_HINT stays none), or add a Step 6 step-6-entry.sh --force-checks true re-invocation branch to stall-recovery.md item 5 and add that file to Files to modify/create
  - From Cursor-dyn-Stall Routing Contract: Add ### MAY_UPDATE stall-recovery.md documenting lint-failure helper-exhaustion retry for steps 3 and 6 with the same launchers as checks-repair-loop.md section 2


### FINDING_2: Exhaustion evidence is not propagated into classifier inputs
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Stall Routing Contract
- **Severity**: major
- **Concern**: The secondary classifier change depends on helper-exhaustion evidence, but the plan does not define or implement a production handoff from repair-loop `LOOP_STATUS=exhausted` or the attempt-cap outcome into the failure-detail, ledger, or state inputs consumed by classification. Consequently, the new branch is unreachable on the relevant stall path and may only pass through synthetic tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify how LOOP_STATUS=exhausted or a lint-fix-attempt-cap bail reason is seeded into classifier-visible BAIL_REASON or state, add a test that exercises that seeding path, or drop the _classify.py change since the primary fix already delivers the requested main-agent repair opportunity
  - From Cursor-Innovation: Either remove the classifier work (preferred minimum change) or add a minimal propagation step: on supported-site `LOOP_STATUS=exhausted` stall only, persist a stable token such as `lint-fix-attempt-cap` into classify-readable state before Step 18, and pin the emitted `MATCHED_CLASSIFIER_PATTERN` to an allowlisted value such as `lint-fix-bail-token`.
  - From Codex-Innovation: Define and implement an explicit evidence handoff, such as persisting a validated exhaustion marker in the existing ledger/state consumed by stall recovery, or remove the classifier change if no such handoff is required
  - From Cursor-Pragmatic: Either remove the classifier slice, or add an explicit persistence step (for example append `LOOP_STATUS=exhausted` to `execution-issues.md` or seed `BAIL_REASON=lint-fix-attempt-cap` on repair-loop terminal outcomes) and test that `classify_main` sees it for steps 3 and 6.
  - From Cursor-Requirements: Add an explicit plan step (or drop _classify.py changes) to persist a stable exhaustion token into classify inputs on repair-loop stall, e.g. set IMPLEMENT_BAIL_REASON=lint-fix-attempt-cap when LOOP_STATUS=exhausted before Step 18, or document that classifier changes are test-only and remove them for minimum scope
  - From Cursor-dyn-Stall Routing Contract: Either wire exhaustion markers into classify evidence on repair-loop NEXT_ACTION=stall or drop the _classify.py/_resume_hint_for work and rely on the primary main-agent-edit path


### FINDING_4: Exhausted ledger records the wrong failure log
- **Reviewer(s)**: Cursor-dyn-Stall Routing Contract
- **Severity**: major
- **Concern**: The proposed exhausted-path ledger population reuses `argv --checks-log` rather than the final redacted log produced during the helper loop. After partial helper edits, this can give the main agent stale failure details that do not reflect the current tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Stall Routing Contract: Mirror no-changes-stale only when loop.last_fix_status == no-changes; for exhausted store the final in-loop redacted path on LoopResult and populate LINT_FIX_LEDGER_FAILURE_DETAIL_LOG from that path after resolve_checks_log_path


### FINDING_1: Add the `LoopResult` owner to the file list and define the final redacted-log carrier
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan requires `run_check_fix_loop` to expose the final validated redacted failure-log path, but omits `python/larch/implement/checks_run_relevant.py`, where `LoopResult` is defined, from the files to modify/create. Without updating this dataclass, the implementation may miss the required typed state, add undocumented dynamic state, or misuse existing ledger fields, preventing `_repair_loop_action` from reliably distinguishing the final in-loop log from the original `argv --checks-log`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/implement/checks_run_relevant.py` with a new optional field (for example, `last_failed_checks_redacted_log`) set only when post-check redaction succeeds.
  - From Codex-Arch: Add `python/larch/implement/checks_run_relevant.py` as an updated file and define the dedicated final-log field and its initialization/propagation contract.
  - From Cursor-Innovation: Add ### UPDATED: python/larch/implement/checks_run_relevant.py with a new LoopResult field (for example final_redacted_checks_log) set on every exhausted terminal return in run_check_fix_loop before _repair_loop_action runs; have the exhausted ledger helper read and validate that field instead of argv --checks-log.
  - From Codex-Innovation: Add `python/larch/implement/checks_run_relevant.py` to the updated files and define the final exhausted-log field there, or specify a concrete alternative that preserves typed state without repurposing existing ledger fields
  - From Cursor-Requirements: Add ### UPDATED: python/larch/implement/checks_run_relevant.py with a LoopResult field (for example final_redacted_log_path) set in run_check_fix_loop before return; have exhausted ledger population read that field instead of argv --checks-log.


### FINDING_3: Rebind exhausted main-agent repair diagnosis to the ledger log
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The planned exhausted `main-agent-edit` path updates the ledger but does not explicitly require the orchestrator to use that ledger failure log as the repair diagnosis. The orchestrator may retain the pre-loop composite digest or input log and apply inline edits against stale failures even after routing is corrected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the planned checks-repair-loop.md update, add a normative rule under NEXT_ACTION=main-agent-edit: when LOOP_STATUS=exhausted and LINT_FIX_LEDGER_READY=true, read LINT_FIX_LEDGER_FAILURE_DETAIL_LOG (and optional STDERR_TAIL_PATH/CODER_LOG_FILE) for repair diagnosis, superseding the section 1 composite digest binding for that branch only.


