## Proposed Design Outline

### Goals
- Remove ~75 always-loaded lines from `skills/design/SKILL.md` by relocating four rare-path or documentation-only bodies to on-entry reference files.
- Preserve all caller pointers, outcome contracts, operator option labels, and happy-path skeletons inline.
- Keep agent-lint G004 scans intact: Wrapper-contract-inventory and Plan-helper-contracts catalogs stay inline.

### Non-goals
- No Python or shell script changes; this is prompt-surface only.
- No refactoring of the four relocated bodies; content moves verbatim.
- No changes to how the bodies behave, only where the text lives.

### Approach sketch
- Create four new `skills/design/references/` files, one per relocated body.
- In SKILL.md, replace each body with a one-line `MANDATORY — READ ENTIRE FILE` pointer.
- For the validator-failure body: keep verbatim option labels (**Fix-and-retry**, **Override**, **Cancel**), Step 5c special-case headings, and the autofix fence inline as a minimal skeleton; move the prose details to the reference.
- For Step 2b.5 rc-handling: keep items 1-2 (fence invocation) and the happy-path breadcrumb inline; move items 3-7 (rc-0 parse, rc-2 error, rc-other error, hard/partition/drift/no-trigger branches) to the reference.
- For the drafter fail-safe: keep the one-line fallback-warning prose inline; move the full "Fail closed when…" paragraph to the reference.
- For the sentinel host table: move the full 14-row table to the reference; keep the introductory paragraph and a one-line MANDATORY READ pointer inline.
- Run `make test-design-structure` before and after to verify no string pins are broken.

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/design/references/sentinel-host-table.md` (new)
- `skills/design/references/step2b-drafter-failsafe.md` (new)
- `skills/design/references/step2b5-rc-handling.md` (new)
- `skills/design/references/validator-failure.md` (new)

### Open questions
- None.
