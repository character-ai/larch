## Proposed Design Outline

### Goals
- Reduce Tier-1a autoload byte footprint by in-place prose condensing in AGENTS.md, KARPATHY_CLAUDE.md, and BASH_AUTHORING.md (289 total lines).
- Add a CI ratchet (lint target + CI wire) that hard-caps line counts on the three files, preventing future prose creep.
- Cross-link overlapping AGENTS.md Honesty bullets to KARPATHY §1 instead of restating them.

### Non-goals
- No rule deletions; no semantic changes to any load-bearing instruction.
- No conditional @-imports (separate issue #2241).
- No changes to `description:` fields or SKILL.md bodies (sibling children).
- No restructuring (sections stay in place; only prose inside sections is trimmed).

### Approach sketch
- AGENTS.md: condense Canonical sources inline descriptions; tighten Output Style and Conventions prose; collapse 1–2 Honesty bullets that restate KARPATHY §1 into a single cross-link. Preserve 7 structure-test-pinned token strings verbatim.
- KARPATHY_CLAUDE.md: tighten preamble and trailing summary line; shorten bullet explanations without removing any of the four §§.
- BASH_AUTHORING.md: remove or cross-link the "Residual Bash after E3" section (near-duplicate of AGENTS.md Conventions); condense the wrapped-grep trap explanation in §1.
- CI ratchet: new `python/cli.py lint tier1a-size` verb + Makefile target that fails if any file exceeds a threshold set to current-minus-trim count; wire to CI lint job. Python-only per G-Skill-2.

### Surfaces in scope
- `AGENTS.md`
- `KARPATHY_CLAUDE.md`
- `BASH_AUTHORING.md`
- `python/lint_tier1a.py` (new ratchet implementation)
- `python/test_lint_tier1a.py` (new harness)
- `Makefile` (new lint target `lint-tier1a-size`, test target `test-lint-tier1a-size`)
- `.github/workflows/` (wire ratchet step to CI lint job)

### Open questions
- None.
