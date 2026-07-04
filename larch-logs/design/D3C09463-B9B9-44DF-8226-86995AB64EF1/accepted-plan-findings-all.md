### FINDING_1: Owner token must reach the publishing child and cleanup
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Process Safety, Codex-dyn-Process Safety
- **Severity**: important
- **Concern**: The generated owner token is only forwarded to cleanup, but the `.py` target that publishes the active-leg record must see the same value; otherwise the record and cleanup invocation will not match and ownership-based cleanup can fail or misfire.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Export the per-invocation owner token in the `larch-run.sh` template before launching `.py` targets (for example `LARCH_ACTIVE_LEG_OWNER_TOKEN`), pass the same value to `implement kill-active-leg --owner-token`, and document the env var in `config.py`.
  - From Codex-Arch: Require `larch-run.sh` to export the per-invocation token before running the `.py` target, and pass the same token to `implement kill-active-leg`.
  - From Cursor-Pragmatic: Export the per-invocation owner token from `larch-run.sh` (via the new config env var) before launching the Python target, and read it in `_publish_active_leg_*`. Keep forwarding the same value to `kill-active-leg --owner-token`.
  - From Codex-Innovation: Export a per-invocation owner-token env var before running the .py target and pass the same value to kill-active-leg, or specify an equivalent publisher-to-cleanup token path.
  - From Codex-Pragmatic: Export the generated token to the Python target environment and pass the same token to kill-active-leg, or have both publisher and cleanup read the same env var
  - From Cursor-Requirements: Export the per-invocation owner token into the child environment before running `.py` targets, use the same value for `implement kill-active-leg --owner-token`, and pin this in `python/tests/state/test_bootstrap.py` plus active-leg publish tests.
  - From Codex-Requirements: Update the plan so larch-run exports the per-invocation token to the Python target that can publish an active-leg record, and also passes that same token to kill-active-leg. Add one assertion tying the published record token to the cleanup argv token.
  - From Cursor-dyn-Process Safety: In bootstrap `_write_larch_run_sh`, generate the token once per invocation, export it under the config constant env var before the `python3 …` target line, and pass the same value to `implement kill-active-leg --owner-token`. State explicitly that both the publisher and cleanup consumer read the same env/CLI value.
  - From Codex-dyn-Process Safety: Make larch-run.sh set the per-invocation token in the Python target environment and pass the same token to implement kill-active-leg. Add a focused test that the published record owner token equals the cleanup argv token.


### FINDING_2: Capture Step 3 loop identity at launch
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Requirements, Codex-dyn-Process Safety
- **Severity**: important
- **Concern**: The Step 3 loop still has no persisted launch-time identity snapshot, so a later teardown helper cannot reliably distinguish the original process group from a recycled pid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `### UPDATED: python/larch/review/plan_review.py` (or an explicit post-`$!` publish call in `design-step3-review.sh`) to write a `DESIGN_TMPDIR` identity JSON at loop entry with pid, pgid, `lstart`, command signature, and expected signature needle.
  - From Codex-Arch: After background launch, record the loop process identity before teardown can run, then pass that record path or fields to the Python teardown helper.
  - From Cursor-Innovation: At _loop_pid=$!, write a small DESIGN_TMPDIR sidecar (or CLI args) with pid, lstart, and command; have the Python helper validate against that snapshot and delete the sidecar on success
  - From Cursor-Requirements: Add an explicit launch contract: immediately after backgrounding `plan-review run`, record pid/pgid, `ps` start time, and normalized command signature to a `DESIGN_TMPDIR` sidecar (wrapper one-shot or `plan_review.py` at setsid entry), and have the new CLI teardown helper read that artifact before signaling.
  - From Codex-dyn-Process Safety: Record Step 3 loop identity immediately after _loop_pid=$! into a non-symlink DESIGN_TMPDIR sidecar, pass that record to the teardown helper, fail closed on missing or mismatched identity, and clear the sidecar after wait.


