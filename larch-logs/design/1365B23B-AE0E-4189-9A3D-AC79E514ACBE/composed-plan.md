## Plan

Extract the verbosity-control rules common to `/design` and `/implement` into one shared anchor. This is a prose-only dedup: no behavior change, no Python or script changes, no topology or manifest registration.

Use the existing lightweight pointer style for the shared anchor only (`Follow shared/verbosity-control.md rules.`); do not use a mandatory `Read and apply` directive for it. The `/design` Step 3 post-notification line is a separate load contract, not a pointer-style anchor; keep it byte-stable.

**Files to modify/create**

### NEW: skills/shared/verbosity-control.md

Create a small shared anchor with:
- Title: `# Verbosity Control`.
- A short intro noting that skill files keep their own preserved/suppressed category lists and step-specific carve-outs.
- The universal rules:
  - Use empty string for the `description` parameter on all Bash tool calls.
  - Use terse 3-5-word descriptions for Agent tool calls.
  - Do not produce explanatory prose between tool outputs beyond the preserved categories listed in the calling skill.
  - Verbosity suppression is prompt-enforced and best-effort.

Do not add this file to `skills/shared/topology.tsv` (existing shared docs carry no row).

### UPDATED: skills/design/SKILL.md

In `### Verbosity Control`:
- Replace the first two bullets (empty Bash `description`, terse Agent `description`) with `Follow shared/verbosity-control.md rules.`
- Replace the current third bullet with a design-local `**Only print:** ...` line that keeps the exact current category list.
- Keep the `**Suppressed output:**` line, including the sentence that architecture diagram content is issue-only via `larch:diagrams`.
- Keep `**Compact reviewer status table**`.
- Keep `**Post-notification for Step 3 waits**` and its existing load-contract line unchanged: `Read and apply ## Step 3 post-notification sequence in ${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md for the detailed reviewer-status-table emit contract.` Do not collapse it to a `Follow ...` pointer or a bare `skills/shared/design-background-wait.md` substring.
- Remove the local `**Limitation**` closer; the shared file now owns the short closer.

### UPDATED: skills/implement/SKILL.md

In `### Verbosity Control`:
- Replace the compact one-line universal rule sentence with `Follow shared/verbosity-control.md rules.`
- Keep the `**Preserved:**` and `**Suppressed:**` lists unchanged.
- Remove the local closer `Verbosity suppression is prompt-enforced and best-effort; may degrade in very long sessions.` Do not preserve the long-session clause; the shared closer is the short form.

**Edge cases**

- The `/design` architecture-diagram suppression line is pinned by `scripts/test-design-structure.sh`. Do not move it to the shared file.
- The `/design` Step 3 post-notification load contract is pinned by `scripts/test-implement-anti-polling-rule.sh`. Keep `**Post-notification for Step 3 waits**` in the Verbosity Control section with the exact `Read and apply ## Step 3 post-notification sequence` literal within eight lines of that header. Do not replace it with pointer-style wording.
- Do not move skill-specific Preserved, Suppressed, or Only print categories into the shared file.
- Do not turn the shared verbosity anchor into a mandatory read. The goal is always-loaded line savings for the common rules only.

**Failure modes**

- If `/design` loses the architecture-diagram suppression literal, `make test-design-structure` fails.
- If `/design` collapses the Step 3 post-notification line to a `Follow ...` pointer or drops the `Read and apply ## Step 3 post-notification sequence` literal from within eight lines of `**Post-notification for Step 3 waits**`, `make test-implement-anti-polling-rule` fails.
- If the shared file becomes too broad, it can blur skill-specific output categories and change orchestrator behavior.

**Testing strategy**

Run `make test-design-structure`, `make test-implement-structure`, `make test-implement-anti-polling-rule`, and `make lint`. No test edits are expected. If a test fails, first restore the pinned literals in the SKILL.md files before considering any harness change.

## Acceptance

- `skills/shared/verbosity-control.md` exists with the three universal rules (empty Bash `description`; terse 3-5-word Agent `description`; no prose between tool outputs beyond each skill's listed categories) and the short closer `Verbosity suppression is prompt-enforced and best-effort.`
- `skills/design/SKILL.md` Verbosity Control references the shared anchor via `Follow shared/verbosity-control.md rules.` and keeps its `Only print:` list, `Suppressed output:` line (with the `larch:diagrams` sentence), Compact reviewer status table, and `Post-notification for Step 3 waits` block byte-stable.
- `skills/implement/SKILL.md` Verbosity Control references the shared anchor via the same pointer, keeps its Preserved/Suppressed lists, and no longer carries the `; may degrade in very long sessions` clause.
- Each SKILL.md Verbosity Control body is ~7-10 always-loaded lines shorter.
- `make test-design-structure`, `make test-implement-structure`, `make test-implement-anti-polling-rule`, and `make lint` pass with no harness edits.

review_status: complete
rounds_completed: 2
diff_lines: 19
