## Proposed Design Outline

### Goals
- Restore OOS to the code-review vote in `/implement` so `[OUT_OF_SCOPE]` findings are adjudicated by the panel instead of silently dropped pre-vote.
- Loosen the OOS acceptance rubric to a "legitimacy" standard for both `/implement` and `/design` voters; still auto-reject pure style/noise/speculation.
- Roll every vote-accepted OOS item into exactly one unifying `[OOS]` issue per run in both skills; no post-vote materiality/count filing gate.

### Non-goals
- Do NOT remove the bundled nit-pruning step; only the OOS-drop gate is removed (user decision).
- Do NOT remove the #6291 design aggregate-severity OOS promotion pool; keep as-is (user decision).
- Do NOT change acceptance for regular in-scope (non-OOS) findings, nor file empty `[OOS]` issues; keep semantic dedup.

### Approach sketch
- `/implement`: delete `_apply_pre_vote_oos_gate` + `PreVoteOosGateResult` plumbing so `_prune_nit_then_pre_vote_gate` prunes nits but no longer strips OOS; OOS rides the ballot in all three branches (normal, validation-exhausted, empty-merge).
- Rubric: rewrite `skills/shared/oos-acceptance-rubric.md` to legitimacy and propagate to every "Update triggers" surface (rendering voter/proposal text, both SKILL.md notes, review-acceptance-rubric.md).
- Report: repurpose `render_dropped_oos_candidate_section` to list voted-and-rejected OOS (source from rejected findings, not `oos-dropped-before-vote.md`); update `run_log_batch.py` projection.
- Filer: confirm `file_oos.py` (`OOS_ISSUES_PER_RUN_CAP=1`) yields exactly one issue with no residual small-batch suppression.
- `/design`: confirm loosened rubric flows through `plan_review_round`/`tally` -> `oos-accepted-design.md` -> Step 5b `/larch:issue` (no gate to remove).

### Surfaces in scope
- `python/larch/review/`: `review_core_body.py`, `review_pipeline.py`, `review_pipeline_shared.py`
- `skills/shared/`: `oos-acceptance-rubric.md`, `review-acceptance-rubric.md`, `voting-protocol.md`
- `python/larch/rendering/rendering.py`; `skills/implement/SKILL.md`, `skills/design/SKILL.md`
- `python/larch/report/review_phase_detail.py`, `run_log_batch.py`; `python/larch/issue/file_oos.py`, `oos_filer.py` (confirm)
- Tests: `tests/review/test_review_pipeline.py`, `tests/report/test_review_phase_detail.py`, design tally tests; new "accepted OOS -> one issue" coverage. Docs: `docs/run-logs.md`, `docs/voting-process.md`

### Open questions
- None. (Both scope forks resolved in Step 1c: keep nit-pruning, keep #6291 pool.)
