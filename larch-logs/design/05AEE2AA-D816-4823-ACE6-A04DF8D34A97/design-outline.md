## Proposed Design Outline

### Goals
- Collapse today's two severity vocabularies into one 3-level scale `major > minor > nit` across the enum, reviewer/judge allowed-sets, voting, rendering, and prompts.
- Cut OOS volume and token cost: reviewers emit only `major`/`minor`; a mechanical filter drops any `nit` before the aggregator/ballot; file OOS only when accepted AND a strict-majority of YES voters rate it `major`.
- Hide non-filed OOS from the human report while keeping all audit data (`round-*/oos.md`, classification TSV) for `/fluff-analysis`, `/rejected-analysis`, `/voter-calibration`.

### Non-goals
- No change to the OOS voting thresholds themselves (keep degraded 1/1, 1+/2, 2+/3) or to in-scope acceptance/points logic beyond the severity-vocabulary swap.
- No change to security routing (separate text classifier, not severity-driven).
- No regression of #6028's filing path for `major`/`minor`; only `nit` is cut at source. No new rendered "dropped candidates" section.

### Approach sketch
- Repoint types/constants: `JudgeSeverity={major,minor,nit}`, `HIGH_SEVERITIES={major}`, `_ALLOWED_SEVERITIES` / `_STRUCTURED_GATE_B_SEVERITIES` → unified set; fix dependent constants (`SEVERITY_BLOCKER`, `_AGGREGATE_HIGH_SEVERITIES`, gate-b rank map).
- Reviewer/voter prompts: "emit `major` and `minor` only; never `nit`"; drop `latent`/`uncertain` naming from rubrics.
- Add a mechanical `nit`-drop before the aggregator/ballot (review pipeline / `round_runner`), routing dropped nits to the `oos-dropped-before-vote.md` audit lineage (unrendered).
- OOS file gate: reuse the existing strict-majority-`major` test as an added filing condition on OOS classification.
- Drop the `## Rejected OOS audit` render in `review_phase_detail.py`; keep the underlying data.

### Surfaces in scope
- `python/larch/review/`: `review_types.py`, `voting.py`, `plan_review_gate_b.py`, `review_tally.py`, `round_runner.py`
- `python/larch/research/research_eval.py`; `python/larch/design/design_oos.py`; `python/larch/rendering/rendering.py`; `python/larch/report/review_phase_detail.py`
- Prompts/docs: `skills/shared/reviewer-templates.md` + pre-rendered agent bodies, voter prompts, `review-acceptance-rubric.md`, `oos-acceptance-rubric.md`, `docs/run-logs.md`

### Open questions
- None. Top-tier naming resolved to `major/minor/nit` in Round 1.
