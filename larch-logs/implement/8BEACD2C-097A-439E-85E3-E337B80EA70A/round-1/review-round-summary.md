# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale note can be re-pinned after a conflict-resolved rebase
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: important
- **Concern**: After `rebase_and_push(...)` succeeds, the ship path can still re-pin an architectural-guidelines note even when the rebase fixer resolved conflicts and changed tracked files. That can leave the final report asserting a pre-conflict assessment over a post-conflict diff the assessment never covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Have `rebase_and_push` report whether conflict resolution changed files, or otherwise detect that case, and call `_invalidate_guidelines_note(...)` instead of `_pin_or_invalidate_guidelines_note(...)` for conflict-resolved or other delta-producing rebases. Keep the pin helper only for true no-delta rebases.
  - From codex-specialist-testing: Expose whether conflict fixing ran and only pin on clean no-delta rebases; direct-invalidate after conflict fixes and add a regression test.


### FINDING_2: Snapshot fallback can pin stale guidance after a head-moving rebase
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_pin_or_invalidate_guidelines_note` can fall back to Phase A snapshot validation when live diff materialization fails. After a head-moving rebase, that fallback can let pin succeed against a stale snapshot even though the working tree diverged, where previous call sites would have invalidated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: When repo_root is set, fail closed to _invalidate_guidelines_note if live diff cannot be materialized, or add a head-moving flag that forbids snapshot-only fallback in pin_note_from_staged_for_current_head.


### FINDING_3: Live-diff pinning can preserve stale assessment text across implementation drift
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The rebase pinning path refreshes the fingerprint but keeps the original assessment text when the live diff changes. If conflict resolution alters feature-branch files, the note can remain consumable without a fresh LLM assessment even though the implementation drifted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Compare stored vs live fingerprints before pinning and invalidate on true implementation drift, or require orchestrator Phase A after conflict-producing rebases.


