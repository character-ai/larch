# scout-plan-archetypes-wrapper.sh

**Purpose**: `/design` Step 3 scout — derives `--scope-files` from the plan’s Files-to-modify headings, invokes `scripts/scout-dynamic-archetypes.sh` in description mode with the plan-review prompt override (forwarding `--codex-present` / `--cursor-present`), then post-filters reserved slugs (`arch`, `edge`, `innovation`, `pragmatic`, `requirements`) and enforces cap 6.

**Primary callers**: `skills/design/SKILL.md` Step 3.

**Stdout KVs**: `SCOUT_STATUS`, `SCOUT_MANIFEST`, `SCOUT_ARCHETYPE_COUNT` (post-filter count).

**Harness**: `skills/design/scripts/test-scout-plan-archetypes-wrapper.sh`.

**Edit in sync**: this file, `scout-plan-archetypes-wrapper.sh`, `scout-plan-archetypes-prompt.txt`, `scripts/scout-dynamic-archetypes.sh` / `.md`, `skills/design/scripts/test-scout-plan-archetypes-wrapper.sh`, `scripts/test-design-structure.sh`, `skills/shared/topology.tsv`.
