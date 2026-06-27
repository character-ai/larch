## Proposed Design Outline

### Goals
- Eliminate one orchestrator turn per diagram-run by folding the `design-step3b-sanitize.sh` call into the `design step5c` preamble (`design_publish.py`)
- Remove dead code: the `oos-step5b-dispatch.md` fallback table (dead since `step5b-prepare` always emits `NEXT_ACTION`)
- Reduce always-loaded and on-entry context by ~170 lines (rc=2/5 abort wall + dead oos dispatch + redundant readability read)

### Non-goals
- No changes to `design-step3b-entry.sh --mode diagram` (diagram composition step; only the separate sanitize fence is removed from the SKILL.md orchestrator)
- No changes to the `python/cli.py mermaid sanitize` CLI interface or its sanitizer logic
- No changes to other Step 5 sub-steps (OOS filing, Step 6 cleanup)

### Approach sketch
- `design_publish.py publish_core`: replace the `.completed/step-5b.5` precondition check with an inline `_sanitize_diagram_candidate()` helper that checks for the candidate, calls `python/cli.py mermaid sanitize`, promotes or skips, appends bounded warnings, and writes the sentinel
- `oos-step5b-dispatch.md`: remove the fallback table section (lines 31-49); add a disagreement assertion to `python/cli.py design step5b-prepare` that stops for repair if `NEXT_ACTION` and `FILE_DESIGN_OOS_STATUS` disagree
- `finalize-step5.md`: add the rc=2/5 abort prose (relocated from SKILL.md); consolidate the two `readability-style.md` MANDATORY-reads to one entry at the top of the Ordering contract
- `SKILL.md Step 5b`: drop the `oos-step5b-dispatch.md` mandatory-read + fallback prose; Step 5b.5: remove the `design-step3b-sanitize.sh` fence call; Step 5c: replace the ~20-line rc wall with a one-line pointer to `finalize-step5.md`
- `scripts/test-design-structure.sh`: remove/update structural pins that reference the retired sanitize fence and oos-dispatch mandatory-read

### Surfaces in scope
- `skills/design/SKILL.md` (Step 5b, 5b.5, 5c sections)
- `skills/design/references/finalize-step5.md`
- `skills/design/references/oos-step5b-dispatch.md`
- `python/design_publish.py` (`publish_core` + new `_sanitize_diagram_candidate` helper)
- `python/cli.py` (`step5b-prepare` verb: add disagreement assertion)
- `scripts/test-design-structure.sh` (update structural pins)
- `skills/design/scripts/design-step3b-sanitize.md` (update: no longer a primary SKILL.md surface)
- SKILL.md Wrapper contract inventory (remove `design-step3b-sanitize.sh` entry)

### Open questions
- None.
