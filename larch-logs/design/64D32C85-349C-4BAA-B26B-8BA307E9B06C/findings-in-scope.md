### FINDING_1: setsid failure drops panel-init-failed terminal contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Generic
- **Severity**: important
- **Concern**: When `--new-process-group` / `os.setsid()` fails, the worker is specified to exit 2. `normalize_step3_status_main` treats `loop_rc==2` as a pre-envelope configuration abort and returns early. That skips `panel-init-failed` synthesis, `STEP3_REVIEW_LOOP_STATUS=panel-init-failed`, `SUMMARY_OUTCOME=failed-judge-panel`, `.step3-review-result.env`, and `.completed/step-3-terminal`. Removing the old `monitor-mode-unavailable` wrapper branch (which called `prelaunch-failure` and emitted `failed-judge-panel`) without retargeting setsid failure regresses the terminal semantics of the path being deleted. The Step 3 background wait may see a premature completion notification and stall without final-summary handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: On setsid failure, emit a `panel-init-failed` stdout envelope (or call `prelaunch_failure` with reason `new-process-group-failed`) and exit 1, or have the wrapper invoke `plan-review prelaunch-failure` when `loop_rc=2` and stdout lacks review KVs; update the planned exit-2 test to match the chosen terminal contract
  - From Codex-Arch: Route rc2 from the new flag through the same prelaunch-failure path, or teach normalize-status to classify that specific rc2 before the early return
  - From Cursor-Innovation: On setsid OSError with --new-process-group, call the existing prelaunch_failure path in-process (reason such as process-group-unavailable) to persist panel-init-failed, then exit 1. Reserve exit 2 for pure argparse misuse. Extend the planned failure test to assert .step3-review-result.env carries panel-init-failed and normalize-status emits SUMMARY_OUTCOME=failed-judge-panel, not exit 2 alone.
  - From Codex-Generic: Handle the new process-group setup failure as a panel-init-failed prelaunch failure. Reuse the existing terminal-envelope path so rc 2 writes/persists `STEP3_REVIEW_LOOP_STATUS=panel-init-failed`, writes the terminal sentinel, emits the failed-judge-panel summary path, and still preserves the worker's loud stderr failure in `plan-review-loop-stderr.log`.

### FINDING_2: setsid failure test cannot observe injected failure across subprocess boundary
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned failure-handling test mixes a parent-process monkeypatch with a subprocess CLI call via `run_cli`. The subprocess runs real code, not the monkeypatched `os.setsid()`, so the test cannot observe the injected failure it is meant to prove. A regression in the new `--new-process-group` error path could ship with a false-green test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep that check in-process with `run_step3_review` and `pytest.raises(SystemExit)`, or inject the failure through an env-controlled shim that the subprocess can actually see.

### FINDING_3: no integration test verifies reviewer subtree teardown or PGID leader semantics
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: blocking
- **Concern**: Removing monitor mode changes the core isolation mechanism to in-worker `os.setsid()`, but existing Step 3 validation stops at stderr quarantine and argv text checks. Nothing verifies that the reviewer subtree is actually reaped on normal completion, cap-hit, or bail, or that `$!` is the process-group leader on the target bash/macOS setup. An orphaned reviewer process or a wrong PGID assumption could regress without any test failure, leaving the core fix unverifiable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add one focused integration test that spawns a long-lived child under the fake loop and asserts it dies on cap-hit or bail, with no stray descendant left behind
  - From Codex-Requirements: Add a small integration check in the existing Step 3 harness, or an equivalent pytest, that launches a fake reviewer process tree under `--new-process-group` and asserts no descendant processes remain after each terminal path. Include an explicit macOS/bash 3.2 smoke or validation step for the `$!` to PGID assumption.
