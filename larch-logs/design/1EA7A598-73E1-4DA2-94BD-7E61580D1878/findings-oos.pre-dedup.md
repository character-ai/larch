### OOS_1: python/larch/implement/ci_monitor.py:356-381
- **Description**: python/larch/implement/ci_monitor.py:356-381. Scenario: Mergeable-bucket policy would be duplicated in gh._pr_checks_json_all_pass and ci_monitor._classify_checks_json after the fix.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/git/gh.py:751-766
- **Phase**: design



### OOS_2: New `STALL_STEP=merge-ci-not-ready` is not allowlisted
- **Description**: New `STALL_STEP=merge-ci-not-ready` is not allowlisted. Scenario: `_safe_step` whitelists `merge-loop-iteration-cap` but not `merge-ci-not-ready`, so stall recovery sanitizes the step to `unknown` and `_classify_text` has no dedicated branch. Terminal stall still works; escalation reports lose the named step.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/state/stall_recovery.py:118-125
- **Phase**: design



### OOS_3: [OUT_OF_SCOPE] Add a hard 3-attempt CI_NOT_READY stall guard
- **Description**: [OUT_OF_SCOPE] Add a hard 3-attempt CI_NOT_READY stall guard. Scenario: A transient stale `gh pr checks` snapshot that repeats three times after the monitor already chose merge would now terminate ship as STALLED, even though the PR may have become mergeable on the next retry.
- **Reviewer**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:2161-2190
- **Phase**: design



