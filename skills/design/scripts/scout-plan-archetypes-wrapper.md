# scout-plan-archetypes-wrapper.sh

**Purpose**: `/design` Step 3 scout — derives `--scope-files` from the plan’s Files-to-modify headings, invokes `scripts/scout-dynamic-archetypes.sh` in description mode with the plan-review prompt override (forwarding `--codex-present` / `--cursor-present`), then post-filters reserved slugs (`arch`, `edge`, `innovation`, `pragmatic`, `requirements`) and enforces cap 3.

**Primary callers**: `skills/design/SKILL.md` Step 3.

**Stdout KVs**: `SCOUT_STATUS`, `SCOUT_MANIFEST`, `SCOUT_ARCHETYPE_COUNT` (post-filter count).

**Harness**: `skills/design/scripts/test-scout-plan-archetypes-wrapper.sh`.

**Edit in sync**: this file, `scout-plan-archetypes-wrapper.sh`, `scout-plan-archetypes-prompt.txt`, `scripts/scout-dynamic-archetypes.sh` / `.md`, `skills/design/scripts/test-scout-plan-archetypes-wrapper.sh`, `scripts/test-design-structure.sh`, `skills/shared/topology.tsv`.

## Scope-anchor-first scouting

Plan review callers pass the staged issue scope anchor through the existing `--description-file` flag. Dynamic archetype scouting should compare the current plan against that anchor; brainstorm-expanded context is non-binding and should not define additional specialist scope.
