## Decision 1: Anchor strategy for SKILL.md key region
- **Question**: How should the SKILL.md key-bullet region be anchored for the drift-guard parser?
- **Resolution**: HTML comment markers — `<!-- write-initial-state-keys:begin -->` / `<!-- write-initial-state-keys:end -->` — wrap the bullet list; the test parses keys strictly between the markers. Robust to surrounding edits; aligns with `.claude/rules/drift-prone-prose-in-docs.md` (no line-number references).
- **Source**: user (Step 1c)

## Decision 2: Equality direction
- **Question**: What equality should the drift guard assert between the SKILL.md key-bullet list and ship-pr.sh write_initial_state emitted keys?
- **Resolution**: Set equality, both directions. Fail if any key is emitted by ship-pr.sh but missing from the SKILL.md region, and fail if any key listed in the SKILL.md region is not emitted by ship-pr.sh. Order is not asserted.
- **Source**: user (Step 1c)

## Decision 3: Test host
- **Question**: Where should the drift assertion live?
- **Resolution**: Extend `scripts/test-implement-structure.sh` (the file the issue body explicitly names) with a new check function. No new top-level test script; no new make target.
- **Source**: issue body (explicit)

## Decision 4: Out-of-scope items
- **Question**: What is explicitly out of scope for this issue?
- **Resolution**: (a) refactoring ship-pr.sh; (b) refactoring SKILL.md prose other than adding the two HTML comment markers around the existing bullet list; (c) drift guards for unrelated key lists; (d) any CI workflow file changes.
- **Source**: issue body ("Not blocking this PR")
