# Design Outline — #6841 (Public routing and pricing documentation)

## Goal
Document the already-merged MODERATE→Cursor `grok-4.5` routing and its pricing in
the two firm-heading docs so the public surface matches the shipped code.

## Non-goals
- No code changes (python/, rate-table values, waterfall roles, topology source/projection).
- No full cost-comparison essay (acceptance wants rates + exemption + default distinction).
- No internal report-tokens bucketing details (`--cursor-grok-*-tokens`, `BUCKETS_cursor_by_model`).
- No topology changes (no Step 2 coder row exists).

## Surfaces
- `docs/external-reviewers.md` — "Implementer (Step 2)" table row + narrative.
- `docs/configuration-and-permissions.md` — `--coder` section, `LARCH_CURSOR_MODEL` global-default note, default-rates section Grok 4.5 row.

## Acceptance (binding)
1. MODERATE documented as Cursor-first with `grok-4.5`.
2. TRIVIAL/HARD documented as Codex-first.
3. `--coder` override documented (reorders the two externals ahead of Claude, every tier).
4. Cursor-unavailable fallback documented (MODERATE falls through to Codex `gpt-5.6-sol`).
5. Grok 4.5 list rates $2.00 / $0.50 / $6.00 per M (input / cache-read / output), Cursor Token Rate surcharge-exempt.
6. Distinction between global Cursor default (`composer-2.5`) and Step 2 MODERATE default (`grok-4.5`).
