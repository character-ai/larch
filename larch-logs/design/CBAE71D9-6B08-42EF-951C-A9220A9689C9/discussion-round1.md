# Discussion Round 1 — #6841 (Public routing and pricing documentation)

Partition Piece 4 of 4 split from #6825. Docs-only: the sibling code pieces
(1–3) are already merged at HEAD (verified in working repo):

- `CODER_TOOL_ORDER_BY_DIFFICULTY` (config.py:312) — MODERATE `("cursor","codex","claude")`.
- `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` (config.py:317) — MODERATE `grok-4.5`.
- `("cursor","grok-4.5")` rate row (report_tokens_cost.py:71) — surcharge-exempt.

## Decision 1: Topology projection scope
- **Question**: Does the generated topology (`skills/shared/topology.tsv` / `docs/topology.md`) need to change for this piece?
- **Resolution**: No. `topology.tsv` (21 source rows) and `docs/topology.md` contain no `implement.step2_coder` / Step 2 implementer row, so the projection does not cover the Step 2 coder and does not change. Editing only the two firm-heading docs.
- **Source**: codebase

## Decision 2: Pricing-rationale depth in docs
- **Question**: How much of the original cost rationale (volume analysis, 22%-cheaper comparison) belongs in user-facing docs?
- **Resolution**: Acceptance criteria call for the Grok 4.5 list rates ($2.00 / $0.50 / $6.00 per M input / cache-read / output) and the Cursor Token Rate surcharge exemption only — not the full cost-comparison essay. Keep doc prose to rates + exemption + the global-vs-Step-2-MODERATE default distinction.
- **Source**: codebase (acceptance criteria)

## Hard constraints / non-goals
- **Must not change**: any code under `python/`, the rate-table values, the `_waterfall_role` definitions, or the topology source/projection. This piece edits Markdown only.
- **Firm headings**: `docs/external-reviewers.md`, `docs/configuration-and-permissions.md`.
- **Non-goal**: documenting the internal `--cursor-grok-*-tokens` bucketing / `BUCKETS_cursor_by_model` split — that is a report-tokens implementation detail, not called out in acceptance criteria.

Recorded 2 decisions resolved.
