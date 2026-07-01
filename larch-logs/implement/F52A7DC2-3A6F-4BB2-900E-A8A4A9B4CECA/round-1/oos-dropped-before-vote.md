### OOS_1: [OUT_OF_SCOPE] keepalive write failure is non-fatal at session setup
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `session_env` keepalive write failure is non-fatal at session setup. Sessions without `.larch-keepalive` keep global no-progress blocking, undermining this PR’s cross-clone fix. Pre-existing `session_env` behavior; not modified in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Global Stop counting is a documented intentional tradeoff
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Global Stop counting is unchanged from pre-fix behavior. Cross-clone Stop events can arm foreign breakers though blocking is now scoped. This PR fixes cross-clone blocking, not cross-clone arming. Documented intentional tradeoff in `hook-no-progress-guard.md:36`; out of scope for this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Exact canonical path equality; no repo-root prefix match
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Scoping uses exact canonical path equality with no subdirectory/repo-root prefix match. Hook `cwd=/repo/subdir` vs marker `CLONE_PATH=/repo` skips block in the owning clone. Pre-existing cwd semantics; not introduced by this change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Same-clone concurrent workflows still cross-block
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Scoping uses repo `CLONE_PATH`, not session tmpdir or `SESSION_ID`. Concurrent `/design` and `/implement` in the same clone (`larch6`) still cross-block when either arms the breaker. Acceptance requires isolation across clones, not across workflows in one clone; same-clone cross-block matches pre-fix behavior for that case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] No auto-recovery when marker tmpdir changes while breaker stays armed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: No auto-recovery when the marker tmpdir still changes (e.g. plan-review artifacts) while the breaker stays armed. The incident workaround (clear only `no-progress-circuit-breaker-armed` and `no-progress-turns.count`) is documented in the improved message but not automated. Not in acceptance criteria; this PR targets cross-clone blast radius.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] run-relevant does not route hook edits to harness tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `run-relevant` does not map `hook-no-progress-guard.sh` edits to `test-hook-no-progress-guard`. Hook-only implement runs may skip the harness locally even though CI runs `test-harnesses-3`. Pre-existing; extend `checks_run_relevant` routing if hook-only local coverage is desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Harness markdown Coverage omits T17–T19
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Harness markdown Coverage section omits T17–T19. Readers of the sibling contract miss new clone-scoping coverage. Update Coverage list when touching the harness doc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

