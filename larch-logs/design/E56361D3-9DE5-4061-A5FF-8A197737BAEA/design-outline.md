## Proposed Design Outline

### Goals
- Remove ~24 always-loaded lines from `SKILL.md` by relocating Python-internal prose that the orchestrator never branches on.
- Consolidate sentinel folded-contract notes (Folded contract paragraph, Tradeoff paragraph, Pause/resume coverage) into `sentinel-host-table.md` where they belong alongside the provenance table.
- Relocate the `/design auto error reporting` section into `finalize-step5.md` so it loads only at Step 5.

### Non-goals
- No behavior change to the orchestrator dispatch, wrappers, or Python verbs.
- No changes to sentinel-host-table.md table rows (they already carry the provenance; only prose is added).
- No changes to Python code.

### Approach sketch
- Add a `## Folded contract and tradeoff` section to `sentinel-host-table.md` with the moved prose from SKILL.md lines 67-69, 71-72.
- Remove those prose paragraphs from SKILL.md, keeping only the existing pointer at line 74.
- Remove the 10 inline `is batch-written by...` / `is written by...` notes from individual step sections in SKILL.md.
- Append a `## /design auto error reporting` section to `finalize-step5.md` with the 10-line section currently in SKILL.md.
- Replace the SKILL.md `### /design auto error reporting` section with a 2-line see-also pointer to `finalize-step5.md`.

### Surfaces in scope
- `skills/design/SKILL.md` (removals only — no new text except pointers)
- `skills/design/references/sentinel-host-table.md` (new section added)
- `skills/design/references/finalize-step5.md` (new section added)

### Open questions
- None.
