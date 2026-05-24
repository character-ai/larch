## Decision 1: Refactor approach
- **Question**: Which approach (Approach 1 extract / Approach 2 trim / Approach 3 split / combination) should the refactor take?
- **Resolution**: Combine Approach 1 (extract Conventions to a separate file) AND Approach 2 (trim duplicated prose). With critical caveat: extraction is conditional on empirical validation of cross-agent include semantics — if no include syntax works for all three agents, fall back to Approach 2 alone.
- **Source**: user

## Decision 2: Cross-agent compatibility constraint
- **Question**: Is AGENTS.md consumed by anything other than CLAUDE.md's `@AGENTS.md` import?
- **Resolution**: Yes. AGENTS.md is consumed natively by multiple agent runtimes: Claude (via CLAUDE.md `@AGENTS.md`), Codex (via `--add-dir "$PWD"` sandbox — reads repo-root AGENTS.md natively per `scripts/launch-codex-implement.md`), Cursor (also reads repo-root AGENTS.md), and Gemini (via `GEMINI.md` containing a single `@./AGENTS.md` line). Any extracted file referenced from AGENTS.md must be loadable by all four — not just Claude. Codex and Cursor do NOT understand Claude's `@filename` import syntax unless that has been empirically verified.
- **Source**: user

## Decision 3: Empirical-validation requirement
- **Question**: Can we assume `@filename` imports work across Claude, Codex, and Cursor?
- **Resolution**: No — must be empirically tested. Plan MUST include a step that creates sample files A (with hypothesized include line) and B (with a unique fact), spawns Claude / Codex / Cursor as external subprocess (same mechanism as `/implement` reviewers via `launch-claude-subprocess.sh` / `launch-codex-implement.sh` / `launch-cursor-implement.sh` or analogous review launchers), and asks each whether it automatically knows B's fact. Only agents that DEMONSTRATE auto-loading get to keep extraction; for any agent that fails, the plan must either pick a different syntax or fall back to Approach 2.
- **Source**: user

## Decision 4: Acceptance criteria
- **Question**: What size target and lint guarantees apply?
- **Resolution**: AGENTS.md ≤ 11000 chars after refactor (per issue acceptance — leaves ~1000 chars buffer for future growth). `make lint` must pass. Existing structure/anchor tests (`test-design-structure`, `test-implement-structure`, etc.) must still pass — no anchor breakage. Semantic content must be preserved (no factual changes to existing guidance, only re-organization and de-duplication).
- **Source**: user / issue body

## Decision 5: Out-of-scope
- **Question**: What is NOT in scope?
- **Resolution**: Out of scope: changes to KARPATHY_CLAUDE.md, BASH_AUTHORING.md, CLAUDE.md (other than possibly adding one new `@`-import line if extraction is taken), docs/, README.md, SECURITY.md, SKILL.md files. The refactor touches AGENTS.md, optionally a new `CONVENTIONS.md` (or similar), and optionally CLAUDE.md (one new line).
- **Source**: codebase (issue scope) + inference

5 decisions resolved.
