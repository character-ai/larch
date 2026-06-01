### FINDING_1: Fix-loop harness still asserts exit-4 stall for vendor outer-loop CI-fix exhaustion
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-dyn-exit-contracts, Codex-dyn-exit-contracts, Codex-dyn-regression-harness
- **Severity**: important
- **Concern**: Plan Decision 3 replaces terminal `exit_stall` at `scripts/ship-pr.sh:2693` with `BAIL_REASON=ci-fix-exhausted` and exit 3, but `scripts/test-ship-pr.sh` is omitted from Files to modify. The fix-loop case `vendor_loop_ci_fix_exhausted` (`scripts/test-ship-pr.sh:2356-2382`, exercised by `make test-ship-pr-fix-loop` / shard 14) still asserts `rc 4` and `STALL_STEP=10-max-retries`. After implementation, the harness fails or implementers may preserve exit 4 and miss the new acceptance criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add scripts/test-ship-pr.sh to the plan and update that case to expect exit 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false (no STALL_STEP=10-max-retries); list make test-ship-pr-fix-loop alongside the other Bash targets in Testing strategy
  - From Cursor-Innovation: Add scripts/test-ship-pr.sh to Files to modify; change that case to assert rc 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false (not STALL_STEP max-retries)
  - From Cursor-Requirements: Update `vendor_loop_ci_fix_exhausted` to expect exit 3, `BAIL_REASON=ci-fix-exhausted`, and autonomous exit-3 state (`BAIL_NEEDS_USER_INPUT=false`, mirroring `scripts/test-ship-pr-fix-loop-2632.inc.sh:63-64`).
  - From Codex-Requirements: Update this existing vendor_loop_ci_fix_exhausted case to expect exit 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false/autonomous routing as appropriate.
  - From Cursor-dyn-exit-contracts: Add an explicit plan step to rewrite this case: assert_rc 3, BAIL_REASON=ci-fix-exhausted, no STALL_STEP=10-max-retries (and keep rebase-storm cases on exit 4 unchanged)
  - From Codex-dyn-exit-contracts: Update this existing assertion to expect rc 3, BAIL_REASON=ci-fix-exhausted, BAIL_NEEDS_USER_INPUT=false, and keep rebase-storm coverage on exit 4
  - From Codex-dyn-regression-harness: Update the existing exhaustion cases to expect rc 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false; keep rebase-storm max-retries tests on rc 4


### FINDING_2: Shared max-retries tail can emit `ci-fix-exhausted` without a real fixer exhaustion
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-dyn-exit-contracts, Codex-dyn-ci-log-surface, Codex-dyn-regression-harness
- **Severity**: important
- **Concern**: Replacing the shared outer-loop exhaustion terminal at `scripts/ship-pr.sh:2567-2693` / `python/ci_monitor.py:1021-1064` with a broad `ci-fix-exhausted` exit-3 path can fire when logs or jobs stayed in progress, no ready failure log existed, and no per-job/vendor fix attempt actually ran. That would route pending or weakly classified CI to autonomous main-agent CI fix without usable failure evidence, instead of preserving stall/wait behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Track whether a vendor/per-job fix was actually attempted against ready failure data; only emit ci-fix-exhausted for that case. Preserve the existing stall/wait behavior for still-in-progress or unclassifiable-no-fix attempts.
  - From Codex-Edge: Track whether a ready-log fix attempt actually ran; emit ci-fix-exhausted only for true fixer exhaustion, and keep the existing stall/wait behavior for still-in-progress cases.
  - From Codex-Pragmatic: Keep the existing stall/waterfall-failed behavior, or gate ci-fix-exhausted on a ready deterministic log plus an actual exhausted fixer dispatch
  - From Codex-dyn-exit-contracts: Track whether a real per-job/vendor fix path ran and exhausted; emit BAIL_REASON=ci-fix-exhausted with BAIL_NEEDS_USER_INPUT=false only for that case, and keep no-log/in-progress exhaustion on the existing stall path
  - From Codex-dyn-ci-log-surface: Gate ci-fix-exhausted on a ready-log fix attempt actually exhausting; keep in-progress/no-dispatch exhaustion on the existing stalled/waterfall-failed path and retain or update the in-progress regression
  - From Codex-dyn-regression-harness: Pin the no-ready-logs path as STALLED/exit 4 or track that at least one ready-log fix attempt ran before returning ci-fix-exhausted; keep/update the existing Python in-progress test and add the matching Bash all-rc3 case only if needed to guard that branch


