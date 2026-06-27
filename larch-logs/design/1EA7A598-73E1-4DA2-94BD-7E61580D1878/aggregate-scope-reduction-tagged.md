### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-22,45-63
- **Concern**: [SCOPE-REDUCTION] The new 3-attempt CI_NOT_READY stall guard adds a new early-fail contract that the bug report does not require.. Scenario: Slow or eventually-consistent PRs can now stop as STALLED after three identical not-ready reads even though the current loop would have progressed.
- **Proposed resolution**: Remove the threshold and guard, and keep only the mergeability-policy fix so ship preserves its existing retry contract.

### FINDING_16:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/git/gh.py:751-839; python/larch/implement/ship.py:2161-2188; python/larch/core/config.py:492
- **Concern**: [SCOPE-REDUCTION] The plan adds a new diagnostic helper, config threshold, and early merge-ci-not-ready stall path even though the chosen policy already fixes the specified skipped/cancelled/neutral/unknown loop by aligning pr_checks_all_pass with ci_monitor.. Scenario: The extra guard creates a new terminal STALLED path for racy or generic CI_NOT_READY reads and expands the patch beyond the minimum required feature path.
- **Proposed resolution**: Drop the new helper, threshold, ship guard, and related tests unless the plan switches to a non-mergeable policy for skipped or neutral checks. Limit the firm change to the gh.py mergeability policy alignment and focused regression coverage.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-Ci Merge Semantics Reviewer
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:17-22,50-63; python/larch/state/stall_recovery.py:1402-1410,1434-1464,434-441
- **Concern**: [SCOPE-REDUCTION] Emitting `STALL_STEP=merge-ci-not-ready` adds a new terminal label that the repo's stall-recovery validator does not accept. `validate_terminal_state` will reject the state, and `_safe_step_value` will round-trip it as `unknown`, so the new stall reason cannot be validated or recovered through the existing tooling.. Scenario: Ship will write the planned terminal state, but downstream stall recovery and reporting will lose the new reason or fail validation, so the new stall path is not round-trippable.
- **Proposed resolution**: Either reuse the already-recognized `merge-loop-iteration-cap` step, or add `merge-ci-not-ready` to the stall-recovery allowlist/classifier and tests before shipping it.
