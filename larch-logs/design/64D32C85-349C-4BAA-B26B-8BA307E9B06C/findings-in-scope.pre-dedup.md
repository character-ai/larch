### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review.py:841-843
- **Concern**: `--new-process-group` / `os.setsid()` failure is specified to exit 2, but `normalize_step3_status_main` treats `loop_rc==2` as a pre-envelope configuration abort. Scenario: The removed `monitor-mode-unavailable` path in `design-step3-review.sh:407-411` staged `panel-init-failed`, printed `SUMMARY_OUTCOME=failed-judge-panel`, and exited before review launch. A setsid failure leaves empty worker stdout, hits the `loop_rc==2` early return, skips `panel-init-failed` synthesis and `SUMMARY_OUTCOME` emission, and exits without `.completed/step-3-terminal`
- **Proposed resolution**: On setsid failure, emit a `panel-init-failed` stdout envelope (or call `prelaunch_failure` with reason `new-process-group-failed`) and exit 1, or have the wrapper invoke `plan-review prelaunch-failure` when `loop_rc=2` and stdout lacks review KVs; update the planned exit-2 test to match the chosen terminal contract



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review.py:841-843
- **Concern**: New --new-process-group failures short-circuit normalize-status before the existing prelaunch panel-init-failed synthesis. Scenario: The worker can exit 2 on os.setsid() failure, but the wrapper now loses the failed-judge-panel contract instead of staging panel-init-failed for a prelaunch isolation failure
- **Proposed resolution**: Route rc2 from the new flag through the same prelaunch-failure path, or teach normalize-status to classify that specific rc2 before the early return



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-step3-review.sh:570-610
- **Concern**: The proposed tests do not verify subtree teardown with a live descendant. Scenario: Removing monitor mode changes the core isolation mechanism, but the harness only checks argv text and stderr routing, so an orphaned reviewer process could regress without any test failure
- **Proposed resolution**: Add one focused integration test that spawns a long-lived child under the fake loop and asserts it dies on cap-hit or bail, with no stray descendant left behind



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review.py:841-843
- **Concern**: Removing monitor-mode-unavailable without retargeting setsid failure terminal handoff drops the existing panel-init-failed / failed-judge-panel path. Scenario: The plan removes the wrapper prelaunch branch that calls plan-review prelaunch-failure and prints SUMMARY_OUTCOME=failed-judge-panel (design-step3-review.sh:407-411). It instead has run_step3_review exit 2 when os.setsid() fails. normalize-status short-circuits on loop_rc=2 before loading .step3-review-result.env, so the wrapper exits 1 with only a generic configuration-error stderr line and no STEP3_REVIEW_LOOP_STATUS=panel-init-failed envelope or failed-judge-panel summary. That regresses the terminal semantics of the path being deleted.
- **Proposed resolution**: On setsid OSError with --new-process-group, call the existing prelaunch_failure path in-process (reason such as process-group-unavailable) to persist panel-init-failed, then exit 1. Reserve exit 2 for pure argparse misuse. Extend the planned failure test to assert .step3-review-result.env carries panel-init-failed and normalize-status emits SUMMARY_OUTCOME=failed-judge-panel, not exit 2 alone.



### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_plan_review.py
- **Concern**: The failure-handling test mixes a parent-process monkeypatch with a subprocess CLI call, so it cannot observe the injected `os.setsid()` failure it is supposed to prove.. Scenario: A regression in the new `--new-process-group` error path could ship with a false-green test, because `run_cli` will execute the real child process instead of the monkeypatched code.
- **Proposed resolution**: Keep that check in-process with `run_step3_review` and `pytest.raises(SystemExit)`, or inject the failure through an env-controlled shim that the subprocess can actually see.



### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-design-step3-review.sh:585-618
- **Concern**: Step 3 validation still stops at stderr quarantine. It does not verify that the new `--new-process-group` path actually reaps the reviewer subtree, or that the `$!` PID is the process-group leader on the target bash/macOS setup.. Scenario: The wrapper can pass the stderr checks while still leaking orphan Codex/Cursor children after normal completion, cap-hit, or bail, which leaves the core regression unfixed and the new process-group change unverifiable.
- **Proposed resolution**: Add a small integration check in the existing Step 3 harness, or an equivalent pytest, that launches a fake reviewer process tree under `--new-process-group` and asserts no descendant processes remain after each terminal path. Include an explicit macOS/bash 3.2 smoke or validation step for the `$!` to PGID assumption.



### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review.py:844-850
- **Concern**: The plan routes `--new-process-group` setup failure to exit code 2, but the current normalizer returns before writing the Step 3 terminal envelope.. Scenario: If `os.setsid()` raises, the worker exits before stdout/result env. The wrapper then calls `normalize-status --loop-rc 2`, which emits only stderr and exits. No `.step3-review-result.env` or `.completed/step-3-terminal` is written, so the Step 3 background wait can treat the completion notification as premature and stall without a final-summary handoff.
- **Proposed resolution**: Handle the new process-group setup failure as a panel-init-failed prelaunch failure. Reuse the existing terminal-envelope path so rc 2 writes/persists `STEP3_REVIEW_LOOP_STATUS=panel-init-failed`, writes the terminal sentinel, emits the failed-judge-panel summary path, and still preserves the worker's loud stderr failure in `plan-review-loop-stderr.log`.



