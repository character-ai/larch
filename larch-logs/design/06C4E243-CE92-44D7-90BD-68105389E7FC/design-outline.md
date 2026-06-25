## Proposed Design Outline

### Goals
- Remove ~17 always-loaded lines from `skills/design/SKILL.md` by eliminating two verbatim duplications on the Step 3 path.
- Replace the resume-fence duplicate (12 lines of `Read and apply` directives + Parameters block) with a one-line back-reference to the first-time wait contract.
- Drop the reviewer-status-table sentence from the Verbosity section (it already lives in `design-background-wait.md`, which the preceding pointer forces to be read).

### Non-goals
- Do not change `skills/shared/design-background-wait.md` content.
- Do not touch any Python, Bash, or test scripts.
- Do not restructure or rename any SKILL.md sections.

### Approach sketch
- Edit `skills/design/SKILL.md` only (two targeted edits).
- Replace lines 648–659 (resume fence duplicate block) with a single back-reference sentence pointing at the first-time Step 3 launch block.
- Remove line 53 (reviewer-status-table sentence) from the Verbosity section; line 51 already redirects readers to the `design-background-wait.md` section that contains it.
- Run `make lint` and `make test-design-structure` to verify no structural pins broke.

### Surfaces in scope
- `skills/design/SKILL.md` (two targeted text edits)

### Open questions
- None.
