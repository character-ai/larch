## Proposed Design Outline

### Goals
- Augment every `/design` prompt that produces user-accessible output of meaningful size so plan text, outline text, brainstorm/sketch output, and OOS Descriptions are born with three style properties: Strunk & White discipline (active voice, omit needless words), dyslexia-friendly accessibility (short sentences, simpler vocabulary, more bullets/headings), AND brevity (shorter is better — overall artifact length minimized within the precision contract).
- Establish one shared style preamble as the single source of truth so future amendments don't drift across the seven-ish prompt surfaces.
- Always-on across every `/design` run; preserve every code reference (paths, flags, identifiers, fenced code, `### NEW|UPDATED|REWRITTEN:` grammar, `diff_lines:` trailer) byte-stable per Round-1 precision contract.

### Non-goals
- No post-hoc rewriter, validator, or protected-span tokenizer; no new `ACTION` in `design-driver.sh`; no new step in the `/design` pipeline.
- No "original vs simplified" duality — one canonical version of every artifact.
- No amendments to `/research`, `/implement`, `/review`, or other skills (scoped to `/design` only).
- Not amending short orchestrator-generated texts in v1 (e.g., `AskUserQuestion` option labels / descriptions) — open question below.

### Approach sketch
- Introduce one shared style preamble file (`skills/design/references/readability-style.md`) defining the three style axes (Strunk & White, dyslexia-friendly, brevity) and the precision-contract carve-outs (code fences, backticks, plan grammar, `diff_lines:` trailer all byte-stable). Resolve apparent tension between dyslexia-friendly chunking (more bullets/headings) and brevity (shorter total bytes) by giving operators explicit precedence: code references > meaning > brevity > dyslexia-friendly chunking > Strunk & White micro-rewrites. The preamble names this order so contributors don't pick a side later.
- Amend SKILL.md step bodies where the orchestrator (Claude) writes user-facing text — at minimum: Step 1d.5 brainstorm-synthesis body, Step 1d.7 outline body, Step 2b plan-drafting body, Step 3b architecture-diagram body, Step 4 rejected-findings printout body, Step 5c `composed-plan.md` composition body. Each amendment instructs the orchestrator to read and apply the preamble before composing.
- Amend external-agent prompt reference files (`brainstorm-prompts.md`, `sketch-prompts.md` for HARD, `dialectic-debate.md` for HARD, `plan-review.md`, `discussion-rounds.md`) so each agent prompt includes the preamble verbatim via substitution token or explicit "READ THIS FIRST" link.
- Cover OOS scope (Round-1 Decision 6) by amending the same reviewer-prompt surface that produces OOS Description fields — no separate Step 5b helper.
- Add a CI / pre-commit lint asserting every amendment site references the preamble so future contributors don't silently drift one prompt out of style.

### Surfaces in scope
- `skills/design/SKILL.md` — step bodies at 1d.5, 1d.7, 2b, 3b, 4, 5c.
- `skills/design/references/design-outline.md`.
- `skills/design/references/brainstorm-prompts.md`.
- `skills/design/references/sketch-prompts.md` (HARD only).
- `skills/design/references/dialectic-debate.md` (HARD only).
- `skills/design/references/plan-review.md`.
- `skills/design/references/discussion-rounds.md`.
- New: `skills/design/references/readability-style.md`.
- New: a lint / pre-commit hook (e.g., entry in `Makefile` + `scripts/lint-readability-preamble.sh`) verifying preamble references at every amendment site.

### Open questions
- Preamble location: `skills/design/references/` (locality) vs `skills/shared/` (so `/research` reports or other skills could reuse later). Recommend `skills/design/references/` for v1 and promote to `skills/shared/` later if reuse emerges.
- Inclusion mechanism: literal substitution token (e.g., `<READABILITY_STYLE>`) embedded at render time vs explicit "MANDATORY — READ THIS FILE" link directive in each prompt. Recommend substitution token for external-agent prompts (no extra round trip) and read-directive for orchestrator-inline writing (orchestrator already reads `.md` references).
- Whether `AskUserQuestion` option labels / descriptions get amended in v1 or deferred. Recommend deferred (already short, low ROI).
