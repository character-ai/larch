### FINDING_2: Harness pin and anti-pattern text are not aligned
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The test harness pin can be satisfied by anti-pattern #5 wording instead of the operational Step 3/Step 5c routing paragraphs, so CI may pass even when the real post-loop routing text remains probe-first or context-insensitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After adding the ~413 routing update, pin a substring unique to that paragraph (for example the ordered empty → prefix-identical repeat → probe rule). Do not treat anti-pattern #5 text alone as coverage for Step 3 post-loop routing.
  - From Cursor-Innovation: Extend the ### UPDATED: skills/design/SKILL.md anti-pattern #5 bullet to require a short ordered Apply block matching the Step 3 post-loop edit and align the test-design-structure pin to that exact substring so anti-pattern #5 and Step 3 routing share one decision tree.
  - From Cursor-Pragmatic: Make the harness and prose edits agree: either add the ordered apply text to the NEVER #5 deliverable and pin that exact substring, or add a separate contains pin on the rewritten line-413 preamble so the harness guards the routing surface that actually drives post-loop behavior.
  - From Codex-Pragmatic: Use context-bound assertions around the Step 3 post-loop anchor and the Step 5c fence/routing anchor, and pin repeat-before-probe silent-yield text at each site


