### FINDING_3: Contract tests still miss repeat-fingerprint pins
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-dyn-Prompt Contract Harness, Codex-dyn-Prompt Contract Harness
- **Severity**: important
- **Concern**: The acceptance harnesses still only pin positive literals or the wrong substrings, so repeat-fingerprint prose can regress without CI failing and stale byte-identical wording can survive alongside the new repeat carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add contains "$SKILL_MD" for the Step 3 post-loop prefix-identical repeat silent-yield routing text, parallel to the planned Step 5c repeat pin
  - From Cursor-Requirements: After adding Step 3 routing prose, add a contains "$SKILL_MD" pin for the ordered premature-notification rule (or the prefix-identical silent-yield sentence) with a label that names Step 3 post-loop routing.
  - From Cursor-dyn-Prompt Contract Harness: Require contains on the full silent-yield repeat sentence e.g. prefix-identical previous non-empty end silently and not_contains byte-identical in the Step 3 fingerprint paragraph plus AGENTS_MD ORCH_NEVER_MD SKILL_MD pins whose substrings cannot pass without the repeat carve-out text
  - From Codex-dyn-Prompt Contract Harness: Add not_contains checks for byte-identical on the shared wait and orchestrator files, and pin the Step 5c block with the exact prefix-identical and first 200 chars literal so the repeat carve-out cannot disappear silently.


### FINDING_4: Anti-pattern #5 still reads empty-output-only and is keyed to the old sentinel
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Anti-pattern #5 still reads like an empty-output-only rule, its body hardcodes the Step 3 terminal sentinel for repeat handling, and the anti-polling harness still keys off the old heading text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the anti-pattern #5 edit, replace the fixed step-3-terminal repeat guard with the active wait terminal sentinel (or defer repeat yield to design-background-wait.md parameters) and pin the revised Apply literal in scripts/test-design-structure.sh
  - From Cursor-Pragmatic: `### UPDATED: scripts/test-implement-anti-polling-rule.sh` (and sibling `.md` if needed): retarget the anchor to the renamed heading and pin `prefix-identical` / first-200-chars literals alongside the existing empty-output checks
  - From Cursor-Pragmatic: Extend the #5 body edit to use the fence's relevant terminal sentinel (or `{terminal_sentinel}` wording from the shared wait rule), not only `step-3-terminal`; keep Step 5c's explicit routing aligned with `.completed/step-5c-terminal`


### FINDING_2: Harness pin and anti-pattern text are not aligned
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The test harness pin can be satisfied by anti-pattern #5 wording instead of the operational Step 3/Step 5c routing paragraphs, so CI may pass even when the real post-loop routing text remains probe-first or context-insensitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After adding the ~413 routing update, pin a substring unique to that paragraph (for example the ordered empty → prefix-identical repeat → probe rule). Do not treat anti-pattern #5 text alone as coverage for Step 3 post-loop routing.
  - From Cursor-Innovation: Extend the ### UPDATED: skills/design/SKILL.md anti-pattern #5 bullet to require a short ordered Apply block matching the Step 3 post-loop edit and align the test-design-structure pin to that exact substring so anti-pattern #5 and Step 3 routing share one decision tree.
  - From Cursor-Pragmatic: Make the harness and prose edits agree: either add the ordered apply text to the NEVER #5 deliverable and pin that exact substring, or add a separate contains pin on the rewritten line-413 preamble so the harness guards the routing surface that actually drives post-loop behavior.
  - From Codex-Pragmatic: Use context-bound assertions around the Step 3 post-loop anchor and the Step 5c fence/routing anchor, and pin repeat-before-probe silent-yield text at each site


