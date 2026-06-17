### FINDING_1: Cross-tool contention tests may not exercise blocking under delayed release
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Contention regression tests may omit holder lock semantics across delayed release. If the implementer calls `release_after` on the first acquire before the contending acquire, the default 0.5s delayed `rmdir` can drop the lock so cross-tool/cross-lane assertions flake or never exercise blocking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In cross-tool and cross-lane test steps, state explicitly: do not call release_after on the holder before the second acquire; pin LARCH_EXTERNAL_STARTUP_LOCK_DELAY high (e.g. 60) or only rmdir in finally

### FINDING_2: Plan omits `docs/linting.md` from startup-lock rename
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan omits `docs/linting.md` from the full startup-lock rename. After the helper and env-var rename, the linting docs may still describe the run-negotiation-round harness as covering Darwin serial-lock acquire/release, leaving stale user-facing documentation for the renamed startup-lock contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add docs/linting.md to the plan and update the row to say Darwin startup-lock acquire/release, matching the new helper and env terminology.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/agents.py:155
- **Concern**: [SCOPE-REDUCTION] Plan renames SerialLockState to StartupLockState even though the approved outline only mandates external_startup_lock_* helpers and LARCH_EXTERNAL_STARTUP_LOCK_* env vars. Scenario: The rename fans out across python/test_agents.py python/test_launch_review.py python/test_review_and_fix.py and monkeypatch type hints without changing runtime behavior
- **Proposed resolution**: Keep the SerialLockState dataclass name; rename only the acquire/release helpers env reads and lock path
