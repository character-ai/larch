### OOS_1: [OUT_OF_SCOPE] Tier-1 probe rules still miss the repeat carve-out
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bg-wait
- **Severity**: important
- **Concern**: The Tier-1 probe prose in AGENTS.md, orchestrator-never, and the Step 3 / Step 5c routing text still lacks a byte-identical repeat carve-out, so readers can keep following the old probe-on-non-empty rule instead of the silent-yield path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Extend AGENTS.md with byte-identical repeat silent-yield carve-out pointing to design-background-wait.md.
  - From cursor-specialist-edge-cases: Add narrow deferral to design-background-wait.md in a follow-up; omitted from this plan's file list.
  - From cursor-specialist-edge-cases: Update the routing preamble to evaluate fingerprint before probe; not in this plan's scope.
  - From cursor-specialist-testing: Update AGENTS.md when scope allows (rejected at plan review)
  - From cursor-specialist-testing: Sync orchestrator-never when scope allows
  - From dyn-dyn-bg-wait: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Fingerprint matching contract is ambiguous
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bg-wait
- **Severity**: important
- **Concern**: The rule says “byte-identical” repeats but also fingerprints only the first 200 chars, so prefix-only matches can be misclassified as either new notifications or repeats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bg-wait: Pick one contract and state it once: either “byte-identical full task output” or “first-200-character fingerprint match,” and drop the conflicting term.

### OOS_3: [OUT_OF_SCOPE] Contract tests do not pin repeat-fingerprint literals
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-bg-wait
- **Severity**: important
- **Concern**: The acceptance harnesses only pin the empty-output and Step 3 terminal literals, so later prose edits could remove the repeat-fingerprint carve-out without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Add check/check_context assertions for new design-background-wait.md and anti-pattern #5 literals
  - From codex-specialist-testing: Add a literal assertion for the new repeat-fingerprint wording and its Step 3-only scope in the design anti-polling harness.
  - From dyn-dyn-bg-wait: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Anti-pattern #5 title still implies empty-output only
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The title still reads like an empty-output-only rule even though the body now covers repeat notifications, so a reader scanning the heading could miss the byte-identical repeat case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Accept plan trade-off or add parenthetical to title when harness allows

