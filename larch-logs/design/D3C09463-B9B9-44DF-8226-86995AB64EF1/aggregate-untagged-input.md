### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh
- **Concern**: Step 3 launch-time identity capture must use the shared Python helper, not Bash-side ps/JSON. Scenario: The plan says to move retained-pid checks into Python, but also has Bash write the loop-identity sidecar right after `_loop_pid=$!` without a pinned write verb. Bash capture can diverge from `process_identity.py` normalization, so trap teardown may fail closed and leave a live loop running after EXIT, or compare against a different signature shape than `/implement` uses.
- **Proposed resolution**: Add a pinned write path (e.g. `plan-review write-loop-identity --design-tmpdir … --pid "$_loop_pid"`) implemented in Python via `process_identity.py`, called immediately after `_loop_pid=$!`; keep Bash to launch, wait, trap dispatch, and sidecar unlink only.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/cli.py
- **Concern**: Step 3 loop teardown CLI surface is still underspecified. Scenario: The plan only says to register a helper in `cli.py` without naming the verb, argv, owning module, or wrapper call site. That was the core of prior FINDING_3 and the plan still does not close it; implementers can wire a helper the Bash wrapper cannot call or register it outside `plan_review` where Step 3 contracts live.
- **Proposed resolution**: Pin one contract in the plan: verb (e.g. `plan-review teardown-loop`), required flags (`--design-tmpdir`, optional `--pid`), handler module/function, `cli.py` dispatch row, the exact `design-step3-review.sh` invocation for trap-only cleanup, and quiet stdout/stderr rules so the existing KV envelope stays stable.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-step3-review.sh:421; python/larch/review/plan_review.py:321-324
- **Concern**: Step 3 sidecar can record the wrapper process group before `--new-process-group` takes effect. Scenario: The plan writes the identity sidecar immediately after `_loop_pid=$!`, but `plan-review run` calls `os.setsid()` inside the child after Python starts. If the sidecar captures pgid before `setsid()`, a trap-time validated kill can target the parent shell or orchestrator process group instead of the review loop.
- **Proposed resolution**: Require the sidecar writer and teardown helper to accept only `pgid == pid == _loop_pid` for Step 3. If that is not true yet, do not publish a sidecar or signal; rely on the existing tmpdir-scoped fallback.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:python/cli.py section
- **Concern**: Step 3 teardown CLI surface is still unpinned. Scenario: FINDING_3 remains open: the plan only says "Register the new helper CLI" without naming the domain/verb, host module, argv grammar, or quiet stdout contract. The wrapper and harness cannot be wired deterministically, so implementers may register a helper the Bash fence never calls.
- **Proposed resolution**: Pin one registration row (for example plan-review kill-loop-group -> larch.review.plan_review.kill_loop_group_main or a thin process_identity wrapper) with required flags (--design-tmpdir, sidecar path from config), exit codes, and no-envelope stdout; mirror it in design-step3-review.sh and test-design-step3-review.sh pins.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/dispatch_leg.py:224-226
- **Concern**: Live Popen timeout cleanup must stay off the validated-kill path. Scenario: The plan routes in-process timeout cleanup through the "same logging helper" as persisted kills. If that helper always runs identity validation, FINDING_10 regresses: ps parse drift or signature mismatch on a live handle can leave timed-out external legs running.
- **Proposed resolution**: Split process_identity into validated persisted teardown versus live-handle teardown that only logs targets then reuses existing SIGTERM/SIGKILL escalation. State explicitly in dispatch_leg that timeout cleanup uses the live path only.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/cli.py:1-20; python/larch/cli.py:16-134
- **Concern**: Step 3 teardown helper registration targets the entry-point shim instead of the canonical dispatcher. Scenario: `python/cli.py` only imports and delegates to `larch.cli`; the dispatch registry that currently exposes `implement kill-active-leg` lives in `python/larch/cli.py`. If the plan only updates the shim, the new identity-validated Step 3 helper is not reachable from `python3 python/cli.py ...`, so the wrapper cannot replace raw `kill -- -$_loop_pid`.
- **Proposed resolution**: Update the plan's file list and registration step to modify `python/larch/cli.py` for the new helper verb, leaving `python/cli.py` unchanged unless a shim-facing test must change.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:407-421; python/larch/review/plan_review.py:356-357
- **Concern**: Bash-side Step 3 identity capture can record the pre-setsid process group. Scenario: The plan writes the sidecar immediately after `_loop_pid=$!`, but the child does not call `os.setsid()` until `plan-review run` enters Python. If Bash samples `pgid` before that call, the sidecar records the parent shell group; later teardown sees a pgid mismatch and fails closed, leaving the live Step 3 loop group to the broad fallback.
- **Proposed resolution**: Write the Step 3 sidecar from `python/larch/review/plan_review.py` immediately after `_apply_new_process_group()` succeeds, or make the recorder refuse to publish until the child identity shows `pgid == pid`; add that file to the plan.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/cli.py:16
- **Concern**: Step 3 teardown helper is assigned to the entrypoint shim, not the canonical CLI registry. Scenario: The plan only lists `### UPDATED: python/cli.py`, but `python/cli.py` just delegates to `larch.cli`; if the registry entry is not added in `python/larch/cli.py`, `design-step3-review.sh` cannot call the identity-validated teardown helper
- **Proposed resolution**: Add `### UPDATED: python/larch/cli.py` for the new registry entry and leave `python/cli.py` unchanged unless the shim itself needs a real change
