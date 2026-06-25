## Decision 1: Both review panels are in scope
- **Question**: Inject guidelines into one panel or both (plan-review design Step 3 + code-review implement Step 5)?
- **Resolution**: Both. Plan-review panel (design Step 3) and code-review panel (implement Step 5) per the issue.
- **Source**: issue

## Decision 2: Code-review reach
- **Question**: The code-review reviewer prompt renders through one shared path used by implement Step 5 AND standalone /review (diff + description). How wide should injection reach?
- **Resolution**: All code-review surfaces. Inject once at the shared renderer (`render specialist`); both implement Step 5 and standalone /review receive the guidelines.
- **Source**: user

## Decision 3: Evaluation framing
- **Question**: Content-only, or explicit instruction?
- **Resolution**: Explicit criterion. Append the untrusted guideline entries PLUS a short instruction telling reviewers they may flag guideline deviations as normal findings.
- **Source**: user

## Decision 4: Absence / empty / invalid behavior
- **Question**: What do reviewers receive when ARCHITECTURAL_GUIDELINES.md is absent, invalid, or has no parseable entries?
- **Resolution**: No-op. Inject nothing. Mirror the existing `read_main` / drafter behavior: emit the block only when `status == present` and `content` is non-empty.
- **Source**: codebase (`python/architectural_guidelines.py` `read_guidelines` / `read_main`)

## Decision 5: No new voting / finding category
- **Question**: Does a guideline-deviation finding need a new category or voting path?
- **Resolution**: No. It flows through existing finding/voting/acceptance machinery like any other finding (maps naturally to the architecture category).
- **Source**: issue + codebase

## Hard constraint A: Entries stay aspirational and non-binding
- Entries cannot override AGENTS.md, skills, or the approved plan.
- For plan review, inject as a SEPARATE untrusted block, distinct from the binding `## Binding issue scope anchor` block. Frame it as aspirational, non-binding context.
- **Source**: issue acceptance criteria

## Hard constraint B: Reuse the established machinery
- Reuse `architectural_guidelines.read_guidelines()` + `issue_wire.emit_untrusted_content_block(tag="architectural_guidelines", text=...)`.
- Consult ARCHITECTURAL_GUIDELINES.md only through the reader; never auto-edit the file.
- **Source**: issue + AGENTS.md

## Hard constraint C: Render-cache key must include guidelines content
- `render specialist` caches prompts keyed by input SHAs (`LARCH_RENDER_CACHE_DIR`). Any injected guidelines content must enter the cache key (or invalidate it) so a guidelines change does not serve a stale cached prompt.
- **Source**: codebase (`python/rendering.py` `render_specialist_main` cache key)

## Non-goals
- Do NOT inject into /research reviewers (`render reviewer`), the design drafter (Step 2b/1d.7 already consults guidelines), or Gate C `present-note` (already consults guidelines). Scope is the independent review panels only.
- Do NOT add a new voting category, threshold, or acceptance path.
- Do NOT change ARCHITECTURAL_GUIDELINES.md content.