### FINDING_4: Update the affected fence-shape harnesses
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan omits existing harness updates that pin the changed active-leg fence and kill shape, so CI can fail even if the code change is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add `scripts/test-implement-fence-shape.sh` and `scripts/test-implement-structure.sh` to the plan and update only the affected assertions.


### FINDING_5: `kill-active-leg` must validate ownership before consuming records
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-dyn-Process Safety
- **Severity**: important
- **Concern**: The consumer side still reads and unlinks the active-leg file before ownership is checked, so a missing token or stale live record can be consumed or erased by the wrong caller.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify validate-then-signal-then-unlink in dispatch_leg kill_active_leg_main; refuse and retain malformed records until an owner consumes them
  - From Cursor-Pragmatic: Require `--owner-token` in `kill_active_leg_main`; on absent/empty token, log refusal and return 0 without reading, unlinking, or signaling.
  - From Codex-dyn-Process Safety: Add required changes: parse `--owner-token`, refuse non-legacy kills when absent, compare to `owner_token` in the JSON record, no-op without unlink on mismatch for live records, and add tests beyond bootstrap string pins.


### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/state/bootstrap.py:167-177
- **Concern**: [SCOPE-REDUCTION] adjacent: bootstrap text says pass owner token only to kill-active-leg cleanup, but dispatch_leg publishes owner from the environment. Scenario: Owner token never reaches the leg publisher; JSON records miss or mismatch the token, so bystander no-ops and owning trap cleanup also fail while stale pgid kills can persist
- **Proposed resolution**: Require one sentence: export the per-invocation owner token in larch-run.sh before the python3 target line and pass the same value to kill-active-leg; drop the only-to-cleanup wording


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:583-596
- **Concern**: [SCOPE-REDUCTION] agent_waterfall, _run_external, and design_dialectic use in-memory Popen handles, not persisted cross-session pgid files. Scenario: Issue incidents trace to kill-active-leg and post-wait Step 3 bash kill; expanding identity work to three more modules drives ~900 diff_lines without a demonstrated cross-clone path
- **Proposed resolution**: Limit v1 to kill-active-leg JSON plus owner token, design-step3-review teardown, finalize logging, and SECURITY.md; defer agent/dialectic kills to a follow-up unless a persisted-pgid path is found


### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:37-43
- **Concern**: [SCOPE-REDUCTION] Direct live Popen cleanup is being folded into fail-closed identity validation. Scenario: The bug path is stale persisted or reaped retained pgids. Applying ps-based fail-closed validation to direct live Popen timeout paths can regress timeout cleanup: if ps parsing fails or command signatures drift, stalled external agents may be left running.
- **Proposed resolution**: Limit identity validation to persisted or retained pid/pgid kill paths that can be stale. For direct live Popen handles, keep the existing terminate or kill behavior and add pre-kill logging only.


### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:37-43 plan.txt:133-167
- **Concern**: [SCOPE-REDUCTION] External agent and dialectic Popen teardown changes over-expand the stale persisted-pgid fix. Scenario: The observed cross-clone bug is in active-leg state, Step 3 retained shell pid cleanup, and finalize observability; changing agent_waterfall, _run_external, and design_dialectic adds broad timeout behavior risk without being required for this fix
- **Proposed resolution**: Remove python/larch/agents/agent_waterfall.py, python/larch/agents/_run_external.py, python/larch/design/design_dialectic.py, and their new tests from the firm plan; track any broader retained-Popen audit separately if still desired


### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:421-427
- **Concern**: [SCOPE-REDUCTION] Step 3 launch identity capture still lands in Bash. Scenario: The plan says move retained-pid checks into Python, but also assigns Bash to write a sidecar with ps start time and command signature right after _loop_pid=$!. That reintroduces fragile Bash 3.2 ps parsing the plan explicitly avoids, and duplicates logic process_identity.py will own.
- **Proposed resolution**: After background launch, call one quiet Python helper to capture ps identity and atomically write the sidecar (for example plan-review write-loop-identity --design-tmpdir ... --pid $_loop_pid with expected needle derived from the launch argv). Keep Bash to pid bookkeeping, wait, and trap gating only.


