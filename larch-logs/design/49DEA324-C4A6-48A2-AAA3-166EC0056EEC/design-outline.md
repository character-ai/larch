## Proposed Design Outline

### Goals
- Add per-role Codex model routing: reviews, votes, and fixes use cheap `gpt-5.4-mini`; the Step 2 implementer keeps strong `gpt-5.5`.
- Cut Codex cost on the review/vote/fix hot paths, serving cost-reduction umbrella #5278.

### Non-goals
- No change to the Step 2 Codex implementer model; it stays strong.
- No change to brainstorm; it stays on the strong key.
- No Mini on Cursor; Cursor reviewers and the validity voter stay on `composer-2.5`.

### Approach sketch
- Add three cheap-bucket env keys (`LARCH_CODEX_REVIEW_MODEL`, `LARCH_CODEX_VOTE_MODEL`, `LARCH_CODEX_FIX_MODEL`, default `gpt-5.4-mini`) in `config.py`; resolve per role in `agents.py`.
- Per-role keys win for their roles even when a global `LARCH_CODEX_MODEL` is set.
- Tag each `resolve_model_args("codex", ...)` call site by role: review, vote, fix, implement.
- Remove the #4062 round-2+ "one generic Codex" collapse so Codex runs full specialists every round.
- Move pragmatism and plan-fidelity voters to Codex with Cursor fallback; fix-appliers, the pricing row, docs, and tests follow.

### Surfaces in scope
- `python/config.py`, `python/agents.py` (keys + resolver)
- `python/plan_review.py`, `python/review_pipeline.py` (reviewers every round + role tags)
- voter dispatch and `render voter` (two voters to Codex + fallback)
- `python/review_and_fix.py`, `python/plan_quality.py` (fix-appliers)
- `python/report_tokens_cost.py` (pricing row); `docs/configuration-and-permissions.md`, `docs/external-reviewers.md`; same-PR tests + parity audit

### Open questions
- Confirm the three env key names at Gate C; otherwise none.
