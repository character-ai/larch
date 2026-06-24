## Proposed Design Outline

### Goals
- Remove ~25 lines of verbatim-duplicated boilerplate from `skills/design/SKILL.md` on the Step 3 hot-path.
- Create a single canonical parameterized anchor in `skills/shared/immediate-background-wait.md`.
- Keep all per-site carve-outs (WAIT clause, dual-sentinel routing, Step 5c-specific guards) as per-site delta text.

### Non-goals
- No logic changes, no AskUserQuestion behavior moved, no judgment branches touched.
- No changes to `test-implement-anti-polling-rule.sh` (STEP3_LITERAL count stays at 2 in SKILL.md).
- No new MANDATORY READ directives added to SKILL.md.

### Approach sketch
- Create `skills/shared/immediate-background-wait.md` with the generalized NEVER-poll and immediate-background-wait text (Blocks B+C, parameterized by sentinel and breadcrumb).
- In SKILL.md: replace 4 inline block occurrences with compact pointer line + per-site delta (sentinel, breadcrumb, extra carve-outs).
- Preamble (Verbosity Control, lines 49-62) stays as the canonical Block A anchor; two inline copies of Block A at Step 3 launch and resume become one-line back-references.
- Per-site STEP3_LITERAL ("NEVER poll `.step3-review-result.env` with a sleep loop.") is preserved in both Step 3 pointer lines to keep the test at count 2.

### Surfaces in scope
- `skills/shared/immediate-background-wait.md` (new file)
- `skills/design/SKILL.md` (4 substitutions: Final summary, Step 3 launch, Step 3 resume, Step 5c)

### Open questions
- None.
