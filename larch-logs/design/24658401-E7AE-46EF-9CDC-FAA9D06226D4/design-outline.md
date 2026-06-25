## Proposed Design Outline

### Goals
- Remove ~2 redundant foreground Bash turns from the dominant `/design` run by folding two entry→follow-up fence pairs.
- Fold `step0-init` work into the route verb on `ROUTE=proceed`; fold `step1d5 --mode complete` into `--mode entry` on the no-brainstorm / `.brainstorm-done` path.
- Preserve all observable behavior: sentinels, the two distinct 1d.5 skip breadcrumbs, emitted KVs, and pause-before-work ordering.

### Non-goals
- No fold on non-proceed routes (clarify / already-planned / resume / cancel).
- Don't delete the `step0-init` verb (already-planned replace-via-full-flow keeps it) or `step1d5 --mode complete` (brainstorm path keeps it).
- No change to Step 2a and later (drafting, review, gates, finalize).

### Approach sketch
- Extract the init body (feature-description write + `init-runparams` call + result-KV emit) into a shared helper; call it from `step0_route_main` only when `route == "proceed"`, emitting route KVs then init KVs in one fence. Advances G-Skill-2 (judgment moves SKILL.md→Python).
- Have `step1d5_main --mode entry` read `run-params.json`; when brainstorm is off or `.brainstorm-done` exists, complete the contiguous prefix (`.completed/step-1d.5`) and emit a skip directive KV in the same fence.
- Thin `skills/design/SKILL.md`: drop the proceed-path `step0-init` fence and the no-brainstorm `--mode complete` fence; orchestrator prints the matching skip breadcrumb from the emitted directive.

### Surfaces in scope
- `python/design_lifecycle.py` — `step0_route_main`, `step0_init_main` / `init_runparams_main`, `step1d5_main`.
- `skills/design/SKILL.md` — Step 0b sub-step 6 and Step 1d.5 fence prose.
- `python/test_design_lifecycle.py`, `scripts/test-design-structure.sh` — regression coverage.

### Open questions
- Exact directive KV names and which side (verb vs orchestrator) prints the two 1d.5 skip breadcrumbs — settle at plan drafting.
