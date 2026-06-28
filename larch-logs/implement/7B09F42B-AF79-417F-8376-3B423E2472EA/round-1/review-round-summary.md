# Review Round 1

- Mode: `diff`
- 2 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Step 8 rc-sidecar forge denial misses cwd-relative writes
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: Step 8 rc-sidecar forge denial misses cwd-relative writes. From a live Step 8 tmpdir, `touch .step-8-ship-handoff.rc` or `: > .step-8-ship-handoff.rc` can still create the release sentinel because the mutation gate only keys off `$IMPLEMENT_TMPDIR` or the canonical dir string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Add a Step 8 cwd-relative target matcher or canonicalize relative mutation targets against `cwd_canon` before the mutation deny test, and cover it in `scripts/test-hook-bg-poll-guard.sh`.


### FINDING_5: Relaunch harness does not lock full stale-handoff contract
- **Reviewer(s)**: dyn-dyn-bg-wait-hooks
- **Severity**: important
- **Concern**: The relaunch regression only asserts that an isolated `rm -f` removes stale sidecars. It does not exercise the full contract from the plan (foreground orchestrator clear → wrapper entry clear at `step-8-ship.sh:18` → marker arm → notification-time rc probe). A regression that breaks wrapper entry cleanup while the documented `rm` shape still passes would slip through CI and leave the stale-rc hook bypass above unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bg-wait-hooks: Extend the dynamic harness to pre-seed stale rc/json, run the foreground clear, invoke the wrapper (stubbed driver), and assert rc/json are absent before the driver stub runs and that `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` would not succeed until the new EXIT trap writes fresh sidecars.

---

**Slot coverage check**: All six inventory slots appear above. Positive-only bullets (commit hashes, implementation confirmations, harness-presence notes, intentional-behavior notes) were not promoted to findings. **FINDING_9** (OOS) and **FINDING_13** (in-scope) share the relaunch-test gap but stay separate because the testing slot marked its version `[OUT_OF_SCOPE]`.


