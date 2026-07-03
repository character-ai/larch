## Proposed Design Outline

### Goals
- Restore forced readability loads at every prose-composition site, across all skills.
- Promote the authority file to `skills/shared/readability-style.md`; one source, no shims.
- Add anti-erosion lint: per-skill coverage, explicit exempt list, count floor.

### Non-goals
- No `<READABILITY_STYLE>` token wiring for non-design external prompts (OOS follow-ups).
- No style-axis or precedence changes; no grammar distortion.
- No restyling of machine-parsed surfaces; byte-stable grammars stay untouched.

### Approach sketch
- Move the authority file; repoint every referrer: /design SKILL.md, references, Python, tests, Makefile.
- Restore bold anchors at /design composition sites (Step 2b, design-outline.md, finalize-step5.md); raise TSV counts; drop the test-design-structure.sh anchor prohibition.
- Wire one directive per skill: public skills via `${CLAUDE_PLUGIN_ROOT}`, dev-only via `$PWD`.
- Extend `lint readability-preamble`: coverage walk of `skills/` and `.claude/skills/`, exempt list, floor assertion.
- Repoint AGENTS.md Output Style at the shared file; keep chat-only rules; narrow the template exemption.

### Surfaces in scope
- `skills/shared/readability-style.md` (new home); every `skills/*/SKILL.md` and `.claude/skills/*/SKILL.md`
- `skills/design/SKILL.md` and references; `skills/implement/SKILL.md` and `execution-issues-tracking.md`
- `python/larch/lint/lint_readability_preamble.py`; `scripts/lint-readability-preamble.tsv` and `.tsv.md`; lint tests
- `python/larch/design/design_step2b.py`; `python/larch/rendering/rendering.py`; `python/larch/implement/checks_run_relevant.py`
- `scripts/test-design-structure.sh`; `AGENTS.md`; `Makefile`

### Open questions
- Exempt-list seed: confirm `alias` and `im` are the only pure-redirect skills after inspection.
