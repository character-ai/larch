# Review Round 2

- Mode: `diff`
- 4 accepted, 6 rejected (3 neutral)

## Accepted Findings

### FINDING_6: No composite integration test for `recovery-out-of-scope` envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: No `checks_commit_route_main` integration test for the recovery-out-of-scope composite envelope. A composite relay regression could pass unit tests on `_run_step4_recovery_recompute` alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add composite test asserting BAIL_REASON=recovery-out-of-scope and absent NEXT_ACTION on full stdout.


### FINDING_7: Step 2 telemetry sentinel written too early and without eligibility gate
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-dispatch-telemetry-output.txt
- **Severity**: important
- **Concern**: `run_dispatch_main` marks every first dispatch and writes `.step2-telemetry-marked` without the old coder/binary eligibility gate and before `subprocess.run(step2-dispatch)` returns. Effects: (1) a normal `--coder codex` run with Codex installed can create an extra Step 2 token row and exhaust budget early; (2) if token mark fails once, later valid dispatches never retry because the sentinel is already present; (3) any first dispatch that later fails (`STATUS=bailed`, prelaunch capture failure after `claude_fallback`, lock contention, etc.) still consumes the once-only guard, so a later retry in the same tmpdir skips Step 2 token/timing entirely and ledger rows / token-budget window boundaries can be missing for the run that actually completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Restore the old eligibility predicate and only write .step2-telemetry-marked after the mark you intend to count succeeds.
  - From dyn-dyn-dispatch-telemetry-output.txt: Write `.step2-telemetry-marked` only after the child exits successfully (or at minimum after a successful dispatch envelope is relayed). Alternatively, key the sentinel to a successful first dispatch (e.g. include child `STATUS` in the guard) and add a regression test that a bailed first dispatch followed by a second non-`--answers` call still emits exactly one Step 2 mark pair.


### FINDING_9: `run_dispatch_main` releases lock before claude-fallback post-child capture
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `run_dispatch_main` releases `dispatch.lock` before the `claude_fallback` post-child capture hook runs. A second dispatch in the gap can mutate the tree before `_capture_prelaunch_porcelain` snapshots it, so recovery pathspecs are derived from the wrong baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: keep the lock held until after the fallback hook completes, or move the hook inside the locked try block


### FINDING_10: `REPO_ROOT` bound in one Bash fence but consumed in another
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-skill-wires-output.txt
- **Severity**: important
- **Concern**: `/implement` Bash fences do not preserve shell state. Step 2.4 binds `REPO_ROOT` in one fence and calls `recovery-paths --repo-root "$REPO_ROOT"` in the next; Step 3 repair refresh in `checks-repair-loop.md:66` reuses `$REPO_ROOT` without rebinding after main-agent edits. A compliant orchestrator runs `recovery-paths` with an empty `--repo-root`, pathspec refresh fails, and composite re-entry can stall despite successful fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Mirror SKILL.md Step 2.4 REPO_ROOT bind-and-fail-closed prose before every repair refresh, or inline --repo-root "$(git rev-parse --show-toplevel)" in the pinned recovery-paths command; update SKILL.md:477 consistently.
  - From dyn-dyn-skill-wires-output.txt: Collapse binding and consumption into one fence (for example inline `--repo-root "$(git rev-parse --show-toplevel)"` plus an empty-check that bails before calling `recovery-paths`), and mirror the same pattern anywhere Step 3 repair refresh re-derives pathspecs.
  - From dyn-dyn-skill-wires-output.txt: Pin a single combined fence that resolves repo root and runs the full `implement recovery-paths --capture-postlaunch …` argv in one call, matching the SKILL Step 2.4 fix.


