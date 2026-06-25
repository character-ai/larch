## Proposed Design Outline

### Goals
- Remove ~21 always-loaded lines from `skills/implement/SKILL.md` by compressing the Checks Failure Entry macro stub and relocating the Durable Bail body.
- Keep runtime behavior identical: all branch semantics already live in the referenced files.

### Non-goals
- No changes to use-site blockquotes (harness-pinned openers/tokens stay as-is).
- No Python or Bash script changes.
- No changes to Step 18, stall-recovery, or any other macro.

### Approach sketch
- Compress `## Checks Failure Entry Macro` in SKILL.md from 8 items to a 3-line stub: read REDACTED_LOG_FILE, MANDATORY-load `checks-repair-loop.md`, follow its site-split.
- Relocate the 8-item `## Durable Bail to Step 18 Macro` body from SKILL.md to `step5-review-branches.md` (new section after the `stall` branch); leave a 1-line pointer in SKILL.md.
- Retarget the `checks-repair-loop.md` pointer (line 83) to note the Durable Bail body is now in `step5-review-branches.md`.
- Update `scripts/test-implement-structure.sh` line 398: move the `'re-run the section 2-pinned composite launcher...'` require check from `skill` to `checks_repair_loop`.

### Surfaces in scope
- `skills/implement/SKILL.md`
- `skills/implement/references/step5-review-branches.md`
- `skills/implement/references/checks-repair-loop.md`
- `scripts/test-implement-structure.sh`

### Open questions
- None.
