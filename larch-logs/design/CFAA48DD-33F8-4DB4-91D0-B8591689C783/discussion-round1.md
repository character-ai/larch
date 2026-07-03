# Discussion Round 1 — issue #6101

## Decision 1: Coverage includes dev-only skills
- **Question**: Does the per-skill readability wiring and lint coverage include dev-only `.claude/skills/*/SKILL.md`, or only public `skills/*/SKILL.md`?
- **Resolution**: All skills. Both public `skills/*/SKILL.md` and dev-only `.claude/skills/*/SKILL.md` get readability directives and lint coverage.
- **Source**: user (explicit mid-run instruction: "It should effect all skills, not just publicly exported")

## Decision 2: Exempt-list posture
- **Question**: Which skills may opt out of the readability directive via the lint exempt list?
- **Resolution**: Minimal exemptions. Only SKILL.md files that are pure redirects with no user-facing prose of their own (candidates after inspection: `alias`, `im`) may be exempted. Every other skill, public and dev-only, gets wired.
- **Source**: user (recommended option auto-accepted after AskUserQuestion timeout; user AFK)

## Decision 3: External-prompt wiring scope
- **Question**: Should this issue also wire `<READABILITY_STYLE>` tokens into other skills' external-agent prompts (reviewer templates, /research prompts)?
- **Resolution**: No. Catalog-wide wiring is orchestrator-inline directives at skill entry or main prose-composition steps. External-prompt token expansion stays where it exists today (/design brainstorm-prompts, plan-review). Other skills' external prompts become OOS follow-up candidates.
- **Source**: user (recommended option auto-accepted after AskUserQuestion timeout; user AFK)

## Decision 4: Path form per skill tier
- **Question**: What path form do readability directives use in each skill tier?
- **Resolution**: Public `skills/*/SKILL.md` and their references use `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`. Dev-only `.claude/skills/*/SKILL.md` use `$PWD/skills/shared/readability-style.md`.
- **Source**: codebase (`.claude/rules/skill-runtime-root-paths.md`)

## Decision 5: Authority file moves to shared scope, no shims
- **Question**: Where does the canonical style file live after this change?
- **Resolution**: `skills/shared/readability-style.md`. The `skills/design/references/` copy is removed, not shimmed. Every referrer is repointed: /design SKILL.md and references, `python/larch/design/design_step2b.py`, the default path in `python/larch/rendering/rendering.py`, `python/larch/implement/checks_run_relevant.py`, the lint manifest, tests, fixtures, Makefile rows.
- **Source**: feature description (issue #6101, Proposed fix item 1) + Step 0c grep of live referrers

## Decision 6: Hard constraints
- **Question**: What must not break?
- **Resolution**: (a) Machine-parsed surfaces stay byte-stable: `KEY=value` grammars, plan grammar, vote tables, manifests. (b) AGENTS.md stays under the tier1a-size budget; pointer approach, not bullet restoration. (c) Style axes and precedence in readability-style.md stay as defined today; "When unsure how short to go: go shorter" is restored in the shared file. (d) No grammar distortion (no Caveman compression). (e) `scripts/test-design-structure.sh` line 517 anchor prohibition is dropped and lines 514-516 updated; harnesses stay green.
- **Source**: feature description (Trade-offs, Acceptance criteria) + codebase (test-design-structure.sh:514-517)

## Decision 7: Anti-erosion guard shape
- **Question**: What guards prevent silent re-erosion?
- **Resolution**: (a) Floor assertion: sum of manifest expected_count values must stay at or above a committed floor constant. (b) Every-skill coverage check: each SKILL.md (public and dev-only) carries a readability directive or an explicit exempt-list entry. (c) Lowering the floor or adding an exemption requires an explicit diff line.
- **Source**: feature description (Proposed fix item 5), refined by Decision 1 (dev-only included)

7 decisions resolved (2 from user, 5 from feature description/codebase).
