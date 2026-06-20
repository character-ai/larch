## Decision 1: Mutation approval model
- **Question**: Should /deps apply issue rewrites and new block-edges autonomously, or propose then apply on approval?
- **Resolution**: Propose, then apply. Show a grouped plan of all rewrites and dependency edges; mutate GitHub only after one operator approval. Matches /combine-issues and /audit-runs norms.
- **Source**: user

## Decision 2: Dependency detection depth
- **Question**: How deep should dependency detection go?
- **Resolution**: Full semantic. LLM-reason over issue pairs to infer latent prerequisite/ordering dependencies, not just explicit cross-references. Writes still gate behind the Decision 1 approval.
- **Source**: user

## Decision 3: REGULAR-issue refresh mode
- **Question**: How aggressively should /deps rewrite stale or inaccurate parts of REGULAR issues?
- **Resolution**: Conservative, edit in place. Fix only parts provably stale or inaccurate vs. latest main; default-keep when uncertain; edit the issue body. Mirrors the /combine-issues per-item actuality check.
- **Source**: user

## Decision 4: Fully-stale REGULAR issues
- **Question**: If a REGULAR issue is entirely stale, rewrite-only or close?
- **Resolution**: Propose closing. Offer to close fully-stale REGULAR issues as "not planned" after approval, like /combine-issues closes fully-stale sources.
- **Source**: user

## Decision 5: Skill placement (public vs dev-only)
- **Question**: Where does /deps live?
- **Resolution**: Public, exported: skills/deps/SKILL.md. The title says "public (exported)". Note: the closest analogs (/combine-issues, /analyze-issues) are dev-only under .claude/skills/; /deps is the first public issue-audit skill, so it must use ${CLAUDE_PLUGIN_ROOT} runtime paths, ship a description with a trigger, and add itself to README/topology.
- **Source**: codebase + feature title

## Decision 6: Issue-state grouping
- **Question**: How are DESIGNING / DESIGNED / IMPLEMENTING / REGULAR sets determined?
- **Resolution**: By title prefix. DESIGNING = `[DESIGNING]`, DESIGNED = `[DESIGNED]`, IMPLEMENTING = `[IMPLEMENTING]`. REGULAR = every other open issue (no in-flight busy prefix). Same scheme /combine-issues filters on.
- **Source**: codebase + feature text

## Decision 7: In-flight dependency handling (the flip rule)
- **Question**: For a desired edge "X blocked by Y" (X depends on Y), what happens when the party that should be blocked is in-flight?
- **Resolution**: Per the feature text. If X is REGULAR, write "X blocked by Y" normally. If X is in-flight (any set but REGULAR), it cannot receive a new blocked-by, so flip: when Y is REGULAR, write "Y blocked by X" (block the potential dependency instead, so the in-flight work lands first). When both X and Y are in-flight, write nothing and emit a loud warning. Skip the flip when it would create a cycle or is otherwise unreasonable ("if reasonable").
- **Source**: feature text

## Decision 8: Dependency expression mechanism
- **Question**: How are new dependencies written?
- **Resolution**: Via /block-issue (native GitHub addBlockedBy). All new edges are expressed through block-issue / `python/cli.py block-issue add-blocked-by` (or `issue add-blocked-by`), never raw gh.
- **Source**: feature text + codebase

## Decision 9: Target repository
- **Question**: Which repo does /deps operate on?
- **Resolution**: The current repository, auto-detected via `gh repo view` / `gh resolve-repo`, with an optional `--repo owner/name` override. Same pattern as /combine-issues.
- **Source**: codebase norm
