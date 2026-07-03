### OOS_1: [OUT_OF_SCOPE] Issue #6114 is intentionally scoped to `test_ship.py`
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The branch appears intentionally limited to `test_ship.py`; the analogous `ci_monitor` and `ci_agentic_fix` coverage is deferred to the later follow-up rather than being omitted from this patch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Test-shipping helpers could be simplified without changing behavior
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The test scaffolding is a bit repetitive, but the duplicated bootstrap, lack of a fail-fast invalidate monkeypatch, and absence of an explicit `_pin_and_load_guidelines_note(..., repo_root=repo_root)` call are maintainability-only issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Related behavioral coverage is still deferred
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Coverage at other call sites remains deferred, so the new ship-level behavioral test does not yet protect the analogous `ci_monitor` / `ci_agentic_fix` rebase paths or the phase-14 rebase path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Missing durable `DIFF_FINGERPRINT` assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new test still omits a durable `DIFF_FINGERPRINT` assertion, leaving a stale fingerprint unguarded even if head pinning passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