### FINDING_4: Second fix-loop case `ci_fix_exhausted` still pins exit-4 stall
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-regression-harness
- **Severity**: important
- **Concern**: Beyond the vendor outer-loop case, `scripts/test-ship-pr.sh:3398-3432` (`ci_fix_exhausted` local fix-loop exhaustion) still asserts exit 4 / stall semantics. The same routing change breaks a second regression under `make test-ship-pr-fix-loop` while the plan only names new coverage in `scripts/test-ship-pr-fix-loop-2632.inc.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Update that case to exit 3 + ci-fix-exhausted; extend Testing strategy to name scripts/test-ship-pr.sh explicitly (not only the 2632 inc)
  - From Codex-dyn-regression-harness: Update the existing exhaustion cases to expect rc 3, BAIL_REASON=ci-fix-exhausted, and BAIL_NEEDS_USER_INPUT=false; keep rebase-storm max-retries tests on rc 4


### FINDING_5: New #3334 regressions in 2632 inc may not run under fix-loop make target
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Plan adds deterministic-no-rerun / transient-still-reruns cases only in `scripts/test-ship-pr-fix-loop-2632.inc.sh`, which is not sourced from `scripts/test-ship-pr.sh`. Those cases never execute under `make test-ship-pr-fix-loop` (shard 14).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Source the inc from the fix-loop section (restore one source line) or add equivalent cases inline in scripts/test-ship-pr.sh; do not rely on the inc alone


### FINDING_7: Bash/Python parity on log readiness before transient rerun classification
- **Reviewer(s)**: Codex-dyn-bash-python-parity
- **Severity**: important
- **Concern**: The Bash retry gate at `scripts/ship-pr.sh:2499-2514` / `scripts/gh-run-logs.sh:50-56` does not require `gh-run-logs` success before `is_transient_net_signature`, while Python at `python/ci_monitor.py:496-500,996-1006` gates rerun on `logs.state == ready`. If `gh-run-logs` fails with transient-looking text, Bash may rerun but Python enters the fix loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-python-parity: Require gh_logs_rc == 0 before Bash calls is_transient_net_signature for rerun; any non-zero log fetch goes to the fix loop


### FINDING_8: Non-code-fix exhaustion (push/launcher) may collapse into `ci-fix-exhausted`
- **Reviewer(s)**: Codex-dyn-bash-python-parity
- **Severity**: important
- **Concern**: Exhaustion mapping at `scripts/ship-pr.sh:2127-2172,2679-2693` and `python/ci_monitor.py:910-963,1051-1064,1183-1192` can route push failed or no-launcher-tier situations to autonomous main-agent CI fix despite the plan saying those remain STALLED; Bash lacks a reason on return 1 to preserve parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-bash-python-parity: Keep non-code-fix failures as immediate STALLED in both paths; only map actual deterministic fixer exhaustion to ci-fix-exhausted


### FINDING_9: `scripts/ci-decide.md` still documents vendor exhaustion as exit 4
- **Reviewer(s)**: Codex-dyn-exit-contracts
- **Severity**: latent
- **Concern**: After the change, `scripts/ci-decide.md:5-7` would still describe `run_evaluate_failure` vendor exhaustion as `exit_stall` with `STALL_STEP=10-max-retries`, contradicting the new autonomous exit-3 token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-exit-contracts: Update this contract sentence to distinguish fix-attempts-exhausted as user-input exit 3, ci-fix-exhausted as autonomous exit 3, and rebase-count exhaustion as exit 4

---

**Merge notes (for voters, not part of machine schema):**
- Raw slots 1, 5, 10, 11, 14, 17, and the vendor portion of 19 → **FINDING_1**.
- Raw slots 2, 3, 9, 15, 18, and the routing portion of 20 → **FINDING_2** (distinct from **FINDING_6**, which argues to drop the feature rather than gate it).
- Raw slot 4 → **FINDING_3**; slot 6 (+ local portion of 19) → **FINDING_4**; slot 7 → **FINDING_5**; slot 8 → **FINDING_6**; slot 12 → **FINDING_7**; slot 13 → **FINDING_8**; slot 16 → **FINDING_9**.

