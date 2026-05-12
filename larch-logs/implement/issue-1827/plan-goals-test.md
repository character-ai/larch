## Goal
Extend `skills/shared/reviewer-templates.md` to cover all three combined-specialist reviewer archetypes with auto-generation pipeline (Sub-task D), and extract shared body from all three implementer agents into `agents/_implementer-base.md` with a generation pipeline (Sub-task E).

## Implementation Plan
See issue #1827. Sub-task D: Add two new archetype sections to reviewer-templates.md, create sibling generation scripts, register in generators.tsv. Sub-task E: Create _implementer-base.md with shared body, create three generation scripts, update test assertions.

## Test plan
1. All five generator scripts pass `--check` mode.
2. `bash scripts/check-generators.sh` exits 0.
3. `/relevant-checks` passes.
