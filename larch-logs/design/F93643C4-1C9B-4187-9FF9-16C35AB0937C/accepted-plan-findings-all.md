### FINDING_1: Structure harness still pins Read-tool Step 17 delivery and forbids Bash re-emission
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The plan switches Step 17 to marker-based extraction from captured wrapper stdout, but `scripts/test-implement-structure.sh` lines 231–234 still require Read-tool Step 17 prose and forbid Bash-output re-emission (`Do NOT use a Bash cat...`, `forbid(...via Bash cat whose output is then re-emitted...)`). A correct implementation can still fail `make test-implement-structure` / CI because structural pins contradict the new emission contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `scripts/test-implement-structure.sh` updates: replace lines 232-234 with pins for marker literals, marker-extraction orchestrator prose, and no Read-tool Step 17 primary path; align `scripts/test-render-cost-line-callsites.sh` Step 17 prose checks similarly
  - From Cursor-Innovation: Extend the planned `scripts/test-implement-structure.sh` edits to retire lines 231-234 and pin the new contract: balanced `---LARCH-SUMMARY-FINAL-BEGIN---`/`---LARCH-SUMMARY-FINAL-END---` extraction, orchestrator verbatim re-emission, and no Step 17 Read fallback
  - From Cursor-Pragmatic: Add explicit plan steps to replace lines 231-234 with pins for marker literals, first balanced pair extraction prose, no Read on Step 17 primary path, and retained Step 18b Read fallback
  - From Cursor-Requirements: Add explicit harness edits: replace those pins with marker-extraction requirements (first balanced `---LARCH-SUMMARY-FINAL-BEGIN---`/`---LARCH-SUMMARY-FINAL-END---` pair from captured output, orchestrator plain-chat re-emission, no Read on Step 17 primary path) and drop the old Bash-cat forbid pin


### FINDING_3: Wrapper best-effort chain lacks pinned non-aborting shell semantics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: Step 16, Slack, and Step 17 must remain best-effort and never block final-report emission or anti-halt continuation to Step 18, but the composed wrapper lacks an explicit errexit / exit-code contract. Unspecified `set -e` / `set -euo pipefail`, redirect failures, or non-zero exits on handled failures can abort the chain and skip final report, stall recovery, or teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin best-effort shell behavior in `step-16-17.sh`/`step-16-17.md`: `set +e` for the chain or guarded calls with `|| true` on Step 16, Slack, and Warnings append; wrapper should still reach Step 17 on Slack failure
  - From Cursor-Innovation: Document and implement `step-16-17.sh` to exit 0 on all best-effort failure paths (match current Step 16/16a/17 semantics); only use non-zero for unrecoverable wrapper/setup faults


### FINDING_5: NEVER #17 and Step 17 cost provenance still describe Read / `--print-stdout` active path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: After SKILL.md adopts marker extraction, NEVER #17 and the Step 17 cost-line sentence still cite Read-tool emission and `final-report write --print-stdout` as the active path. That conflicts with the wrapper/marker contract and confuses orchestrators and reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Explicitly rewrite NEVER #17 “How to apply” and the Step 17 cost-line sentence to name `step-16-17.sh`, marker extraction, and `final-report write` without `--print-stdout` on the active path; keep Step 18b Read fallback unchanged


### FINDING_6: Slack failure log append lacks required redaction
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The planned Slack failure log append to `execution-issues.md` is not required to redact captured output. That file flows into committed run logs, so webhook or token-like text surfaced by the Slack helper can be preserved without the existing append-failure redaction backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add --redact to the Slack run-log append-failure call and keep the fix limited to that append path


### FINDING_7: Step 17 orchestrator gate prose still keys on per-script success after fence collapse
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: After three fences merge into `step-16-17.sh`, the orchestrator only sees combined stdout. Leftover prose such as “if the script succeeded” and “On non-zero exit from the Step 17 … write call” misroutes emission and conflicts with marker-based handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit SKILL.md cleanup item: replace success/non-zero Step 17 wrapper semantics with marker-presence rules and document that internal Step 17 failures are logged inside the composed wrapper while the outer fence still continues to Step 18




