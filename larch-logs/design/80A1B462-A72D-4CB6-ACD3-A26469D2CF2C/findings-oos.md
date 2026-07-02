### OOS_1: Step 3 MAV uses rubric-by-reference while other parity sites carry inline OOS bullets
- **Description**: Step 3 MAV uses rubric-by-reference while other parity sites carry inline OOS bullets. Scenario: After compression, an implementer may paste the shortened inline paragraph into design SKILL (widening scope) or assume parity failed when design correctly stays a rubric pointer
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:441
- **Phase**: design



### OOS_2: Static voter preamble duplicates much of the dynamically embedded review-acceptance-rubric.md body
- **Description**: Static voter preamble duplicates much of the dynamically embedded review-acceptance-rubric.md body. Scenario: The plan compresses both surfaces separately; render_voter_main still loads the full rubric after lines 1138-1152 that repeat default-deny, severity floor, and OOS-signal guidance. Sentence folding there yields smaller savings than deleting redundant static lines already covered by the embedded rubric.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/rendering/rendering.py:1136-1154
- **Phase**: design



