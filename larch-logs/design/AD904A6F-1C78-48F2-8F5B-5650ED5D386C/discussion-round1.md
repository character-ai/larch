## Decision 1: Architecture diagram destination on the GitHub issue
- **Question**: Where should /design place the architecture diagram on the issue?
- **Resolution**: As a separate `larch:diagrams` summary comment on the tracking issue (NOT embedded in the larch:plan body block; NOT both).
- **Source**: user

## Decision 2: /implement architecture references
- **Question**: Should /implement keep generating/embedding the architecture diagram anywhere (PR body, larch:diagrams comment)?
- **Resolution**: Remove all architecture-generation references from /implement: drop the Architecture Diagram section from `pr-body-template.md`; `step-7a.sh` compose_summary_diagrams no longer GENERATES architecture content; `ship-pr.sh` stops reading `ARCHITECTURE_DIAGRAM_FILE`. /design owns architecture-diagram generation end-to-end. /implement's `larch:diagrams` comment upsert must PRESERVE the Architecture section that /design wrote (read existing comment body, keep Architecture, merge in new Code Flow). This reconciles "remove generation" with "preserve when upserting".
- **Source**: user

## Decision 3: larch:diagrams comment shared marker
- **Question**: How can /design and /implement upsert the same larch:diagrams comment when each has its own RUN_ID?
- **Resolution**: Use a stable marker `<!-- larch:diagrams v1 -->` (no `runid=` slot) so both /design and /implement upsert the same comment via `tracking-issue-summary.sh upsert-summary`. Document this as an exception in `summary-comment-template.md` (only `larch:diagrams` is shared; `larch:plan` / `larch:metadata` / `larch:final-summary` keep their per-run runid).
- **Source**: codebase (`tracking-issue-summary.sh` matches comments by exact marker on first line)

## Decision 4: Non-architectural plans
- **Question**: What happens when /design Step 3b skips diagram generation (docs-only / non-architectural)?
- **Resolution**: /design does not upsert the larch:diagrams comment at all. /implement, when it runs, finds no existing comment and posts only its own Code Flow content (Architecture section absent or short placeholder). Same behavior as today for the "non-architectural" branch; only the architectural path gains a posting.
- **Source**: codebase (Step 3b non-architectural skip is the existing contract)

## Decision 5: Backward compat with orphan comments
- **Question**: What happens to existing `<!-- larch:diagrams v1 runid=... -->` comments from older /implement runs after the marker changes to stable?
- **Resolution**: Leave existing orphan comments as-is (no migration). Future /implement runs use the stable marker and the orphan stays as historical artifact. This avoids a one-shot migration script. Operators can manually delete orphans if desired.
- **Source**: codebase (tradeoff between rollout cost and orphan cleanup)
