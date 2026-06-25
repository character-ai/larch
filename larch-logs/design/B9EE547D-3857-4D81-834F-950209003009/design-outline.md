## Proposed Design Outline

### Goals
- Eliminate 5 repeated checks-failure entry blocks in `skills/implement/SKILL.md` via a single named section.
- Eliminate ~5 remaining manual durable-bail seeding blocks via a named macro section (parallel to Rebase Checkpoint Macro).
- Each call site supplies only its variable token; no judgment is removed.

### Non-goals
- No Python changes.
- No changes to `checks-repair-loop.md`, `step5-review-branches.md`, or other references files.
- No routing logic changes; dedup is prose-only.

### Approach sketch
- Add `## Checks-Failure Entry` section to `SKILL.md`. Five sites replace boilerplate with "See **Checks-Failure Entry**; apply pinned `--site <X>` args from `checks-repair-loop.md`."
- Add `## Durable-Bail to Step 18 Macro` section to `SKILL.md` (near `## Rebase Checkpoint Macro`). Each remaining manual-seed site references the macro and supplies `STALL_STEP` / `STALL_REASON`.
- Inspect `scripts/test-implement-fence-shape.sh`; update `EXPECTED_OLD`/`EXPECTED_NEW` only if Bash fence count changes.

### Surfaces in scope
- `skills/implement/SKILL.md` (macro section additions + ~10 call-site rewrites)
- `scripts/test-implement-fence-shape.sh` (inspection; update if needed)

### Open questions
- None. Commit-route dependency (#5271) is already merged.
