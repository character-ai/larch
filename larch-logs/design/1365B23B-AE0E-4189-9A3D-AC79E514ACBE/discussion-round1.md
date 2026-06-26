## Decision 1: Shared closer text
- **Question**: The two closers are not identical (design ends "...best-effort."; implement adds "; may degrade in very long sessions."). What is the shared closer?
- **Resolution**: Shared file uses the short closer "Verbosity suppression is prompt-enforced and best-effort." Drop implement's "; may degrade in very long sessions." clause.
- **Source**: user

## Decision 2: How each SKILL.md references the shared core
- **Question**: How should each skill pull in the shared core so the "always-loaded lines" savings are realized?
- **Resolution**: Lightweight pointer line in each always-loaded SKILL.md body (matches the existing `Follow shared/progress-reporting.md rules.` precedent). Not a mandatory Read-and-apply directive.
- **Source**: user

## Decision 3: Shared core scope
- **Question**: What moves into skills/shared/verbosity-control.md vs. stays per-skill?
- **Resolution**: Shared file holds only the universal rules: empty `description` on Bash calls; terse 3-5-word `description` on Agent calls; no explanatory prose between tool outputs beyond each skill's own listed categories; plus the short closer. Each skill keeps its own Preserved/Suppressed category lists.
- **Source**: issue + codebase

## Decision 4: Design-specific carve-outs stay in design SKILL.md (hard constraint)
- **Question**: Which design Verbosity Control content must NOT move to the shared file?
- **Resolution**: design keeps its `Only print:` category enumeration, the `Suppressed output:` line (including `architecture diagram content is issue-only via larch:diagrams`), the `Compact reviewer status table` carve-out, and the `Post-notification for Step 3 waits` pointer. test-design-structure.sh:231 pins the architecture-diagram line in design SKILL.md; test-implement-anti-polling-rule.sh pins `Post-notification for Step 3 waits` with the `skills/shared/design-background-wait.md` reference and `Read and apply ## Step 3 post-notification sequence` within 8 lines after the anchor. These must remain in design SKILL.md.
- **Source**: codebase (hard constraint)

## Decision 5: No manifest / topology registration
- **Question**: Does adding skills/shared/verbosity-control.md require a topology.tsv row or other registry entry?
- **Resolution**: No. Existing skills/shared/*.md docs (progress-reporting.md, design-background-wait.md, etc.) carry no topology.tsv row; the new file follows the same skills/shared/*.md canonical-doc convention (title + intro + rules).
- **Source**: codebase

## Decision 6: Tests and lint (must-have)
- **Question**: What verifies done?
- **Resolution**: `make test-design-structure`, `make test-implement-structure`, `make test-implement-anti-polling-rule`, and `make lint` must pass. Pinned literals stay in their SKILL.md files, so no test edits are expected; verify and only touch tests if a pin genuinely moved.
- **Source**: issue + codebase

## Non-goals
- Do not change verbosity behavior; this is pure extraction/dedup of prose.
- Do not touch other skills (review, research) — surface is design + implement + the new shared file only.
