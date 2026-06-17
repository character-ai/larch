### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_agents.py:95-109
- **Concern**: Contention regression tests omit holder lock semantics across delayed release. Scenario: Implementer calls release_after on the first acquire before the contending acquire; default 0.5s delayed rmdir drops the lock and the cross-tool/cross-lane assertion flakes or never exercises blocking
- **Proposed resolution**: In cross-tool and cross-lane test steps, state explicitly: do not call release_after on the holder before the second acquire; pin LARCH_EXTERNAL_STARTUP_LOCK_DELAY high (e.g. 60) or only rmdir in finally

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: docs/linting.md:229
- **Concern**: Plan omits docs/linting.md from the full startup-lock rename. Scenario: After the helper and env-var rename, the linting docs still describe the run-negotiation-round harness as covering Darwin serial-lock acquire/release, leaving stale user-facing docs for the renamed startup-lock contract
- **Proposed resolution**: Add docs/linting.md to the plan and update the row to say Darwin startup-lock acquire/release, matching the new helper and env terminology.