### FINDING_1: Stale summary can emit when Step 17 render fails
- **Reviewer(s)**: Cursor-Arch, Codex-Generic
- **Severity**: important
- **Concern**: Marker emission is gated only on non-empty `summary-final.md`, not on Step 17 render success. If `final-report write` fails before rewriting `summary-final.md` (for example invalid `RUN_ID` at `python/pr_body.py:944-945`) but a prior non-empty `summary-final.md` remains from an earlier ship `final-report write`, the wrapper can still print markers and SKILL.md can tell the orchestrator to emit and write `.step17-emitted`. That may surface a stale terminal summary and suppress Step 18b refresh because `.step17-emitted` is already set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Capture `step-17.sh --no-print-stdout` exit code before the best-effort `|| true`; print markers only when that rc is 0 and `summary-final.md` is non-empty. If upsert failures after a successful body write should still hand off, have `step-17` exit 0 when the body was persisted even when tracking upsert fails
  - From Codex-Generic: Capture `step-17.sh --no-print-stdout` exit code before the best-effort `|| true`; print markers only when that rc is 0 and `summary-final.md` is non-empty. If upsert failures after a successful body write should still hand off, have `step-17` exit 0 when the body was persisted even when tracking upsert fails




### FINDING_2: Handoff exit 0 after stamp/upsert failure drops Tool Failures logging
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The planned handoff may let `step-17.sh --no-print-stdout` exit 0 when `summary-final.md` was refreshed even if stamp or tracking upsert fails. `step-17.sh` today only appends Tool Failures on non-zero `final-report write` rc. Stamp/upsert failures would then be silent in `execution-issues.md` while markers still emit. In `python/pr_body.py`, `write_final_report` can return non-zero for stamp or upsert failure after writing `summary-final.md`; a wrapper that treats “file refreshed” as success would hide those errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In --no-print-stdout mode, when final-report write returns 0 for handoff but ERROR/status KVs or stderr indicate stamp or upsert failure, append a Warnings or Tool Failures entry before exiting 0; or keep non-zero rc and rely solely on the shell snapshot gate only when Python is unchanged.


### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/pr_body.py:988-1026
- **Concern**: [SCOPE-REDUCTION] Global write_final_report rc softening is optional and widens caller contracts. Scenario: The plan marks python/pr_body.py rc narrowing as optional yet still lists it. Returning 0 after summary.write_text when stamp or tracking upsert fails changes behavior for run_logs._write_final_report (python/run_logs.py:1117-1122), write_final_report_main STATUS= KV emission, and step18b WFR_RC. Ship/finalization paths that today fail closed on upsert failure would continue with STATUS=ok while GitHub comment update failed
- **Proposed resolution**: Omit python/pr_body.py and python/test_pr_body.py from this PR. Rely on the already-required step-17.sh --no-print-stdout snapshot handoff exit (plan lines 66-72) to exit 0 only when summary-final.md bytes changed this invocation; keep Python rc unchanged for other callers


### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:87-97
- **Concern**: [SCOPE-REDUCTION] python/pr_body.py is listed under mandatory Files to modify/create while Approach calls the same change optional but preferred. Scenario: Implementers treat Python rc narrowing as required scope, adding pr_body.py and test_pr_body.py churn when step-17.sh --no-print-stdout snapshot handoff already satisfies acceptance for post-persist upsert/stamp failures
- **Proposed resolution**: Remove python/pr_body.py and python/test_pr_body.py from this PR file list; keep shell snapshot exit semantics in step-17.sh as the sole handoff contract unless a follow-up issue opts into Python rc changes


### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/pr_body.py:988-1026; skills/implement/scripts/write-final-report.md:54-59; skills/implement/scripts/test-write-final-report.sh:163-171
- **Concern**: [SCOPE-REDUCTION] Proposed python/pr_body.py rc change makes post-persist stamp or tracking-upsert failures return success, which changes the existing final-report CLI failure contract. Scenario: The plan says Step 17 failures still use the Tool Failures append path, but changing final-report write to rc 0 means step-17.sh will not take its existing non-zero logging branch. It also conflicts with the documented and tested upsert-failure contract that expects STATUS=failed and non-zero exit
- **Proposed resolution**: Do not change python/pr_body.py rc semantics for this feature. Keep final-report write returning non-zero on stamp/upsert failure. Implement the new handoff only in step-17.sh --no-print-stdout: capture the non-zero rc, append the existing Tool Failures entry, then exit 0 for wrapper handoff only when summary-final.md was refreshed this invocation


