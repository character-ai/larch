### OOS_1: [OUT_OF_SCOPE] NEVER #4 foreground-probe exception still includes repeats
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-contract-prose
- **Severity**: important
- **Concern**: `skills/shared/orchestrator-never.md` still describes the `/design` foreground-probe exception as applying to non-empty task output without excluding prefix-identical repeats, so secondary readers can infer repeats remain probe-eligible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Qualify to new or changed non-empty in a follow-up outside this diff.

### OOS_2: [OUT_OF_SCOPE] Repeat fingerprint can collide on long shared prefixes
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The 200-char prefix fingerprint can collide on long shared prefixes, so distinct notifications may be treated as repeats and silently dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Accept documented behavior or widen fingerprint in a separate runtime change.

### OOS_3: [OUT_OF_SCOPE] Anti-pattern prose compression is harder to audit
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The anti-pattern prose compression is outside plan scope and does not create a direct contract regression, but it makes the audit trail for unrelated rules a little harder to follow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Revert or isolate readability edits in a docs-only follow-up if desired.

### OOS_4: [OUT_OF_SCOPE] Final summary wait still delegates repeat handling to shared rule
- **Reviewer(s)**: dyn-dyn-contract-prose
- **Severity**: latent
- **Concern**: The final-summary background wait delegates repeat handling to `design-background-wait.md:15` rather than inlining the ordered contract, so that path inherits whatever ordering the shared paragraph keeps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-contract-prose: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Repeat carve-out text omits the fingerprint baseline
- **Reviewer(s)**: dyn-dyn-contract-prose
- **Severity**: latent
- **Concern**: The repeat carve-out text omits the Step 3 fingerprint baseline, "prior non-empty one in the same wait", leaving ambiguous what the first non-empty notification compares against.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-contract-prose: Address the concern above.

