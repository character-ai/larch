## Proposed Design Outline

### Goals
- Rebalance `review.voters` (the code-review voting panel used by `/review` and `/implement` Step 5) to single-vendor Codex-first: flip the validity voter (slot 1) from Cursor-primary to Codex-primary, matching the already Codex-primary plan-fidelity and pragmatism voters (slots 2/3).
- Every code-review voter now waterfalls Codex, then Cursor, then Claude.
- Keep documentation and same-file default-label mirrors in sync with the new primary vendor.

### Non-goals
- Do not change `design.plan_voters` (the `/design` plan-review voting panel). It stays Claude plus Codex plus Cursor, unchanged.
- Do not change the both-externals-down fallback mechanism. Voter-1 alone already falls back to a single spawned Claude vote today; this already satisfies "no triplicate Claude" and is preserved as-is, not rebuilt.
- Do not touch the `review.panel` (code-quality reviewer) roster, only the `review.voters` (voting) roster.
- Do not change model version defaults (`gpt-5.4-mini`, `composer-2.5`, `claude-sonnet-4-6`). These are already the active defaults through the existing "vote" model-role resolution.

### Approach sketch
- Edit `python/larch/core/config.py`'s `review.voters` `VoterPolicyDefault` for voter-1: flip `primary_tool` cursor to codex, flip `default_label`/`output_name` cursor-validity to codex-validity, reorder `semantic_labels` to lead with codex, and update the role's `doc_fallback` description string.
- Sync the small number of same-file default-label mirrors that duplicate voter-1's old default label as a display fallback (`agent_voters.py` DispatchState default, `review_core_body.py` default-tool tuple, `_voting_calibration.py` fallback dict).
- Update hand-maintained docs that describe today's Cursor-primary validity voter as current fact (`docs/voting-process.md`, `skills/shared/voting-protocol.md`, `docs/run-logs.md`, `docs/external-reviewers.md`).

### Surfaces in scope
- `python/larch/core/config.py`
- `python/larch/agents/agent_voters.py`
- `python/larch/review/review_core_body.py`
- `python/larch/review/_voting_calibration.py`
- `docs/voting-process.md`, `skills/shared/voting-protocol.md`, `docs/run-logs.md`, `docs/external-reviewers.md`
- Existing tests covering these defaults (update expectations, no new test infrastructure)

### Open questions
- None. The one ambiguity found during research (both-down fallback semantics) is resolved in Decision 1 of discussion-round1.md: preserve today's single-Claude-voter mechanism.
