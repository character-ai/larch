### FINDING_1: Step 3 routing still probe-first on repeats
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The firm `skills/design/SKILL.md` update list never requires rewriting the Step 3 post-loop `NEXT_ACTION` preamble, so the live routing text can still treat premature notifications as “yield or probe” without first silent-yielding prefix-identical repeats. That leaves the Step 3 control path able to foreground-probe repeat notifications even after the surrounding anti-pattern and wait prose change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a firm `skills/design/SKILL.md` bullet to amend the Step 3 post-loop routing preamble (~413) with the same ordered contract as the updated anti-pattern: empty output → silent yield; prefix-identical repeat over the first 200 chars with absent `{terminal_sentinel}` → silent yield; first/changed non-empty premature output → at most one foreground probe.
  - From Cursor-Innovation: Add a firm bullet under ### UPDATED: skills/design/SKILL.md to rewrite the Step 3 post-loop premature-notification paragraph before the NEXT_ACTION table: empty output silent yield; prefix-identical repeat over the first 200 chars with the active terminal sentinel absent silent yield; first or changed non-empty premature output at most one foreground probe per shared rules; only then parse when the terminal sentinel is present.
  - From Cursor-Pragmatic: Add a firm ### UPDATED: skills/design/SKILL.md bullet to rewrite the post-loop premature-notification preamble with the ordered contract: empty output silent yield; prefix-identical repeat over the first 200 chars with absent active terminal sentinel silent yield; first or changed non-empty premature notification at most one foreground probe; sentinel present then post-notification routing.
  - From Cursor-Requirements: In `skills/design/SKILL.md` Step 3 post-loop routing, replace yield or probe without parsing with an explicit ordered rule: empty output ends silently; prefix-identical repeat (first 200 chars) with absent `{terminal_sentinel}` ends silently; first or changed non-empty premature output gets at most one foreground probe; proceed only after the terminal sentinel is present.

### FINDING_2: Harness pin and anti-pattern text are not aligned
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The test harness pin can be satisfied by anti-pattern #5 wording instead of the operational Step 3/Step 5c routing paragraphs, so CI may pass even when the real post-loop routing text remains probe-first or context-insensitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After adding the ~413 routing update, pin a substring unique to that paragraph (for example the ordered empty → prefix-identical repeat → probe rule). Do not treat anti-pattern #5 text alone as coverage for Step 3 post-loop routing.
  - From Cursor-Innovation: Extend the ### UPDATED: skills/design/SKILL.md anti-pattern #5 bullet to require a short ordered Apply block matching the Step 3 post-loop edit and align the test-design-structure pin to that exact substring so anti-pattern #5 and Step 3 routing share one decision tree.
  - From Cursor-Pragmatic: Make the harness and prose edits agree: either add the ordered apply text to the NEVER #5 deliverable and pin that exact substring, or add a separate contains pin on the rewritten line-413 preamble so the harness guards the routing surface that actually drives post-loop behavior.
  - From Codex-Pragmatic: Use context-bound assertions around the Step 3 post-loop anchor and the Step 5c fence/routing anchor, and pin repeat-before-probe silent-yield text at each site

### FINDING_3: AGENTS.md non-empty probe rule remains unconditional
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The planned `AGENTS.md` probe-rule update does not qualify the leading non-empty probe condition, so Tier-1 readers can still foreground-probe every non-empty premature notification before the repeat silent-yield carve-out applies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Qualify the AGENTS.md non-empty premature-notification sentence to first or changed non-empty output only, and state evaluation order: empty output silent yield; prefix-identical repeat (first 200 chars) with absent terminal sentinel silent yield; otherwise one foreground probe against the active wait terminal sentinel.
