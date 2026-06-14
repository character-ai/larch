## Decision 1: Enrichment location for closed-blocker resolution
- **Question**: Should closed-blocker state enrichment happen in `fetch_deps_main` (filter before planner sees them) or in `plan_inherited_main` (add --repo, call gh per missing blocker)?
- **Resolution**: Enrich in `plan_inherited_main`. Add optional `--repo` arg; when non-empty, resolve each unique blocker number absent from `meta` via `gh issue view <n> --json number,state,title --repo <repo>`. Failed reads stay `unknown` (fail-closed preserved). When `--repo` is empty, skip enrichment and existing behavior is unchanged.
- **Source**: issue (preferred approach), codebase

## Decision 2: New classification bucket name
- **Question**: Is `satisfied` the right name for closed-blocker edges?
- **Resolution**: Yes — `satisfied` (reason: "blocker issue already closed (dependency satisfied)"). Distinct from `safe`, `exception`, `unknown`. Emitted as `satisfied_edges` in plan_inherited output.
- **Source**: issue

## Decision 3: Write behavior for satisfied edges
- **Question**: Should satisfied edges be written to GitHub (add-blocked-by call)?
- **Resolution**: No write. Writing a blocked_by edge to a closed issue is a no-op at best. Satisfied edges appear in `satisfied_edges` output; close_eligible does not penalize sources tied only to satisfied edges.
- **Source**: issue

## Decision 4: Item A (close-stale) scope and interface
- **Question**: Should close-stale be a new CLI verb or a flag on close-sources?
- **Resolution**: New verb `close-stale` with `--issues <csv>`, `--repo`, `--reason <text>`, optional `--comment-file <path>`, optional `--dry-run`. Mirrors close-sources structure. SKILL.md oos-2 gets a branch for the all-items-stale case.
- **Source**: issue, codebase (close_sources_main pattern)

## Decision 5: Item D (apply mapping fragment) output format
- **Question**: What format for SOURCE_TO_COMBINED_JSON_FRAGMENT?
- **Resolution**: JSON object `{"<source1>": <combined>, "<source2>": <combined>}` — same shape as source_to_combined.json entries. Emitted on stdout when --defer-close. SKILL.md oos-5 documents accumulation.
- **Source**: issue, codebase (apply_main output pattern)

## Decision 6: Item C (oos-6c SKILL.md prose) scope
- **Question**: What does oos-6c clarification entail?
- **Resolution**: Update oos-6c to state plainly that the refresh resolves combined-issue-metadata races (newly created host issues not yet in meta), NOT closed-blocker edges. Closed-blocker edges are terminal-satisfied after the primary fix; they never appear as unknown in the first place. Remove the implication that refresh can reclassify closed-blocker unknowns.
- **Source**: issue, SKILL.md oos-6c
